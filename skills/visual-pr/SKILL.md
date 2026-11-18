---
name: visual-pr
description: Compose a concise PR description with a structural sketch when it helps explain the change. Use when asked to describe a PR or during finalize step 5.
---

# Visual PR

Help a reviewer understand why the change exists, how it works, and what was verified.
Scale the description to the change; a small fix may need only a short explanation and verification.

## Compose

1. Establish the target branch or PR and its base. Read the complete diff, relevant surrounding
   code, applicable repository instructions, and the ticket or brief when available. During finalize,
   use the reviewed diff and evidence bundle supplied by the caller. When updating an existing PR,
   read its current body with `gh pr view` and preserve human-written context and links.
2. Follow the PR conventions in `../or-mode/playbooks/opening-a-pr.md` and the repository. Spend
   about 120 words of prose plus at most one table. Start with the full Jira URL — `closes` when the
   PR completes the ticket's scope, `relates to` when it delivers only a part — and never invent a
   ticket. Then one opening paragraph: what was wrong or missing, and what the change does. Then
   `## Verification`. A one-file or otherwise small diff ends there. `## Scope`, `## Tradeoffs`, and
   `## Blast Radius` earn their place only when a reviewer needs them to assess the change, and
   `## Blast Radius` is one sentence.
3. Add a structural view only when the change has a shape a reviewer must hold in their head — a
   flow, a contract, a component tree. Never on a test-only or one-line diff. Choose the smallest one
   that helps: a before/after pseudocode diff, a call or data-flow tree, a key type or API contract.
   Use the existing `show-me` skill's conventions when useful; keep the result inline in
   GitHub Markdown. Prefer a focused diff for an existing shape and a complete block for a new one.
   Label pseudocode as illustrative. Check every path, symbol, and relationship against the code;
   preserve decision order and conditions, including failure paths, when simplifying control flow.
   Omit visuals that merely repeat the prose or list changed files.
4. Keep explanations separate from proof. Under `## Verification`, lift the evidence bundle's
   `## For the PR` body verbatim, without local paths, bundle metadata, or raw logs. It is already
   written in the shape the PR needs: one plain sentence naming the surface that was driven and why
   it is right for this diff, then a `| Driven | Observed |` table holding every count and number.
   No `Verification tier:` label, and no "this proves … / it does not …" pair unless a tier lower
   than the whole job was taken, in which case one sentence states the excuse. If that excerpt
   carries local bookkeeping or spends prose on numbers, correct it before composing the description.
   Include the screenshots and recordings required by finalize Step 1 alongside the claims they
   support; finalize owns their upload. A diagram alone proves no runtime behavior. If required
   media is missing, state the capture or upload blocker in `## Verification` and report it to the
   caller; do not silently omit it or invent a result.
5. Read the draft as a reviewer without access to local files. Remove empty sections, boilerplate,
   repetition, sentences that restate the diff, and claims unsupported by the diff or evidence. On
   updates, replace evidence attachments superseded by fixes with current captures; retain unrelated
   human content and attachments.

A test-only PR at full budget reads like this:

    closes https://jira.example.com/browse/PROJ-1234

    `DateRangeParser` turns the report filter's free-text range into start and end dates, but only
    the report endpoint's tests covered it indirectly. This adds 12 direct tests, one per accepted
    format. Production code is unchanged.

    ## Verification

    Test-only diff, so the question is whether the tests catch what they claim. Each format rule
    was broken in production code one at a time.

    | Driven | Observed |
    |---|---|
    | Break each of the 4 format rules | exactly its tests fail, the rest pass |
    | Restore production, run the 12 tests and the project suite | 12/12, 2,140/2,140 |
    | Build with analyzers on | clean |

## Deliver

Return the PR body, or save it to the caller's requested path outside the tracked source. Do not
create task folders or commit description drafts. This skill does not commit, push, open PRs, or merge;
finalize owns delivery.

If the user explicitly requested updating an existing PR's description, publish the composed body
with `gh pr edit <number> --body-file <path>` and read it back to confirm. Otherwise return the draft
for the caller to publish. Keep scratch paths and workflow narration out of the PR body.
