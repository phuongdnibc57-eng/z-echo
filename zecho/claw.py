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
