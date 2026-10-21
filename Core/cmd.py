from dataclasses import dataclass
import socket

@dataclass
class RedisCmd:
    cmd: str
    args: list[str]

@dataclass
class RedisCmds:
    cmds: list[RedisCmd]

@dataclass
class Client:
    socket : socket.socket
    address : tuple
    db: int = 0