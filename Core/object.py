from dataclasses import dataclass
from typing import Any

@dataclass
class Obj:
    TypeEncoding: int
    value : Any
    ExpiresAt: int

OBJ_TYPE_STRING = 0 << 4  # String object
OBJ_TYPE_LIST = 1 << 4     # List object
OBJ_TYPE_SET = 2 << 4      # SET object
OBJ_TYPE_ZSET = 3 << 4     # Sorted set object
OBJ_TYPE_HASH = 4 << 4    # Hash object
OBJ_TYPE_MODULE = 5 << 4   # Module object
OBJ_TYPE_STREAM = 6 << 4   # stream object

OBJ_ENCODING_RAW = 0   # Raw representaions
OBJ_ENCODING_INT = 1   # Encoded as integer
OBJ_ENCODING_HT = 2    # Encoded as hash table
OBJ_ENCODING_ZIPMAP = 3 # Encoded as zipmap
OBJ_ENCODING_LINKEDLIST = 4  # Encoded as linked list 
OBJ_ENCODING_ZIPLIST = 5   # Encoded as ziplist
OBJ_ENCODING_INTSET = 6   # Encoded as intset
OBJ_ENCODING_SKIPLIST = 7  # Encoded as skiplist
OBJ_ENCODING_EMBSTR = 8    # Encoded as embeded string >> 44 Byte
OBJ_ENCODING_QUICKLIST = 9 
OBJ_ENCODING_STREAM = 10