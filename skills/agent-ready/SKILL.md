---
name: agent-ready
description: Audit and reshape a feature area into an agent-ready paved path, or apply the same correction ladder during feature work. Use only for explicit /agent-ready, $agent-ready, or equivalent make/hunt requests.
disable-model-invocation: true
---

# Agent-ready

## 0. Modes

Use this skill in one of two modes:

- **SWEEP** retroactively audits an existing area, ranks its findings, and ships the fixes as
  ordered, small, verified PRs.
- **WIP** applies the same discipline while a feature is being built, so each correction lands at
  the strongest feasible layer the same day it is learned.

`or-mode` conducts this workflow. Read the repository's `AGENTS.md` and `CLAUDE.md` first; they
own authority, permissions, commands, and delivery rules. Use `deslop-sweep` for its conflict-zone
and worktree rules rather than copying them here. Read [worker-tail.md](references/worker-tail.md)
before dispatching a worker.

## 1. Correction ladder

Give every audit finding and every review correction a layer number:

1. Codebase, architecture, or data structure: make the bad state impossible.
2. Static analysis, compiler, or CI: reject the remaining bad state deterministically.
3. Repository rules or review bots: catch a stable violation at the repository boundary.
4. Skill: teach a repeatable procedure with the needed tools.
5. Style guide or human review: retain judgment that cannot be derived or checked.

Choose the lowest feasible layer. If a layer 1 or 2 fix is practical, do not leave the lesson as a
rule or a skill. Layer-5 residue becomes a proposal to the human, never a new prose rule. Product
semantics, billing, quotas, and other user-visible decisions become tickets and decision-trail
entries, not refactors made by inference.

## 2. SWEEP

### Establish the work root

Before editing, identify the canonical repository and base branch. If a second repository is
involved, prove which checkout is authoritative before counting findings; name dormant or legacy
trees explicitly. Read the charter, roadmap, decisions, existing briefs, audits, and recent run
handoffs before dispatching. Create or use this layout:

```text
README.md                 charter and exit predicate
ROADMAP.md                one status surface
decisions.md              one line per decision
briefs/                   eight-field worker briefs
audits/                   read-only reports
runs/<id>/HANDOFF.md      one six-header handoff per run
logs/                     worker stdout and stderr
```

The sweep is complete only when every audit-derived item is a merged or open PR, or is explicitly
parked in `ROADMAP.md` with a reason. Record each PR URL, evidence bundle, and CI watcher there.
The lead reviews every diff and merges only under the human's standing grant.

### Read-only audit wave

Run four parallel, independent, read-only audits. Use the copy-ready shapes in
[audit-templates.md](references/audit-templates.md):

- **Architecture:** list invalid states and duplication in a findings table with
  `F# | invalid state or duplication | file:line | target shape | layer | blast radius | confidence | size`,
  then state the target shape, behavior-preserving sequence, and enforcement candidates.
- **Review inventory:** mine the last N merged PRs touching the area's paths, including human and
  bot comments and follow-up fix commits. Cluster corrections, rank by count times leverage, and
  map every cluster to the strongest preventing layer.
- **Verification surface:** inventory every way the area is proven, the one paved path or its
  absence, and every evidence-standard violation.
- **Tooling or worker repository:** first establish the canonical repository, then audit its
  boundaries, copy targets, contracts, and enforcements. A dormant legacy checkout is evidence,
  not the ship target.

Cross-check review clusters against `ROADMAP.md`. A top cluster with no item at layer 1 or 2 is
parked there with the reason. Keep product-semantics findings as ticket candidates.

### Plan and dispatch waves

Use the correction layer and file overlap to order the work:

1. **Subtract, extract, pin:** dead paths, one-caller wrappers, pure extraction, and contract pins
   such as TS-to-C# parity or bijection tests.
2. **Remove illegal states:** one enum instead of enum times bool, a transition table instead of
   scattered pairs, a lifecycle-owning interface, or one store instead of two.
3. **Pave and enforce:** architecture tests, lint rules, CI checks, and one pointer where agents
   actually look.

Disjoint files may run in parallel. Shared files, services, queues, databases, and evidence
indexes serialize. Write the dependency explicitly: which item runs now and which item waits.
Use [wave-planning.md](references/wave-planning.md) for the overlap example and worker recovery
pattern.

Each item gets one eight-field brief on disk using the active `or-mode` brief template, one fresh
worktree, and one worker routed through `delegate`. The worker follows
[worker-tail.md](references/worker-tail.md), runs the repo's live verification, and leaves a
durable evidence bundle before its PR. The lead reviews scope, comments, and attribution, records
the URL, arms one watcher, and owns the tail. Never let a product-semantic finding turn into code
without the required human decision.

## 3. Build the verification lever with wave 1

Do this alongside the first implementation wave, never after it. A `control-<app>` CLI must be
able to launch or connect to the real app, drive the external flow, assert the external result,
and write durable raw evidence. A feature map must name user intent, entry point, drive command,
expected result, and evidence location. Its drive stamps derive from valid evidence bundles, not
hand edits.

Use the repository's `verify-<app>` skill when it exists; otherwise create the smallest one that
can prove the changed surface. A bundle lives under `~/<repo>-verify/evidence/<timestamp>-<slug>/`
and includes `EVIDENCE.md` with SHA header, driven-to-observed table, raw artifacts, caveats, and a
`## For the PR` block, plus an index entry. Exercise the real user path and side effect. Tests,
typechecks, mocks, and a prediction endpoint are supporting evidence, not a full job proof.

A drive that runs an agent on a developer machine gives it its own HOME. Snapshot the developer's
global state (`~/.gitconfig`, user-level package installs, tool homes) before the drive and diff it
after; a change there is a finding, not noise. Evidence collection
starts at the drive's trigger time, so a reused job id cannot bundle an earlier run's files as its
own.

When the verify skill has no drive for the surface a brief changes, the brief authorizes adding
one. Otherwise workers hand-build an invocation outside the skill, and the next worker does it
again.

Shared infrastructure has one driver at a time. Check ownership first, poll while another driver
is active, and never kill a process or container you did not start. The live acceptance run is
explicitly permitted even when a worker-tail `FORBIDDEN` section otherwise bans service launches.

## 4. WIP

Before implementing a feature, ask whether a verification lever exists for its surface. If not,
the first PR is the lever. Name the data shape before logic: use a state machine for state, a
registry for variants, and a typed model for repeated shapes. Make the second variant a real seam,
not a copied branch.

For every review correction, assign a layer immediately. If layer 1 or 2 is feasible, ship that
constraint in the same PR or a same-day follow-up. Leave no shim or parallel old/new path for an
agent to copy; delete the old way in the same wave. Put a workaround in `decisions.md` and a
ticket or PR, never in a code comment.

## 5. Reporting and completion

Append one timestamped decision and evidence pointer per meaningful choice. Rewrite the run's
`HANDOFF.md` whenever the tail moves, with exactly:

```text
## Built
## PRs
## Evidence
## Needs you
## Loose ends
## Harness
```

The last acceptance test of a sweep is a fresh, unattended session shipping one small ticket in the
area through the paved path. Grade it hands-off, and fix the harness defects it exposes only after
the grade, so the fixes cannot change the outcome.

`ROADMAP.md` is the status surface. The handoff must state the exit predicate, canonical-repo
decision, findings left at each layer, PR URLs and heads, evidence verdicts, deliberate omissions,
deviations, and any context compaction. End only when the predicate is true or a genuine blocker is
under `## Needs you`; a blocked run still writes the handoff.
