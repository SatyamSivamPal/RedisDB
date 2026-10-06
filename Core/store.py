import time
from Config import config
store: dict[str, "Obj"] = {}

class Obj:
    def __init__(self, value: str, expiresAt: int):
        self.value = value
        self.expiresAt = expiresAt

def NewObj(value: str, durationMs: int) -> Obj:
    expiresAt = -1
    if durationMs > 0:
        expiresAt = int(time.time() * 1000) + durationMs

    return Obj(
        value,
        expiresAt
    )

def Put(key: str, obj: Obj) -> None:
    if len(store) >= config.keysLimit:
        evict()
        
    store[key] = obj

def Get(key: str) -> Obj | None:
    value = store.get(key)
    if value is not None:
        if value.expiresAt <= int(time.time() * 1000):
            del store[key]
            return None

    return value

def Delete(key: str) -> bool:
    if key not in store:
        return False

    del store[key]
    return True

