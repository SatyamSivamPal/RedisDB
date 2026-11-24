from dataclasses import dataclass, field
from Core.clock import getIdleTime

@dataclass
class PoolItem:
    key: str
    lastAccessAt: int

@dataclass
class EvictionPool:
    pool: list[PoolItem] = field(default_factory=list)
    keyset: dict[str, PoolItem] = field(default_factory=dict)
    size: int = 16

    def Push(self, key:str, lastAccessAt: int) -> None:
        #Avoid duplicate keys
        if key in self.keyset:
            return

        item = PoolItem(key, lastAccessAt)
        idleTime = getIdleTime(lastAccessAt)

        #If pool has space, add the candidate
        if len(self.pool) < self.size:
            self.pool.append(item)
            self.keyset[key] = item
        else:
            #Pool is full.
            #The last item is least idle candidate,
            #sorted according to the idle time most idle time at first, ...
            lastItem = self.pool[-1]
            lastIdleTime = getIdleTime(lastItem.lastAccessAt)

            #if the new canidate has more idle time,
            #then new candidate is more qualfied then that (i.e more idle)
            if idleTime <= lastIdleTime:
                return

            #remove the least desirable candidate
            self.pool.pop()
            self.keyset.pop(lastItem.key, None)

            #add new candidate
            self.pool.append(item)
            self.keyset[key] = item

        #sort by idle time, not the optimized in redis they 
        #used the memove literally copying and inserting in the middle
        self.pool.sort(
            key=lambda item: getIdleTime(item.lastAccessAt),
            reverse=True
        )

    def Pop(self) -> PoolItem | None:
        if not self.pool:
            return None

        #the first item with most idle time
        item = self.pool.pop(0)
        self.keyset.pop(item.key, None)
        return item

ePoolSizeMax = 16
ePool = EvictionPool(size=ePoolSizeMax)
