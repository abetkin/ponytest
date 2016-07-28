_is_standalone = True

def is_standalone_use(value=NotImplemented):
    if value is not NotImplemented:
        global _is_standalone
        _is_standalone = value
    return _is_standalone
