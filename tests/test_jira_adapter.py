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
