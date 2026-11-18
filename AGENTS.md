# orstack

Agent skills, shipped three ways from this one tree: as a Claude Code plugin and a Codex plugin, both defined inline in `.claude-plugin/marketplace.json`, and through `npx skills`, which copies `skills/<name>/` folders. A new skill is a new folder; nothing else needs wiring. Don't add a root `.claude-plugin/plugin.json`: with one there, Codex treats the repo as a plugin and stops loading `.agents/skills/`.

`.agents/skills/` holds skills for working on this repo itself (linked under `.claude/skills/` for Claude Code). They set `metadata: internal: true` so `npx skills` doesn't install them.

## A skill folder

- `SKILL.md`: `name` and `description` frontmatter, then the instructions. Every agent reads this file. Quote the description if it contains `: `, or strict YAML parsers drop the skill.
- `agents/openai.yaml`: what Codex shows (`display_name`, `short_description`, `default_prompt`) and `policy.allow_implicit_invocation`.
- A skill that runs only when asked sets `disable-model-invocation: true` in `SKILL.md` and `allow_implicit_invocation: false` in `openai.yaml`. Keep the two in step.
- `references/`, `scripts/`: refer to them relative to the skill's own directory. Installs live in versioned cache paths, so never use `~/` or repo-root paths.

## Checks

- `python3 skills/finalize/scripts/pr-owner.py self-test`
- `claude plugin test mods/clean-claude` and `claude plugin validate .`

## Rules

- Keep it generic. Anything that belongs to one workplace (repos, CI recipes, tickets, infrastructure) goes in that repo's `AGENTS.md` or the user's global instructions, which the skills already defer to.
- Anything taken from another project goes through `/maintain-upstream`, which holds the pins, pristine copies, derivation map and review log. A skill derived from another project carries that project's license as its own `LICENSE.txt`.
