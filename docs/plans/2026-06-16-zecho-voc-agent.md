# Z-Echo — Voice-of-Customer Agent · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build "Z-Echo" — a set of composable Claw skills (sharing one tested toolkit) that turn internal Zalo product feedback into a deduplicated, routed, self-learning backlog with proactive close-loop and digests.

**Architecture:** Four Claw skills (`zecho-triage`, `zecho-closeloop`, `zecho-digest`, `zecho-verdict`) all import one deterministic Python toolkit `zecho/` (tested). The toolkit owns every must-be-correct decision (reporter selection + exactly-once mark, thresholds, IDs, pool CRUD, Jira); skills (LLM) own judgment + language. Store is file-based under `data/` (markdown + YAML frontmatter) and is the **source of truth**. Jira is an optional adapter; everything works without it.

**Tech Stack:** Python 3.11, pytest, PyYAML, requests (Jira). No DB, no vector store. Dedup = component-narrow → LLM reads English `short_desc` → fetch full body (LLM judgment, lives in `zecho-triage` skill). Cron = Claw scheduler launching `zecho-closeloop` / `zecho-digest`.

**Split principle:** *must-be-correct → toolkit (deterministic, tested); language/judgment → skill (LLM).* `zecho-closeloop` is hybrid on purpose: the toolkit selects which reporters to notify and marks them notified (exactly-once); the LLM only composes the message text in the reporter's language.

**Spec:** [`docs/specs/2026-06-16-zecho-voc-agent-design.md`](../specs/2026-06-16-zecho-voc-agent-design.md) · **Architecture:** [`docs/architecture.md`](../architecture.md)

---

## Conventions (read once)

- **Language (D12):** frontmatter is **English** (incl. `short_desc`); body keeps the reporter's original language; bot replies in the reporter's `lang`.
- **IDs:** issues `ISS-NNNN` (zero-padded 4 digits); feedback `fb_NNNN`.
- **Severity scale:** `low=25, medium=50, high=75, critical=100`. `impact` and `segment` are 0–100.
- **Priority weights (default):** `w1=0.30 (impact), w2=0.30 (frequency), w3=0.15 (segment), w4=0.25 (severity)`.
- **Frequency normalization for priority:** `min(freq, 50) / 50 * 100`.
- **Issue status:** `new, routed, awaiting_po_reason, in_progress, resolved, closed`.
- **Feedback status:** `new, clarifying, pooled, deflected, dropped`.
- **TDD:** write failing test → run (fail) → implement → run (pass) → commit. Commit after every task.
- **Run tests with:** `python -m pytest -q` (from repo root `C:\Users\nhuy\Projects\z-echo`).

---

## File Structure

```
z-echo/                            # repo root
  pyproject.toml                   # package + pytest config
  zecho/                            # python TOOLKIT (deterministic, tested)
    __init__.py
    frontmatter.py                 # parse/serialize/load/save markdown+YAML frontmatter
    versions.py                    # parse_version, version_gt, newer_than_all
    priority.py                    # compute_priority + severity map
    issues.py                      # issue file CRUD: create/load/query/bump/reporters/status/verdict
    ownership.py                   # parse ownership.md, route(component)->squad
    threshold.py                   # daily-digest notice-threshold evaluation
    render.py                      # template-fallback message strings (close-loop + digest)
    jira_adapter.py                # Adapter protocol, NoopAdapter, JiraAdapter
    claw.py                        # claw_send(channel, message) thin wrapper (mockable)
    closeloop.py                   # DETERMINISTIC selection: pending_notifications() + mark_sent()
    digest.py                      # DETERMINISTIC: collect squad/PO digest data + threshold reasons
  scripts/
    pool_jira.py                   # CLI: sync one issue file -> Jira, write back jira_key
    seed.py                        # copy fixtures into a working data/
  skills/                          # CLAW SKILLS (LLM prompts; each imports the toolkit)
    zecho-triage/SKILL.md           # reactive: capture→clarify→dedup→route→pool
    zecho-closeloop/SKILL.md        # cron ~5': toolkit selects+marks, LLM composes per-lang
    zecho-digest/SKILL.md           # cron 9:00: toolkit collects, LLM writes narrative digest
    zecho-verdict/SKILL.md          # reactive: PO tag bot → write-back verdict
  data/
    ownership.md                   # squad <-> component, feedback_group_id, oncall
    feedback/<YYYY-MM-DD>/fb_*.md
    issues/ISS-*.md                # the pool (source of truth)
    kb/*.md                        # general PO rules (not tied to one issue)
    notifications.log              # append-only audit
  tests/
    test_frontmatter.py  test_versions.py  test_priority.py  test_issues.py
    test_ownership.py    test_threshold.py test_render.py    test_jira_adapter.py
    test_closeloop.py    test_digest.py    test_scripts.py
    fixtures/                      # seed issues + feedback scenarios for acceptance
  scenarios/
    README.md                      # manual acceptance scenarios mapped to A1..A5
```

**Module responsibilities (one job each):**
- `frontmatter` — byte-level read/write of the `---\nYAML\n---\nbody` format. Knows nothing about issues.
- `versions` — semver-ish compare of strings like `25.6.1`.
- `priority` — pure numeric scoring.
- `issues` — the only module that knows the issue-file shape (frontmatter + `## Symptoms`/`## Reporters`/`## PO verdict`). Built on `frontmatter`.
- `ownership` — parse the routing table.
- `threshold` — pure predicate over issue frontmatter dicts.
- `render` — template-fallback string formatting (skills may override with LLM text).
- `jira_adapter` — the only module that talks to Jira; swappable with Noop.
- `claw` — the only module that sends to Claw; mockable.
- `closeloop` — **deterministic** notify selection (`pending_notifications`) + `mark_sent` (exactly-once). No LLM.
- `digest` — **deterministic** collection of per-squad/PO digest data + threshold reasons. No LLM.
- `scripts/` — `pool_jira.py` (Jira REST), `seed.py` (fixtures→data).
- `skills/` — Claw prompts. Each is a thin LLM layer that calls the toolkit for correctness and adds judgment/language.

---

## Phase 0 — Scaffold

### Task 0: Project scaffold + pytest

**Files:**
- Create: `pyproject.toml`, `zecho/__init__.py`, `tests/__init__.py`, `scripts/__init__.py`, `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "zecho"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PyYAML>=6.0", "requests>=2.31"]

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create empty package + test init**

```python
# zecho/__init__.py
__all__ = []
```
```python
# tests/__init__.py
```
```python
# scripts/__init__.py
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.env
```

- [ ] **Step 4: Install deps + confirm pytest runs**

Run: `python -m pip install -e . && python -m pytest -q`
Expected: `no tests ran` (exit 0/5) — pytest is wired.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml zecho/__init__.py tests/__init__.py scripts/__init__.py .gitignore
git commit -m "chore: scaffold zecho python package + pytest"
```

---

## Phase 1 — Data layer: frontmatter + versions + priority

### Task 1: `frontmatter` parse/serialize

**Files:**
- Create: `zecho/frontmatter.py`, `tests/test_frontmatter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_frontmatter.py
from zecho import frontmatter as fm

def test_parse_roundtrip(tmp_path):
    text = "---\nid: ISS-0001\nfreq: 3\n---\n# Title\nbody line\n"
    meta, body = fm.parse(text)
    assert meta["id"] == "ISS-0001"
    assert meta["freq"] == 3
    assert body == "# Title\nbody line\n"

def test_serialize_roundtrip():
    meta = {"id": "ISS-0002", "component": "payment, qr"}
    body = "# T\nx\n"
    out = fm.serialize(meta, body)
    meta2, body2 = fm.parse(out)
    assert meta2["id"] == "ISS-0002"
    assert meta2["component"] == "payment, qr"
    assert body2 == body

def test_load_save(tmp_path):
    p = tmp_path / "x.md"
    fm.save(p, {"id": "ISS-0003"}, "body\n")
    meta, body = fm.load(p)
    assert meta["id"] == "ISS-0003"
    assert body == "body\n"

def test_parse_no_frontmatter():
    meta, body = fm.parse("just body\n")
    assert meta == {}
    assert body == "just body\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_frontmatter.py -q`
Expected: FAIL (module `zecho.frontmatter` not found).

- [ ] **Step 3: Implement**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_frontmatter.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: markdown frontmatter parse/serialize"
```

### Task 2: `versions` compare

**Files:**
- Create: `zecho/versions.py`, `tests/test_versions.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_versions.py
from zecho import versions as v

def test_parse_version():
    assert v.parse_version("25.6.1") == (25, 6, 1)
    assert v.parse_version("25.6") == (25, 6)

def test_version_gt():
    assert v.version_gt("25.7.0", "25.6.1") is True
    assert v.version_gt("25.6.1", "25.6.1") is False
    assert v.version_gt("25.6", "25.6.1") is False

def test_newer_than_all():
    assert v.newer_than_all("25.7.0", ["25.6.0", "25.6.1"]) is True
    assert v.newer_than_all("25.6.1", ["25.6.0", "25.6.1"]) is False
    assert v.newer_than_all("25.6.0", ["25.6.1"]) is False
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_versions.py -q`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

```python
# zecho/versions.py
def parse_version(s: str):
    return tuple(int(p) for p in str(s).strip().split("."))

def version_gt(a: str, b: str) -> bool:
    return parse_version(a) > parse_version(b)

def newer_than_all(candidate: str, versions) -> bool:
    """True if candidate is strictly newer than every version in the list."""
    return all(version_gt(candidate, x) for x in versions)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_versions.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/versions.py tests/test_versions.py
git commit -m "feat: version compare helpers for verdict scoping"
```

### Task 3: `priority` scoring

**Files:**
- Create: `zecho/priority.py`, `tests/test_priority.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_priority.py
from zecho import priority as p

def test_severity_map():
    assert p.SEVERITY["high"] == 75
    assert p.SEVERITY["critical"] == 100

def test_compute_priority_bounds():
    score = p.compute_priority(impact=100, freq=50, segment=100, severity="critical")
    assert score == 100
    low = p.compute_priority(impact=0, freq=0, segment=0, severity="low")
    assert low == round(0.25 * 25)  # only severity contributes

def test_freq_capped():
    a = p.compute_priority(impact=0, freq=50, segment=0, severity="low")
    b = p.compute_priority(impact=0, freq=999, segment=0, severity="low")
    assert a == b  # freq capped at 50
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_priority.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# zecho/priority.py
SEVERITY = {"low": 25, "medium": 50, "high": 75, "critical": 100}
WEIGHTS = {"impact": 0.30, "freq": 0.30, "segment": 0.15, "severity": 0.25}

def compute_priority(impact: float, freq: int, segment: float, severity: str,
                     weights: dict = WEIGHTS) -> int:
    freq_norm = min(freq, 50) / 50 * 100
    sev = SEVERITY[severity]
    score = (weights["impact"] * impact
             + weights["freq"] * freq_norm
             + weights["segment"] * segment
             + weights["severity"] * sev)
    return round(score)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_priority.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/priority.py tests/test_priority.py
git commit -m "feat: transparent priority scoring"
```

---

## Phase 2 — Issue store (the pool)

### Task 4: `issues` — create / load / id allocation

**Files:**
- Create: `zecho/issues.py`, `tests/test_issues.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_issues.py
from zecho import issues

def test_next_id_empty(tmp_path):
    assert issues.next_issue_id(tmp_path) == "ISS-0001"

def test_create_and_load(tmp_path):
    iid = issues.create_issue(
        tmp_path,
        fields={"theme": "payment-qr-fail", "component": "payment, qr",
                "squad": "payment", "severity": "high", "priority": 82,
                "affected_versions": "25.6.0, 25.6.1", "affected_devices": "android-14",
                "freq": 1, "first_seen": "2026-06-15", "last_seen": "2026-06-15"},
        short_desc="QR payment spins then errors out, Android 14 only",
        title="QR payment fail on Android 14",
        symptoms=["scan QR then spinner then error", "Android 14 only"],
    )
    assert iid == "ISS-0001"
    meta, body = issues.load_issue(tmp_path, iid)
    assert meta["status"] == "new"
    assert meta["short_desc"].startswith("QR payment")
    assert "## Symptoms" in body
    assert issues.next_issue_id(tmp_path) == "ISS-0002"
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_issues.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement (part 1 of `issues.py`)**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_issues.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/issues.py tests/test_issues.py
git commit -m "feat: issue file create/load + id allocation"
```

### Task 5: `issues` — bump frequency, query by frontmatter

**Files:**
- Modify: `zecho/issues.py`, `tests/test_issues.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_issues.py
def _seed(tmp_path):
    issues.create_issue(tmp_path,
        fields={"component": "payment, qr", "squad": "payment", "severity": "high",
                "freq": 1, "last_seen": "2026-06-15"},
        short_desc="QR payment spins then errors out",
        title="QR fail", symptoms=["x"])

def test_bump_frequency(tmp_path):
    _seed(tmp_path)
    issues.bump_frequency(tmp_path, "ISS-0001", last_seen="2026-06-16")
    meta, _ = issues.load_issue(tmp_path, "ISS-0001")
    assert meta["freq"] == 2
    assert meta["last_seen"] == "2026-06-16"

def test_query_by_component(tmp_path):
    _seed(tmp_path)
    issues.create_issue(tmp_path,
        fields={"component": "chat", "squad": "messaging", "severity": "low", "freq": 1},
        short_desc="sticker won't load", title="sticker", symptoms=["y"])
    hits = issues.query(tmp_path, component_contains="payment")
    assert hits == ["ISS-0001"]
    all_ids = issues.query(tmp_path)
    assert all_ids == ["ISS-0001", "ISS-0002"]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_issues.py -q`
Expected: FAIL (`bump_frequency`/`query` missing).

- [ ] **Step 3: Implement (append to `issues.py`)**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_issues.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/issues.py tests/test_issues.py
git commit -m "feat: issue bump frequency + frontmatter query"
```

### Task 6: `issues` — reporters (append, list unnotified, mark notified)

**Files:**
- Modify: `zecho/issues.py`, `tests/test_issues.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_issues.py
def test_reporters_flow(tmp_path):
    _seed(tmp_path)
    issues.add_reporter(tmp_path, "ISS-0001", "@nvA", "zalo:group:prod-payment", "2026-06-15")
    issues.add_reporter(tmp_path, "ISS-0001", "@nvB", "zalo:dm", "2026-06-15")
    issues.add_reporter(tmp_path, "ISS-0001", "@nvA", "zalo:group:prod-payment", "2026-06-15")  # dup ignored
    rs = issues.unnotified_reporters(tmp_path, "ISS-0001")
    assert [r.handle for r in rs] == ["@nvA", "@nvB"]
    assert rs[0].channel == "zalo:group:prod-payment"
    issues.mark_notified(tmp_path, "ISS-0001", "@nvA")
    rs2 = issues.unnotified_reporters(tmp_path, "ISS-0001")
    assert [r.handle for r in rs2] == ["@nvB"]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_issues.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement (append to `issues.py`)**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_issues.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/issues.py tests/test_issues.py
git commit -m "feat: reporter tracking for close-loop"
```

### Task 7: `issues` — status + PO verdict write-back (reason required, version-scoped)

**Files:**
- Modify: `zecho/issues.py`, `tests/test_issues.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_issues.py
import pytest

def test_set_status(tmp_path):
    _seed(tmp_path)
    issues.set_status(tmp_path, "ISS-0001", "resolved")
    meta, _ = issues.load_issue(tmp_path, "ISS-0001")
    assert meta["status"] == "resolved"

def test_append_verdict_requires_reason(tmp_path):
    _seed(tmp_path)
    with pytest.raises(ValueError):
        issues.append_verdict(tmp_path, "ISS-0001", verdict="not_a_bug",
                              by="@po", reason="", scope_versions=["25.6.1"])

def test_append_verdict(tmp_path):
    _seed(tmp_path)
    issues.append_verdict(tmp_path, "ISS-0001", verdict="not_a_bug", by="@po",
                          reason="user had wrong timezone", scope_versions=["25.6.0", "25.6.1"])
    meta, body = issues.load_issue(tmp_path, "ISS-0001")
    assert "## PO verdict" in body
    assert "not_a_bug" in body
    assert "wrong timezone" in body
    v = issues.read_verdict(tmp_path, "ISS-0001")
    assert v["verdict"] == "not_a_bug"
    assert v["scope_versions"] == ["25.6.0", "25.6.1"]
    assert v["reason"]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_issues.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement (append to `issues.py`)**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_issues.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add zecho/issues.py tests/test_issues.py
git commit -m "feat: status + PO verdict write-back (reason required, version-scoped)"
```

---

## Phase 3 — Ownership routing

### Task 8: `ownership` parse + route

**Files:**
- Create: `zecho/ownership.py`, `tests/test_ownership.py`, `data/ownership.md`

- [ ] **Step 1: Create `data/ownership.md`**

```markdown
| squad | components | feedback_group_id | oncall |
|-------|-----------|-------------------|--------|
| payment | payment, qr, wallet | zalo:group:squad-payment | @oncall_pay |
| messaging | chat, sticker, call | zalo:group:squad-msg | @oncall_msg |
```

- [ ] **Step 2: Write failing test**

```python
# tests/test_ownership.py
from zecho import ownership

TABLE = "data/ownership.md"

def test_parse(tmp_path):
    p = tmp_path / "own.md"
    p.write_text(
        "| squad | components | feedback_group_id | oncall |\n"
        "|--|--|--|--|\n"
        "| payment | payment, qr | zalo:group:squad-payment | @oncall_pay |\n",
        encoding="utf-8")
    squads = ownership.parse_ownership(p)
    assert squads[0].name == "payment"
    assert "qr" in squads[0].components
    assert squads[0].feedback_group_id == "zalo:group:squad-payment"
    assert squads[0].oncall == "@oncall_pay"

def test_route(tmp_path):
    p = tmp_path / "own.md"
    p.write_text(
        "| squad | components | feedback_group_id | oncall |\n"
        "|--|--|--|--|\n"
        "| payment | payment, qr | g1 | @a |\n"
        "| messaging | chat | g2 | @b |\n", encoding="utf-8")
    squads = ownership.parse_ownership(p)
    assert ownership.route(squads, "qr").name == "payment"
    assert ownership.route(squads, "chat").name == "messaging"
    assert ownership.route(squads, "unknown") is None
```

- [ ] **Step 3: Run to verify fail**

Run: `python -m pytest tests/test_ownership.py -q`
Expected: FAIL.

- [ ] **Step 4: Implement**

```python
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
```

- [ ] **Step 5: Run to verify pass + commit**

Run: `python -m pytest tests/test_ownership.py -q`
Expected: PASS (2 passed).
```bash
git add zecho/ownership.py tests/test_ownership.py data/ownership.md
git commit -m "feat: ownership map parse + component routing"
```

---

## Phase 4 — Jira adapter (optional) + pool_jira script

### Task 9: `jira_adapter` protocol + Noop + Jira

**Files:**
- Create: `zecho/jira_adapter.py`, `tests/test_jira_adapter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_jira_adapter.py
from zecho import jira_adapter as ja

def test_noop_adapter():
    a = ja.NoopAdapter()
    assert a.upsert({"id": "ISS-0001"}, "body") is None
    assert a.recently_changed() == []

def test_jira_adapter_upsert(monkeypatch):
    calls = {}
    def fake_post(url, json, auth, timeout):
        calls["url"] = url
        calls["json"] = json
        class R:
            status_code = 201
            def json(self): return {"key": "PAY-2451"}
            def raise_for_status(self): pass
        return R()
    a = ja.JiraAdapter(base_url="https://j/", project="PAY",
                       email="e", token="t")
    monkeypatch.setattr(ja.requests, "post", fake_post)
    key = a.upsert({"id": "ISS-0001", "short_desc": "QR fail",
                    "severity": "high"}, "body text")
    assert key == "PAY-2451"
    assert calls["json"]["fields"]["project"]["key"] == "PAY"
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_jira_adapter.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# zecho/jira_adapter.py
from typing import Protocol
import requests

class Adapter(Protocol):
    def upsert(self, meta: dict, body: str): ...
    def recently_changed(self) -> list: ...

class NoopAdapter:
    """Used when Jira is disabled. Pool stays file-only."""
    def upsert(self, meta: dict, body: str):
        return None
    def recently_changed(self) -> list:
        return []

class JiraAdapter:
    def __init__(self, base_url, project, email, token):
        self.base_url = base_url.rstrip("/")
        self.project = project
        self.auth = (email, token)

    def upsert(self, meta: dict, body: str):
        if meta.get("jira_key"):
            return meta["jira_key"]  # already synced (V1: no field update)
        payload = {"fields": {
            "project": {"key": self.project},
            "summary": meta.get("short_desc", meta["id"]),
            "description": body,
            "issuetype": {"name": "Bug"},
        }}
        r = requests.post(f"{self.base_url}/rest/api/2/issue",
                          json=payload, auth=self.auth, timeout=20)
        r.raise_for_status()
        return r.json()["key"]

    def recently_changed(self, minutes: int = 5) -> list:
        jql = (f'project={self.project} AND status CHANGED TO '
               f'(Done,Resolved,"Won' + "'" + 't Fix",Invalid) AFTER -{minutes}m')
        r = requests.get(f"{self.base_url}/rest/api/2/search",
                         params={"jql": jql, "fields": "status,resolution,fixVersions"},
                         auth=self.auth, timeout=20)
        r.raise_for_status()
        out = []
        for it in r.json().get("issues", []):
            f = it["fields"]
            fixed = f["fixVersions"][0]["name"] if f.get("fixVersions") else None
            out.append({"key": it["key"], "status": f["status"]["name"], "fixed_in": fixed})
        return out
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_jira_adapter.py -q`
Expected: PASS (2 passed).
```bash
git add zecho/jira_adapter.py tests/test_jira_adapter.py
git commit -m "feat: optional Jira adapter (Noop + REST), file pool stays source of truth"
```

### Task 10: `scripts/pool_jira.py` — sync one issue, write back key

**Files:**
- Create: `scripts/pool_jira.py`, add test to `tests/test_scripts.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_scripts.py
import importlib, sys
from zecho import issues, frontmatter as fm

def _make_issue(tmp_path):
    issues.create_issue(tmp_path, fields={"component": "payment", "severity": "high", "freq": 1},
                        short_desc="QR fail", title="QR", symptoms=["x"])

def test_pool_jira_writes_back_key(tmp_path, monkeypatch):
    _make_issue(tmp_path)
    import scripts.pool_jira as pj
    class FakeAdapter:
        def upsert(self, meta, body): return "PAY-9001"
    monkeypatch.setattr(pj, "build_adapter", lambda: FakeAdapter())
    pj.run(str(tmp_path / "ISS-0001.md"))
    meta, _ = issues.load_issue(tmp_path, "ISS-0001")
    assert meta["jira_key"] == "PAY-9001"
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_scripts.py::test_pool_jira_writes_back_key -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# scripts/pool_jira.py
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zecho import frontmatter as fm
from zecho import jira_adapter as ja

def build_adapter():
    if os.environ.get("JIRA_BASE_URL"):
        return ja.JiraAdapter(os.environ["JIRA_BASE_URL"], os.environ["JIRA_PROJECT"],
                              os.environ["JIRA_EMAIL"], os.environ["JIRA_TOKEN"])
    return ja.NoopAdapter()

def run(issue_path: str):
    meta, body = fm.load(issue_path)
    key = build_adapter().upsert(meta, body)
    if key and meta.get("jira_key") != key:
        meta["jira_key"] = key
        fm.save(issue_path, meta, body)
    return key

if __name__ == "__main__":
    print(run(sys.argv[1]))
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_scripts.py::test_pool_jira_writes_back_key -q`
Expected: PASS.
```bash
git add scripts/pool_jira.py tests/test_scripts.py
git commit -m "feat: pool_jira script syncs issue to Jira + writes back key"
```

---

## Phase 5 — Close-loop toolkit (claw + render + closeloop selection)

### Task 11: `claw` send wrapper

**Files:**
- Create: `zecho/claw.py`, `tests/test_render.py` (claw smoke)

- [ ] **Step 1: Write failing test**

```python
# tests/test_render.py
from zecho import claw

def test_claw_send_uses_sink(monkeypatch):
    sent = []
    monkeypatch.setattr(claw, "_SINK", sent.append)
    claw.claw_send("zalo:dm:@nvA", "hi")
    assert sent == [{"channel": "zalo:dm:@nvA", "message": "hi"}]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_render.py::test_claw_send_uses_sink -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# zecho/claw.py
"""Thin Claw outbound wrapper. In Claw runtime, _SINK is replaced by the real
send. In tests, monkeypatch _SINK to capture messages."""
import json, sys

def _default_sink(payload):
    # Claw cron captures stdout lines prefixed CLAW_SEND as outbound messages.
    sys.stdout.write("CLAW_SEND " + json.dumps(payload, ensure_ascii=False) + "\n")

_SINK = _default_sink

def claw_send(channel: str, message: str) -> None:
    _SINK({"channel": channel, "message": message})
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_render.py::test_claw_send_uses_sink -q`
Expected: PASS.
```bash
git add zecho/claw.py tests/test_render.py
git commit -m "feat: claw send wrapper (mockable sink)"
```

### Task 12: `render` — close-loop + digest messages (bilingual)

**Files:**
- Create: `zecho/render.py`, add tests to `tests/test_render.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_render.py
from zecho import render

def test_render_close_msg_fixed_vi():
    msg = render.close_msg(jira_key="PAY-2451", verdict=None, reason=None,
                           fixed_in="25.7", lang="vi")
    assert "PAY-2451" in msg and "25.7" in msg

def test_render_close_msg_fixed_en_no_version():
    msg = render.close_msg(jira_key="PAY-1", verdict=None, reason=None, fixed_in=None, lang="en")
    assert "latest" in msg
    assert "mới nhất" not in msg

def test_render_close_msg_verdict_en():
    msg = render.close_msg(jira_key="PAY-2451", verdict="not_a_bug",
                           reason="wrong timezone", fixed_in=None, lang="en")
    assert "not_a_bug" in msg or "not a bug" in msg.lower()
    assert "wrong timezone" in msg

def test_render_squad_digest():
    items = [{"id": "ISS-0007", "short_desc": "QR payment fail", "severity": "high",
              "freq": 18, "jira_key": "PAY-2451"}]
    out = render.squad_digest("payment", items, reasons=["High mới"])
    assert "payment" in out.lower()
    assert "PAY-2451" in out
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_render.py -q`
Expected: FAIL (render funcs missing).

- [ ] **Step 3: Implement**

```python
# zecho/render.py
_FIXED = {
    "vi": "Cảm ơn bạn đã báo! Sự cố ({key}) đã được khắc phục ở phiên bản {ver} 🎉",
    "en": "Thanks for reporting! The issue ({key}) is fixed in version {ver} 🎉",
}
_VERDICT = {
    "vi": "Cập nhật về phản hồi của bạn ({key}): kết luận **{verdict}** — lý do: {reason}. "
          "Nếu bạn vẫn gặp lỗi, nhắn 'vẫn lỗi' để mình mở lại.",
    "en": "Update on your report ({key}): verdict **{verdict}** — reason: {reason}. "
          "If you still see the issue, reply 'still broken' to re-open.",
}

def close_msg(jira_key, verdict, reason, fixed_in, lang="vi") -> str:
    lang = lang if lang in ("vi", "en") else "vi"
    key = jira_key or "issue"
    if verdict and verdict != "fixed":
        return _VERDICT[lang].format(key=key, verdict=verdict, reason=reason)
    return _FIXED[lang].format(key=key, ver=fixed_in or ("latest" if lang == "en" else "mới nhất"))

def squad_digest(squad: str, items: list, reasons: list) -> str:
    head = f"🟠 [Squad {squad}] Daily feedback digest"
    if reasons:
        head += " — " + ", ".join(reasons)
    lines = [head]
    for it in items:
        key = it.get("jira_key", it["id"])
        lines.append(f"• [{it.get('severity','?')}] {it['short_desc']} — "
                     f"{it.get('freq','?')} báo cáo → {key}")
    return "\n".join(lines)

def po_digest(items: list) -> str:
    lines = ["📋 [PO] Daily rollup"]
    by_theme = {}
    for it in items:
        by_theme.setdefault(it.get("theme", it["id"]), 0)
        by_theme[it.get("theme", it["id"])] += int(it.get("freq", 0))
    for theme, vol in sorted(by_theme.items(), key=lambda kv: -kv[1]):
        lines.append(f"• {theme}: {vol} feedback")
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_render.py -q`
Expected: PASS (4 passed).
```bash
git add zecho/render.py tests/test_render.py
git commit -m "feat: bilingual close-loop + digest message rendering"
```

### Task 13: `zecho/closeloop.py` — deterministic notify selection + exactly-once mark

> This is the toolkit core of the `zecho-closeloop` skill. **Selection + marking are deterministic
> and tested here.** The skill (Task 20) only composes the message text per reporter language; the
> default `compose` (template) is used in tests and as fallback.

**Files:**
- Create: `zecho/closeloop.py`, `tests/test_closeloop.py`
- Modify: `zecho/issues.py` (add `find_by_jira_key`)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_closeloop.py
from zecho import issues, closeloop as cl

def test_pending_and_run_notifies_resolved(tmp_path, monkeypatch):
    issues.create_issue(tmp_path, fields={"component": "payment", "severity": "high",
                        "freq": 1, "status": "resolved", "fixed_in": "25.7",
                        "jira_key": "PAY-1"}, short_desc="QR fail", title="QR", symptoms=["x"])
    issues.add_reporter(tmp_path, "ISS-0001", "@nvA", "zalo:group:prod-payment", "2026-06-15")
    issues.add_reporter(tmp_path, "ISS-0001", "@nvB", "zalo:dm", "2026-06-15")
    # deterministic selection
    pend = cl.pending_notifications(str(tmp_path), lang_of=lambda iid, h: "vi")
    assert sorted(n.channel for n in pend) == ["zalo:dm", "zalo:group:prod-payment"]
    # run sends + marks exactly-once
    sent = []
    monkeypatch.setattr(cl.claw, "claw_send", lambda ch, m: sent.append((ch, m)))
    cl.run(issues_dir=str(tmp_path), adapter=cl.NoopAdapter(), lang_of=lambda iid, h: "vi")
    assert sorted(ch for ch, _ in sent) == ["zalo:dm", "zalo:group:prod-payment"]
    assert issues.unnotified_reporters(tmp_path, "ISS-0001") == []
    # second run is a no-op (exactly-once)
    sent.clear()
    cl.run(issues_dir=str(tmp_path), adapter=cl.NoopAdapter(), lang_of=lambda iid, h: "vi")
    assert sent == []

def test_awaiting_reason_blocks_notify(tmp_path, monkeypatch):
    issues.create_issue(tmp_path, fields={"component": "payment", "severity": "high",
                        "freq": 1, "status": "routed", "jira_key": "PAY-2"},
                        short_desc="QR fail", title="QR", symptoms=["x"])
    issues.add_reporter(tmp_path, "ISS-0001", "@nvA", "zalo:dm", "2026-06-15")
    sent = []
    monkeypatch.setattr(cl.claw, "claw_send", lambda ch, m: sent.append((ch, m)))
    class A(cl.NoopAdapter):
        def recently_changed(self):
            return [{"key": "PAY-2", "status": "Invalid", "fixed_in": None}]
    cl.run(issues_dir=str(tmp_path), adapter=A(), lang_of=lambda iid, h: "vi")
    meta, _ = issues.load_issue(tmp_path, "ISS-0001")
    assert meta["status"] == "awaiting_po_reason"
    # reporter NOT notified; exactly one message (the PO question)
    assert len(sent) == 1
    assert issues.unnotified_reporters(tmp_path, "ISS-0001")  # still pending
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_closeloop.py -q`
Expected: FAIL (`zecho.closeloop` missing).

- [ ] **Step 3: Add `find_by_jira_key` to `issues.py`**

```python
# append to zecho/issues.py
def find_by_jira_key(issues_dir, jira_key):
    for iid in list_issue_ids(issues_dir):
        meta, _ = load_issue(issues_dir, iid)
        if meta.get("jira_key") == jira_key:
            return iid
    return None
```

- [ ] **Step 4: Implement `zecho/closeloop.py`**

```python
# zecho/closeloop.py
from dataclasses import dataclass
from pathlib import Path
from zecho import issues, claw, render, frontmatter as fm
from zecho.jira_adapter import NoopAdapter

@dataclass
class Notification:
    iid: str
    handle: str
    channel: str
    jira_key: str
    verdict: str
    reason: str
    fixed_in: str
    lang: str

def reflect_jira(issues_dir, adapter, po_group="zalo:group:po"):
    """Apply Jira status changes into issue files (source of truth). If a verdict-type
    status arrives without a recorded reason, set awaiting_po_reason and ask the PO."""
    for ch in adapter.recently_changed():
        iid = issues.find_by_jira_key(issues_dir, ch["key"])
        if not iid:
            continue
        if ch["status"] in ("Done", "Resolved") or ch.get("fixed_in"):
            meta, body = issues.load_issue(issues_dir, iid)
            if ch.get("fixed_in"):
                meta["fixed_in"] = ch["fixed_in"]
            meta["status"] = "resolved"
            fm.save(Path(issues_dir) / f"{iid}.md", meta, body)
        elif issues.read_verdict(issues_dir, iid) is None:
            issues.set_status(issues_dir, iid, "awaiting_po_reason")
            claw.claw_send(po_group, f"@po cho 1 dòng lý do cho {ch['key']} ({ch['status']})?")

def pending_notifications(issues_dir, lang_of=None):
    """DETERMINISTIC: reporters that must be notified now — issue is resolved OR has a
    complete verdict, and is NOT awaiting_po_reason. Returns list[Notification]."""
    lang_of = lang_of or (lambda iid, handle: "vi")
    out = []
    for iid in issues.query(issues_dir):
        meta, _ = issues.load_issue(issues_dir, iid)
        status = meta.get("status")
        verdict = issues.read_verdict(issues_dir, iid)
        ready = status == "resolved" or (verdict is not None)
        if not ready or status == "awaiting_po_reason":
            continue
        for r in issues.unnotified_reporters(issues_dir, iid):
            out.append(Notification(
                iid=iid, handle=r.handle, channel=r.channel,
                jira_key=meta.get("jira_key"),
                verdict=(verdict or {}).get("verdict"),
                reason=(verdict or {}).get("reason"),
                fixed_in=meta.get("fixed_in"),
                lang=lang_of(iid, r.handle)))
    return out

def default_compose(n: Notification) -> str:
    """Template fallback. The zecho-closeloop skill overrides this with LLM text."""
    return render.close_msg(jira_key=n.jira_key, verdict=n.verdict,
                            reason=n.reason, fixed_in=n.fixed_in, lang=n.lang)

def run(issues_dir, adapter=None, lang_of=None, compose=None, po_group="zalo:group:po"):
    """Full deterministic cycle: reflect Jira → for each pending notification, send via
    `compose` then mark notified (exactly-once)."""
    adapter = adapter or NoopAdapter()
    compose = compose or default_compose
    reflect_jira(issues_dir, adapter, po_group)
    for n in pending_notifications(issues_dir, lang_of):
        claw.claw_send(n.channel, compose(n))
        issues.mark_notified(issues_dir, n.iid, n.handle)
```

- [ ] **Step 5: Run to verify pass + commit**

Run: `python -m pytest tests/test_closeloop.py -q`
Expected: PASS (2 passed).
```bash
git add zecho/closeloop.py zecho/issues.py tests/test_closeloop.py
git commit -m "feat: closeloop toolkit — deterministic notify selection + exactly-once mark"
```

---

## Phase 6 — Daily digest

### Task 14: `threshold` notice evaluation

**Files:**
- Create: `zecho/threshold.py`, `tests/test_threshold.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_threshold.py
from zecho import threshold as th
from datetime import datetime

CFG = th.NoticeConfig()  # defaults: spike_pct=0.5, spike_abs=10, sla_high_h=4, sla_critical_h=1

def test_high_new_triggers():
    issues = [{"id": "ISS-1", "severity": "high", "status": "routed",
               "freq": 2, "prev_freq": 2, "first_seen_hours": 1, "ack": False}]
    assert "High mới" in th.notice_reasons(issues, CFG)

def test_spike_triggers():
    issues = [{"id": "ISS-1", "severity": "medium", "status": "routed",
               "freq": 20, "prev_freq": 5, "first_seen_hours": 100, "ack": True}]
    reasons = th.notice_reasons(issues, CFG)
    assert any("Spike" in r for r in reasons)

def test_quiet_day_no_reason():
    issues = [{"id": "ISS-1", "severity": "low", "status": "routed",
               "freq": 3, "prev_freq": 3, "first_seen_hours": 100, "ack": True}]
    assert th.notice_reasons(issues, CFG) == []
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_threshold.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# zecho/threshold.py
from dataclasses import dataclass

@dataclass
class NoticeConfig:
    spike_pct: float = 0.5
    spike_abs: int = 10
    sla_high_h: int = 4
    sla_critical_h: int = 1

def notice_reasons(issues: list, cfg: NoticeConfig = NoticeConfig()) -> list:
    """issues: list of dicts with keys severity, status, freq, prev_freq,
    first_seen_hours, ack(bool). Returns list of human reasons (empty => stay silent)."""
    reasons = []
    for it in issues:
        sev = it.get("severity")
        if sev in ("high", "critical") and it.get("first_seen_hours", 999) <= 24:
            reasons.append("High mới")
        prev = it.get("prev_freq", 0)
        grew = it.get("freq", 0) - prev
        if prev > 0 and (grew >= cfg.spike_abs or grew / prev >= cfg.spike_pct):
            reasons.append(f"Spike {it['id']}")
        if not it.get("ack", True):
            limit = cfg.sla_critical_h if sev == "critical" else cfg.sla_high_h
            if sev in ("high", "critical") and it.get("first_seen_hours", 0) >= limit:
                reasons.append(f"SLA breach {it['id']}")
        if it.get("status") == "resolved" and it.get("freq", 0) > it.get("prev_freq", 0):
            reasons.append(f"Recurring {it['id']}")
    # dedupe preserving order
    seen, out = set(), []
    for r in reasons:
        if r not in seen:
            seen.add(r); out.append(r)
    return out
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_threshold.py -q`
Expected: PASS (3 passed).
```bash
git add zecho/threshold.py tests/test_threshold.py
git commit -m "feat: daily-digest notice-threshold evaluation"
```

### Task 15: `zecho/digest.py` — deterministic collection (per-squad data + threshold + PO rollup)

> Toolkit core of the `zecho-digest` skill. **Collection + threshold are deterministic and tested
> here.** The skill (Task 21) turns the returned structured data into narrative prose; the
> `render.*` templates are the test/fallback path.

**Files:**
- Create: `zecho/digest.py`, `tests/test_digest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_digest.py
from zecho import issues, digest

def _ownership(tmp_path):
    own = tmp_path / "ownership.md"
    own.write_text("| squad | components | feedback_group_id | oncall |\n|--|--|--|--|\n"
                   "| payment | payment | zalo:group:squad-payment | @op |\n"
                   "| messaging | chat | zalo:group:squad-msg | @om |\n", encoding="utf-8")
    return own

def test_squad_reports_gating(tmp_path):
    own = _ownership(tmp_path)
    idir = tmp_path / "issues"
    issues.create_issue(idir, fields={"component": "payment", "squad": "payment",
        "severity": "high", "freq": 1, "theme": "qr", "status": "routed"},
        short_desc="QR fail", title="QR", symptoms=["x"])
    issues.create_issue(idir, fields={"component": "chat", "squad": "messaging",
        "severity": "low", "freq": 1, "theme": "sticker", "status": "routed"},
        short_desc="sticker", title="S", symptoms=["y"])
    reports, all_items = digest.squad_reports(str(idir), str(own),
        metrics=lambda iid: {"first_seen_hours": 1, "prev_freq": 0, "ack": False})
    by = {r["squad"].name: r for r in reports}
    assert by["payment"]["reasons"]        # High mới -> should post
    assert by["messaging"]["reasons"] == []  # quiet -> stay silent
    assert len(all_items) == 2
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_digest.py -q`
Expected: FAIL (`zecho.digest` missing).

- [ ] **Step 3: Implement `zecho/digest.py`**

```python
# zecho/digest.py
from zecho import issues, ownership, threshold

def squad_reports(issues_dir, ownership_path, metrics=None):
    """DETERMINISTIC. Return (reports, all_items) where reports is a list of
    {squad, items, reasons}. A squad with empty reasons must NOT be posted.
    `metrics(iid)` supplies first_seen_hours/prev_freq/ack for threshold checks."""
    metrics = metrics or (lambda iid: {"first_seen_hours": 999, "prev_freq": 0, "ack": True})
    squads = ownership.parse_ownership(ownership_path)
    reports, all_items = [], []
    for s in squads:
        items = []
        for iid in issues.query(issues_dir, squad=s.name):
            meta, _ = issues.load_issue(issues_dir, iid)
            d = {**meta, **metrics(iid)}
            items.append(d)
            all_items.append(d)
        reasons = threshold.notice_reasons(items)
        reports.append({"squad": s, "items": items, "reasons": reasons})
    return reports, all_items

def run(issues_dir, ownership_path, po_group, metrics=None, compose_squad=None, compose_po=None):
    """Template/fallback driver (the skill overrides compose_* with LLM narrative)."""
    from zecho import render, claw
    compose_squad = compose_squad or (lambda sq, items, reasons: render.squad_digest(sq.name, items, reasons))
    compose_po = compose_po or (lambda items: render.po_digest(items))
    reports, all_items = squad_reports(issues_dir, ownership_path, metrics)
    for rep in reports:
        if rep["reasons"]:
            claw.claw_send(rep["squad"].feedback_group_id,
                           compose_squad(rep["squad"], rep["items"], rep["reasons"]))
    claw.claw_send(po_group, compose_po(all_items))
```

- [ ] **Step 4: Run to verify pass + commit**

Run: `python -m pytest tests/test_digest.py -q`
Expected: PASS (1 passed).
```bash
git add zecho/digest.py tests/test_digest.py
git commit -m "feat: digest toolkit — deterministic per-squad collection + threshold gating"
```

---

## Phase 7 — Skills (Claw prompts; each imports the toolkit)

> These tasks author the Claw skill prompts. "Tests" here are scenario fixtures + a manual
> checklist (`scenarios/README.md`), since dedup/clarify/narrative are LLM behavior. The
> deterministic parts they rely on are already tested in the toolkit (Phases 1–6).

### Task 16: `zecho-triage` skill — pipeline overview + language rule + slots

**Files:**
- Create: `skills/zecho-triage/SKILL.md`

- [ ] **Step 1: Write SKILL.md (full content)**

```markdown
---
name: zecho-triage
description: >
  Voice-of-Customer triage agent for internal Zalo product feedback. Use when an
  employee tags the bot with a bug/feedback (optionally with a screenshot) in a Zalo
  group or DM. Captures, clarifies, deduplicates against the pool, routes to the owning
  squad, and pools as an issue file.
---

# Z-Echo — Voice-of-Customer triage agent

You turn raw internal feedback into a clean, deduplicated, routed backlog. The pool lives
in `data/issues/*.md` (markdown + YAML frontmatter) and is the **source of truth**. You
operate it with native file tools: `grep`, `glob`, `view`, `edit`, `create`, and the tested
Python toolkit `zecho/` (e.g. `python -c "from zecho import issues; ..."`) for any
must-be-correct mutation (id allocation, freq bump, reporter append). Proactive flows
(close-loop, digest) are SEPARATE skills run by Claw cron — not your job here.

## Language rule (strict)
- Accept feedback in **English or Vietnamese**.
- **Frontmatter is always English** (every field, including `short_desc`) — translate/normalize.
- **Body keeps the reporter's original language** (their words, `## Symptoms`, verdict reason).
- **Reply to the reporter in their language** (the `lang` you detected: `vi` or `en`).

## Pipeline (per inbound feedback)
1. ENRICH — if a screenshot is attached, read it: infer screen, error state, app_version,
   device. Detect `lang`. Create `data/feedback/<YYYY-MM-DD>/fb_<id>.md` (frontmatter EN,
   body original).
2. CLARIFY — compute missing slots for the issue_type (table below). Ask at most **2–3**
   questions; skip any slot the screenshot already filled; then proceed with what you have.
3. VALIDATE/DEDUP — see "Dedup (2-tier)" below. Decide: known | fixed | verdict | self | spam | new.
4. SYNTHESIZE — for `new`: write `short_desc` (English, describe the underlying problem),
   pick `component`, `theme`, `severity`; compute priority via the documented formula.
5. ROUTE — read `data/ownership.md`; map `component` → squad/group/oncall.
6. POOL — create or +1 the issue file; append the reporter; (Jira optional via pool_jira.py).

## Slot templates (information-gap)
| issue_type | required slots |
|---|---|
| crash | device, os_version, app_version, repro_steps |
| ux_complaint | screen/flow, expectation |
| payment_fail | txn_id, amount, time, method |
| performance | screen, network, frequency |
| feature_request | use_case, current_workaround |
```

- [ ] **Step 2: Verify the file exists and is valid markdown**

Run: `python -c "import pathlib; assert pathlib.Path('skills/zecho-triage/SKILL.md').read_text(encoding='utf-8').startswith('---')"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add skills/zecho-triage/SKILL.md
git commit -m "docs: zecho-triage skill — pipeline overview + language rule + slots"
```

### Task 17: `zecho-triage` skill — Dedup (2-tier) + Validate branches

**Files:**
- Modify: `skills/zecho-triage/SKILL.md`

- [ ] **Step 1: Append the dedup + validate section**

````markdown
## Dedup (2-tier — no keywords)
1. **Narrow** by `component` (a stable enum): `grep -rl "component: <comp>" data/issues/`.
   `component` may be multi-value; if the narrow set is empty, **widen**: read the
   `short_desc` line of ALL issues (one line each, cheap at V1 scale).
2. **Read `short_desc`** of the candidates (English, in frontmatter) → shortlist suspects.
3. **Fetch full body** of each suspect (`view` the file, read `## Symptoms`) → judge if it is
   truly the same underlying problem. The new feedback may be VI and the issue body EN (or
   vice-versa) — compare meaning across languages.

## Validate branches (decision)
- **known** (same underlying problem, no blocking verdict): +1 the issue via toolkit
  (`issues.bump_frequency`, `issues.add_reporter`); if the new wording reveals a new facet,
  refine `short_desc`/`## Symptoms` with `edit`. Reply that it is a known issue being tracked.
- **fixed** (a matching issue has `fixed_in` ≤ a version older than the user's): tell them to
  update to that version.
- **verdict** (a matching issue has a `## PO verdict`):
  - If the user's `app_version` is **newer than all** `scope_versions` → do NOT deflect;
    treat as a possible regression: **re-open** (set issue status back to `routed`) and +1.
  - Else **soft-deflect**: relay the verdict + reason, and add an escape hatch: tell them to
    reply "vẫn lỗi"/"still broken" to escalate. If they do, drop the deflect and escalate.
- **self** (a general rule in `data/kb/*.md` explains it is not a bug / user-fixable):
  reply with the self-fix.
- **spam/abuse**: drop (set feedback status `dropped`).
- **new**: continue to SYNTHESIZE → ROUTE → POOL.

## Realtime escalation
If `severity` is `critical` at POOL time, immediately message the squad `oncall` (from
ownership.md) — do not wait for the daily digest.
````

- [ ] **Step 2: Commit**

```bash
git add skills/zecho-triage/SKILL.md
git commit -m "docs: zecho-triage skill — dedup 2-tier + validate branches + verdict guards"
```

### Task 18: `zecho-triage` skill — file format reference (exact frontmatter)

**Files:**
- Modify: `skills/zecho-triage/SKILL.md`

- [ ] **Step 1: Append the file-format reference**

````markdown
## Issue file format (write exactly this shape)
```markdown
---
id: ISS-0007
jira_key:                # optional; set by pool_jira.py
status: routed           # new|routed|awaiting_po_reason|in_progress|resolved|closed
theme: payment-qr-fail
component: payment, qr
squad: payment
severity: high           # low|medium|high|critical
priority: 82
affected_versions: 25.6.0, 25.6.1
affected_devices: android-14
fixed_in:
freq: 1
first_seen: 2026-06-15
last_seen: 2026-06-15
short_desc: QR payment spins then errors out, Android 14 only
---
# <English title>
## Symptoms
- <merged symptom lines, may be EN>
## Reporters
- @nvA | zalo:group:prod-payment | 2026-06-15 | notified:no
```

## Feedback file format
```markdown
---
id: fb_0042
reporter: @nvA
channel: zalo:group:prod-payment
issue_type: payment_fail
app_version: 25.6.1
device: android-14
lang: vi
status: pooled           # new|clarifying|pooled|deflected|dropped
linked_issue: ISS-0007
created_at: 2026-06-15T22:10
---
<original-language feedback text>
```

## PO verdict block (append to issue body)
```markdown
## PO verdict
- verdict: not_a_bug     # not_a_bug|wont_fix|invalid|backlog|fixed
- by: @po_pay | 2026-06-15
- reason: <REQUIRED one line>
- scope_versions: 25.6.0, 25.6.1
```
A verdict without a `reason` is invalid — set issue `status: awaiting_po_reason` and ask the
PO for one line before notifying reporters.
````

- [ ] **Step 2: Commit**

```bash
git add skills/zecho-triage/SKILL.md
git commit -m "docs: zecho-triage skill — exact file formats for issue/feedback/verdict"
```

### Task 18B: `zecho-verdict`, `zecho-closeloop`, `zecho-digest` skills

> Three more skills, each thin: they call the tested toolkit for correctness and add LLM
> judgment/language. The verdict skill is reactive (PO tags bot); the other two are launched
> by Claw cron (Task 21).

**Files:**
- Create: `skills/zecho-verdict/SKILL.md`, `skills/zecho-closeloop/SKILL.md`, `skills/zecho-digest/SKILL.md`

- [ ] **Step 1: Write `skills/zecho-verdict/SKILL.md`**

````markdown
---
name: zecho-verdict
description: >
  Records a Product Owner's verdict on a pooled issue. Use when a PO tags the bot in a squad
  group (or replies on an issue) to rule on it: not a bug / won't fix / invalid / backlog /
  fixed, WITH a one-line reason. Writes the verdict back into the issue so future duplicates
  are auto-handled.
---

# Z-Echo — PO verdict write-back

When a PO rules on an issue:
1. Identify the issue id (they reference `ISS-xxxx` or a Jira key; resolve via
   `grep` / `issues.find_by_jira_key`).
2. Require a **one-line reason**. If missing, ask for exactly one line — do not proceed.
3. Determine `scope_versions` = the issue's current `affected_versions` (the verdict only
   applies to these; a newer version may regress).
4. Write it with the toolkit (keeps YAML valid, enforces reason):
   `python -c "from zecho import issues; issues.append_verdict('data/issues','ISS-0007', verdict='not_a_bug', by='@po_pay', reason='<one line>', scope_versions=['25.6.0','25.6.1'])"`
5. **Issue vs general rule:** "Would this verdict still be true for a DIFFERENT issue?
   Yes → also write a general rule in `data/kb/<topic>.md` (so the triage `self` branch can
   use it). No → it stays in the issue file only."

Reporters are NOT notified here — that is the `zecho-closeloop` skill's job on the next cron tick.
````

- [ ] **Step 2: Write `skills/zecho-closeloop/SKILL.md`**

````markdown
---
name: zecho-closeloop
description: >
  Proactive close-the-loop notifier. Launched by Claw cron (~5 min). Notifies every reporter
  of a resolved/verdicted issue, on their ORIGINAL channel, in their language — exactly once.
---

# Z-Echo — close-the-loop

Run on each cron tick:
1. Reflect external state (optional Jira) into the file pool:
   `python -c "from zecho import closeloop, scripts; ..."` — use `closeloop.reflect_jira(issues_dir, adapter)`.
   (With no Jira, this is a no-op; verdicts arrive via the zecho-verdict skill.)
2. Get the deterministic worklist (the toolkit decides WHO, never you):
   `from zecho import closeloop; pend = closeloop.pending_notifications('data/issues', lang_of=...)`
3. For EACH `Notification n` in `pend`:
   - Compose the message yourself in `n.lang` (vi/en): thank them; if `n.fixed_in` say it is
     fixed in that version; if `n.verdict` relay verdict + `n.reason` and add the escape hatch
     ("reply 'vẫn lỗi'/'still broken' to re-open").
   - `claw_send(n.channel, <your text>)` then mark done via
     `issues.mark_notified('data/issues', n.iid, n.handle)`.
4. Never notify an issue whose status is `awaiting_po_reason` (the toolkit already excludes it).

The selection and the mark are deterministic (toolkit). You only write the words.
If you prefer a non-LLM fallback, `closeloop.run(...)` does the whole cycle with templates.
````

- [ ] **Step 3: Write `skills/zecho-digest/SKILL.md`**

````markdown
---
name: zecho-digest
description: >
  Proactive daily digest. Launched by Claw cron (09:00). Posts a per-squad digest ONLY when a
  notice threshold is crossed, plus a PO rollup. Writes narrative, not a flat dump.
---

# Z-Echo — daily digest

Run once per day:
1. Collect deterministic data + threshold reasons (the toolkit decides whether a squad
   qualifies, never you):
   `from zecho import digest; reports, all_items = digest.squad_reports('data/issues','data/ownership.md', metrics=...)`
   (`metrics(iid)` supplies first_seen_hours / prev_freq / ack; in V1 derive from issue dates.)
2. For EACH `report` with non-empty `report["reasons"]`:
   - Write a short **narrative** for `report["items"]` (what's new/spiking/recurring, what to
     ack, trend vs yesterday) — not a flat list.
   - `claw_send(report["squad"].feedback_group_id, <your narrative>)`.
   - Squads with empty `reasons` → **stay silent** (do not post).
3. Write a PO rollup from `all_items` (top themes by volume, new vs recurring, deltas) and
   `claw_send('zalo:group:po', <rollup>)`.

Template fallback for testing: `digest.run('data/issues','data/ownership.md','zalo:group:po')`.
````

- [ ] **Step 4: Verify all three exist**

Run: `python -c "import pathlib; [pathlib.Path(f'skills/{s}/SKILL.md').read_text(encoding='utf-8') for s in ('zecho-verdict','zecho-closeloop','zecho-digest')]"`
Expected: no error.

- [ ] **Step 5: Commit**

```bash
git add skills/zecho-verdict/SKILL.md skills/zecho-closeloop/SKILL.md skills/zecho-digest/SKILL.md
git commit -m "docs: zecho-verdict + zecho-closeloop + zecho-digest skills"
```

---

## Phase 8 — Seed data, scenarios, cron, README

### Task 19: Seed pool + feedback fixtures (real + synthetic)

**Files:**
- Create: `tests/fixtures/issues/ISS-0007.md`, `tests/fixtures/issues/ISS-0008.md`, `tests/fixtures/feedback/dup_qr.md`, `tests/fixtures/feedback/new_login.md`, `tests/fixtures/feedback/verdict_timezone.md`
- Create: `scripts/seed.py`

- [ ] **Step 1: Create two seed issues**

```markdown
<!-- tests/fixtures/issues/ISS-0007.md -->
---
id: ISS-0007
jira_key: PAY-2451
status: routed
theme: payment-qr-fail
component: payment, qr
squad: payment
severity: high
priority: 82
affected_versions: 25.6.0, 25.6.1
affected_devices: android-14
fixed_in:
freq: 18
first_seen: 2026-06-14
last_seen: 2026-06-15
short_desc: QR payment spins then errors out, Android 14 only
---
# QR payment fail on Android 14
## Symptoms
- scan QR then spinner then error
- Android 14 only, 25.6.x
## Reporters
- @nvA | zalo:group:prod-payment | 2026-06-15 | notified:no
```

```markdown
<!-- tests/fixtures/issues/ISS-0008.md -->
---
id: ISS-0008
jira_key: ACC-1190
status: closed
theme: clock-display
component: account, settings
squad: account
severity: low
priority: 30
affected_versions: 25.6.0, 25.6.1
affected_devices: ios-17
fixed_in:
freq: 4
first_seen: 2026-06-13
last_seen: 2026-06-14
short_desc: Clock shows wrong time after travel across timezones
---
# Wrong clock after timezone change
## Symptoms
- time off by hours after flying
## Reporters
- @nvC | zalo:dm | 2026-06-14 | notified:no
## PO verdict
- verdict: not_a_bug
- by: @po_acc | 2026-06-14
- reason: device timezone set to manual; app follows OS setting
- scope_versions: 25.6.0, 25.6.1
```

- [ ] **Step 2: Create three feedback scenario files**

```markdown
<!-- tests/fixtures/feedback/dup_qr.md  (should DEDUP into ISS-0007) -->
---
id: fb_1001
reporter: @nvD
channel: zalo:group:prod-payment
issue_type: payment_fail
app_version: 25.6.1
device: android-14
lang: vi
status: new
linked_issue:
created_at: 2026-06-16T09:00
---
Mình quét mã QR để trả tiền thì nó quay quay rồi báo lỗi, máy Android 14.
```

```markdown
<!-- tests/fixtures/feedback/new_login.md  (should be NEW, route to a login/account squad) -->
---
id: fb_1002
reporter: @nvE
channel: zalo:dm
issue_type: crash
app_version: 25.6.1
device: ios-17
lang: en
status: new
linked_issue:
created_at: 2026-06-16T09:05
---
App crashes right after I tap "Login with OTP" on iPhone.
```

```markdown
<!-- tests/fixtures/feedback/verdict_timezone.md (matches ISS-0008 verdict; same version -> soft-deflect) -->
---
id: fb_1003
reporter: @nvF
channel: zalo:dm
issue_type: ux_complaint
app_version: 25.6.1
device: ios-17
lang: vi
status: new
linked_issue:
created_at: 2026-06-16T09:10
---
Đồng hồ trong app hiển thị sai giờ sau khi mình đi nước ngoài về.
```

- [ ] **Step 3: Create `scripts/seed.py` to copy fixtures into a working `data/`**

```python
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
```

- [ ] **Step 4: Verify seed runs**

Run: `python scripts/seed.py data` then `python -c "from zecho import issues; print(issues.query('data/issues'))"`
Expected: `['ISS-0007', 'ISS-0008']`

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures scripts/seed.py
git commit -m "test: seed pool + feedback scenario fixtures (real+synthetic)"
```

### Task 20: Acceptance scenarios doc (maps to A1–A5)

**Files:**
- Create: `scenarios/README.md`

- [ ] **Step 1: Write the acceptance checklist**

```markdown
# Acceptance scenarios (map to spec §8)

Run `python scripts/seed.py data` first. Drive the agent via Claw with the fixture feedback.

## A1 — Dedup
- Send `tests/fixtures/feedback/dup_qr.md` content → agent must +1 **ISS-0007**
  (freq 18→19, reporter @nvD appended), NOT create a new issue.
- Send `tests/fixtures/feedback/new_login.md` → agent creates a NEW issue (ISS-0009) and
  routes it (login/account). Verify with `grep -rl "short_desc" data/issues/`.

## A2 — Close-loop
- `python -c "from zecho import issues; issues.set_status('data/issues','ISS-0007','resolved')"`
  then set `fixed_in: 25.7` in the file.
- Run the close-loop cycle:
  `python -c "from zecho import closeloop; closeloop.run(issues_dir='data/issues')"`.
  Verify each reporter of ISS-0007 receives a message on their **original channel** and is
  marked `notified:yes`. (In Claw, the `zecho-closeloop` skill does this with LLM-composed text.)

## A3 — Learning (verdict reuse, version guard)
- Send `verdict_timezone.md` (app_version 25.6.1 = within ISS-0008 scope_versions) →
  agent **soft-deflects** with the recorded reason + escape hatch.
- Change its `app_version` to `25.8.0` (newer than scope) → agent must NOT deflect; re-open.

## A4 — Digest
- Run `python -c "from zecho import digest; digest.run('data/issues','data/ownership.md','zalo:group:po')"`.
  A squad with a High-new/spike issue gets a post; a quiet squad gets none; PO group gets a
  rollup. (In Claw, the `zecho-digest` skill writes the narrative.)

## A5 — Jira-optional
- Unset JIRA_* env vars. Re-run A1–A4. All must pass using the file pool only
  (`pool_jira.py` returns None; closeloop uses NoopAdapter).
```

- [ ] **Step 2: Commit**

```bash
git add scenarios/README.md
git commit -m "docs: acceptance scenarios mapped to A1-A5"
```

### Task 21: Cron declaration + run docs

**Files:**
- Create: `cron.md` (Claw cron schedule), `README.md`

- [ ] **Step 1: Write `cron.md`**

```markdown
# Claw cron schedule for Z-Echo

Cron launches a SKILL (an agent turn), which calls the tested toolkit:
- every 5 minutes → launch skill `zecho-closeloop`
- 09:00 daily     → launch skill `zecho-digest`

Non-LLM fallback (pure toolkit, for CI/smoke):
- close-loop: `python -c "from zecho import closeloop; closeloop.run(issues_dir='data/issues')"`
- digest:     `python -c "from zecho import digest; digest.run('data/issues','data/ownership.md','zalo:group:po')"`

Environment (optional Jira; omit to run file-only):
- JIRA_BASE_URL, JIRA_PROJECT, JIRA_EMAIL, JIRA_TOKEN
- ZECHO_DATA (default `data`), ZECHO_PO_GROUP (default `zalo:group:po`)
```

- [ ] **Step 2: Write `README.md`** (project root)

```markdown
# Z-Echo — Voice-of-Customer Agent (Claw skills + toolkit)

Internal Zalo feedback → deduplicated, routed, self-learning backlog with proactive
close-loop + digests. File-based pool (`data/issues/`) is the source of truth; Jira is optional.

Four Claw skills share one tested toolkit `zecho/`:
`zecho-triage` (reactive pipeline), `zecho-verdict` (PO write-back), `zecho-closeloop` (cron),
`zecho-digest` (cron). Must-be-correct logic lives in the toolkit; skills add judgment + language.

## Quickstart
```bash
python -m pip install -e .
python -m pytest -q
python scripts/seed.py data
```
See `docs/specs/2026-06-16-zecho-voc-agent-design.md` (spec), `docs/architecture.md`,
`scenarios/README.md` (acceptance), `cron.md` (schedule), `skills/*/SKILL.md` (agent prompts).
```

- [ ] **Step 3: Run the full suite green**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add cron.md README.md
git commit -m "docs: cron schedule (skills) + project README"
```

---

## Final verification (run after all tasks)

- [ ] `python -m pytest -q` → all green.
- [ ] `python scripts/seed.py data` → `data/issues/ISS-0007.md`, `ISS-0008.md` exist.
- [ ] `python -c "from zecho import digest; digest.run('data/issues','data/ownership.md','zalo:group:po')"` → prints `CLAW_SEND ...` lines.
- [ ] Walk `scenarios/README.md` A1–A5 with the agent via Claw; all five pass.
- [ ] Confirm A5 passes with all `JIRA_*` env vars unset (file-only pool).

---

## Spec coverage map (self-review)

| Spec requirement | Task(s) |
|---|---|
| G1 multimodal intake (vision core) | 16 (ENRICH), 19 fixtures |
| G2 clarify (gap, ≤2–3, stop) | 16 (slots) |
| G3 dedup 2-tier short_desc | 4–6, 17 |
| G4 validate/deflect (soft) | 17 |
| G5 synthesize + route | 3, 8, 16 |
| G6 close-loop (original channel) | 11–13, 18B (zecho-closeloop) |
| G7 daily digest (gated) + PO + escalation | 14–15, 17, 18B (zecho-digest) |
| G8 learning (verdict, version-scoped) | 7, 17, 18B (zecho-verdict), 19 |
| G9 Jira-optional | 9–10, 13 (NoopAdapter), 20 (A5) |
| D5 channel-original notify | 12–13, 18B |
| D8 verdict version guard | 2, 17, 20 (A3) |
| D12 i18n frontmatter EN / body original | 12, 16, 19 |
| Multi-skill packaging (D4) | 16, 17, 18, 18B |
| Acceptance A1–A5 | 20, final verification |
```
