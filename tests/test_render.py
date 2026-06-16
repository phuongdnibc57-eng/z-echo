# tests/test_render.py
from zecho import claw

def test_claw_send_uses_sink(monkeypatch):
    sent = []
    monkeypatch.setattr(claw, "_SINK", sent.append)
    claw.claw_send("zalo:dm:@nvA", "hi")
    assert sent == [{"channel": "zalo:dm:@nvA", "message": "hi"}]

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
