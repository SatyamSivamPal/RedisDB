def getType(te: int) -> int:
    return te & 0b11110000

def getEncoding(te: int) -> int:
    return te & 0b00001111

def assertType(te: int, t: int) -> ValueError | None:
    if getType(te) != t:
        return ValueError("the operations is not permitted on this type")

    return None

def assertEncoding(te: int, e: int) -> ValueError | None:
    if getEncoding(te) != e:
        return ValueError("the operations is not permitted on this encoding")

    return None