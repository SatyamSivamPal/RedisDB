from Config import config
from Core.cmd import RedisDB
from Core.evictionpool import ePool
from Config.config import databases
import random
import time

def deleteKey(db: RedisDB, key: str):    
    db.store.pop(key, None)
    db.expires.pop(key, None)

#Evicts the first key it found while iterating the map
def evictFirst():
    for db in databases:
        if db.store:
            key = next(iter(db.store))
            deleteKey(db, key)
            return

# Evicts the key on random manner to make space for the new key to add
def evictAllkeysRandom():
    evictCount = max(
        1,
        int(config.EvictionRatio * config.keysLimit)
    )
    candidates = []
    for dbIndex, db in enumerate(databases):
        for key in db.store:
            candidates.append((dbIndex, key))

    selected_candidates = random.sample(
        candidates,
        min(evictCount, len(candidates))
    )

    for dbIndex, key in selected_candidates:
        deleteKey(databases[dbIndex], key)

#Approximated LRU algorithm 
def populateEvictionPool():
    sampleSize:int = 5
    for dbIndex, db in enumerate(databases):
        if not db.store:
            continue

        sampleKeys = random.sample(
            list(db.store.keys()),
            min(sampleSize, len(db.store))
        )

        for key in sampleKeys:
            expiryTime = db.expires.get(key)
            if expiryTime is not None and expiryTime <= int(time.time() * 1000):
                deleteKey(db, key)
                continue

            obj = db.store.get(key)
            if obj is None:
                continue

            #Encoding the DB index with the key to avoid collisions
            poolKey = f"{dbIndex}\0{key}"
            ePool.Push(poolKey, obj.LastAccessedAt)


def evictAllkeysLRU():
    evictCount = int(config.EvictionRatio * config.keysLimit)
    maxAttempts: int = max(100, evictCount * 20)
    evicted:int = 0
    attempts:int = 0

    #start with a clean pool for this eviction cycle
    while evicted < evictCount and attempts < maxAttempts:
        #Refill when the pool is empty
        if not ePool.pool:
            populateEvictionPool()

            #after populating no candidate can be added
            if not ePool.pool:
                break

        #get the best candidate to evict
        candidate = ePool.Pop()
        if candidate is None:
            break

        attempts += 1
        dbIndexStr, key = candidate.key.split("\0", 1)
        dbIndex = int(dbIndexStr)
        db = databases[dbIndex]
        obj = db.store.get(key)
        if obj is None:
            continue

        #if the candidate may have been accessed during the sampling time
        if obj.LastAccessedAt != candidate.lastAccessAt:
            continue

        #Evict the LRU candidate
        deleteKey(db, key)
        evicted += 1


def evict() -> None:
    match config.EvictionStratergy:
        case "simple-first":
            evictFirst()
        case "allkeys-random":
            evictAllkeysRandom()
        case "allkeys-lru":
            evictAllkeysLRU()