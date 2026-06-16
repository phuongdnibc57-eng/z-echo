---
name: zecho-verdict
description: >
  Records a Product Owner's verdict on a pooled issue. Use when a PO tags the bot in a squad
  group (or replies on an issue) to rule on it: not a bug / won't fix / invalid / backlog /
  fixed, WITH a one-line reason. Writes the verdict back into the issue so future duplicates
  are auto-handled.
---

# Z-Echo — PO verdict write-back

When a PO rules on an issue:
1. Identify the issue id (they reference `ISS-xxxx` or a Jira key; resolve via
   `grep` / `issues.find_by_jira_key`).
2. Require a **one-line reason**. If missing, ask for exactly one line — do not proceed.
3. Determine `scope_versions` = the issue's current `affected_versions` (the verdict only
   applies to these; a newer version may regress).
4. Write it with the toolkit (keeps YAML valid, enforces reason):
   `python -c "from zecho import issues; issues.append_verdict('data/issues','ISS-0007', verdict='not_a_bug', by='@po_pay', reason='<one line>', scope_versions=['25.6.0','25.6.1'])"`
5. **Issue vs general rule:** "Would this verdict still be true for a DIFFERENT issue?
   Yes → also write a general rule in `data/kb/<topic>.md` (so the triage `self` branch can
   use it). No → it stays in the issue file only."

Reporters are NOT notified here — that is the `zecho-closeloop` skill's job on the next cron tick.
