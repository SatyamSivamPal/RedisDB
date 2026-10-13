from Core import resp
from Core.store import Put, NewObj, Get, Delete
import time
import socket
from io import BytesIO
from Core import cmd
from Core.aof import AppendAOF, BGRewriteAOF
from Core import type_string
from Core.object import OBJ_TYPE_STRING, OBJ_ENCODING_INT
from Core.typeEncoding import assertType, assertEncoding

RESP_NIL = b"$-1\r\n"
RESP_OK = b"+OK\r\n"
RESP_ZERO = b":0\r\n"
RESP_ONE = b":1\r\n"
RESP_MINUS_1 = b":-1\r\n"
RESP_MINUS_2 = b":-2\r\n"

def evalDEL(args: list[str]) -> bytes:
    countDeleted = 0
    if len(args) == 0:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'del' command"), False)
    
    for key in args:
        if Delete(key):
            countDeleted += 1

    if countDeleted > 0:
        AppendAOF(["DEL", *args])
    return resp.Encode(countDeleted, False)

def evalEXPIRE(args: list[str]) -> bytes:
    if len(args) <= 1:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'expire' command"), False)
    
    key = args[0]
    try:
        exDurationSec = int(args[1])
    except ValueError:
        return resp.Encode(ValueError(" ERR value is not an integer or out of range"), False)

    obj = Get(key)

    # Return -> 0 if the key does not exists, or operation skipped due to the provided arguments
    if obj is None:
        return RESP_ZERO

    obj.ExpiresAt = int(time.time() * 1000) + exDurationSec * 1000

    # Return -> 1 if the expires was set
    return RESP_MINUS_1
    
def evalSET(args: list[str]) -> bytes:
    if len(args) <= 1:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'set' command"), False)

    key = args[0]
    value = args[1]
    oType, oEnc = type_string.deduceTypeEncoding(value)
    exDurationMs = -1
    i = 2

    while i < len(args):
        options = args[i]
        match options.upper():
            case "EX":
                i += 1
                if i >= len(args):
                    return resp.Encode(ValueError("ERR syntax error"), False)
                try:
                    exDurationSec = int(args[3])
                except ValueError:
                    return resp.Encode(ValueError("ERR value is not an integer or out of range"), False)
                exDurationMs = exDurationSec * 1000
            case _:
                return resp.Encode(ValueError("ERR syntax error"), False)
        i+=1

    #putting the key and value in a Hash Table
    Put(key, NewObj(value, exDurationMs, oType, oEnc))
    AppendAOF(["SET", key, value])
    return RESP_OK

def evalGET(args: list[str]) -> bytes:
    if len(args) != 1:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'get' command"), False)

    key = args[0]
    obj = Get(key)

    #Key doesnot exists
    if obj is None:
        return RESP_NIL

    currentTime = int(time.time() * 1000)

    #if key has already expired
    if obj.ExpiresAt != -1 and obj.ExpiresAt <= currentTime:
        return RESP_NIL

    return resp.Encode(obj.value, False)

def evalTTL(args: list[str]) -> bytes:
    if len(args) != 1:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'ttl' command"), False)

    key = args[0]
    obj = Get(key)

    #Key doesnot exist return -2
    if obj is None:
        return RESP_MINUS_2

    #if key exists but no expirations time is set for the key -> -1
    if obj.ExpiresAt == -1:
        return RESP_MINUS_1

    #send the time remaining for the expiry
    currentTime = int(time.time() * 1000)
    durationMs = obj.ExpiresAt - currentTime

    #key has been expired -> -2
    if durationMs < 0 :
        return RESP_MINUS_2

    return resp.Encode(int(durationMs/1000), False)

def evalPING(args: list[str]) -> bytes:
    if len(args) >= 2:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'ping' command"), False)

    if len(args) == 0:
        res = resp.Encode("PONG", True)
    else:
        res = resp.Encode(args[0], False)

    return res
    
def evalBGREWRITEAOF(args: list[str]) -> bytes:
    if len(args) != 0:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'bgrewrite' command"), False)

    if not BGRewriteAOF():
        return resp.Encode(ValueError("ERR AOF rewrite is already in progress"), False)
    
    return RESP_OK

def evalINCR(args: list[str]) -> bytes:
    if (len(args) != 1):
        return resp.Encode(ValueError("ERR wrong number of arguments for 'incr' command"), False)

    key: str = args[0]
    obj = Get(key)

    if obj is None:
        obj = NewObj("0", -1, OBJ_TYPE_STRING, OBJ_ENCODING_INT)
        Put(key, obj)

    try:
        assertType(obj.TypeEncoding, OBJ_TYPE_STRING)
    except ValueError as err:
        return resp.Encode(str(err), False)

    try:
        assertEncoding(obj.TypeEncoding, OBJ_ENCODING_INT)
    except ValueError as err:
        return resp.Encode(str(err), False)

    i = int(obj.value, 10)
    i += 1
    obj.value = str(i)
    return resp.Encode(i, False)

def EvalAndRespond(c: socket.socket, commands: cmd.RedisCmds) -> ValueError | None:
    response = bytearray()
    buf = BytesIO(response)

    for command in commands:
        match command.cmd.upper():
            case "PING":
                buf.write(evalPING(command.args))
            case "SET": 
                buf.write(evalSET(command.args))
            case "GET":
                buf.write(evalGET(command.args))
            case "TTL":
                buf.write(evalTTL(command.args))
            case "DEL":
                buf.write(evalDEL(command.args))
            case "EXPIRE":
                buf.write(evalEXPIRE(command.args))
            case "BGREWRITEAOF":
                buf.write(evalBGREWRITEAOF(command.args))
            case "INCR":
                buf.write(evalINCR(command.args))
            case _:
                buf.write(evalPING(command.args))
                
    c.sendall(buf.getvalue())