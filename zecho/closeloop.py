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
