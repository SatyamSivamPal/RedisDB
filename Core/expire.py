from logger import logger
from Core.store import store
import time

def expireSample() -> float:
    limit = 20
    expiredCount = 0
    currentTime = int(time.time() * 1000)

    for key, obj in list(store.items()):
        if obj.expiresAt != -1:
            limit -= 1
            if obj.expiresAt <= currentTime:
                del store[key]
                expiredCount += 1

        if limit == 0:
            break

    return expiredCount / 20.0

def DeleteExpiredKeys():
    while True:
        percentage = expireSample()

        if percentage < 0.25:
            break

    logger.info("Deleted the expired but undeleted keys. total keys %d", len(store))