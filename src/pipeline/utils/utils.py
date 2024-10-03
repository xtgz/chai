def safe_int(val: str) -> int | None:
    if val == "":
        return None
    return int(val)
