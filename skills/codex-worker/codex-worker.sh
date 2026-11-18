#!/usr/bin/env bash
# Run one persistent, unrestricted Codex task while inheriting normal Codex configuration.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  codex-worker [options] <prompt>
  codex-worker [options] resume <session-id> <prompt>
  printf '%s' '<prompt>' | codex-worker [options]

Options:
  -C, --cd <dir>       Working directory (default: current directory)
      --model <model>  Override configured model
      --effort <value> Override configured reasoning effort
      --fast           Use the priority (fast) service tier for this run
      --allow-non-git  Allow execution outside a Git repository
  -h, --help           Show this help
EOF
}

die() {
  printf 'codex-worker: %s\n' "$*" >&2
  exit 2
}

take_value() {
  local flag="$1"
  [[ $# -ge 2 && -n "$2" ]] || die "$flag requires a value"
  REPLY="$2"
}

cd_dir="$PWD"
model=""
effort=""
fast=0
allow_non_git=0
mode="exec"
resume_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --model)
      take_value "$1" "${2:-}"
      model="$REPLY"
      shift 2
      ;;
    --model=*) model="${1#*=}"; [[ -n "$model" ]] || die "--model requires a value"; shift ;;
    --effort)
      take_value "$1" "${2:-}"
      effort="$REPLY"
      shift 2
      ;;
    --effort=*) effort="${1#*=}"; [[ -n "$effort" ]] || die "--effort requires a value"; shift ;;
    --cd|-C)
      take_value "$1" "${2:-}"
      cd_dir="$REPLY"
      shift 2
      ;;
    --cd=*) cd_dir="${1#*=}"; [[ -n "$cd_dir" ]] || die "--cd requires a value"; shift ;;
    --fast) fast=1; shift ;;
    --allow-non-git) allow_non_git=1; shift ;;
    resume)
      [[ "$mode" == "exec" ]] || die "resume may be specified only once"
      mode="resume"
      shift
      [[ $# -gt 0 && "$1" != -* ]] || die "resume requires a session id"
      resume_id="$1"
      shift
      ;;
    --) shift; break ;;
    -*) die "unknown option: $1" ;;
    *) break ;;
  esac
done

session_accounts="${XDG_STATE_HOME:-$HOME/.local/state}/codex-worker/session-accounts.tsv"
if [[ -z "${CODEX_WORKER_BIN:-}" ]]; then
  if [[ "$mode" == "resume" ]]; then
    CODEX_WORKER_BIN="$(awk -F'\t' -v id="$resume_id" '$1 == id { bin = $2 } END { print bin }' "$session_accounts" 2>/dev/null || true)"
  fi
  if [[ -z "${CODEX_WORKER_BIN:-}" ]]; then
    account="$("$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/codex-account")"
    [[ "$account" == codex_personal ]] && CODEX_WORKER_BIN=codex-personal || CODEX_WORKER_BIN=codex
  fi
  printf 'codex-worker: account %s\n' "$CODEX_WORKER_BIN" >&2
fi
codex_bin="$CODEX_WORKER_BIN"
command -v "$codex_bin" >/dev/null 2>&1 || codex_bin="$HOME/.local/bin/${codex_bin##*/}"
[[ -x "$codex_bin" || -n "$(command -v "$codex_bin" 2>/dev/null)" ]] || die "codex binary not found: $CODEX_WORKER_BIN"

[[ -d "$cd_dir" ]] || die "working directory does not exist: $cd_dir"
cd_dir="$(cd "$cd_dir" && pwd -P)"

prompt_args=()
if [[ $# -gt 0 ]]; then
  prompt_args=("$*")
  # Prevent an inherited, open stdin pipe from being appended to an argument prompt.
  exec 0</dev/null
else
  [[ ! -t 0 ]] || die "a prompt argument or piped stdin is required"
  prompt_args=(-)
fi

last_msg="$(mktemp -t codex-worker.XXXXXX)"
events="$(mktemp -t codex-worker-events.XXXXXX)"
trap 'rm -f "$last_msg" "$events"' EXIT

args=(exec -C "$cd_dir" --dangerously-bypass-approvals-and-sandbox --json -o "$last_msg")
[[ "$allow_non_git" -eq 1 ]] && args+=(--skip-git-repo-check)
[[ -n "$model" ]] && args+=(--model "$model")
[[ -n "$effort" ]] && args+=(-c "model_reasoning_effort=$effort")
[[ "$fast" -eq 1 ]] && args+=(-c "service_tier=priority")

if [[ "$mode" == "resume" ]]; then
  args+=(resume "$resume_id")
fi
args+=("${prompt_args[@]}")

# Keep Codex's event stream visible on stderr while retaining it for session-id extraction.
set +e
"$codex_bin" "${args[@]}" 2>&1 | tee "$events" >&2
rc="${PIPESTATUS[0]}"
set -e

cat "$last_msg"
sid="$(sed -n 's/.*"type":"thread.started".*"thread_id":"\([^"]*\)".*/\1/p' "$events" | head -1)"
if [[ -n "$sid" ]]; then
  mkdir -p "$(dirname "$session_accounts")"
  printf '%s\t%s\n' "$sid" "$CODEX_WORKER_BIN" >> "$session_accounts"
  printf '\n\ncodex session: %s\n' "$sid"
fi
exit "$rc"
