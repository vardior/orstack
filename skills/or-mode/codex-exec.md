# Codex exec recipe

Three rules for a Codex worker's `exec` cells, `exec_command`, `write_stdin` and `wait`. Claude Code
persists large outputs, notifies on background completion and asks without blocking; Codex does none
of these, so each rule replaces one of them.

## Read a file whole

Before reading a file or a SKILL.md, size the read from `wc -c <file>`: set `max_output_tokens` to
bytes/3 plus margin on `exec_command`, and on the cell's `// @exec` line when there is one. A file
too large for one read goes in numbered ranges (`nl -ba <file> | sed -n '1,300p'`, then the next
range). Never use a blanket 1000–2000 cap. On `Warning: truncated output`, read only the missing
range; never rerun the same command with the same cap.

Why: the tool drops everything past the cap. finalize is about 3.4k tokens and a verify skill about 4.6k,
so a 2000 cap hides the steps a worker is then asked to follow. 369 of 1,370 SKILL.md reads and
1,911 outputs (31.8M tokens) were cut off between 2026-10-06 and 2026-10-20, with 112 immediate reruns.

## Wait on a long job once

A job that may run over about a minute (build, test, live stack) starts once, with its output
going to a log file, and `wait-log` watches it with the seconds you expect the job to take (its
usual time, or your honest guess). The cell waits in a loop of its own, and you wait on the cell:

```js
let r = await tools.exec_command({cmd: "{ <job>; echo \"exit=$?\"; } > <log> 2>&1 & <or-mode skill directory>/scripts/wait-log <log> <expected-seconds>", yield_time_ms: 30000, max_output_tokens: 400});
while (r.session_id) r = await tools.write_stdin({session_id: r.session_id, chars: "", yield_time_ms: 300000, max_output_tokens: 400});
text(r);
```

`wait-log` exits 0 or 1 with the job, or 3 with `STALLED` and the log's tail once the job has run
twice the expected time and its log has not grown for 5 minutes. On `STALLED`, find what it is
stuck on from the tail (a registry fetch, a lock, a dead service), fix or kill it, and report the
stall; never wait on the same job again unchanged.
If the cell returns `Script running with cell ID <n>`, call `wait` on that cell with
`yield_time_ms: 1000000`, again after each return until `Script completed`, then read the log's tail
or grep it for the verdict. For a job you did not start (such as a remote deploy), the one watcher is a
shell `until` loop that exits on a terminal state and gives up at a deadline twice the expected time,
e.g. `end=$(($(date +%s)+<2x-seconds>)); until grep -q '^exit=' <log> || [ $(date +%s) -gt $end ]; do sleep 30; done`.
A probe of a pull request checks out its head SHA, never `refs/pull/<n>/merge`, which disappears
when the PR merges or conflicts.
A loop that greps the process list must exclude itself (`pgrep -f '[d]otnet test'`, or `kill -0`
on a saved PID); otherwise it matches its own command line and never exits. Lead-dispatched PR tails follow finalize Step 5 and or-mode. Never make repeated
one-minute `wait` calls or `write_stdin` polls from your own turns.

Why: Codex sends no background-completion notice, and each poll you make re-sends the whole
context. Short yields cost 5,452 `wait` calls, about 500 `write_stdin` polls and 336 sleeps, 56 hours
of blocking, a 60-minute p90 turn and 30 turns Or interrupted.

## Ask without blocking

Never call `request_user_input_async` for a question already answered by `~/.agents/AGENTS.md` or
the brief: scope, whether to merge or rebase on dev, or permission for safe, reversible, in-scope
work. When a decision really is outside both, send it to your home (the lead or chief-of-staff
thread, or the handoff folder, that the brief names for talking back) as one message with the
options, your recommendation, a deadline, and what you will do if the deadline passes unanswered. Then keep
working on everything that does not depend on the answer.

Why: `request_user_input_async` stops the worker until Or answers. Of 29 asks, most waited 15
minutes to 3 hours and two went unanswered for 4–5 days, many on questions those files already settle.
