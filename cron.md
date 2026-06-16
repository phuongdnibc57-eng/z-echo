# Claw cron schedule for Z-Echo

Cron launches a SKILL (an agent turn), which calls the tested toolkit:
- every 5 minutes → launch skill `zecho-closeloop`
- 09:00 daily     → launch skill `zecho-digest`

Non-LLM fallback (pure toolkit, for CI/smoke):
- close-loop: `python -c "from zecho import closeloop; closeloop.run(issues_dir='data/issues')"`
- digest:     `python -c "from zecho import digest; digest.run('data/issues','data/ownership.md','zalo:group:po')"`

Environment (optional Jira; omit to run file-only):
- JIRA_BASE_URL, JIRA_PROJECT, JIRA_EMAIL, JIRA_TOKEN
- ZECHO_DATA (default `data`), ZECHO_PO_GROUP (default `zalo:group:po`)
