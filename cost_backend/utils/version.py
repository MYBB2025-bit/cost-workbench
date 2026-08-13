"""版本号比较（语义化：v1.2.3 / 1.2.3）。"""


def _split(v: str):
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return parts[:3]


def version_gt(a: str, b: str) -> bool:
    """a 是否严格大于 b。"""
    return _split(a) > _split(b)


def version_ge(a: str, b: str) -> bool:
    return _split(a) >= _split(b)


def version_eq(a: str, b: str) -> bool:
    return _split(a) == _split(b)
