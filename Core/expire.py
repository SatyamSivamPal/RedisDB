from Config.config import DB_COUNT, databases
from Core.object import Obj
from Core.cmd import RedisDB
import time
import random

current_expire_db = 0

def hasExpired(db: RedisDB, key: str) -> bool:
    expiry_time = db.expires.get(key)

    if expiry_time is None:
        return False

    current_time = int(time.time() * 1000)
    return expiry_time <= current_time

def DeleteExpiredKeys(db:RedisDB, sample_size: int) -> tuple[int, int]:
    if not db.expires:
        return 0, 0

    sample_keys = random.sample(list(db.expires.keys()), min(sample_size, len(db.expires)))
    now_ms = int(time.time() * 1000)
    expired_cnt = 0

    for key in sample_keys:
        expiry_time = db.expires.get(key)

        if(expiry_time is not None and expiry_time <= now_ms):
            #delete from both the dictionary
            db.store.pop(key, None)
            db.expires.pop(key, None)

            expired_cnt += 1

    return len(sample_keys), expired_cnt

def ActiveExpireCycle() -> int:
    global current_expire_db
    db = databases[current_expire_db]

    sample_size = 20
    total_expired = 0

    for _ in range(sample_size):
        sample_cnt, expired_cnt = DeleteExpiredKeys(db, sample_size)

        if sample_cnt == 0:
            break

        total_expired += expired_cnt
        expired_ratio = expired_cnt / sample_cnt
        if expired_ratio <= 0.25:
            break

    current_expire_db = (current_expire_db + 1) % DB_COUNT

    return total_expired