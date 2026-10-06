from dataclasses import dataclass

@dataclass
class RedisCmd:
    cmd: str
    args: list[str]

@dataclass
class RedisCmds:
    cmds: list[RedisCmd]
