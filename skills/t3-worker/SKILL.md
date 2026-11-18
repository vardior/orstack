---
name: t3-worker
description: "Delegate a coding or analysis task to Codex as a T3 Code thread Or can watch and steer from the T3 app, via the local t3-worker wrapper. Trial paused: use only when the user names t3-worker or a T3 worker, or to continue a previous T3 worker thread. Otherwise use codex-worker."
argument-hint: '[resume <thread-id>] [--cd <dir>] [--model <model>] [--effort <effort>] [--account work|personal] [--title <title>] <prompt>'
---

# t3-worker

> **Early review.** This skill replaces `codex-worker` on trial. If anything about it creates friction (a confusing step, a wrong default, an error, a missing answer, a slow or stuck run), tell Or in your reply without being asked: name the command you ran, what went wrong, and the driver log path from stderr. Then finish the task with `codex-worker`.

Run one Codex task as a T3 thread through the wrapper next to this file:

```bash
<this skill's directory>/t3-worker --cd /absolute/path/to/repo "<prompt>"
```

## Contract

- The T3 Code desktop app must be running, with the `t3` MCP server registered in Claude Code at user scope, signed in, and given a `timeout` above one hour. Without that timeout, Claude Code aborts every wait after 60 s with "The operation timed out."
- `--cd` picks the checkout. It must be a git checkout whose main repository is a T3 project. A linked worktree binds as that worktree on its current branch, and the main checkout binds as the project root.
- Model and effort default to the `codex` CLI's configured values. The account follows `codex-worker`'s account picker unless `--account` is given.
- Codex runs with the permission mode the `t3` connection was approved with, and does not inherit the Claude conversation. Give it a self-contained brief with the goal, scope, constraints, and completion evidence.
- Stdout holds the final answer followed by `t3 thread: <id>`; progress, errors and the driver log path go to stderr. A non-zero exit means the run did not complete or the answer could not be recovered; the thread itself may still hold the work.
- A haiku `claude -p` driver makes the MCP calls. The wrapper refuses its result if the driver changed the brief, workspace strategy, or model selection.

## Continue a thread

```bash
<this skill's directory>/t3-worker resume <thread-id> "<next instruction>"
```

The thread keeps its checkout, model, effort and account.

## Execution

- Run every call as Claude Code background Bash with an exit marker, then stop issuing turns until it fires: `(t3-worker … ; echo "exit=$?") > run.log 2>&1`. One wait can block for up to an hour inside the driver, and that must never hold this session's turn.
- Watch or steer the thread from the T3 app while it runs; do not poll it.
- On failure, read a bounded tail of stderr and the driver log before retrying. Never relaunch blindly: the thread may already exist and be running.
- Return the final answer and thread id to the user.
