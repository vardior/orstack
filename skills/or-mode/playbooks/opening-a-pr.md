### Opening a PR

Invoked at the end of every code playbook. **Every PR goes through the `finalize` skill** (`/finalize` in Claude, `$finalize` in Codex) — it is the single pre-PR gate: verify live → deslop → review → clean diff → PR → tail. Copy its steps into the task plan as visible items before starting; a step you skip stays in the plan with `skip: <reason>`. This playbook sets the standards that gate applies. Delegates that open PRs get the same instruction in their brief.

**Worktree.** Work from a git worktree off the base branch for anything that shouldn't squat on the main checkout; subagents inherit it. Concurrent workers never share a branch or worktree.

**Repo facts.** Base branch, commit convention, test commands, and delivery mode come from the repo's CLAUDE.md/AGENTS.md and `git log` — not from this playbook. Or's global rules apply: PR body's first line carries `closes <full Jira URL>` or `relates to <full Jira URL>` when a ticket exists.

**Commits.** Commit liberally while working; rebase into small, ordered commits before opening. Each commit is a future PR: landable, ordered to tell the story. Amend when the fix belongs in a just-made commit; new commit when separable.

**Diff hygiene.** Before commit: run the `deslop` skill over the branch diff (slop and needless structure — delegates' diffs included); then review the full diff and drop strays — scaffolding tests, debug output, leftover artifacts, narrating comments. The PR contains only changes serving its stated purpose. This applies on every PR, not just the finalize chain.

**Titles.** Follow the repo's convention (check recent `git log`); default `type(scope): subject`, short and imperative, naming a real symbol when one carries the change. No trailing period.

**Descriptions.** The `visual-pr` skill composes the body during finalize. The budget is about 120 words of prose plus at most one table. First line: `closes <full Jira URL>` when the PR completes the ticket's scope, `relates to <full Jira URL>` when it delivers only a part. Then one opening paragraph — what was wrong or missing, and what the change does — and `## Verification`. A one-file or otherwise small diff gets nothing more. Add a section only when a reviewer needs it to assess this change, and never one that restates the diff or repeats a fact the opening paragraph already stated:

- `## Scope` — when the boundary matters: both sides of a rename, what's in and out. Real symbols and paths. A structural sketch belongs here when the change has a shape — a flow, a contract, a component tree — and never on a test-only or one-line diff.
- `## Tradeoffs` — a real choice only.
- `## Blast Radius` — one sentence: who the change touches and what being wrong costs (plain revert, revert plus data or migration rollback, customer-visible once shipped). Omit it when the change is a plain revert away from harmless.
- `## Verification` — the evidence bundle's `## For the PR` block, verbatim. It opens with one plain sentence naming the surface that was driven and why it is the right one for this diff: no `Verification tier:` label, and no "this proves … / it does not …" pair unless a tier lower than the whole job was taken, in which case one sentence states the excuse. Driven → observed goes in a two-column `| Driven | Observed |` table in the reviewer's vocabulary — outcomes, not command names — with every count and number in the table rather than in prose, and builds and unit tests as one row at most. Nothing else from the bundle crosses over — no bundle id, SHA lines, evidence-file column, or `EVIDENCE.md` comment; those are local bookkeeping and a reviewer cannot open files on your disk. The bundle path goes in your final report instead. An artifact a reviewer would actually want is committed as a test or pasted as its one-line result. When the agent that verified is not the agent writing the PR body, the verifier's REPORT hands over the bundle path and the PR-prep brief lifts the block from it — "the commands *you* ran" is never the whole section. No live-verification evidence to cite → stop; do not open the PR on builds and unit tests alone.

Attach screenshots/recordings when they prove a claim. No `## Summary` / `## Test plan` boilerplate. A commit body does not restate its subject.

**Size and stacks.** Prefer a few narrow PRs to one large one. Delivery mode is a repo fact: repos with GitHub stacked PRs enabled can stack follow-ups via `gh stack` (`init`/`add`/`submit`); everywhere else, sequence independent PRs or note the dependency in the body. Rebase on the base branch before substantial stack work.

**Readiness.** Open PRs ready, not draft, unless the repo's contract says otherwise. `gh pr view <number>` before referring to PR status.

**Tail.** Opening the PR is not the terminal state — CI and review bots report after it. Post the URL and keep building, but a "done"/"all green" report written before the tail settles says so: `provisional — tail pending: <PRs>`. No session, handoff, or pause ends with uncommitted work on any branch: commit it (`wip:` is fine), push, and name it in the handoff. A lead-dispatched worker hands off the tail under finalize Step 5; the lead handles its events under or-mode. Run a babysit pass when asked. Push back when review feedback drifts from intent.
