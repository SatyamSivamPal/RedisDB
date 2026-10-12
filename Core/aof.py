from Config import config
from logger import logger
from Core.store import store
from Core.store import Obj
from Core import resp
import os
import copy
import multiprocessing
from multiprocessing import Process
import select

rewriteProcess: Process | None = None
rewriteBuffer: list[bytes] = []
isRewriting: bool = False
notifyReadFD: int | None = None
notifyWriteFD: int | None = None
tempFile = config.AOFFile  + ".tmp"

def AppendAOF(command: list[str]) -> None:
    global rewriteBuffer

    encode = resp.Encode(command, False)
    with open(config.AOFFile, "ab") as fp:
        fp.write(encode)
        fp.flush()

    if isRewriting:
        rewriteBuffer.append(encode)

def dumpKey(fp, key: str, obj: Obj):
    fp.write(resp.Encode(["SET", key, obj.value], False))

    if obj.expiresAt != -1:
        fp.write(resp.Encode(["PEXPIREAT", key, obj.expiresAt], False))

def DumpSnapShot(snapshot: dict[str, Obj], tempFile: str, read_fd: int, write_fd: int) -> None:
    try:
        os.close(read_fd)
        with open(tempFile, "wb") as fp:
            for key, obj in snapshot.items():
                dumpKey(fp, key, obj, )

            fp.flush()
            os.fsync(fp.fileno())

        os.write(write_fd, b"S")
        logger.info("AOF snapshot written successfully")

    except BaseException:
        try:
            os.write(write_fd, b"E")
        except OSError:
            pass
        raise

    finally:
        try:
            os.close(write_fd)
        except OSError:
            pass

def BGRewriteAOF() -> bool:
    global rewriteProcess, rewriteBuffer, isRewriting, notifyReadFD, notifyWriteFD

    if isRewriting:
        return False

    #snapshot taken of the store dataset and also maintain 
    #that only epoll event or main process only update the store
    snapshot: dict[str, Obj] = copy.deepcopy(store)
    rewriteBuffer = []
    isRewriting = True
    read_fd = None
    write_fd = None

    try:
        read_fd, write_fd = os.pipe()
        context = multiprocessing.get_context("fork")

        process = context.Process(
            target= DumpSnapShot,
            args=(snapshot, tempFile, read_fd, write_fd)
        )

        process.start()

        os.close(write_fd)
        write_fd = None

        notifyReadFD = read_fd
        notifyWriteFD = None
        rewriteProcess = process
        epollFD = config.epollFD

        epollFD.register(notifyReadFD, select.EPOLLIN)
        logger.info("Background AOF rewrite started...")
        return True
        
    except Exception:
        logger.exception("Could not start AOF rewrite")

        if read_fd is not None:
            try:
                os.close(read_fd)
            except OSError:
                pass

        if write_fd is not None:
            try:
                os.close(write_fd)
            except OSError:
                pass

        notifyReadFD = None
        notifyWriteFD = None
        rewriteProcess = None
        isRewriting = False
        rewriteBuffer = []

        return False

def FinishRewrite() -> bool:
    global rewriteProcess, rewriteBuffer, isRewriting, notifyReadFD

    fd = notifyReadFD
    process = rewriteProcess
    epollFD = config.epollFD

    try:
        if fd is None or process is None:
            return False
        try:
            epollFD.unregister(fd)
        except OSError:
            pass

        status = os.read(fd, 1)
        os.close(fd)
        notifyReadFD = None

        process.join()

        if(status != b"S" or process.exitcode != 0 or not os.path.exists(tempFile)):
            logger.error("Background rewrite failed")
            if os.path.exists(tempFile):
                os.remove(tempFile)

            return False

        with open(tempFile, "ab") as fp:
            for payload in rewriteBuffer:
                fp.write(payload)

            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tempFile, config.AOFFile)
        logger.info("Background AOF rewrite completed successfully...")
        return True
    
    except Exception:
        logger.exception("Error while finalizing the AOF rewrite")
        if os.path.exists(tempFile):
            try:
                os.remove(tempFile)
            except OSError:
                pass
        return False

    finally:
        isRewriting = False
        rewriteBuffer = []
        rewriteProcess = None
        notifyReadFD = None
