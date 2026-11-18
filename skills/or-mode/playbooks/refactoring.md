### Refactoring

**You own the contract. The structure changes; the behavior does not.** For "refactor", "rename", "extract", "inline", "dedupe", "restructure", "move this module", "tidy up". Distinct from Feature (adds behavior) and Bug fix (corrects it).

A refactor that smuggles in a behavior change loses its safety net. If the cleanup reveals a missing feature or a real bug, split it out and ship the structural change first against the pinned contract. A redesign is allowed, but name it and route to Feature.

1. Pin the behavior contract first. Learn the contract from the code, name the existing tests that hold it, and add a characterization test or equivalence harness only where material behavior is unprotected, before any structure moves. The pin makes "refactor" a checkable claim. Type check, lint, and snapshots of incidental structure are not a pin.
2. Name the structure the code is missing: a state machine over scattered booleans, a table or registry over spread-out branching, a typed model over repeated shape assumptions. Boring code stays when the shape is already clear and local; the reshape must delete branches or invalid states, not add indirection. For a retroactive sweep, `agent-ready` ranks the missing structure on the correction ladder before choosing the move.
3. Name the target shape — module layout, types, call graph as if built today. `design-it-twice` the shape before the move when the target shape is expensive to undo — a published interface, a persisted shape, a cross-service contract; an internal reshape with all callers in the repo is not.
4. Subtract before you add. Delete dead weight, collapse one-caller wrappers, drop redundant validators and orphan references before introducing the new shape. The smallest change that reaches the target shape ships.
5. Move in small behavior-preserving steps, each keeping the pin green. For API reshapes, migrate every caller and delete the old API in the same wave — no compatibility shims, no parallel old-and-new paths. Spot-check every rename against actual files; renames silently miss usages in strings, prose, and back-references. When delegation is allowed, delegate mechanical edits per the active runtime's guidance or use `codex-worker` for high fan-out; review the diff yourself.
6. Prove behavior unchanged on the real artifact, not "it compiles": diff old-vs-new outputs, replay a recorded baseline, or smoke-run the matching surface. Own the verification; don't trust a delegate's "looks good".
7. Confirm the change earns its place: fewer layers between question and answer, less hidden state, fewer single-consumer indirections. If the diff doesn't lower reader load somewhere, revert it.
8. Rebase into small ordered commits that tell the story — subtraction, then reshape, then follow-on cleanup, so a single revert undoes one slice. Run **Opening a PR**.

**Reply:** the structure that changed, the pin you held it against, the equivalence proof, the reader-load delta, what shipped and what got reverted. No new behavior.
