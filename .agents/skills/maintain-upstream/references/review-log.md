# Review log

Newest first. Each entry lists what was taken and what was deliberately not taken, so a later review doesn't propose it again.

## Standing decisions

- **No fan-out.** pstack's arenas, judge panels and per-subsystem readers, and the parallel reviewers and implementers in mattpocock/skills, assume agents are cheap. orstack runs one agent per question, with a second only when two model families disagree on a decision that is expensive to undo (`skills/or-mode/SKILL.md`). Read every port through that first.
- **Invocation costs context.** A description the model can see is paid for in every session, in exchange for discoverability. A skill only the user invokes costs nothing but must be remembered. That trade is why `finalize` may be invoked implicitly and most others are explicit-only.
- **Runtime-specific features stay upstream:** Cursor's `/loop`, CDP forensics, control-cli/control-ui/canvases, install and setup plumbing.

## 2026-11-17: cursor/plugins through `2f87c85`, mattpocock/skills through `5863806`

Nothing taken. The verification skills haven't changed upstream since the last pins. pstack's `worker.md` (operator rules handed to started agents) is covered by each runtime loading its global instructions, and its never-ask and no-extra-gate rules conflict with asking for decisions and with `finalize`. sharpen's prototype-before-asking is covered by the rule that every question carries a recommendation found by investigating. Also declined: shorter rewrites, reflect and architect without subagents, Opus-first model routing (`delegate` owns routing), statechart fixes and Orchestrate's removal (both unported). From mattpocock/skills: the fresh-context subagent rule is already how `codex-worker` and the Agent tool start workers; the chief-of-staff retro sample and shared wiki overlap my own retro and memory setup; software-factory is course material.

## 2026-10-29: cursor/plugins through `c742dd6`, mattpocock/skills at `59db609`

Taken from pstack `ab1f702`: decide what a measurement has to resolve before running it (now in the `diagnosing-bugs` perf checklist), and mid-run discoveries count only when they serve the goal (`autonomous-run` step 4). Not taken: the statechart compiler and renderer, Orchestrate, swarm, interrogate's run-only rewrite, ketchup-video, reflect, worktree-audit, the plan validator, autopilot and setup changes, and both watch-pr fixes (orstack's already caps sleeps at the deadline and watches one named head). No pristine copy changed.

Taken from mattpocock/skills: `diagnosing-bugs` confirms a forced mutation landed before trusting the red (`f3fc563`); `grilling` words yes/no questions so yes accepts the recommendation (`95249b0`). Not taken: a commit-cited code-claim wiki, retro's mandatory writing-for-agents load, code-review's parallel reviewers, implement's ticket-title announcement, the tdd seam gate, teach, wayfinder, setup/wizard/readme.

## 2026-10-23: cursor/plugins at `8b3326d`

Source of `create-formal-verification-skill`; its pristine copy is at this commit.

## 2026-10-18: cursor/plugins at `bc14437`

Taken: usable-app readiness and stand-in proof limits (`c49b37a`), measured-number checks and schema-backed boundary review (`23e4138`), cheap diagnostic signal proposals (`36cecbf`), agent-mistake design checks (`a586282`). Only the `create-verification-skill` pristine copy was refreshed. Not taken: ketchup (`bro` plus a separate decision queue cover it), in-your-own-words (restate-first exists), correct (`agent-ready` owns enforcement), sharpen, poteto-help (no router needed), effort routing (`delegate`), the remaining fresh-worker and PR-heading changes (covered), hourly autopilot, prompt cuts (keeping the local proof and ownership gates), the reasoning-over-rules rewrite, perf mantras (`diagnosing-bugs` owns perf), the branded type-guard example, the unslop description, watch-pr/worktree-audit/check-plan fixes (scripts deliberately unported), version and model churn.

## 2026-10-07: mattpocock/skills v1.3.1 (`6fd9479`)

Taken: retro's rule that coding standards bind the reviewer, not the implementer, into my retro process. Not taken: implement-spec (a parallel ticket graph, against the fan-out cap), pr's template (`visual-pr` already carries blast radius and evidence), the GLOSSARY.md rename.

## 2026-09-17: humanlayer/skills at `4e39d8f`, mattpocock/skills at `74ca5fe`

`visual-pr` and `grilling` derived; see the derivation map.

## 2026-09-10: cursor/plugins pstack v0.15.1 (`7366ac1`)

Reviewed alongside poteto's pstack guide pt. 2 (an X article, 2026-09-09). Taken: the restate-first trigger, and architect's ideas into a personal design skill not shipped here. Not taken: `architect` as a skill, `multi-phase-plan` and `check-plan.mjs` (plans live in the runtime's todo tool), `perf-issue` (a good hypothesis generator; `diagnosing-bugs` owns perf for now, a candidate for a later port), runtime and trace forensics, `worktree-cleanup`, shipping/orchestrate/autopilot (≈ `finalize` plus `autonomous-run`), hillclimb/eval/visual-parity/authoring-a-skill (add when needed), teach/recall/technical-writing. The playbook pristine copies stay at `68836dd`, since no playbook text was taken.

## 2026-08-31: cursor/plugins at `fd87869`

`deslop` cherry-picked from cursor-team-kit. Not taken from cursor-team-kit: review-and-ship (≈ `finalize`), fix-ci/loop-on-ci/fix-merge-conflicts/get-pr-comments (≈ babysitting a PR), verify-this, continual-learning. CLI-first control guidance taken from poteto's [pstack guide pt. 1](https://x.com/poteto/status/2094457600259842065).

## 2026-08-30: cursor/plugins pstack v0.14.5 (`68836dd`)

The fork point: `or-mode` and its ten playbooks, `create-verification-skill`, `maintain-verification-skill` and `bro`. Not taken: the principles tree (global instructions cover it), how/why/arena/swarm/interrogate, orchestrate/autopilot/shipping/hillclimb/eval/visual-parity and the remaining playbooks, setup-pstack, automate-me, make-bot-ui, benny, and the watch-pr/orch scripts.
