---
name: deslop
description: Remove AI-generated code slop and clean up code style
---

# Remove AI code slop

Check the diff against the base branch and remove AI-generated slop introduced in the branch.

## Focus Areas

- Every comment, doc comment, or docstring the branch added, unless a tool consumes the text (the schema exceptions in the global working defaults, such as REST API Swagger docs or MCP tool schemas). Do not soften or shorten them — delete them, and rename or split the code if it needed explaining. Moving the text into the PR body or commit message does not discharge this; the code has to carry the reason by itself
- Defensive checks or try/catch blocks that are abnormal for trusted code paths
- Casts to `any` used only to bypass type issues
- Deeply nested code that should be simplified with early returns
- Duplication, wrappers, or indirection the branch added where a direct call or an existing helper would do
- Dead code the branch left behind: unused members, parameters, branches, or flags
- Other patterns inconsistent with the file and surrounding codebase

## Guardrails

- Keep behavior unchanged unless fixing a clear bug.
- Prefer minimal, focused edits over broad rewrites.
- Keep the final summary concise (1-3 sentences).
