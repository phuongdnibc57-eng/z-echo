# Z-Echo — Voice-of-Customer Agent (Claw skills + toolkit)

Internal Zalo feedback → deduplicated, routed, self-learning backlog with proactive
close-loop + digests. File-based pool (`data/issues/`) is the source of truth; Jira is optional.

Four Claw skills share one tested toolkit `zecho/`:
`zecho-triage` (reactive pipeline), `zecho-verdict` (PO write-back), `zecho-closeloop` (cron),
`zecho-digest` (cron). Must-be-correct logic lives in the toolkit; skills add judgment + language.

## Quickstart
```bash
python -m pip install -e .
python -m pytest -q
python scripts/seed.py data
```
See `docs/specs/2026-06-16-zecho-voc-agent-design.md` (spec), `docs/architecture.md`,
`scenarios/README.md` (acceptance), `cron.md` (schedule), `skills/*/SKILL.md` (agent prompts).
