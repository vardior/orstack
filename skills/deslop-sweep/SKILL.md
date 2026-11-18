---
name: deslop-sweep
description: "Repo-wide deslop of an existing code area with no branch diff: scout, batched automerge-safe PRs, adversarial reviewer, conflict-zone first. Use only for /deslop-sweep in Claude, $deslop-sweep in Codex, or an explicit request to sweep an area for slop and dead code."
disable-model-invocation: true
---

# Repo-wide deslop sweep

`deslop` cleans what a branch introduced. This skill cleans long-lived code the user names ("sweep the billing feature"), as small, independently mergeable PRs safe enough to automerge once approved. What counts as slop is `deslop`'s focus areas and guardrails, plus dead code and duplication; zero behavior change is mandatory and net code removal is the preferred outcome. Three delegate roles; the orchestrator only dispatches, gates, and merges.

## 0. Conflict zone first

Before any dispatch, compute the union of files touched by the owner's open PRs in the target repo(s) (`gh pr list --author @me --state open --json number,files`) and write it to a file at the work root. Scouts prefer candidates outside it; a candidate inside it is flagged `CONFLICT:#<pr>` and only proposed if trivially rebaseable. Refresh the zone when an open PR merges, and **recompute it before resuming any deferred batch** — a zone is a dispatch-time fact and is stale by resume.

Each PR gets its own worktree, never one a feature session is using.

## 1. Scout (read-only, one per area)

- **What counts**, ranked: (1) dead code — members with zero references repo-wide, including string-based lookups, DI registrations, reflection, serialized property names, config keys; unused parameters, test helpers, unreachable branches; (2) duplication — near-identical helpers or blocks → one; (3) slop per `deslop`, plus needless materialization, needless async wrappers, try/catch that only rethrows, pointless locals, redundant `else` after return, 1:1 pass-through records, one-implementation interfaces with no second adapter (a test fake counts as a second — leave those); (4) naming/readability only when bundled with the above.
- **What does not count**: persisted shapes (stored entities, schema snapshots, options classes, migrations), public contracts (REST bodies/responses, queue messages, feature flags, deploy config), behavior changes, new abstractions, reformat-only churn, public renames, anything changing rendered output or test-visible text.
- **Output per candidate**: title, `risk: trivial|low` (drop anything higher), estimated LOC removed, conflict flag, `path:line` list, the precise change, safety evidence (exact greps run and their counts, call sites, tests pinning behavior), and a cheap deterministic verification recipe. Then `## Suggested PR batches` — independently mergeable, one theme each, under ~300 changed lines, ordered by safety — and `## Rejected` with reasons so nobody re-investigates. A hand-wavy safety argument is worse than no candidate.

## 2. Implementer (one per batch)

- Own worktree off the latest base branch, branch `or/<area>-cleanup-<slug>`. Only the assigned candidates; a candidate that turns out not provably dead/equivalent is dropped and reported, never "fixed while here". No opportunistic extras, no reformatting untouched lines.
- Verify with the repo's own build/test/lint commands (analyzers on — CI parity), re-run the scout's grep after the change and paste the empty result, run any repo drift checks. Confirm the diff touches none of the "does not count" surfaces; an unexpected snapshot change means stop and report, not update.
- One commit, plain wording, no attribution. PR body: one sentence of what is removed and why it is safe; `## What` per candidate; `## Safety` with the grep evidence and pinning tests; `## Verification` with commands and results. Report the PR URL, `--stat`, implemented/dropped candidates, verification tails, and the first thing a reviewer should look at.

## 3. Reviewer (read-only, one per PR)

Adversarial: the PR is meant to automerge, so the reviewer is the last line of defense. Read the whole diff. For every removed symbol run an independent repo-wide grep — do not trust the implementer's. For every rewritten expression build the input-case table (null/empty/case/culture/ordering/exception paths) and confirm before == after per row. Check the forbidden surfaces and scope. Verdict `APPROVE | REQUEST-CHANGES | BLOCK`, findings most severe first with the concrete failing input, and one line: "Automerge-safe? yes/no — why".

## 4. Merge gate

Conjunctive: reviewer APPROVE **and** GitHub approval **and** CI clean **and** no snapshot files in the diff. An agent-side CI watcher is not the safety net — the repo's required checks / merge queue are; do not automerge in a repo without them.

Keep a `decisions.md` in the worktree (batches, deferrals and their gating PRs, each merge verdict) — this runs unattended.
