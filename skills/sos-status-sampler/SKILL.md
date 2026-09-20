---
name: sos-status-sampler
description: "Check and sample SoS job status. Use when the user asks to sample SoS jobs, inspect task status, or requests verbose SoS status for specific task IDs."
---

# SoS Status Sampling

- Run `sos status -v4 <task_id>` for each provided task ID.
- If the user wants a sample and provides an ID, use it directly; otherwise sample a few recent tasks from `~/.sos/tasks`.
- Report the status succinctly.

Example:

```bash
sos status -v4 tbb8d5e93f739f958
```
