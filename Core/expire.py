from logger import logger
from Core.store import getDB
from Config.config import DB_COUNT
from Core.object import Obj
import time
import random

current_expire_db = 0

def DeleteExpiredKeys(store: dict[str, Obj], sample_size: int) -> tuple[int, int]:
    if not store:
        return 0, 0

    sample_keys = random.sample(list(store.keys()), min(sample_size, len(store)))
    now_ms = int(time.time() * 1000)
    expired_cnt = 0

    for key in sample_keys:
        obj = store.get(key)

        if(obj is not None and obj.ExpiresAt != -1 and obj.ExpiresAt <= now_ms):
            del store[key]
            expired_cnt += 1

    return len(sample_keys), expired_cnt

def ActiveExpireCycle() -> int:
    global current_expire_db
    db = getDB(current_expire_db)
    sample_size = 20

    for _ in range(sample_size):
        sample_cnt, expired_cnt = DeleteExpiredKeys(db, sample_size)

        if sample_cnt == 0:
            break

        expired_ratio = expired_cnt / sample_cnt
        if expired_ratio <= 0.25:
            break

    current_expire_db = (current_expire_db + 1) % DB_COUNT