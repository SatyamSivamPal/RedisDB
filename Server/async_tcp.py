import socket
import select
import time
from logger import logger
from Config import config
from Core.expire import ActiveExpireCycle
from Server.sync_tcp import readCommands, respond
from datetime import datetime, timedelta
from Core import aof    
from Core.cmd import Client

def RunAsyncTCPServer():
    logger.info("Starting an asynchronus TCP server on %s %d", config.host, config.port)
    max_clients = 20000
    conn_clients = 0
    cronFrequency = 0.1
    lastCronExecTime = time.monotonic()
    Clients:dict[int, Client] = {}

    # create socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(False)

    #Bind the ip4 and port
    server.bind((config.host, config.port))

    #listen
    server.listen(max_clients)

    #AsyncIO starts here!!

    #creating EPOLL instance
    config.epollFD = select.epoll()
    serverFD = server.fileno()
    config.epollFD.register(
        serverFD,
        select.EPOLLIN
    )

    while True:
        # Cron job for server maintanence
        now = time.monotonic()
        elapsed = now - lastCronExecTime
        timeout = max(0.0, cronFrequency - elapsed)
        
        events = config.epollFD.poll(timeout)
        now = time.monotonic()
        if now - lastCronExecTime >= cronFrequency:
            ActiveExpireCycle()
            lastCronExecTime = now

        for fd, event in events:
            # notification to the main process about the status of child process
            if fd == aof.notifyReadFD:
                aof.FinishRewrite()

            #accept the incoming connection from new client
            elif fd == serverFD:
                clientSocket, clientAddress = server.accept()
                conn_clients += 1
                logger.info("Client connected with address %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], conn_clients)
                clientSocket.setblocking(False)
                clientFD = clientSocket.fileno()

                #stores the client
                Clients[clientFD] = Client(
                    socket = clientSocket,
                    address = clientAddress
                )

                #Register new client
                config.epollFD.register(
                    clientFD,
                    select.EPOLLIN
                )

            #existing client with some command
            elif fd in Clients:
                client: Client = Clients[fd]
                clientSocket = client.socket
                clientAddress = client.address
                clientDB = client.db

                commands, err = readCommands(client)
                if commands is None and err is None:
                    conn_clients -= 1
                    logger.info("Client Disconnected from %s %d, concurrent clients: %d", clientAddress[0], clientAddress[1], conn_clients)
                    clientSocket.close()
                    break

                #RESP / command error
                if err is not None:
                    logger.error("Command error: %s", err)

                respond(client, commands)
                


