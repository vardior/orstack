### Pause safely

**You own a clean stop. Leave a checkpoint a cold-start agent can resume from.** For "pause safely", "I need to go offline", and when context is about to compact mid-task. Explicit or compaction-triggered only — "going to bed, keep going" means continue (Autonomous run already checkpoints per iteration).

1. Stop at a safe boundary. Finish the current atomic step or back out of it. Never stop mid-edit in a known-broken state. Start nothing new; cancel nested subagents.
2. Don't cross an irreversible line to pause. No PR and no push unless one was already out.
3. Make the work durable. Commit uncommitted edits as one clear `wip:` commit on the current branch. If the tree is broken, say so in the commit body in one line.
4. Write the resume note off-context: intent, what you were doing, progress and what's verified, current state, next steps, key files, gotchas. Target: `<work-root>/decisions.md` or a `<slug>-resume.md` next to it. The in-context plan won't survive summarization; the file will.

**Reply:** where you are in the loop, what's on disk versus still in your head (paths, no diff dumps), the commits made and whether the tree is clean, and the first action on resume. This is a pause, not a final report; resume is the Session pickup playbook reading this note.
