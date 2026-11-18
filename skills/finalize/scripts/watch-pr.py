import argparse
import json
import math
import subprocess
import sys
import time

GREEN = {'success', 'neutral', 'skipped'}


def seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be a finite positive number')
    return number


def gh(endpoint, jq, deadline, paginate=False):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    command = ['gh', 'api', endpoint, '--jq', jq]
    if paginate:
        command.append('--paginate')
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          timeout=min(120, remaining)).stdout.strip()


def checks(repo, head, deadline):
    prefix = f'repos/{repo}/commits/{head}'
    runs = gh(prefix + '/check-runs?per_page=100&filter=latest',
              '.check_runs[] | [.id, .app.id, .name, .status, .conclusion, .details_url] | @json',
              deadline, paginate=True)
    statuses = gh(prefix + '/statuses?per_page=100',
                  '.[] | [.id, .context, .state, .target_url] | @json', deadline, paginate=True)
    latest = {}
    for line in runs.splitlines():
        identity, app, name, status, conclusion, url = json.loads(line)
        key = ('check', app, name)
        value = (identity, name, status == 'completed', conclusion in GREEN, url)
        if key not in latest or identity > latest[key][0]:
            latest[key] = value
    for line in statuses.splitlines():
        identity, name, state, url = json.loads(line)
        key = ('status', name)
        value = (identity, name, state in {'success', 'failure', 'error'}, state == 'success', url)
        if key not in latest or identity > latest[key][0]:
            latest[key] = value
    return tuple(sorted(latest.values()))


def main():
    parser = argparse.ArgumentParser(description='Wait for a PR head and its checks to settle. '
                                     'Exit codes: 0 green, 1 failed, 3 head moved, 4 timeout.')
    parser.add_argument('pr', type=int)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--timeout-minutes', type=seconds, default=90)
    parser.add_argument('--settle-seconds', type=seconds, default=60)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout_minutes * 60
    previous = None
    terminal_since = None
    interval = 5
    error = ''
    current = ()
    while time.monotonic() < deadline:
        try:
            endpoint = f'repos/{args.repo}/pulls/{args.pr}'
            head = gh(endpoint, '.head.sha', deadline)
            if head != args.head:
                print(f'HEAD MOVED {args.repo}#{args.pr}: expected {args.head}, current {head}')
                return 3
            current = checks(args.repo, args.head, deadline)
            head = gh(endpoint, '.head.sha', deadline)
            if head != args.head:
                print(f'HEAD MOVED {args.repo}#{args.pr}: expected {args.head}, current {head}')
                return 3
            now = time.monotonic()
            changed = current != previous
            terminal = bool(current) and all(check[2] for check in current)
            if changed or not terminal or terminal_since is None:
                terminal_since = now if terminal else None
            if terminal_since is not None and now - terminal_since >= args.settle_seconds:
                failed = [check for check in current if not check[3]]
                outcome = 'RED' if failed else 'GREEN'
                print(f'{outcome} {args.repo}#{args.pr} head {args.head}: {len(current)} checks settled')
                for _, name, _, _, url in failed:
                    print(f'  {name}: {url or "(no URL)"}')
                return 1 if failed else 0
            previous = current
            error = ''
            interval = 5 if changed else min(30, interval * 1.5)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, TimeoutError) as failure:
            terminal_since = None
            error = (failure.stderr or '').strip() if isinstance(failure, subprocess.CalledProcessError) else str(failure)
            interval = min(30, interval * 1.5)
        delay = interval
        if terminal_since is not None:
            delay = min(delay, max(0, terminal_since + args.settle_seconds - time.monotonic()))
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
    print(f'TIMEOUT {args.repo}#{args.pr} head {args.head}: checks did not settle; {len(current)} last observed')
    if error:
        print(f'  Last API error: {error}')
    for _, name, terminal, green, url in current:
        if terminal and not green:
            print(f'  {name}: {url or "(no URL)"}')
    return 4


if __name__ == '__main__':
    sys.exit(main())
