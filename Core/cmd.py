from dataclasses import dataclass, field
import socket
from Core.object import Obj

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

@dataclass
class RedisDB:
        #stores key -> obj
        store: dict[str, Obj] = field(default_factory=dict)

        #stores key -> expires
        expires: dict[str, int] = field(default_factory=dict)
