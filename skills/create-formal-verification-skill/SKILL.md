---
name: create-formal-verification-skill
description: "Generate a project-local skill that formally verifies the code where a bug costs the most and tests reach the least, in any language, with whichever verification tool fits. Use only for /create-formal-verification-skill in Claude, $create-formal-verification-skill in Codex, or an explicit request to model-check a race, prove an invariant, or formally verify concurrency, retries, state machines, parsers, or unsafe code."
disable-model-invocation: true
---

# Create a formal verification skill

A test checks the cases that someone thought to write. Formal verification checks every case in a stated scope: every order of steps in a model, every input up to a bound, or every input. This skill finds the part of the repo where that matters most, verifies one property of it, and leaves a project-local skill that lets the next agent check a change against that property. Write that skill for an agent who reads it cold, mid-change, and has never seen your work. The user must be able to trust the result and act on it without learning the verification language.

## Choose the target from the code

Answer from the codebase, and ask the user only what you cannot observe. If the user named an area or a bug, start there.

A good target is a promise the code makes, where a break harms users and tests rarely reach the case that breaks it. Choose the strongest such target in the repo, not the one that is easiest to verify.

## Let the question choose the tool

Pick the tool that answers the question at the lowest cost: a model checker, a proof assistant, an SMT-backed verifier, or another tool. Whether events can happen in a bad order usually suits a model checker over a small model of the design, and TLA+ is the default for that in any language. Whether the code itself behaves for every input, as with memory safety, overflow, or a data-structure invariant, usually suits a verifier that runs on the code. If no verifier runs on this language, say so, and test the real code with generated inputs, not a hand model of the function. A property that must hold at every size, where a bound is not enough, can need a proof. Prefer a tool that the repo's developers can install and run, and tell the user why you chose it.

Name the evidence tier of every result, and never let one stand in for another:

- **Model check**: every order of steps in the model, within its bounds. It says nothing about code the model misdescribes.
- **Implementation replay**: the real code at one boundary, such as production storage methods against a disposable store, driven in a counterexample's order. It is not proof that the queue, scheduler, or deployment produces that order.
- **Property-based test**: the real code on generated inputs. It covers what was generated, not every input.
- **Whole-system proof**: every input at every size, for the code the proof covers. Claim it only when a proof checker accepted it.

## What makes it good

- **True to the code.** Every part of the model or proof points to code that a reviewer can open. What the verification treats as one indivisible step is one indivisible step in the code: each separate database write, message publication, and lock acquisition is its own step, even when the code issues them back to back. Name any model-only bookkeeping as model-only. When the code retries, give every write the attempt that issued it and check whether the real write is conditioned on that attempt; a write keyed only by entity ID can let an old attempt overwrite a new one. Names come from this repo.
- **Able to fail.** A check that you have never seen fail proves nothing. Show each property failing on a broken variant of the real code it guards, such as a removed check or a reordered step: change the implementation, rebuild it, and rerun both the model and the implementation replay against it. A runner that refuses because source hashes or strings changed detects drift, not the break. When a guard validates one document and writes another, mutate its synchronization separately from the validation and detect that mutant with a real overlap or rollback; a sequential replay alone can miss its removal.
- **Findings stay findings.** When the current code breaks the property, report it with the counterexample in the code's terms. Replay the counterexample through the real boundary before calling it an implementation finding, and investigate when model and replay disagree. Do not weaken the property or the model until it passes, and do not change product code unless the user asks.
- **Honest about scope.** Say what is verified, under which bounds and assumptions, at which evidence tier, and what is left out. A pass covers the model or the bound, not the whole system.
- **Readable without the tool.** State the property and the harm in one plain sentence each. Tell a counterexample as a short sequence of steps in the code's words.
- **Cheap to rerun.** One command, a reproducible tool version, and a run short enough that the next agent will use it on every relevant change. Write logs, counterexamples, and a machine-readable report to an evidence directory outside the checkout. A crash or a missing report is an incomplete run, never a verdict.
- **Kept in step with the code.** Record which files and functions each check covers, and the commit at which you last confirmed that the verification describes them. When the covered code changes after that commit, the next agent can see that the verification needs another look.
- **Leaves nothing behind.** The runner owns every disposable store, container, and scratch database it creates and removes them. A mutation run restores the exact original source in a `finally` path, rebuilds, reruns the baseline, and confirms the covered files match their recorded hashes. After an interrupted run, restore only the deliberate mutation and keep any other work in the tree.

## Generate the verify skill

Write a project-local skill with frontmatter that names the area and says when to use it. Without frontmatter, the skill never registers. Preserve an existing project skill convention; for a repo used by both Claude and Codex, make `.agents/skills/<name>/` canonical and add a relative `.claude/skills/<name>` symlink to it. From the skill alone, the next agent must be able to tell whether a change touches the verified code, run the check, tell a real bug from a modeling error, run the mutation check, and update the verification when a change is intended. Put the coverage record and the sync commit in the skill, and tell the next agent to move the sync commit forward only after it confirms that the verification describes the code at the new commit. Use this repo's real commands, paths, and nouns, and leave no placeholders.

## Prove it before you hand off

Validate a skill's schema and Claude/Codex invocation metadata with `python3 <this skill's directory>/scripts/validate-skill.py <skill-directory>`. It checks the original metadata and uses the managed Codex skill-creator validator for the remaining schema, normalizing only the checked Claude extension in temporary storage. It requires PyYAML and the validator under `${CODEX_HOME:-~/.codex}`; it does not prove runtime discovery or invocation behavior.

Follow the generated skill once, as the next agent would, on a scratch change that breaks the property in the real code. It must catch the break. Then drop the scratch change and confirm that the check is back where it started: passing, or failing only on the findings you will report, with its disposable resources gone and the covered source byte-identical. A verify skill that was never run is a draft. If the skill misses the break or a step does not run, fix the skill or the verification, not the scratch change.

## Hand off

Tell the user what you verified, which tool you used and why, the bounds, the evidence tier, what the check found in plain words, how to run it, and what it does not cover. Suggest a second target only if you found a close one. For upkeep, the generated skill's own correspondence and mutation steps are the procedure.

Record every finding where your global instructions say findings live, or else in the target repository's own docs, with the fields of [the example record](references/findings/example-retry-isolation.md), detailed enough to survive deletion of the evidence directory. Change orstack only through a worktree, as its `AGENTS.md` describes. Leave fix state as the owner reports it; do not mark a finding fixed until the fix has merged and the check passes against it.
