### Autonomous run

**You own the exit condition. Define done, then drive to it without stopping.** For "going to bed", "run until done", or "keep checking until X".

1. State the exit condition as a checkable predicate before the first iteration (tests green, repro fixed, all N PRs merged). A vague goal stalls; a predicate lets you stop.
2. Choose one completion mechanism for each job: automatic child completion, a blocking task wait, a native PR watch, or a background completion watcher. While waiting, let the mechanism block or wake the session; do not run model turns to repeat status checks. If no event mechanism exists, one bounded script polls the terminal predicate with sensible backoff and reports once. A wait that may outlive the session goes into `decisions.md` with its predicate, watcher and resume command, so a fresh session reattaches instead of starting a second watcher.
3. Each iteration makes the smallest change the evidence justifies, verifies it against the predicate, commits if it advanced, discards changes that didn't help. Belt-and-suspenders that "might help" gets reverted, not left to ride. Verify each unit before the next instead of batching checks at the end.
4. Mid-run discoveries that support the goal are yours. Address broken skills, related bugs, flaky verifiers, and fixable drift yourself; put out-of-band fixes in their own PR. Do not park reversible work for the human. Surface only irreversible actions, genuine product/preference calls no experiment can settle, or a real dead end. Return to the predicate after each side fix.
5. Checkpoint every iteration in the decision trail (the worktree's `decisions.md`): one line per iteration — what changed, whether the predicate moved, evidence pointer. A run with no trail can't be audited or resumed.
6. Stop when the predicate is met. A plateau is not a stop — pivot the approach to push past it. Surface a genuine dead end rather than spinning, and never relax the predicate to declare victory. A grade-and-fix loop freezes its rubric before round one and stops after a round with no correctness findings or at five rounds, because a fresh grader always finds something.

**Reply:** the exit condition, iterations run, what landed, what was discarded, final predicate state — as the final report in `or-mode/SKILL.md`. A stale report is worse than none: send a corrected one when the tail moves.
