import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("127.0.0.1", 7379))

while True:
    command = input("> ")

    client.sendall((command + "\n").encode("utf-8"))
    response = client.recv(512)

    if command == "exit":
            break

    if not response:
        print("Server Disconnected")
        break

    print("Server - ", response.decode("utf-8"))

client.close()