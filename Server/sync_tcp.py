from logger import logger
from typing import Any
from Config import config
import socket
from Core import resp, cmd, eval

def toArrayString(data: list[Any]) -> tuple[list[str], ValueError | None]:
    res:list[str] = [None] * len(data)

    for i in range(len(data)):
        res[i] = str(data[i])

    return res, None

def readCommands(clientSocket: socket.socket) -> tuple[cmd.RedisCmds | None, Exception | None]:
    buffer = bytearray()
    chunk = clientSocket.recv(512)

    if not chunk:
        return None, None

    buffer.extend(chunk)
    values, err = resp.Decode(buffer)
    if err is not None:
        return None, err

    cmds: list[cmd.RedisCmd] = []
    for value in values:
        tokens, err = toArrayString(value)
        if err is not None:
            return None, err

        cmds.append(cmd.RedisCmd(
            cmd = tokens[0].upper(),
            args = tokens[1:]
        ))

    return cmds, None

def respond(c: socket.socket, commands: cmd.RedisCmds) -> None:
    eval.EvalAndRespond(c, commands)

def RunSyncTCPServer():
    logger.info("Starting a synchronus TCP server on %s %d", config.host, config.port)
    con_clients = 0

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((config.host, config.port))
        server_socket.listen()
        
        while True:
            #.accept() => Blocking call: not allowing other clients to connect
            clientSocket, clientAddress = server_socket.accept()
            con_clients += 1
            logger.info("Client connected with address %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], con_clients)

            while True:
                command, err = readCommands(clientSocket)

                #client disconnected
                if command is None and err is None:
                    con_clients -= 1
                    logger.info("Client Disconnected from %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], con_clients)
                    clientSocket.close()
                    break

                #RESP / command error
                if err is not None:
                    logger.error("Command error: %s", err)

                respond(clientSocket, command)

    except Exception as e:
        logger.error("Server Error %s", e)

    finally:
        server_socket.close()
