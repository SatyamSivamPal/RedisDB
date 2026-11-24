import time

def getCurrentClock() -> int:
    return int(time.time()) & 0x00FFFFFF

def getIdleTime(lastAccessedAt: int) -> int:
    curr = getCurrentClock()
    if curr >= lastAccessedAt:
        return curr-lastAccessedAt

    return (0x00FFFFFF - lastAccessedAt) + curr