---
name: create-verification-skill
description: "Generate a project-local verification skill that drives an app the way a user does across Claude and Codex. Use only for /create-verification-skill in Claude, $create-verification-skill in Codex, or an explicit request to add a real UI/CLI/service proof workflow."
disable-model-invocation: true
---

# Create a verification skill

Every serious project needs a scripted way to drive the real app and prove behavior: launch it, exercise a feature the way a user would, and capture evidence. This skill generates that as a project-local `verify-<app>` skill tailored to the repo. You write the generator's output for the next agent, not for a human: it will be read cold, mid-task, by an agent that has never seen the app.

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI/TUI, a desktop app, an API, a mobile app, a library? A repo can have several; pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented dev command (package scripts, Makefile, README quickstart). Note ports, env vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically? Existing harnesses first — Playwright/Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port. Only then pick a generic recipe: browser/CDP for web and Electron, a tmux/PTY harness for CLI/TUI, plain HTTP for services.
- **Observe:** what evidence can be captured? Screenshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, say so in the generated skill: refusing to double-drive a shared instance beats corrupting the user's session.

If the checkout doesn't build or start as-is, fix that first (or report it precisely) before generating; a skill written against a broken base teaches wrong steps. When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, clearly marked as verification scaffolding, and remove it in cleanup.

## 2. Generate the skill

Choose the skill location before writing it. Preserve an existing project convention. For a repo used by both runtimes, make `.agents/skills/verify-<app>/` the canonical directory and add a relative `.claude/skills/verify-<app>` symlink to it; do not maintain two editable copies. For Claude-only or Codex-only repos, use that runtime's normal project skill directory.

Write `<skill-dir>/SKILL.md` with portable YAML frontmatter (`name: verify-<app>` and a `description` that names the app, the surface, and when to reach for it). Do not add runtime-specific frontmatter. Add `agents/openai.yaml` only when Codex-specific UI metadata or invocation policy is actually needed. Ground these sections in what the interview found, with no placeholders left:

- **Launch:** the exact command that starts the app for verification, and how to tell it's usable after migrations and seeding from an empty data dir; a responding port or healthy database can precede completed initialization. Include teardown. For a short-lived CLI or TUI there is no server to keep alive: launch means build the binary (or install deps) once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" — process up, right version/build, port owned by us, auth valid. An agent runs this first whenever anything looks off.
- **Drive:** the harness recipe with real selectors/commands from this repo, not examples. Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes. Where is fixed: a durable `evidence/` directory owned by the skill (never a session scratchpad — those are reaped), one bundle per run at `evidence/<YYYYMMDD-HHMMSS>-<slug>/` holding `EVIDENCE.md` (SHA header naming every branch, worktree, and harness SHA driven; a scenario table of driven → observed → evidence file; negative probes; caveats stated honestly; and a `## For the PR` block — the same proof written for a reviewer with no access to this disk: surface exercised, what it proves and does not prove, driven → observed, no bundle id, SHAs, or file pointers) plus the raw artifacts it cites, and an `evidence/INDEX.md` line per bundle (date, slug, SHAs, PRs, verdict) so a human can find what a session proved without reading transcripts. Two audiences, one file: the PR's `## Verification` section lifts the `## For the PR` block verbatim; everything else in the bundle is for Or and the digest and never crosses into the PR. State the proof standards: exercise the real user path, not internal setters or test-only endpoints; capture the action and the resulting state, not just the final screen; verify side effects (files written, rows inserted, messages sent) alongside what's visible; mocks only where a production boundary already isolates the external system. When the safe path is a dry-run or test mode, verify what it actually skips by observing (files, network, git refs) rather than trusting its name: some dry-runs still touch the network or open a browser.
- **Cleanup:** how to tear down instances the run created. Never kill by process name; kill what you started. Cleanup removes instances and scratch state, never the evidence: proof artifacts survive the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill body. A helper the reader has to reverse-engineer is not a helper.
- **Control CLI:** prefer shipping the Drive/Observe recipes as one small `control-<app>` CLI (subcommands like `doctor`, `snapshot`, `screenshot`, `send`, `press`, `wait-settle`) instead of prose an agent re-improvises into throwaway scripts — a lever, not markdown. Design it agent-friendly: composable subcommands that gradually disclose functionality, `--dry-run` on anything destructive, error messages that say what to do instead, machine-readable output (JSON), rich `--help`. The feature map's "Driving it" sections then quote CLI invocations, and every drive becomes reproducible. Skip the CLI only when an existing harness already gives one-command drives.

Add a one-line pointer to the generated skill in each agent instruction file the repo actually uses (`AGENTS.md` and/or `CLAUDE.md`).

## 3. Seed the feature map

Create `<skill-dir>/features/README.md` plus one file per user-facing feature you can identify (aim for the top 3-5 to start, from routes, commands, menus, or docs). Follow the shape in [`references/feature-map-example/`](references/feature-map-example/), with a README index and one file per feature. Each file answers, from the user's point of view: what the feature is, how to reach it, how to drive it with the harness, and what observable end state proves it works. The four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`. If seed data misses a journey's prerequisite, report the failure in that feature's `Gotchas`; keep the journey intact. The map is the repo's maintained verification source; a proof that drives one convenient entry point is incomplete when the map lists others.

## 4. Prove the generated skill before handing it over

Run its own instructions end to end once: launch, doctor, drive ONE mapped feature (one is enough; the map exists so later runs can cover the rest), capture evidence, clean up. After cleanup, confirm the evidence still exists at the named location — a cleanup that eats the proof fails this step. Fix what fails, and run the generated cleanup after every failed iteration too, so broken attempts don't strand processes and ports. A generated skill that was never executed is a draft, not a deliverable. When using a stand-in, list setup it supplied that the real target would lack; leave those steps unverified until exercised on that target.

## 5. Offer the maintenance loop

Point the user at `maintain-verification-skill` (`/maintain-verification-skill` in Claude or `$maintain-verification-skill` in Codex) for keeping the map honest as the app changes. Suggest a cadence only if they ask.
