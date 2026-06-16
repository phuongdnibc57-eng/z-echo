# zecho/digest.py
from zecho import issues, ownership, threshold

def squad_reports(issues_dir, ownership_path, metrics=None):
    """DETERMINISTIC. Return (reports, all_items) where reports is a list of
    {squad, items, reasons}. A squad with empty reasons must NOT be posted.
    `metrics(iid)` supplies first_seen_hours/prev_freq/ack for threshold checks."""
    metrics = metrics or (lambda iid: {"first_seen_hours": 999, "prev_freq": 0, "ack": True})
    squads = ownership.parse_ownership(ownership_path)
    reports, all_items = [], []
    for s in squads:
        items = []
        for iid in issues.query(issues_dir, squad=s.name):
            meta, _ = issues.load_issue(issues_dir, iid)
            d = {**meta, **metrics(iid)}
            items.append(d)
            all_items.append(d)
        reasons = threshold.notice_reasons(items)
        reports.append({"squad": s, "items": items, "reasons": reasons})
    return reports, all_items

def run(issues_dir, ownership_path, po_group, metrics=None, compose_squad=None, compose_po=None):
    """Template/fallback driver (the skill overrides compose_* with LLM narrative)."""
    from zecho import render, claw
    compose_squad = compose_squad or (lambda sq, items, reasons: render.squad_digest(sq.name, items, reasons))
    compose_po = compose_po or (lambda items: render.po_digest(items))
    reports, all_items = squad_reports(issues_dir, ownership_path, metrics)
    for rep in reports:
        if rep["reasons"]:
            claw.claw_send(rep["squad"].feedback_group_id,
                           compose_squad(rep["squad"], rep["items"], rep["reasons"]))
    claw.claw_send(po_group, compose_po(all_items))
