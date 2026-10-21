host = "0.0.0.0"
port = "7379"

keysLimit : int = 10
max_command_size = 512
DB_COUNT: int = 4

AOFFile = "./redis.aof" 
epollFD = None

EvictionStratergy: str = "allkeys-random"
EvictionRatio: float = 0.40