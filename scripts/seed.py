# scripts/seed.py
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(dest="data"):
    dest = ROOT / dest
    (dest / "issues").mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "tests/fixtures/issues").glob("*.md"):
        shutil.copy(f, dest / "issues" / f.name)
    print(f"seeded {dest/'issues'}")

if __name__ == "__main__":
    run(*(sys.argv[1:] or []))
