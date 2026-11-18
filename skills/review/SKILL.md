---
name: review
description: Review a code change for actionable bugs, regressions, and violations of repository conventions. Use when asked for code review or during finalize.
---

# Code review

Understand the intended behavior, read the change in context, and report issues the author should
fix before shipping. Use one reviewer; a separate adversarial pass is the caller's decision.

## Review

1. Establish the requested scope and base, including uncommitted changes when requested. Read the
   applicable repository instructions and the ticket or brief, if available.
2. Read the diff and enough surrounding code to understand the affected behavior. Follow callers,
   consumers, and data flow where needed.
3. Look for correctness bugs, regressions, security issues, and meaningful performance or
   compatibility problems. Check whether the implementation fulfills the intended behavior and
   handles relevant failure cases.
   At untyped boundaries, check that validation proves the complete promised shape, not just a
   field's presence or a type assertion. Prefer parsing through the existing authoritative schema;
   flag incomplete validators, and do not require a new schema dependency for one guard.
   For every new or changed database query, including filters passed to storage helpers, name the
   collection/table and usable index from the repository's index declarations. Flag equality
   predicates left to post-fetch filtering behind a low-selectivity leading key (server, tenant,
   provider); an index scan alone is not proof of adequate coverage. Count repeated lookup call
   sites across operations and loops, quantify their frequency per item/job/request, and multiply
   by per-call cost. Flag data re-fetched that the caller already holds. Where explain evidence
   exists, compare work examined with rows returned; for
   Mongo, compare `totalDocsExamined` and `totalKeysExamined` with `nReturned`, not just `IXSCAN`
   versus `COLLSCAN`. State missing planner evidence rather than treating it as a pass.
   Any comment, doc comment, or docstring the change adds is a convention violation unless a tool
   consumes the text (REST API Swagger docs, MCP tool schemas); report each
   with its line. Code that is only understandable with the PR body or ticket at hand is also a
   finding: the code must explain itself to a reader with no other context.
4. Examine tests and verification evidence. Determine what they actually cover and identify
   material gaps. For changed tests, name the failure each would catch. Treat a weakened, rewritten, or
   deleted assertion, a refreshed snapshot, or new mocking around the changed code as a hidden
   regression until the diff shows the contract changed. A missing test is a finding only with a
   concrete failure scenario; counts and coverage are not. Flag tests that mirror the
   implementation without adding protection. When invoked by finalize, assess whether its required live verification covers
   the delivered change, including changes made after verification. Verification that stopped
   short of the end-to-end job without a stated, sufficient excuse is a finding in its own right.
   When the change alters an interface, a constructor or DI registration, an options shape, or a
   supported-value set, check finalize's affected-CI evidence: a specific consumer project or
   existing test it should have selected and did not run is a finding; a generic call for more
   tests is not.
5. Investigate suspected issues before reporting them. Use a focused reproduction when practical;
   distinguish demonstrated failures from conclusions supported by code inspection.

## Findings

Report actionable issues introduced or exposed by this change, highest severity first. For each,
name the severity, affected file and line, triggering input or situation, and what goes wrong and
why it matters.

Prefer concrete reasoning over speculative concerns. Skip style preferences, generic advice,
and unrelated cleanup unless they violate an explicit repository rule or materially affect the
change. Report any substantiated bug, including unfamiliar failure modes. Do not invent findings
to fill a quota.

If no actionable issues are found, say so. Briefly state any material verification limitation;
do not imply that inspection proved runtime behavior. Merge authorization stays with the caller.

Review is read-only unless fixes are requested. Do not change code, maintain shared instructions,
post comments, or merge as part of this skill.
