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
