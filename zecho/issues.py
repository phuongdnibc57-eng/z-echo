# zecho/issues.py
from pathlib import Path
from zecho import frontmatter as fm

def _issue_path(issues_dir, iid):
    return Path(issues_dir) / f"{iid}.md"

def list_issue_ids(issues_dir):
    d = Path(issues_dir)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("ISS-*.md"))

def next_issue_id(issues_dir) -> str:
    ids = list_issue_ids(issues_dir)
    n = max((int(i.split("-")[1]) for i in ids), default=0) + 1
    return f"ISS-{n:04d}"

def create_issue(issues_dir, fields: dict, short_desc: str, title: str,
                 symptoms: list) -> str:
    Path(issues_dir).mkdir(parents=True, exist_ok=True)
    iid = next_issue_id(issues_dir)
    meta = {"id": iid, "status": "new"}
    meta.update(fields)
    meta["short_desc"] = short_desc
    sym = "\n".join(f"- {s}" for s in symptoms)
    body = (f"# {title}\n"
            f"## Symptoms\n{sym}\n"
            f"## Reporters\n")
    fm.save(_issue_path(issues_dir, iid), meta, body)
    return iid

def load_issue(issues_dir, iid):
    return fm.load(_issue_path(issues_dir, iid))

def bump_frequency(issues_dir, iid, last_seen: str) -> None:
    meta, body = load_issue(issues_dir, iid)
    meta["freq"] = int(meta.get("freq", 0)) + 1
    meta["last_seen"] = last_seen
    fm.save(_issue_path(issues_dir, iid), meta, body)

def query(issues_dir, component_contains: str = None, **equals) -> list:
    """Return issue ids whose frontmatter matches. component_contains does a
    substring match on the comma-joined component field."""
    out = []
    for iid in list_issue_ids(issues_dir):
        meta, _ = load_issue(issues_dir, iid)
        if component_contains is not None:
            if component_contains not in str(meta.get("component", "")):
                continue
        if all(str(meta.get(k)) == str(val) for k, val in equals.items()):
            out.append(iid)
    return out

from dataclasses import dataclass

@dataclass
class Reporter:
    handle: str
    channel: str
    date: str
    notified: bool

def _parse_reporter_line(line: str):
    # format: "- @handle | channel | date | notified:no"
    raw = line.lstrip("-").strip()
    parts = [p.strip() for p in raw.split("|")]
    handle, channel, date = parts[0], parts[1], parts[2]
    notified = parts[3].split(":")[1].strip().lower() == "yes"
    return Reporter(handle, channel, date, notified)

def _split_reporters(body: str):
    """Return (head, reporter_lines, tail_after_block)."""
    marker = "## Reporters"
    idx = body.find(marker)
    if idx == -1:
        return body.rstrip("\n") + "\n## Reporters\n", [], ""
    head = body[: idx + len(marker)] + "\n"
    rest = body[idx + len(marker):].lstrip("\n")
    lines, tail = [], ""
    rest_lines = rest.splitlines()
    consumed = 0
    for ln in rest_lines:
        if ln.startswith("- @"):
            lines.append(ln)
            consumed += 1
        elif ln.startswith("## "):
            break
        else:
            consumed += 1  # skip blanks within block
    tail_start = "\n".join(rest_lines[consumed:])
    tail = ("\n" + tail_start) if tail_start else ""
    return head, lines, tail

def _reporters(body):
    _, lines, _ = _split_reporters(body)
    return [_parse_reporter_line(l) for l in lines]

def _write_reporters(body, reporters):
    head, _, tail = _split_reporters(body)
    block = "".join(
        f"- {r.handle} | {r.channel} | {r.date} | notified:{'yes' if r.notified else 'no'}\n"
        for r in reporters)
    return head + block + tail

def add_reporter(issues_dir, iid, handle, channel, date) -> None:
    meta, body = load_issue(issues_dir, iid)
    reps = _reporters(body)
    if any(r.handle == handle for r in reps):
        return
    reps.append(Reporter(handle, channel, date, notified=False))
    fm.save(_issue_path(issues_dir, iid), meta, _write_reporters(body, reps))

def unnotified_reporters(issues_dir, iid):
    _, body = load_issue(issues_dir, iid)
    return [r for r in _reporters(body) if not r.notified]

def mark_notified(issues_dir, iid, handle) -> None:
    meta, body = load_issue(issues_dir, iid)
    reps = _reporters(body)
    for r in reps:
        if r.handle == handle:
            r.notified = True
    fm.save(_issue_path(issues_dir, iid), meta, _write_reporters(body, reps))

def set_status(issues_dir, iid, status) -> None:
    meta, body = load_issue(issues_dir, iid)
    meta["status"] = status
    fm.save(_issue_path(issues_dir, iid), meta, body)

def append_verdict(issues_dir, iid, verdict, by, reason, scope_versions) -> None:
    if not reason or not reason.strip():
        raise ValueError("PO verdict requires a non-empty reason")
    meta, body = load_issue(issues_dir, iid)
    scope = ", ".join(scope_versions)
    block = (f"\n## PO verdict\n"
             f"- verdict: {verdict}\n"
             f"- by: {by}\n"
             f"- reason: {reason.strip()}\n"
             f"- scope_versions: {scope}\n")
    status = "resolved" if verdict == "fixed" else "closed"
    meta["status"] = status
    fm.save(_issue_path(issues_dir, iid), meta, body.rstrip("\n") + "\n" + block)

def read_verdict(issues_dir, iid):
    _, body = load_issue(issues_dir, iid)
    idx = body.find("## PO verdict")
    if idx == -1:
        return None
    out = {}
    for ln in body[idx:].splitlines():
        if ln.startswith("- "):
            k, _, v = ln[2:].partition(":")
            k, v = k.strip(), v.strip()
            out[k] = [s.strip() for s in v.split(",")] if k == "scope_versions" else v
    return out

# append to zecho/issues.py
def find_by_jira_key(issues_dir, jira_key):
    for iid in list_issue_ids(issues_dir):
        meta, _ = load_issue(issues_dir, iid)
        if meta.get("jira_key") == jira_key:
            return iid
    return None
