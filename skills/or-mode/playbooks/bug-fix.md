### Bug fix

**You own this task. Plan, review, verify.** For a reported defect to reproduce, root-cause, and fix with runtime evidence.

Be scientific. Every shipped line traces to runtime evidence. Belt-and-suspenders that "might help" is a hypothesis, not a fix; it does not ship. When evidence refutes a hypothesis, revert what it motivated. The smallest change the evidence justifies ships, nothing more.

0. Restate the report in plain words: the symptom, who hits it, and the observable that says fixed. Separate the reporter's hypothesis from the symptom; the hypothesis is one candidate in step 1, not the starting point.
1. Run the `diagnosing-bugs` skill — it owns the diagnosis loop (reproduce, hypothesize, bisect, instrument, confirm the mechanism). Its non-negotiables apply here: reproduce it yourself on the matching surface (the repo's `verify-<app>` skill if present, else drive the surface directly); don't hand the repro to the user. Ask the user only with a stated, specific reason the surface cannot be reached from here, and only after driving it as far as it goes. A bug you can't reproduce, you can't prove fixed.
2. Confirm the surviving *mechanism* with runtime evidence before designing the fix; a design grounded on a plausible-but-unconfirmed cause can be unanimously wrong while the real cause sits one subsystem over.
3. Plan the fix. `design-it-twice` first only when the fix reshapes a seam that is expensive to undo; a fix crossing a module boundary does not by itself earn a design round. When delegation is allowed, delegate implementation per the active runtime's guidance, with file paths, scope, and success criteria; use `codex-worker` for a precisely specified independent Codex sequence. Review the diff yourself.
4. Verify on the same surface; the original repro now passes. "Inconclusive" or wrong-surface is not a pass; flag it. Unit tests show branch behavior, not bug absence.
5. When the bug has a practical test seam, keep a regression test that fails on the buggy code and passes on the fix with the same assertion, and confirm the red is the defect, not setup or fixture. No seam, or the test costs more than the bug: `skip: <reason>` and keep the repro. Separate red/green commits are optional.
6. Run **Opening a PR**.

**Reply:** what was broken, root cause, fix, how you verified. Paste failing-then-passing repro output verbatim.
