"""WHP-JCS-I1 canonical bytes (shared by the SDK and the verifier)."""

def _order(s):
    return s.encode("utf-16-be")

def _str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"': out.append('\\"')
        elif ch == '\\': out.append('\\\\')
        elif ch == '\b': out.append('\\b')
        elif ch == '\t': out.append('\\t')
        elif ch == '\n': out.append('\\n')
        elif ch == '\f': out.append('\\f')
        elif ch == '\r': out.append('\\r')
        elif o < 0x20: out.append('\\u%04x' % o)
        elif 0xD800 <= o <= 0xDFFF: raise ValueError("unpaired surrogate: rejected by WHP-JCS-I1")
        else: out.append(ch)
    out.append('"')
    return ''.join(out)

def jcs(v):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, bool): raise TypeError
    if isinstance(v, int):
        if abs(v) > 9007199254740991: raise ValueError("unsafe integer: rejected by WHP-JCS-I1")
        return str(v)
    if isinstance(v, float): raise ValueError("floating-point token: rejected by WHP-JCS-I1")
    if isinstance(v, str): return _str(v)
    if isinstance(v, list): return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_str(k) + ":" + jcs(x) for k, x in sorted(v.items(), key=lambda kv: _order(kv[0]))) + "}"
    raise TypeError(type(v))
