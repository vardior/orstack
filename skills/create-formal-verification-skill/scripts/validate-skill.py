#!/usr/bin/env python3

import argparse
import os
import re
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml


def validate_skill(skill: Path) -> tuple[bool, str]:
    content = (skill / "SKILL.md").read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid or missing YAML frontmatter"
    frontmatter = yaml.safe_load(match.group(1))
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    disabled = frontmatter.get("disable-model-invocation", False)
    if type(disabled) is not bool:
        return False, "disable-model-invocation must be a boolean"

    metadata_path = skill / "agents" / "openai.yaml"
    metadata = yaml.safe_load(metadata_path.read_text()) if metadata_path.exists() else {}
    if not isinstance(metadata, dict):
        return False, "agents/openai.yaml must be a YAML dictionary"
    policy = metadata.get("policy", {})
    if not isinstance(policy, dict):
        return False, "agents/openai.yaml policy must be a YAML dictionary"
    implicit = policy.get("allow_implicit_invocation", True)
    if type(implicit) is not bool:
        return False, "policy.allow_implicit_invocation must be a boolean"
    if disabled == implicit:
        return False, "Invocation policies disagree: disable-model-invocation must equal the inverse of policy.allow_implicit_invocation (defaults: false and true)"

    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    validator = codex_home / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
    validate = runpy.run_path(str(validator))["validate_skill"]
    if "disable-model-invocation" not in frontmatter:
        return validate(skill)
    del frontmatter["disable-model-invocation"]
    with TemporaryDirectory(prefix="orstack-skill-schema-") as scratch:
        normalized = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---" + content[match.end():]
        (Path(scratch) / "SKILL.md").write_text(normalized)
        return validate(Path(scratch))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a skill's schema and matching Claude/Codex invocation policies")
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    try:
        valid, message = validate_skill(args.skill_directory)
    except (OSError, yaml.YAMLError) as error:
        valid, message = False, str(error)
    print(f"{args.skill_directory}: {'valid schema and invocation metadata' if valid else message}")
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
