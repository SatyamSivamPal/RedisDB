import socket
import select
from logger import logger
from Config import config
from Core.expire import DeleteExpiredKeys
from Server.sync_tcp import readCommands, respond
from datetime import datetime, timedelta

def RunAsyncTCPServer():
    logger.info("Starting an asynchronus TCP server on %s %d", config.host, config.port)
    max_clients = 20000
    conn_clients = 0
    cronFrequency = timedelta(seconds=1)
    lastCronExecTime = datetime.now()
    clients = {}

    # create socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(False)

    #Bind the ip4 and port
    server.bind((config.host, config.port))

    #listen
    server.listen(max_clients)

    #AsyncIO starts here!!

    #creating EPOLL instance
    epollFD = select.epoll()
    serverFD = server.fileno()
    epollFD.register(
        serverFD,
        select.EPOLLIN
    )

    while True:
        # delete the active keys which are not get
        if datetime.now() > lastCronExecTime + cronFrequency:
            DeleteExpiredKeys()
            lastCronExecTime = datetime.now()

        events = epollFD.poll(-1)
        for fd, event in events:
            #accept the incoming connection from new client
            if fd == serverFD:
                clientSocket, clientAddress = server.accept()
                conn_clients += 1
                logger.info("Client connected with address %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], conn_clients)
                clientSocket.setblocking(False)
                clientFD = clientSocket.fileno()

                #stores the client
                clients[clientFD] = {
                    "socket" : clientSocket,
                    "address" : clientAddress
                }

                #Register new client
                epollFD.register(
                    clientFD,
                    select.EPOLLIN
                )

            #existing client with some command
            else:
                clientFD = fd
                client = clients[clientFD]
                clientSocket = client["socket"]
                clientAddress = client["address"]

                commands, err = readCommands(clientSocket)
                if commands is None and err is None:
                    conn_clients -= 1
                    logger.info("Client Disconnected from %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], conn_clients)
                    clientSocket.close()
                    break

                #RESP / command error
                if err is not None:
                    logger.error("Command error: %s", err)

                respond(clientSocket, commands)
                


