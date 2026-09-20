---
name: record-handoff
description: Create a timestamped handoff note in `handoff/` when the user says "hands off", asks for a handoff, or wants the current situation written down for the next session.
---

# Record Handoff

## Workflow

1. Inspect the current conversation, recent tool output, and any relevant workspace state.
2. Create `handoff/` in the current workspace if it does not exist.
3. Write a new Markdown file named with a sortable timestamp, such as `2026-03-17_16-42-03.md`.
4. Summarize only what is actually known. Separate facts from inferences when needed.
5. Never overwrite an existing handoff note.

## Content

Include:
- Current objective
- Work completed
- Important files, commands, or decisions
- Open questions, blockers, or assumptions
- Recommended next step

## Style

- Keep it concise and actionable.
- Use bullets and short headings.
- Write enough context that a future session can resume without rereading the whole thread.
