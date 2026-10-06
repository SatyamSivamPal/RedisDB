from Core import resp
from Core.store import Put, NewObj, Get, Delete
import time
import socket
from Core import cmd

RESP_NIL = b"$-1\r\n"

def evalDEL(c: socket.socket, args: list[str]) -> ValueError | None:
    countDeleted = 0
    if len(args) == 0:
        return ValueError("(error) ERR wrong number of arguments for 'del' command")
    
    for key in args:
        if Delete(key):
            countDeleted += 1

    response = resp.Encode(countDeleted, False)
    c.sendall(response)
    return None

def evalEXPIRE(c: socket.socket, args: list[str]) -> ValueError | None:
    if len(args) <= 1:
        return ValueError("(error) ERR wrong number of arguments for 'expire' command")
    
    key = args[0]
    try:
        exDurationSec = int(args[1])
    except ValueError:
        return ValueError("(error) ERR value is not an integer or out of range")

    obj = Get(key)

    # Return -> 0 if the key does not exists, or operation skipped due to the provided arguments
    if obj is None:
        c.sendall(b":0\r\n")
        return None

    obj.expiresAt = int(time.time() * 1000) + exDurationSec * 1000

    # Return -> 1 if the expires was set
    c.sendall(b":1\r\n")
    return None
    
def evalSET(c: socket.socket, args: list[str]) -> ValueError | None:
    if len(args) <= 1:
        return ValueError("(error) ERR wrong number of arguments for 'set' command")

    key = args[0]
    value = args[1]
    exDurationMs = -1
    i = 2

    while i < len(args):
        options = args[i]
        match options.upper():
            case "EX":
                i += 1
                if i >= len(args):
                    return ValueError("(error) ERR syntax error")
                try:
                    exDurationSec = int(args[3])
                except ValueError:
                    return ValueError("(error) ERR value is not an integer or out of range")
                exDurationMs = exDurationSec * 1000
            case _:
                return ValueError("(error) ERR syntax error")
        i+=1

    #putting the key and value in a Hash Table
    Put(key, NewObj(value, exDurationMs))
    respond = resp.Encode("OK", True)
    c.sendall(respond)
    return None

def evalGET(c: socket.socket, args: list[str]) -> ValueError | None:
    if len(args) != 1:
        return ValueError("ERR wrong number of arguments for 'get' command")

    key = args[0]
    obj = Get(key)

    #Key doesnot exists
    if obj is None:
        c.sendall(RESP_NIL)
        return None

    currentTime = int(time.time() * 1000)

    #if key has already expired
    if obj.expiresAt != -1 and obj.expiresAt <= currentTime:
        c.sendall(RESP_NIL)
        return None

    respond = resp.Encode(obj.value, False)
    c.sendall(respond)
    return None

def evalTTL(c: socket.socket, args: list[str]) -> ValueError | None:
    if len(args) != 1:
        return ValueError("(error) ERR wrong number of arguments for 'ttl' command")

    key = args[0]
    obj = Get(key)

    #Key doesnot exist return -2
    if obj is None:
        c.sendall(b":-2\r\n")
        return None

    #if key exists but no expirations time is set for the key -> -1
    if obj.expiresAt == -1:
        c.sendall(b":-1\r\n")
        return None

    #send the time remaining for the expiry
    currentTime = int(time.time() * 1000)
    durationMs = obj.expiresAt - currentTime

    #key has been expired -> -2
    if durationMs < 0 :
        c.sendall(b":-2\r\n")
        return None

    respond = resp.Encode(int(durationMs/1000), False)
    c.sendall(respond)
    return None

def evalPING(c: socket.socket, args: list[str]) -> ValueError | None:
    if len(args) >= 2:
        return ValueError("(error) ERR wrong number of arguments for 'ping' command")

    if len(args) == 0:
        res = resp.Encode("PONG", True)
    else:
        res = resp.Encode(args[0], False)

    c.sendall(res)
    return None
    
def EvalAndRespond(c: socket.socket, command: cmd.RedisCmd) -> ValueError | None:
    match command.cmd.upper():
        case "PING":
            return evalPING(c, command.args)
        case "SET": 
            return evalSET(c, command.args)
        case "GET":
            return evalGET(c, command.args)
        case "TTL":
            return evalTTL(c, command.args)
        case "DEL":
            return evalDEL(c, command.args)
        case "EXPIRE":
            return evalEXPIRE(c, command.args)
        case _:
            return ValueError(f"Unknown Command '{command.cmd}'")