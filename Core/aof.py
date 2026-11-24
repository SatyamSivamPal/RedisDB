from Config import config
from logger import logger
from Core.store import Obj
from Core import resp
from Core.cmd import RedisDB
import os
import copy
import multiprocessing
from multiprocessing import Process
import select
import time

rewriteProcess: Process | None = None
rewriteBuffer: list[bytes] = []
isRewriting: bool = False
notifyReadFD: int | None = None
notifyWriteFD: int | None = None
tempFile = config.AOFFile  + ".tmp"

#Append a command to the AOF file. Every command is prefixed with a SELECT 
#so that redis will know which logical database it belongs to.
def AppendAOF(dbIndex: int, command: list[str]) -> None:
    global rewriteBuffer

    selectCommand = resp.Encode(["SELECT", str(dbIndex)], False)
    commandPayLoad = resp.Encode(command, False)
    payload = selectCommand + commandPayLoad

    with open(config.AOFFile, "ab") as fp:
        fp.write(payload)
        fp.flush()

    if isRewriting:
        rewriteBuffer.append(payload)

def dumpKey(fp, key: str, obj: Obj, expiryTime: int | None) -> None:
    fp.write(resp.Encode(["SET", key, obj.value], False))

    if expiryTime is not None:
        fp.write(resp.Encode(["PEXPIREAT", key, obj.ExpiresAt], False))

#child process which work is to write the snapshot of all the databases.
def DumpSnapShot(snapshot: list[RedisDB], tempFile: str, read_fd: int, write_fd: int) -> None:
    try:
        os.close(read_fd)
        currentTime = int(time.time() * 1000)
        with open(tempFile, "wb") as fp:
            for dbIndex, db in enumerate(snapshot):
                fp.write(resp.Encode(["SELECT", str(dbIndex)], False))
                for key, obj in db.store.items():
                    expiryTime = db.expires.get(key)
                    #Skips the key that have been expired 
                    if expiryTime is not None and expiryTime <= currentTime:
                        continue

                    dumpKey(fp, key, obj, expiryTime)
                    
            fp.flush()
            os.fsync(fp.fileno())

        #Notify parent process that snapshot is ready
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

#Start the background AOF rewrite
def BGRewriteAOF(databases: list) -> bool:
    global rewriteProcess, rewriteBuffer, isRewriting, notifyReadFD, notifyWriteFD

    if isRewriting:
        return False

    #snapshot taken of the store dataset and also maintain 
    #that only epoll event or main process only update the store
    snapshot: list[RedisDB] = copy.deepcopy(databases)
    rewriteBuffer = []
    isRewriting = True
    read_fd = None
    write_fd = None

    try:
        #create notification pipe read_fd = parent process will read
        #write_fd = child process will write on that pipe
        read_fd, write_fd = os.pipe()
        context = multiprocessing.get_context("fork")

        process = context.Process(
            target= DumpSnapShot,
            args=(snapshot, tempFile, read_fd, write_fd)
        )

        #trigering the child process with function name DumpSnapShot
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

#Called the parent process when child process sent its completion notifications
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
