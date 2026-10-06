
def evictFirst(store):
    for key in store:
        del store[key]
        return

def evict(store) -> None:
    evictFirst(store)