# zecho/versions.py
def parse_version(s: str):
    return tuple(int(p) for p in str(s).strip().split("."))

def version_gt(a: str, b: str) -> bool:
    return parse_version(a) > parse_version(b)

def newer_than_all(candidate: str, versions) -> bool:
    """True if candidate is strictly newer than every version in the list."""
    return all(version_gt(candidate, x) for x in versions)
