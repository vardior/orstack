---
name: maintain-upstream
description: "Review the projects orstack borrows from (cursor/plugins pstack and cursor-team-kit, mattpocock/skills, humanlayer/skills) since their last pins, port what is worth taking, and record the review. Use only for /maintain-upstream in Claude, $maintain-upstream in Codex, or an explicit request to refresh upstream."
disable-model-invocation: true
metadata:
  internal: true
---

# Maintain upstream

orstack is a hard fork. Nothing syncs automatically: each review reads what changed upstream since the last pin, takes the few ideas worth taking in orstack's own wording, and records the decision so the next review doesn't relitigate it.

Everything about upstream lives in this directory:

- `sources.json`: each source repo, its license, the commit it was last reviewed through, the paths to watch, and which pristine copy came from which upstream file at which commit.
- `pristine/`: unedited copies of the upstream files orstack's skills were derived from, so `diff -ru pristine/<source>/<path> ../../../skills/<skill>` shows exactly what orstack changed. Never edit them except to refresh one to a newer upstream commit.
- `references/derivation-map.md`: which orstack file came from where, and how it differs.
- `references/review-log.md`: one dated entry per review, with what was taken and what was deliberately not taken and why. Read it before proposing anything.

## Review

1. For each source in `sources.json`, clone it shallowly enough to reach the pin (`gh repo clone <repo> <scratch>/<name> -- --filter=blob:none`) and list `git log --oneline <reviewedThrough>..HEAD -- <watch paths>`. A source with no commits in range is done.
2. For each commit, read the change and decide: take, or not take with a one-line reason. Not take when `review-log.md` already declined the same idea, when an orstack skill already covers it, when it is specific to the source's runtime (Cursor tools, Cursor CDP), or when it fans out agents: orstack runs one agent per question, with a second only when two model families disagree on a decision that is expensive to undo.
3. Port each take into the orstack skill that owns the behavior, in orstack's wording, keeping the skill's existing structure. A whole new skill copied from upstream needs its license notice in the repo's `LICENSE`.
4. When a pristine file's upstream source changed and you took text from that change, refresh the pristine copy to the new commit in the same commit as the port, and update its `at` in `sources.json`. Leave pristine copies you took nothing from at their old commit.
5. Set each source's `reviewedThrough` to the commit you reviewed through, add a `review-log.md` entry (date, source, range, taken with commit refs, not taken with reasons), and update `derivation-map.md` for any file whose origin changed.

Report the takes, the declines that weren't already in the log, and anything you were unsure about, so the user can overrule before it merges.
