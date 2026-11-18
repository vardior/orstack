# Audit templates

Use these as copy-ready report shapes. Every claim has a file-and-line citation or an explicit
source query. Keep raw review data beside the report as JSONL, not in the agent's working context.

## Architecture

```markdown
# <area> architecture audit

## 1. Nouns
| Noun | Canonical definition | Spellings found | Evidence |
|---|---|---|---|

## 2. Boundaries
| From | To | Evidence | Enforced? | Gap |
|---|---|---|---|---|

## 3. Copy targets
### Good
### Bad
| Pattern | Evidence | Why it spreads | Correction |
|---|---|---|---|

## 4. Findings ranked
| F# | invalid state or duplication | file:line | target shape | layer | blast radius | confidence | size |
|---|---|---|---|---|---|---|---|

## 5. Target shape
## 6. Enforcements
| Mechanism | Forbids | Existing violation | Cost |
|---|---|---|---|
```

## Review inventory

List the exact PR population and cutoff. Use `gh` read-only calls to fetch the last N merged PRs
touching the area's paths, then fetch each PR's review comments, review bodies, issue comments, and
commits. The review-comment calls are `gh api repos/{owner}/{repo}/pulls/{n}/comments --paginate`,
with the matching `pulls/{n}/reviews` and `issues/{n}/comments` calls. Filter with `--jq`; retain
trimmed records in a sibling `<report>.raw.jsonl` file:

```json
{"repo":"owner/repo","pr":123,"url":"https://github.com/owner/repo/pull/123","author":"user","is_bot":false,"kind":"comment","text":"...","path":"src/file.ts","cluster_id":"C01"}
```

```markdown
## 1. Method and coverage
## 2. Clusters
| ID | Name | Count | Example URLs | Correction | Layer | Mechanism | Exists? |
|---|---|---:|---|---|---:|---|---|
## 3. Already-encoded
## 4. Top 10 by leverage
## 5. Style-guide residue
```

Classify human versus bot explicitly. Count substantive corrections, nits, approvals, and excluded
acknowledgements separately. Every cluster needs at least two real examples.

## Verification surface

```markdown
# <area> verification-surface audit
## 1. Inventory
| # | Surface | Location | Level | Entry command | Evidence | Last proven | Status | Overlaps |
|---:|---|---|---|---|---|---|---|---|
## 2. Overlap map
| Question | Keep | Delete or fold | Capability to preserve |
|---|---|---|---|
## 3. Feature-map gaps
| Feature or route | Mapped? | CLI-drivable? | Ever driven? | Missing lever or fixture |
|---|---|---|---|---|
## 4. Paved path proposal
## 5. Skill consolidation plan
## 6. Feature-map maintenance
```

Every inventory row names a real entry command and evidence location. Distinguish worker-only,
context assembly, triggered job, CI lifecycle, and UI proof. “Never” is valid only when the
evidence index or source proves it; a stale stamp is a finding.

## Tooling or worker repository

```markdown
# <repo> tooling audit
## 1. Nouns and layout
| Noun | Defining files | Alternate spellings | Assessment |
|---|---|---|---|
## 2. Boundaries
| Boundary | Evidence | Enforced? | Holding mechanism |
|---|---|---|---|
## 3. Copy targets
## 4. Findings ranked
| ID | Finding | Evidence | Fix | Layer | Blast radius | Reversibility | Size |
|---|---|---|---|---:|---|---|---|
## 5. Enforcements
## 6. Contract surface
```

Derive the import graph from actual imports. Count current violations before proposing a lint
promotion. Cover every field and error code in the caller-visible contract. If a second checkout is
present, record the canonical decision and treat the legacy checkout as a comparison only.

List every directory an agent job shares with later jobs: caches, tool homes, `/tmp` paths. For
each, say whether any tool reads configuration or executes code from it. A shared Gradle user home
runs every `init.d` script on each build, so one job could plant code in the next; share only
content no tool executes.
