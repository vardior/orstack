# Delegate brief template

Copy verbatim and fill every field. A dispatch missing any header is malformed.

```
GOAL         one sentence, the outcome, executable by a stranger with no chat access
SCOPE        pr-owner owner id `lead:<lead session id>` for a lead-dispatched PR; paths it may write,
             including the evidence bundle directory; paths it may not; its
             worktree or branch; its parent commit, and when another in-flight task writes the
             same file, class, contract or workflow, which task integrates second (stacked on the
             first's head, or dispatched after it merges), decided before this one starts;
             list every file the task forces outside its obvious area (a migration's registration,
             a snapshot file), since a missing one is a stop; say that the write list bounds
             the committed diff, and that untracked or git-ignored files a verify recipe generates
             are allowed
CONTEXT      pointers to files and PRs; paste upstream reports in full — workers cannot see siblings
DATA SHAPE   the named shape and its organizing structure, chosen before the delegate writes logic
ACCEPTANCE   checkable criteria, one per line; a lint or audit gate reads "no new findings against
             base" unless you have seen it pass on base
VERIFY       exact commands you have run in this repo this session (not reconstructed from docs
             or a reader's report — repo docs are wrong often enough), or the verify-<app> skill
             invocation, plus known gotchas; point to an existing fixture or benchmark harness
             before creating another, extending only the missing cases; a build or test runs in
             one blocking call (in Codex, `wait` with `yield_time_ms: 1000000`; 60000 is not the
             cap), never re-polled at short yields, since every poll re-sends the whole context;
             each long job states its expected duration and is watched by `wait-log`
             (codex-exec.md), which reports a stall at twice that instead of waiting on a hang;
             an integration test class runs with `--no-build` once red and once green per change,
             after one build, while unit tests carry the iteration; name those classes: a
             filter that matches a whole area is not a class and runs at most once, as the last
             step before the push, and after a red run only the failed tests rerun (CI is the
             full-suite proof); a worker that stops to ask keeps its stack, database and fixtures
             up and continues with whatever the answer does not change
FORBIDDEN    no rebase, no force-push, no fixes outside scope, plus task-specific bans; must not
             contradict ACCEPTANCE or VERIFY — carve out the live acceptance run and never require
             a check whose pass condition needs a forbidden write
REPORT       `handed-off: pr-owner <repo>#<pr>` when handing off a PR; status, branch, head SHA,
             verdict, what was actually run, evidence bundle path
             (when anything was verified), deviations, follow-ups, and whether your context
             compacted during the task (and at which step), and Harness lines in the format of
             the final report in or-mode's SKILL.md (`none` if nothing). At most about 40 lines:
             point at files instead of pasting them
```
