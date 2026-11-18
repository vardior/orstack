---
name: codex-worker
description: Delegate a coding or analysis task to a headless Codex subprocess (the configured Sol model) via the local codex-worker wrapper. Use whenever the user says to use codex-worker or codex, when offloading well-scoped implementation, review, or research work to a separate model, or when continuing a previous Codex session.
---

# codex-worker

Run one headless Codex task through the wrapper next to this file:

```bash
<this skill's directory>/codex-worker "<prompt>"
```

## Contract

- Codex runs non-interactively with approvals and sandboxing bypassed.
- The wrapper picks the Codex account for each new session and names it on stderr. A resume stays on the account that ran the session's last turn.
- User and project Codex configuration remains loaded. Model, effort, provider, MCPs, hooks, and other settings therefore match normal Codex unless explicitly overridden.
- Sessions persist. Stdout contains the final answer followed by `codex session: <id>`; progress and errors go to stderr.
- The wrapper uses its current directory unless `--cd <dir>` is supplied. Always pass the intended repository explicitly when it matters.
- Codex does not inherit the Claude conversation. Give it a self-contained brief with the goal, scope, constraints, and completion evidence.

## Continue a session

Resume in the same repository and pass only the follow-up instruction:

```bash
<this skill's directory>/codex-worker \
  resume 01a0621b-ecfd-7772-996b-c4361bd341f0 \
  --cd /absolute/path/to/repo \
  "<next instruction>"
```

The explicit directory is load-bearing: resuming a Codex session does not restore its original working directory automatically.

## Overrides

- `--model <model>` overrides the configured model.
- `--effort <effort>` overrides configured reasoning effort; let Codex validate whether the selected model supports it.
- `--fast` runs this session on the priority (fast) service tier. Fast is never the default; pass it only when Or asks for fast mode.
- `--allow-non-git` permits execution outside a Git repository.
- `CODEX_WORKER_BIN` pins the account's binary (`codex` for work, `codex-personal` for personal).
- Prompt input can come from stdin when no prompt argument is supplied.

Do not add web-search flags: unrestricted Codex already uses its configured/default search behavior.

## Execution

- Run long tasks using Claude Code's background Bash execution. Do not poll in a foreground loop.
- The wrapper prints no `exit=` line, so a detached run appends its own for a watcher to wait on: `(codex-worker … ; echo "exit=$?") > run.log 2>&1 &`.
- "Not supported when using Codex with a ChatGPT account" within seconds means a stale CLI: run `codex update`, never pin an older model. A "cybersecurity risk" refusal means the brief reads as offensive security: restate the same checks as correctness or parity QA.
- Preserve the wrapper's exit code. On failure, inspect a bounded tail or error-filtered view of stderr; do not dump a large completed event stream into the conversation.
- Return the final answer and session ID to the user.

For native code review, resumable background-job management, status/result/cancel, or Claude-to-Codex transcript transfer, use the official OpenAI Claude Code Codex plugin instead of extending this wrapper.
