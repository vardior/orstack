# Wave planning

Order work by file overlap, not by theme. List each item's files before dispatch. Disjoint files
can run in parallel. A shared file, service, queue, database, or evidence index creates an ordered
edge; name the item that waits and recompute the overlap zone before resuming deferred work.

## Worked example

Five items on one service: A (new export endpoint), B (rate limiter middleware), C (export job
queue), D (admin UI for export history), E (retention cleanup). The safe order was `A ∥ B now;
C after A; D after C; E after C`:

```text
A export endpoint          ∥          B rate limiter
       │
       ▼
C export job queue
       │
       ├──────────────┐
       ▼              ▼
D admin history   E retention cleanup
```

A and B touched disjoint files, but both live drives used the same local database and therefore
took turns. C extended the handler A added, so it waited. D and E both read C's job records and
ran after it; they could run in parallel with each other because their files were disjoint. Put
the exact paths and the shared-resource owner in each brief.

Re-derive every audit target against the current tree before writing its brief. Audits go stale
within a day: an item may already be done, and a proposed shape may break a checked-in rule. Read
the nearest `AGENTS.md` for each directory the brief touches. Where an audit shape contradicts a
strict rule there, the rule wins and the brief says so. A brief once asked for a
`Record<Enum, config>` in a frontend that bans them, and review bounced the PR.

An audit gap can be a decision. Before briefing "add the missing X", grep the owning skill's
references and the git log for X's removal. An audit once flagged a missing flow doc that the
owner had deleted on purpose, with a skill rule banning agents from recreating it.

## Worker dies mid-tail

Treat the uncommitted diff as the work, not as lost work. A fresh worker should:

1. Read the original brief, the worker's `decisions.md`, the PR review threads, and the current
   worktree diff.
2. Map each hunk to the review thread or acceptance item it serves; drop unexplained hunks.
3. Prove the recovered change with the requested tests and live evidence, then commit it on top.
4. Reply to each applicable thread with the commit that carries the fix, run `finalize`, push, and
   tail the exact head.

Record the death cause, recovery worker, preserved evidence, and any missing proof in the handoff.
Do not force-push, amend a head recorded in evidence, or rerun a shared live drive while another
worker owns the queue.
