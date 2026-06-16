---
name: zecho-digest
description: >
  Proactive daily digest. Launched by Claw cron (09:00). Posts a per-squad digest ONLY when a
  notice threshold is crossed, plus a PO rollup. Writes narrative, not a flat dump.
---

# Z-Echo — daily digest

Run once per day:
1. Collect deterministic data + threshold reasons (the toolkit decides whether a squad
   qualifies, never you):
   `from zecho import digest; reports, all_items = digest.squad_reports('data/issues','data/ownership.md', metrics=...)`
   (`metrics(iid)` supplies first_seen_hours / prev_freq / ack; in V1 derive from issue dates.)
2. For EACH `report` with non-empty `report["reasons"]`:
   - Write a short **narrative** for `report["items"]` (what's new/spiking/recurring, what to
     ack, trend vs yesterday) — not a flat list.
   - `claw_send(report["squad"].feedback_group_id, <your narrative>)`.
   - Squads with empty `reasons` → **stay silent** (do not post).
3. Write a PO rollup from `all_items` (top themes by volume, new vs recurring, deltas) and
   `claw_send('zalo:group:po', <rollup>)`.

Template fallback for testing: `digest.run('data/issues','data/ownership.md','zalo:group:po')`.
