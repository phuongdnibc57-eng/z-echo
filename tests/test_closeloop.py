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
