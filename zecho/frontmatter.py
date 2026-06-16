# zecho/frontmatter.py
from pathlib import Path
import yaml

_DELIM = "---"

def parse(text: str):
    """Return (meta: dict, body: str). Missing frontmatter -> ({}, text)."""
    if not text.startswith(_DELIM + "\n") and not text.startswith(_DELIM + "\r\n"):
        return {}, text
    lines = text.splitlines(keepends=True)
    # lines[0] is the opening delimiter; find the closing one
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIM:
            yaml_block = "".join(lines[1:i])
            body = "".join(lines[i + 1:])
            meta = yaml.safe_load(yaml_block) or {}
            return meta, body
    return {}, text  # unterminated frontmatter -> treat as body

def serialize(meta: dict, body: str) -> str:
    yaml_block = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip("\n")
    return f"{_DELIM}\n{yaml_block}\n{_DELIM}\n{body}"

def load(path):
    return parse(Path(path).read_text(encoding="utf-8"))

def save(path, meta: dict, body: str) -> None:
    Path(path).write_text(serialize(meta, body), encoding="utf-8")
