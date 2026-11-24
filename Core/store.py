import time
from Config import config
from Core.eviction import evict
from Core.clock import getCurrentClock
from logger import logger
from Core import object
from Core.cmd import RedisDB
from Core.expire import hasExpired
from Config.config import databases

Obj = object.Obj

def setExpiry(db: RedisDB, key: str, expDurationMs: int) -> None:
    db.expires[key] = int(time.time() * 1000) + expDurationMs

def getDB(db_index: int) -> RedisDB:
    if not 0 <= db_index < config.DB_COUNT:
        raise ValueError("ERR DB index is out of range")

    return databases[db_index]

def NewObj(value: str, oType: int, oEncoding: int) -> Obj:
    return Obj(
        value = value,
        TypeEncoding = oType | oEncoding,
        LastAccessedAt = getCurrentClock()
    )   

def Put(db: RedisDB, key: str, obj: Obj, durationMs:int = -1) -> None:
    obj.LastAccessedAt = getCurrentClock()

    #total keys accross all the logical databases
    totalKeys:int = sum(len(database.store) for database in databases)

    if totalKeys >= config.keysLimit:
        evict()

    db.store[key] = obj
    if durationMs > 0:
        setExpiry(db, key, durationMs)
    else:
        db.expires.pop(key, None)

def Get(db: RedisDB, key: str) -> Obj | None:
    value = db.store.get(key)
    if value is None:
        return None

    if hasExpired(db, key):
        logger.info("Deleted due to the GET")
        del db.store[key]
        del db.expires[key]
        return None

    value.LastAccessedAt = getCurrentClock()
    return value

def Delete(db: RedisDB, key: str) -> bool:
    if key not in db.store:
        return False

    del db.store[key]
    db.expires.pop(key, None)
    return True

