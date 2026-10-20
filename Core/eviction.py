from Config import config

def evictFirst(store):
    for key in store:
        del store[key]
        return

def evictAllkeysRandom(store):
    evictCount = int(config.EvictionRatio * config.keysLimit)

    for k in list(store.keys()):
        del store[k]
        evictCount -= 1

        if evictCount <= 0:
            break


def evict(store) -> None:
    match config.EvictionStratergy:
        case "simple-first":
            evictFirst(store)
        case "allkeys-random":
            evictAllkeysRandom(store)