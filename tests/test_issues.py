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
