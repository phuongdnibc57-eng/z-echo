---
name: zecho-closeloop
description: >
  Proactive close-the-loop notifier. Launched by Claw cron (~5 min). Notifies every reporter
  of a resolved/verdicted issue, on their ORIGINAL channel, in their language — exactly once.
---

# Z-Echo — close-the-loop

Run on each cron tick:
1. Reflect external state (optional Jira) into the file pool:
   `python -c "from zecho import closeloop, scripts; ..."` — use `closeloop.reflect_jira(issues_dir, adapter)`.
   (With no Jira, this is a no-op; verdicts arrive via the zecho-verdict skill.)
2. Get the deterministic worklist (the toolkit decides WHO, never you):
   `from zecho import closeloop; pend = closeloop.pending_notifications('data/issues', lang_of=...)`
3. For EACH `Notification n` in `pend`:
   - Compose the message yourself in `n.lang` (vi/en): thank them; if `n.fixed_in` say it is
     fixed in that version; if `n.verdict` relay verdict + `n.reason` and add the escape hatch
     ("reply 'vẫn lỗi'/'still broken' to re-open").
   - Invoke the `zecho-send` skill with `chatId=n.channel` and the composed message, scheduling a one-time cron job for delivery in ~10 seconds, then mark done via `issues.mark_notified('data/issues', n.iid, n.handle)`.
4. Never notify an issue whose status is `awaiting_po_reason` (the toolkit already excludes it).

The selection and the mark are deterministic (toolkit). You only write the words.
If you prefer a non-LLM fallback, `closeloop.run(...)` does the whole cycle with templates.
