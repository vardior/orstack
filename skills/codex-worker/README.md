# Codex account split

I split Codex work between two accounts. Each new Codex thread picks its account at random, weighted
by the ratio in `codex-account`. Agents run that roll and use whatever it prints.

## Accounts

| Account | T3 provider instance | CLI binary | Codex home |
|---|---|---|---|
| Personal | `codex_personal` | `~/.local/bin/codex-personal` | `~/.codex-personal` (its own `auth.json`; config, sessions and history are symlinked to `~/.codex`) |
| Work | `codex` | `~/.local/bin/codex` | `~/.codex` |

Since both share the sessions directory, a session can resume from either account.

## Where the roll happens

- `codex-account` in this directory is the roll. It prints `codex_personal` with probability
  `personal_share_percent` and `codex` otherwise. The ratio lives only there.
- `codex-worker.sh` rolls for each new session unless `CODEX_WORKER_BIN` pins a binary, and prints
  the binary it chose on stderr (`codex-worker: account <binary>`). After every run it appends
  `<session id>\t<binary>` to `~/.local/state/codex-worker/session-accounts.tsv`, and a resume reuses
  that session's last binary instead of rolling again. The prompt cache is per account, so a resume on
  the other account re-reads the whole history uncached (measured 2026-10-14: about 48% cached after
  a switch, against about 99% on the same account). A resume of a session with no entry rolls.
- Bot T3 spawns (`delegate_task`, `t3_thread_launch`): `~/.local/share/orstack/bots/procedures/workers.md`
  tells bots to run `codex-account` before each new Codex worker and use the instance it prints.

## Adjust

Edit `personal_share_percent` in `codex-account`. `100` sends everything to personal and `0` sends
everything to work. To check the split:

    for i in $(seq 400); do <this skill's directory>/codex-account; done | sort | uniq -c

## Remove

1. Delete the `CODEX_WORKER_BIN` roll block and the `session_accounts` lines in `codex-worker.sh`,
   and restore `codex_bin="${CODEX_WORKER_BIN:-codex-personal}"`, or whichever account you want as
   the default. Delete `~/.local/state/codex-worker/`.
2. Delete the `codex-account` line in the bots' `procedures/workers.md` and give the charters a fixed
   `instanceId`.
3. Delete `codex-account`.
