# {}, {}, {}, {} => 4 database db0, db1, db2, db3 by default db0 
# keys = int number of keys
from Config import config

KeyspaceStat = [{} for _ in range(config.DB_COUNT)]

def UpdateDBStat(num: int, metric: str, value: int):
    #num = database number, metric = keys (string), value = no. of keys (int)
    KeyspaceStat[num][metric] = value