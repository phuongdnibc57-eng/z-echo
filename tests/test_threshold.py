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
