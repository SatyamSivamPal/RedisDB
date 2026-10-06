from logger import logger

def readLength(data: bytes) -> tuple[int, int]:
    length = 0
    for pos in range(len(data)):
        b = data[pos]
        if not (b >= ord('0') and b <= ord("9")):
            return length, pos+2

        length = length * 10 + (b - ord('0'))
    return 0,0


#Returns - [string, delta, error] & start = [+]
def readSimpleString(data: bytes) -> tuple[str, int, ValueError | None]:
    pos = 1
    while data[pos] != b'\r'[0]:
        pos += 1

    value = data[1:pos].decode("utf-8")
    return value, pos+2, None


#Read the encode error message from data 
#Returns - [ErrorString, delta, error] & start = [-]
def readError(data: bytes) -> tuple[str, int, ValueError | None]:
    return readSimpleString(data)


#Return - [Integer, delta, error] & starts = [:]
def readInteger(data: bytes) -> tuple[int, int, ValueError | None]:
    pos = 1
    while data[pos] != b'\r'[0]:
        pos += 1

    return int(data[1:pos]), pos+2, None


#Return - [string, delta, error]
def readBulkString(data: bytes) -> tuple[str, int, ValueError | None]:
    pos = 1
    len, delta = readLength(data[pos:])
    pos += delta

    value = data[pos:pos+len].decode("utf-8")
    return value, pos+len+2, None


def readArray(data: bytes) -> tuple[list | None, int, ValueError | None]:
    pos = 1
    cnt, delta = readLength(data[pos:])
    pos += delta

    elems = [None] * cnt
    for i in range(cnt):
        value, delta, err = DecodeOne(data[pos:])
        if err is not None:
            return None, 0, err
        
        elems[i] = value
        pos += delta

    return elems, pos, None

def DecodeOne(data: bytes) -> tuple[any | None, int, ValueError | None]:
    if len(data) == 0:
        return None, 0, ValueError("No Data")

    dataType = data[0:1]
    match dataType:
        case b'+':
            return readSimpleString(data)
        case b'-':
            return readError(data)
        case b':':
            return readInteger(data)
        case b'$':
            return readBulkString(data)
        case b'*':
            return readArray(data)
        case _:
            return None, 0, ValueError("Unknown RESP type")

def DecodeArrayString(data: bytes) -> tuple[list[str], ValueError | None]:
    value, err = Decode(data)
    if err is not None:
        return None, err

    tokens = [None] * len(value)
    for i in range(len(tokens)):
        tokens[i] = str(value[i])

    return tokens, None


def Decode(data: bytes) -> tuple[any | None, ValueError | None]:
    if len(data) == 0:
        logger.error("No Data")
        return None, ValueError("No Data")

    value, _, err = DecodeOne(data)
    return value, err

def Encode(data: any, isSimple: bool) -> bytes:
    match data:
        case str():
            #simple string
            if isSimple:
                return b"+" + data.encode("utf-8") + b"\r\n"

            #Bulk String
            length = str(len(data)).encode("utf-8")
            return (b"$" + length + b"\r\n" + data.encode("utf-8") + b"\r\n")

        case int():
            return b":" + str(data).encode("utf-8") + b"\r\n"

        case _:
            return None