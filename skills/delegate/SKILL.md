---
name: delegate
description: Pick the model for a subagent and dispatch it safely. Use before spawning any subagent, agent, or worker fleet; when deciding between codex (Sol or Luna), opus, sonnet, fable, or haiku for a task; and when splitting work across parallel workers. Not for choosing the model of the current session.
---

# delegate

Route each delegate on merit, one decision per agent. Never spawn a default-model fleet — a fleet is N routing decisions, not one.

## The routing test

**"Can I fill the delegate brief template for this?"** (`../or-mode/brief-template.md` — eight fields, executable by a stranger with no chat access.)

- **Yes** → **codex** (the newest Sol model). Separate, much larger budget at roughly opus-level capability for scoped code work.
- **No, because it's genuinely hard or ambiguous** → **opus**.
- **No, because it's entangled with this session's context or needs Claude-side tools** → **sonnet** or **opus** by difficulty.
- **Work on Claude Code itself** — function-hook plugins, skills, hooks, harness settings — → a Claude model regardless of how briefable it looks: the API is absent from codex's training data, the types come from a live Claude session, and the whole loop (`claude plugin validate`, `--plugin-dir`, the engine log) is Claude-side tooling. A domain judgment, not a quota one.
- **Prose that agents or Or will read** (writing or restructuring skills, agent docs, reference docs, write-ups for Or) → a Claude model, opus or sonnet by difficulty, however briefable it looks. Or prefers Claude's writing. Code that ships alongside the prose stays on the code lane.
- **Bulk reading of transcripts, logs or session histories** (a census, a retro, an audit of many sessions) → sonnet, or haiku when each item gets a mechanical label, however ambiguous each judgment looks; never opus (Or, 2026-11-12). Split the items across several such agents rather than one large one, and review their labels yourself.

Sonnet and opus drain the same Claude quota at similar effective per-task cost, so difficulty — not price — decides between them. Codex is the one genuinely cheaper lane.

## The lanes

| Model | Use it for |
|---|---|
| **Sol** (codex) | The default workhorse for code implementation: any well-scoped coding task with a fillable, self-contained brief; all high-fan-out, mechanical, or high-volume work; and independent cross-model takes — second opinion, adversarial verify, redundant implementation to diff against. |
| **Luna** (codex) | Trivial mechanical work on the Codex side: scans, polling, triage, and bulk edits whose spec is fully pinned. The Codex counterpart to haiku. |
| **opus** | Genuinely hard or ambiguous work: architecture, planning, gnarly debugging, adversarial review, real-bug-finding code review, and implementation too entangled with session context to brief a stranger. Effort follows the policy below. |
| **sonnet** | A Claude-delegated skill or subtask where the work is very trivial and opus would be overkill, and bulk transcript or log curation. |
| **fable** | Exceptional difficulty only: the hardest, most novel, long-horizon reasoning where raw intelligence is the bottleneck and a wrong answer is very costly. Best model available, premium price — sparingly and deliberately. |
| **haiku** | Trivial mechanical lookups and scans (fetch, grep-level search, API polling) where even writing a codex brief is overkill. |

Default order: **Sol** for implementation, fan-out, and cross-model checks → **opus** when it's genuinely hard → **sonnet** only for trivial Claude-side work → **fable** only when the difficulty justifies the top price.

Sol and opus are about the same level, so when Or says one provider's quota is low, swap them. Never use Astra or any other OpenAI frontier model.

## Effort

Implementation defaults to **medium** on every provider. Pass it explicitly when dispatching or continuing a worker; a high-effort parent does not make its children high-effort. For the Codex wrapper, pass `--effort medium`; for app-owned or native delegation, set the selected model's reasoning/effort option to medium.

If the native delegation tool cannot set effort, use a supported delegation interface that can. Do not assume a child of a high-effort session will use the medium default.

Use **high** only for truly challenging work and name the concrete difficulty in the brief. A long-horizon engineer owning a multi-week feature, such as the AI DevTools engineer, qualifies; its bounded implementation children still default to medium. A large diff, many files, routine verification, or parallel execution alone does not qualify. An explicit effort requested by Or takes precedence.

## Picking the exact model

Never copy a model id from notes, briefs, charters or memory: versions move and old ids keep working,
so a stale pin fails silently. Read the live catalog once per session, and again only when a dispatch rejects the id or Or says the lineup changed; take the newest id in the lane:
in T3, `orchestrator_capabilities`; elsewhere, the `codex` CLI's configured model (`codex-worker`
uses it when `--model` is omitted). Pass `--model` only for the Luna lane (the newest Luna id) or when Or names one.

## Dispatching codex

Outside a workflow, invoke the `codex-worker` skill directly; no intermediary needed. The `t3-worker` trial is paused (2026-10-26: T3 approves this MCP client read-only, so launches are refused); use it only when Or names it. If `codex-worker` is missing from the skill list, the cause is a `skillOverrides["codex-worker"]` entry in `~/.claude/settings.json` hiding it — delete the key (absent = available) rather than falling back to a Claude model silently. Inside a Claude `Workflow`, `agent()` cannot spawn codex natively — spawn a low-effort **sonnet** agent as a thin driver that invokes the CLI and relays the result verbatim, nothing more.

From a Codex session, the same-runtime worker *is* Sol; the Claude-model lanes above are reachable only from Claude Code.

A codex worker inherits `~/.agents/AGENTS.md` and the repo's `AGENTS.md`, but not this skill and not the Claude conversation. For cross-runtime delegation the brief is load-bearing: inline any rule the task depends on.

## Dispatching to the cloud

When your global instructions or the repo's agent docs define a cloud-worker lane for the repo, follow its fit rules there; it can take tasks the lanes above would have given to Codex locally.

## Delegate hygiene

- Choose one completion mechanism when dispatching: the runtime's automatic child completion notification, a blocking task wait, or a background completion watcher. For a lead-dispatched PR, use finalize Step 5 for the worker handoff and or-mode for the lead’s event handling. Inspect the result on completion, failure, or a real intervention request; never spend model turns repeatedly checking an unchanged task. If no event mechanism exists, one script polls the terminal predicate with a bounded timeout and sensible backoff, then reports once.
- Codex workers are standalone workers like any subagent — no codex-specific guardrails, no baked-in "don't commit" rule. Decide commit, test, and push rigor per task, not per model.
- Spawn a background agent that runs git writes with `isolation: "worktree"`; telling it to use a worktree enforces nothing, and it can move HEAD under the lead. Claude Code refuses any command in such an agent that it cannot prove keeps git inside the worktree, so the brief says: one plain command per Bash call, literal quoted arguments and absolute paths; no `cd … &&`, `env -u`, `bash -c`/`zsh -ic`, `source`, loops or heredoc interpreters; anything compound goes in a script file run as `bash /abs/path/script.sh`.
- Briefs, worker logs and worker scratch go in your session's scratchpad or under `~/wt/<repo>/<slug>`, never inside an installed skills or plugin directory. Those directories are the live skills.
- You own every delegate's output: review the diff and write your own summary. Never pass through what a worker said.
