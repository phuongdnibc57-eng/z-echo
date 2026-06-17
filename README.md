# Z-Echo — Voice-of-Customer Agent for Zalo

**Z-Echo** is an AI agent that turns the messy stream of internal product feedback at Zalo
into a clean, deduplicated, routed, **self-learning** backlog — and closes the loop back to
whoever reported each issue. It runs as a set of skills sharing
one tested Python toolkit.

> Built for the GreenNode Claw-a-thon. Scope **V1 = internal employees only** (Zalo staff
> dogfooding the product). External end-users are a later phase.

---

## What it does

A Zalo employee tags the bot in a group (or DMs it) with a bug/complaint — often a screenshot,
in Vietnamese **or** English. Z-Echo then runs the full feedback lifecycle:

1. **Capture & Enrich** — reads the screenshot (vision is core): infers the screen, error
   state, app version, device; detects the reporter's language.
2. **Clarify** — asks at most 2–3 follow-up questions, only for the slots still missing for
   that issue type (and skips anything the screenshot already answered).
3. **Validate / Dedup** — a 2-tier match against the existing pool: narrow by `component`,
   read each candidate's English `short_desc`, then fetch the full body to judge if it's the
   same underlying problem. Decides: **known · fixed · verdict · self · spam · new**.
4. **Synthesize & Route** — for a new issue: writes an English `short_desc`, picks
   component/theme/severity, computes a transparent priority score, and routes to the owning
   squad via `data/ownership.md`.
5. **Pool** — creates or `+1`s a markdown issue file (the pool). Optionally syncs to Jira via jira-cli.
6. **Close the loop** — when an issue is resolved or a PO rules on it, every original reporter
   is notified **on their original channel, in their language** — exactly once.
7. **Digest** — a daily per-squad digest (only when something crosses a notice threshold) plus
   a PO rollup. Critical issues escalate to on-call immediately.
8. **Learn** — a PO's verdict (`not_a_bug`, `wont_fix`, …, **with a one-line reason**) is
   written back into the pool. The next identical feedback is auto-handled with that reason —
   no vector DB, no training, just the file the dedup step already reads.

### Why it's different

- **Grounded in product knowledge** — it knows which component belongs to which squad, what's
  already fixed in which version, and what a PO previously ruled. That knowledge lives inside
  Zalo, so it can't be copied by an outside tool.
- **Self-learning loop** — PO verdicts become reusable knowledge automatically.
- **Closed-loop** — the reporter actually hears back. Most feedback tools forget this step.
- **Knows when to stay silent** — the digest only speaks when a threshold is crossed.

---

## Design principle: toolkit vs. skill

The single most important idea in the codebase:

> **Must-be-correct decisions → the tested Python toolkit (`zecho/`).**
> **Language & judgment → the Claw skills (LLM).**

| Lives in the **toolkit** (deterministic, unit-tested) | Lives in the **skills** (LLM judgment) |
|---|---|
| Picking *which* reporters to notify + marking them notified **exactly once** | Composing the actual message text in the reporter's language |
| Allocating issue IDs, bumping frequency, querying the pool | Deciding if two pieces of feedback are the same problem (dedup) |
| Computing notice thresholds / SLA / priority score | Writing the narrative daily digest ("complaints about X up 40%…") |
| Writing a PO verdict (reason required, version-scoped) | Understanding the PO's intent when they tag the bot |
| Jira sync via jira-cli | Clarifying questions, routing judgment |

This is why notifications can never be sent twice or to the wrong person — that logic is in
tested code, not in a prompt.

## Quickstart

From the repo root:

```bash
python -m pip install -e .      # install the zecho toolkit
python -m pytest -q             # expect: 34 passed
python scripts/seed.py data     # seed the demo pool (ISS-0007, ISS-0008)
```

Try the deterministic toolkit directly (no Claw needed):

```bash
# Daily-digest gating: payment squad speaks (High new), messaging stays silent
python -c "from zecho import digest; r,a=digest.squad_reports('data/issues','data/ownership.md',metrics=lambda i:{'first_seen_hours':1,'prev_freq':0,'ack':False}); print([(x['squad'].name,x['reasons']) for x in r])"

# Close-loop: who gets notified for a resolved issue
python -c "from zecho import issues,closeloop; issues.set_status('data/issues','ISS-0007','resolved'); print([(n.handle,n.channel) for n in closeloop.pending_notifications('data/issues')])"
```

Full A1–A5 acceptance walkthrough: see `scenarios/README.md`.

---

## Onboarding a new Claw

When you spin up a fresh Claw and it asks *"who am I, and who are you?"*, paste this to give it
its identity and first task:

```
You are Z-Echo, a Voice-of-Customer agent for Zalo's internal product team.
I'm the Product Owner.

Your job: turn raw internal feedback (bug reports / complaints, often with
screenshots, in Vietnamese OR English) into a clean, deduplicated, routed,
self-learning backlog — and close the loop back to whoever reported it.

Everything you need is at: /Users/lap15564/Projects/z-echo
- skills/zecho-triage | zecho-verdict | zecho-closeloop | zecho-digest | zecho-send /SKILL.md
  = your behavior prompts (read these to learn your role)
- zecho/  = a TESTED Python toolkit you call for anything that must be exact
  (pool CRUD, issue IDs, dedup, notify selection exactly-once, thresholds)
- data/   = the file-based pool = source of truth; data/ownership.md maps
  components -> squads
- docs/architecture.md, docs/specs/, scenarios/README.md (acceptance A1-A5),
  cron.md (your scheduled jobs), docs/jira-cli-integration.md (Jira setup)

Core rules:
- Frontmatter is always English (incl. short_desc); body keeps the reporter's
  original language; reply to each reporter in THEIR language.
- Dedup = narrow by component -> read short_desc -> fetch full body -> judge.
- Deflects are soft (always give a "still broken / vẫn lỗi" escape hatch).
- PO verdicts are version-scoped; a newer version re-opens (possible regression).
- If jira-cli is available, create Jira issues first and use the returned key.

First task, in order:
1. Read the 5 SKILL.md files + docs/architecture.md to load your role.
2. Verify the toolkit: `python -m pip install -e .` then `python -m pytest -q`
   (expect 34 passed).
3. Seed demo data: `python scripts/seed.py data`.
4. Then take ONE sample feedback from tests/fixtures/feedback/ and walk me
   through how you'd handle it end-to-end (capture -> clarify -> dedup -> route
   -> pool) using the zecho-triage skill, calling the toolkit for the exact bits.

After that, operate reactively when I paste feedback. Run closeloop (~5 min) and
digest (09:00) per cron.md.
```

After onboarding, Z-Echo operates **reactively** when you paste feedback (or it's tagged in a
group), and **proactively** on schedule via `cron.md`:

- `zecho-closeloop` — every ~5 minutes — notify reporters of resolved/verdicted issues.
- `zecho-digest` — 09:00 daily — per-squad gated digest + PO rollup.

---

## Documentation

- `docs/architecture.md` — architecture, diagrams, and decisions D1–D12
- `docs/specs/2026-06-16-zecho-voc-agent-design.md` — design spec
- `docs/plans/2026-06-16-zecho-voc-agent.md` — implementation plan
- `docs/jira-cli-integration.md` — Jira integration via jira-cli
- `scenarios/README.md` — acceptance scenarios A1–A5
- `cron.md` — Claw cron schedule
- `skills/*/SKILL.md` — the agent behavior prompts

