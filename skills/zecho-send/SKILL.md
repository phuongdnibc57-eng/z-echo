---
name: zecho-send
description: >
  Send a single outbound message to a chat via a one-time cron job. Use this skill when the agent needs to proactively deliver a message to a known chat.
---

# Z-Echo — send one message

Use this skill when the agent is asked to deliver a single message to a known chat.

Inputs:
- `chatId`: the destination chat or user identifier.
- `message`: the text to send.

Behavior:
1. Validate that `chatId` and `message` are present.
2. Use the cron tool to create a one-time job scheduled for ~10 seconds in the future.
3. The scheduled job should deliver the `message` to the `zalo` channel with `chatId`

This skill does not compose text or decide routing — it simply schedules one outbound delivery from the agent.
