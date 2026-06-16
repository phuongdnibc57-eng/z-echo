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
