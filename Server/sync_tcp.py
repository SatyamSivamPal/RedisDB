from logger import logger
from Config import config
import socket
from Core import resp, cmd, eval

def readCommand(clientSocket: socket.socket) -> tuple[cmd.RedisCmd | None, Exception | None]:
    buffer = bytearray()
    chunk = clientSocket.recv(512)

    if not chunk:
        return None, None

    buffer.extend(chunk)
    tokens, err = resp.DecodeArrayString(buffer)
    if err is not None:
        return None, err

    command = cmd.RedisCmd(
        cmd = tokens[0],
        args = tokens[1:]
    )

    return command, None

def respondError(c: socket.socket, err: ValueError) -> None:
    response = f"-{err}\r\n"
    c.sendall(response.encode("utf-8"))

def respond(c: socket.socket, command: cmd.RedisCmd) -> None:
    err = eval.EvalAndRespond(c, command)

    if err is not None:
        respondError(c, err)

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
                command, err = readCommand(clientSocket)

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
