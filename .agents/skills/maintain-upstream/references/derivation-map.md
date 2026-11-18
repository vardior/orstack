# Derivation map

| orstack file | Derived from | How it differs |
|---|---|---|
| `skills/or-mode/SKILL.md` | pstack `poteto-mode/SKILL.md` | Rewritten: routes to orstack's skills, uses idioms that work in both Claude Code and Codex, defers authority rules to the active runtime. The restate-first trigger comes from poteto's pstack guide pt. 2 ("indirect prompt"). |
| `skills/or-mode/playbooks/*.md` (10) | pstack `poteto-mode/playbooks/*.md` | Adapted: Cursor tools became Claude Code and Codex tools, `gt` became `gh`, pstack skills became orstack's. |
| `skills/create-verification-skill/` | pstack, same name | Ported to a portable `.agents/skills` + `.claude/skills` layout with orstack's drivers. Adds CLI-first control guidance (from poteto's guide pt. 1) and a fixed evidence-bundle layout (`evidence/<ts>-<slug>/EVIDENCE.md`, `INDEX.md`, and a `## For the PR` block as the only reviewer-facing excerpt). Readiness, missing-seed failures and stand-in proof limits adapted from `c49b37a`. Feature files may carry a `## Source` section with implementing paths, which upstream keeps out of the map. |
| `skills/maintain-verification-skill/` | pstack, same name | Ported with the same substitutions. Triage moves hand-run procedures into the control CLI, and `--features` scopes a run to named features. |
| `skills/create-formal-verification-skill/` | pstack, same name (`8b3326d`) | Explicit-only in both runtimes. Adds evidence tiers, separate-step and per-attempt write modeling, mutation of the real implementation, counterexample replay through the real boundary, external evidence, exact restoration and owned-resource cleanup. `maintain-formal-verification-skill` isn't ported; the generated skill carries its own upkeep. |
| `skills/deslop/` | cursor-team-kit `skills/deslop/` (`fd87869`) | Near-verbatim. "main" became the base branch, and two structural focus areas (duplication and indirection, dead code) were added. |
| `skills/bro/` | pstack `skills/bro` | Verbatim. |
| `skills/grilling/` | mattpocock/skills `skills/productivity/grilling/` (`74ca5fe`) | Fan-out removed, a brief-writing paragraph added, yes/no questions worded so yes accepts the recommendation (`95249b0`). |
| `skills/visual-pr/` | humanlayer/skills `plugins/visual-pr` (`4e39d8f`) | The idea of a structural PR description, in orstack's wording. Keeps orstack's ticket and verification conventions and leaves commit, push and PR creation to finalize. The fixed template, HumanLayer task paths and final-answer template weren't ported. Its MIT notice ships next to the skill. |
| `skills/diagnosing-bugs/` | partly mattpocock/skills | Confirms a forced mutation landed before trusting a red test (`f3fc563`). The perf checklist's "decide what a measurement must resolve first" comes from pstack `ab1f702`. |
| `skills/deslop-sweep/` | none | Orstack's own, built on `deslop`'s focus areas. |

Pristine copies of the pstack and cursor-team-kit sources are in `../pristine/`; `../sources.json` says which commit each is at. mattpocock/skills and humanlayer/skills have none, because only ideas were taken.
