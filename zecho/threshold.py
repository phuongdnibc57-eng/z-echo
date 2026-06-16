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
