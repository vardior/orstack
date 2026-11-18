# orstack

These are the skills I give my coding agents. The same skills work in Claude Code, Codex and any other agent that reads `SKILL.md`. I started from Cursor's [pstack](https://github.com/cursor/plugins/tree/main/pstack) and have been reshaping it on my daily work since. [The derivation map](.agents/skills/maintain-upstream/references/derivation-map.md) says what came from where.

Most of it enforces one habit: an agent doesn't get to call a change done until it has run it for real, cleaned up its own slop, had it reviewed, and handed the PR's CI off to something that keeps watching it.

## Skills

| Skill | What it does |
|---|---|
| `or-mode` | A task router I turn on by hand. It picks one of ten playbooks (bug fix, feature, investigation, refactor, babysitting a PR and so on), copies its steps into the plan, and sends each step to the skill that handles it. |
| `finalize` | What a branch goes through before it becomes a PR: verify live, deslop, review, clean the diff, open the PR, hand off CI. |
| `review` | One review pass over a diff for bugs, regressions, repo conventions and missing verification. |
| `deslop` / `deslop-sweep` | Removes AI slop from a branch diff, or cleans up an existing area in small PRs that are safe to automerge. |
| `visual-pr` | Short PR descriptions, with a structural sketch when one helps. |
| `delegate` | Picks the model for a subagent (Codex or Claude) and dispatches it. |
| `codex-worker` / `t3-worker` | Runs Codex headless, or as a thread you can watch in my [T3 Code fork](https://github.com/vardior/t3code). |
| `diagnosing-bugs` | A loop for hard bugs and performance regressions. |
| `create-verification-skill` / `maintain-verification-skill` | Writes and maintains a `verify-<app>` skill for a repo, so "prove it works" has a scripted answer. |
| `create-formal-verification-skill` | Model-checks one risky promise and replays any counterexample through the real code. |
| `agent-ready`, `grilling`, `bro` | These run only when you ask for them. They reshape an area so agents can work in it, interview you until a plan is settled, or restate the last reply in plain words. |

[`mods/clean-claude`](mods/clean-claude) is a small Claude Code mod. It moves tools most sessions never call (Artifact, the built-in browser and a few others) behind ToolSearch, which keeps about 20k tokens of tool schemas out of every session that doesn't need them, and `/context-audit` shows what a session loads before you type.

## Install

Claude Code:

```
/plugin marketplace add vardior/orstack
/plugin install orstack@orstack
```

Add `/plugin install clean-claude@orstack` for the mod.

Codex:

```bash
codex plugin marketplace add vardior/orstack
codex plugin add orstack@orstack
```

Anything else (Cursor, OpenCode, Gemini and the rest):

```bash
npx skills add vardior/orstack
```

Call a skill by name: `/finalize` in Claude Code, `$finalize` in Codex. Plugin installs update themselves; with `npx skills`, run `npx skills update`.

Nothing here knows about a particular repo. CI recipes, verification skills and ticket conventions come from that repo's own `AGENTS.md` or from your global instructions.

## License

[MIT](LICENSE). Parts come from Cursor's pstack and cursor-team-kit, HumanLayer's visual-pr and Matt Pocock's skills, which are also MIT.
