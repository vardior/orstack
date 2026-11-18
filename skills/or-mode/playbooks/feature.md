### Feature

**You own the design. Plan, review, verify.** New or changed behavior.

1. Understand the affected subsystem first (Investigation step 1, scaled to need — one reader when delegation is allowed, summaries not dumps).
2. `design-it-twice` for the interface/shape when the seam is expensive to undo (published interface, persisted data shape, cross-service contract) — a module boundary alone is not the trigger. Skipping stays as `design-it-twice skipped: <reason>`; do not fold an expensive-to-undo decision silently into implementation.
3. Write the throughput checkpoint as five todo items. A dimension that genuinely does not apply keeps its item with `n/a: <reason>` rather than being dropped:
   - **Blocking first steps.** Gates run before fan-out.
   - **Independent workstreams.** Disjoint files, services, or layers parallelize. This is the one place agents multiply: parallelism across separable work, never fan-out at one question (standing trigger). Shared writes serialize. Disjointness is by file, not theme: list each slice's files before dispatch; a file in two slices means one slice or an explicit order. Compute the no-go zone (files touched by your open PRs) before dispatch and recompute it when resuming deferred work.
   - **Shared mutable state.** Default to splitting the target so concurrent workers don't share a file, branch, or key; serialize only for real invariants.
   - **Smallest safe decomposition.** If one worker is best, name why.
   - **Deliverable slicing.** Name the smallest independently-landable PR and what stacks on it, before fan-out; `n/a: <reason>` if genuinely atomic. When the user conditions scope on cost ("if it's cheap, do it all"), that is an empirical fork — answer it with an estimate for each branch, not a silent choice. When stacking: one owner per PR, the coordinator alone owns stack topology.
4. Name the data shape and its organizing structure (state machine / table / typed model) before any logic is written; put it in the delegate's brief. When delegation is allowed, delegate implementation per the active runtime's guidance with a specific scope (file paths, the named shape, success criteria); review the diff yourself. For work worth doing solo, the same brief becomes your own plan — the discipline is the brief, not the delegation. Surgical edits; port shared-primitive improvements to all consumers and verify each. Commit liberally. Implementation is the test of the design: a parameter, state, or branch the chosen shape did not anticipate is surfaced in the decision trail, not absorbed. A *pattern* — the same workaround across unrelated call sites, escape hatches (`any`, casts, optional fields always set in practice), callers needing the abstraction's internal rules, a lock where the shape said state was not shared — means the shape is wrong: stop, re-ground on what was built, re-run `design-it-twice` with the new constraints as day-one assumptions and a smaller sketch, then continue. Bolting fixes onto a wrong shape is the failure this step exists to catch. In WIP mode, `agent-ready` applies the same ladder to each correction received in review.
5. Verify on the matching surface — the repo's `verify-<app>` skill if present, else drive the real surface. "Inconclusive" or wrong-surface is not a pass; flag it.
6. Rebase into small, ordered commits, each landable and verified before the next; stack follow-ups.
7. If the design is contested or the diff is expensive to undo, add one adversarial reviewer briefed to refute it (cross-family `codex-worker`, via `delegate`) on top of finalize's `review` — never a higher code-review level, which is an eight-angle fleet. Reviews run against a pinned committed SHA, and fix rounds start only after every reviewer of that SHA reports (per the standing trigger).
8. Run **Opening a PR**.

Rewrite the checkpoint at phase boundaries; spawn a fresh delegate with consolidated scope rather than chaining interrupts.

**Reply:** what you built, what you chose and why, open decisions. Tables for design alternatives.
