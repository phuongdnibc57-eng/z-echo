# Acceptance scenarios (map to spec §8)

Run `python scripts/seed.py data` first. Drive the agent via Claw with the fixture feedback.

## A1 — Dedup
- Send `tests/fixtures/feedback/dup_qr.md` content → agent must +1 **ISS-0007**
  (freq 18→19, reporter @nvD appended), NOT create a new issue.
- Send `tests/fixtures/feedback/new_login.md` → agent creates a NEW issue (ISS-0009) and
  routes it (login/account). Verify with `grep -rl "short_desc" data/issues/`.

## A2 — Close-loop
- `python -c "from zecho import issues; issues.set_status('data/issues','ISS-0007','resolved')"`
  then set `fixed_in: 25.7` in the file.
- Run the close-loop cycle:
  `python -c "from zecho import closeloop; closeloop.run(issues_dir='data/issues')"`.
  Verify each reporter of ISS-0007 receives a message on their **original channel** and is
  marked `notified:yes`. (In Claw, the `zecho-closeloop` skill does this with LLM-composed text.)

## A3 — Learning (verdict reuse, version guard)
- Send `verdict_timezone.md` (app_version 25.6.1 = within ISS-0008 scope_versions) →
  agent **soft-deflects** with the recorded reason + escape hatch.
- Change its `app_version` to `25.8.0` (newer than scope) → agent must NOT deflect; re-open.

## A4 — Digest
- Run `python -c "from zecho import digest; digest.run('data/issues','data/ownership.md','zalo:group:po')"`.
  A squad with a High-new/spike issue gets a post; a quiet squad gets none; PO group gets a
  rollup. (In Claw, the `zecho-digest` skill writes the narrative.)

## A5 — Jira-optional
- Unset JIRA_* env vars. Re-run A1–A4. All must pass using the file pool only
  (`pool_jira.py` returns None; closeloop uses NoopAdapter).
