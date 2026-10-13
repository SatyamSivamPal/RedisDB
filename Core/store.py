import time
from Config import config
from Core.eviction import evict
from logger import logger
from Core import object

Obj = object.Obj

store: dict[str, "Obj"] = {}

def NewObj(value: str, durationMs: int, oType: int, oEncoding: int) -> Obj:
    expiresAt = -1
    if durationMs > 0:
        expiresAt = int(time.time() * 1000) + durationMs

    return Obj(
        value = value,
        TypeEncoding = oType | oEncoding,
        ExpiresAt = expiresAt
    )

def Put(key: str, obj: Obj) -> None:
    if len(store) >= config.keysLimit:
        evict(store)

    store[key] = obj

def Get(key: str) -> Obj | None:
    value = store.get(key)
    if value is not None:
        if value.ExpiresAt != -1 and value.ExpiresAt <= int(time.time() * 1000):
            logger.info("Deleted due to the GET")
            del store[key]
            return None

    return value

def Delete(key: str) -> bool:
    if key not in store:
        return False

    del store[key]
    return True

