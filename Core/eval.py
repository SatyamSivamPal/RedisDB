from Core import resp
from Core.store import Put, NewObj, Get, Delete, getDB, setExpiry
from Config.config import databases
import time
from Core.cmd import Client
from io import BytesIO, StringIO
from Core import cmd
from Core.expire import hasExpired
from Config.config import DB_COUNT
from Core.aof import AppendAOF, BGRewriteAOF
from Core import type_string
from Core.object import OBJ_TYPE_STRING, OBJ_ENCODING_INT
from Core.typeEncoding import assertType, assertEncoding
from Core.eviction import evictAllkeysLRU

RESP_NIL = b"$-1\r\n"
RESP_OK = b"+OK\r\n"
RESP_ZERO = b":0\r\n"
RESP_ONE = b":1\r\n"
RESP_MINUS_1 = b":-1\r\n"
RESP_MINUS_2 = b":-2\r\n"

def evalDEL(args: list[str], client: Client) -> bytes:
    if len(args) == 0:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'del' command"), False)

    db = getDB(client.db)
    countDeleted = 0
    for key in args:
        if Delete(db, key):
            countDeleted += 1

    if countDeleted > 0:
        AppendAOF(client.db, ["DEL", *args])

    return resp.Encode(countDeleted, False)

def evalEXPIRE(args: list[str], client: Client) -> bytes:
    if len(args) <= 1:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'expire' command"), False)

    db = getDB(client.db)
    key = args[0]
    try:
        exDurationSec = int(args[1])
    except ValueError:
        return resp.Encode(ValueError(" ERR value is not an integer or out of range"), False)

    obj = Get(db, key)

    # Return -> 0 if the key does not exists, or operation skipped due to the provided arguments
    if obj is None:
        return RESP_ZERO

    # Exists but the time is 0 or negative immediately delete the key and return 1
    exDurationMs = exDurationSec * 1000
    if exDurationMs <= 0:
        del db.store[key]
        db.expires.pop(key, None)
        return RESP_ONE
    
    # Return -> 1 if the expires was set
    setExpiry(db, key, exDurationMs)
    return RESP_ONE
    
def evalSET(args: list[str], client: Client) -> bytes:
    if len(args) <= 1:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'set' command"), False)

    db = getDB(client.db)
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
    obj = NewObj(value, oType, oEnc)
    Put(db, key, obj, exDurationMs)
    AppendAOF(client.db, ["SET", key, value])
    return RESP_OK

def evalGET(args: list[str], client: Client) -> bytes:
    if len(args) != 1:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'get' command"), False)

    db = getDB(client.db)
    key = args[0]
    obj = Get(db, key)

    #Key doesnot exists
    if obj is None:
        return RESP_NIL

    currentTime = int(time.time() * 1000)

    #if key has already expired
    if hasExpired(db, key):
        return RESP_NIL

    return resp.Encode(obj.value, False)

def evalTTL(args: list[str], client: Client) -> bytes:
    if len(args) != 1:
        return resp.Encode(ValueError(" ERR wrong number of arguments for 'ttl' command"), False)

    key = args[0]
    db = getDB(client.db)
    obj = Get(db, key)

    #Key doesnot exist return -2
    if obj is None:
        return RESP_MINUS_2

    #Expiration time
    expiry_time = db.expires.get(key)

    #if key exists but no expirations time is set for the key -> -1
    if expiry_time is None:
        return RESP_MINUS_1

    #send the time remaining for the expiry
    currentTime = int(time.time() * 1000)
    durationMs = expiry_time - currentTime

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
    
def evalBGREWRITEAOF(args: list[str], client: Client) -> bytes:
    
    if len(args) != 0:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'bgrewrite' command"), False)

    if not BGRewriteAOF(databases):
        return resp.Encode(ValueError("ERR AOF rewrite is already in progress"), False)
    
    return RESP_OK

def evalINCR(args: list[str], client: Client) -> bytes:
    if (len(args) != 1):
        return resp.Encode(ValueError("ERR wrong number of arguments for 'incr' command"), False)

    key: str = args[0]
    db = getDB(client.db)
    obj = Get(db, key)

    if obj is None:
        obj = NewObj("0", OBJ_TYPE_STRING, OBJ_ENCODING_INT)
        Put(db, key, obj)

    try:
        assertType(obj.TypeEncoding, OBJ_TYPE_STRING)
    except ValueError as err:
        return resp.Encode(str(err), False)

    try:
        assertEncoding(obj.TypeEncoding, OBJ_ENCODING_INT)
    except ValueError as err:
        return resp.Encode(str(err), False)

    try:
        i = int(obj.value, 10)
    except ValueError:
        return resp.Encode(ValueError("ERR value is not an integer or out of range"), False)
    i += 1
    obj.value = str(i)
    AppendAOF(client.db, ["INCR", key])
    return resp.Encode(i, False)

def evalSELECT(args: list[str], client: Client) -> bytes:
    if len(args) != 1:
        return resp.Encode(ValueError("ERR wrong number of arguments for 'select' command"), False)

    try:
        db_index = int(args[0])
    except ValueError:
        return resp.Encode(ValueError("ERR invalid DB index", False))

    if not 0 <= db_index < DB_COUNT:
        return resp.Encode("ERR DB index is out of range", False)

    client.db = db_index
    return RESP_OK

def evalLRU(args: list[str], client: Client) -> bytes:
    if len(args) > 1:
        return resp.Encode(ValueError("Err invalid number of arguments for the LRU command"), False)

    evictAllkeysLRU()
    return RESP_OK

def EvalAndRespond(client: Client, commands: cmd.RedisCmds) -> ValueError | None:
    response = bytearray()
    buf = BytesIO(response)

    clientSocket = client.socket
    for command in commands:
        match command.cmd.upper():
            case "PING":
                buf.write(evalPING(command.args))
            case "SET": 
                buf.write(evalSET(command.args, client))
            case "GET":
                buf.write(evalGET(command.args, client))
            case "TTL":
                buf.write(evalTTL(command.args, client))
            case "DEL":
                buf.write(evalDEL(command.args, client))
            case "EXPIRE":
                buf.write(evalEXPIRE(command.args, client))
            case "BGREWRITEAOF":
                buf.write(evalBGREWRITEAOF(command.args, client))
            case "INCR":
                buf.write(evalINCR(command.args, client))
            case "SELECT":
                buf.write(evalSELECT(command.args, client))
            case "LRU":
                buf.write(evalLRU(command.args, client))
            case _:
                buf.write(evalPING(command.args))

    clientSocket.sendall(buf.getvalue())