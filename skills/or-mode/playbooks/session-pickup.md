### Session pickup

**You own the resume point. Read the prior trail, don't redo it.** For "take over this", "resume this", "continue from <transcript/branch>", "pick up where X left off".

A pickup is inheritance. The prior agent already paid the cost of reading the code, running the repros, making the design choices. Redoing loses the bias check and burns context. Resist the urge to re-derive; read.

1. Locate the prior trail: a `decisions.md`, handoff, or resume note in the worktree (the file is the truth, not the chat), the active runtime's task or session history, or a pushed branch. Parse a long transcript in a subagent when delegation is allowed and keep the reduced timeline in the main thread.
2. Reconstruct operational state: the branch and worktree, what already landed (`git log`, `git diff` against the base), the open todos, the decisions made. The prior trail is authoritative input.
3. Diff done vs pending. Name the resume point; do not re-run the prior repro or redo completed work. A "let me verify from scratch" pass is the tell that you're treating the trail as untrustworthy when it's actually authoritative.
4. Route the remaining work to the matching playbook. The pickup playbook ends here; the routed playbook owns the rest.
5. Verify the inherited *claims of completion* against the original goal on the real artifact before building on them. A passing prior self-report is not the proof.

**Reply:** where the prior agent stopped, what you inherited vs redid (ideally nothing redone), the resume point, and the outcome.
