# Worker tail

Read the repository authority files and the brief before changing code. Define a checkable exit
condition, keep one concise decision line per iteration in the named `decisions.md`, make the
smallest evidence-backed change, and commit it. Route fully specified execution through `delegate`.

Before the PR:

- Run the repository's named drift and agent-document checks, with the exact paths or `--all` form
  required by that repository.
- Run the repo's live acceptance flow and preserve the durable evidence bundle. A test or build
  alone is not live proof.
- Run `finalize` before opening the PR. It owns live verification, deslop, review,
  diff cleanup, PR creation, and the tail.

Do not push the base branch. Do not edit `AGENTS.md`, `CLAUDE.md`, skills, hooks, or unrelated
files. Put no AI, agent, or model attribution in source, commits, PR text, review replies, or
evidence intended for reviewers. Do not merge, auto-merge, or open a draft. Stage named files only.
Wait for foreground commands to finish; a headless worker must not end its turn to wait.

Review bots post after the PR opens. Finish only after they have posted on the current head and
every thread is answered or resolved. A brief or ticket that says "merges" means ready to merge; the
lead merges.

Finish only after the requested `HANDOFF.md` exists. Its six headers are `## Built`, `## PRs`,
`## Evidence`, `## Needs you`, `## Loose ends`, and `## Harness`. The `FORBIDDEN` list never forbids the live
acceptance run explicitly required by `VERIFY`; report any lower verification tier and its reason
in the evidence bundle and handoff.
