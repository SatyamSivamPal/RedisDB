from Core import object

#Object STRING Enocded to = [INT, EMBSTR, RAW]
def deduceTypeEncoding(v: str) -> tuple[int, int]:
    oType = object.OBJ_TYPE_STRING
    try:
        int(v, 10)
        return oType, object.OBJ_ENCODING_INT
    except ValueError:
        pass

    if len(v) <= 44:
        return oType, object.OBJ_ENCODING_EMBSTR

    return oType, object.OBJ_ENCODING_RAW