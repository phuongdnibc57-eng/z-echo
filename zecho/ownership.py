# zecho/ownership.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Squad:
    name: str
    components: list
    feedback_group_id: str
    oncall: str

def parse_ownership(path) -> list:
    squads = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "squad" or set(cells[0]) <= {"-"}:
            continue
        comps = [c.strip() for c in cells[1].split(",") if c.strip()]
        squads.append(Squad(cells[0], comps, cells[2], cells[3]))
    return squads

def route(squads, component: str):
    for s in squads:
        if component in s.components:
            return s
    return None
