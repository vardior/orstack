import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.local/state/orstack/pr-owner'
BOTS = Path.home() / '.local/share/orstack/bots'
WAKE = Path.home() / '.claude/wake'
CONFIG_PATH = Path.home() / '.config/orstack/pr-owner.json'
CONFIG = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
CLAUDE_REVIEW_REPOS = set(CONFIG.get('claudeReviewRepos', []))
RED_TRIAGE = CONFIG.get('redTriage', {})
SCHEDULE_LABEL = 'com.orstack.pr-owner'
SCHEDULE_PLIST = Path.home() / 'Library/LaunchAgents' / f'{SCHEDULE_LABEL}.plist'


def sibling(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


watch = sibling('watch-pr')
review = sibling('claude-review-round')


class OwnerError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def stamp(now):
    return dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def epoch(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command(arguments, timeout=120):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OwnerError(f'{Path(arguments[0]).name}: {type(error).__name__}') from None
    if result.returncode:
        raise OwnerError(f'{Path(arguments[0]).name} exited {result.returncode}')
    return result.stdout


def clean_approval(body):
    body = body.replace('**', '')
    return bool(re.match(r'\s*✅', body)) and not any(
        re.match(r'\s*[-*]?\s*🟠', line) and not re.match(r'\s*[-*]?\s*🟠\s*Minor\b', line)
        for line in body.splitlines())


class GitHub:
    def api(self, path):
        return json.loads(command(['gh', 'api', path]))

    def pages(self, path, key=None):
        pages = json.loads(command(['gh', 'api', '--paginate', '--slurp', path]))
        return [item for page in pages for item in (page[key] if key else page)]

    def pull(self, repo, pr):
        return self.api(f'repos/{repo}/pulls/{pr}')

    def gates(self, repo, base):
        try:
            body = self.api(f'repos/{repo}/branches/{quote(base, safe="")}/protection/required_status_checks')
        except OwnerError:
            return None
        checks = body.get('checks') or []
        return checks + [{'context': name, 'app_id': None} for name in body.get('contexts', [])
                         if name not in {check['context'] for check in checks}]

    def head_time(self, repo, head):
        return epoch(self.api(f'repos/{repo}/commits/{head}')['commit']['committer']['date'])

    def checks(self, repo, head):
        def query(path, jq, deadline, paginate=False):
            output = command(['gh', 'api', path, '--jq', jq] + (['--paginate'] if paginate else []))
            rows = [json.loads(line) for line in output.splitlines()]
            if '/check-runs?' in path:
                self.check_contexts = {(row[2], row[1]) for row in rows}
            else:
                self.status_contexts = {row[1] for row in rows}
            return output
        watch.gh = query
        return [list(check) for check in watch.checks(repo, head, time.monotonic() + 240)]

    def required_present(self, repo, head, gates):
        if not gates:
            return True
        return all(any(name == gate['context'] and
                       (gate.get('app_id') in (None, -1) or app == gate['app_id'])
                       for name, app in self.check_contexts)
                   or (gate.get('app_id') in (None, -1) and gate['context'] in self.status_contexts)
                   for gate in gates)

    def graphql(self, query, **variables):
        arguments = ['gh', 'api', 'graphql', '-f', 'query=' + query]
        for key, value in variables.items():
            if value is not None:
                arguments += ['-F', f'{key}={value}']
        result = json.loads(command(arguments))
        if result.get('errors'):
            raise OwnerError('review threads GraphQL query failed')
        return result['data']

    def thread_findings(self, repo, pr):
        owner, name = repo.split('/')
        cursor = None
        findings = []
        while True:
            data = self.graphql('''query($owner:String!,$name:String!,$pr:Int!,$cursor:String) {
                repository(owner:$owner,name:$name) { pullRequest(number:$pr) {
                    reviewThreads(first:100,after:$cursor) {
                        pageInfo { hasNextPage endCursor }
                        nodes { id isResolved isOutdated comments(first:100) {
                            pageInfo { hasNextPage endCursor }
                            nodes { author { login } body url }
                        } }
                    }
                } }
            }''', owner=owner, name=name, pr=pr, cursor=cursor)
            threads = data['repository']['pullRequest']['reviewThreads']
            for thread in threads['nodes']:
                if thread['isResolved'] or thread['isOutdated']:
                    continue
                comments = thread['comments']
                first, *replies = comments['nodes']
                author = (first['author'] or {}).get('login')
                if repo in CLAUDE_REVIEW_REPOS and author in review.CLAUDE_LOGINS:
                    continue
                while comments['pageInfo']['hasNextPage']:
                    data = self.graphql('''query($id:ID!,$cursor:String) {
                        node(id:$id) { ... on PullRequestReviewThread {
                            comments(first:100,after:$cursor) {
                                pageInfo { hasNextPage endCursor }
                                nodes { author { login } }
                            }
                        } }
                    }''', id=thread['id'], cursor=comments['pageInfo']['endCursor'])
                    comments = data['node']['comments']
                    replies.extend(comments['nodes'])
                if not any((reply['author'] or {}).get('login') != author for reply in replies):
                    findings.append(dict(kind='thread', id=thread['id'], author=author,
                                         title=review.first_line(first['body']), url=first['url']))
            if not threads['pageInfo']['hasNextPage']:
                return findings
            cursor = threads['pageInfo']['endCursor']

    def review(self, repo, pr, head):
        threads = self.thread_findings(repo, pr)
        if repo not in CLAUDE_REVIEW_REPOS:
            return None, threads
        runs = self.pages(f'repos/{repo}/actions/runs?head_sha={head}&per_page=100', 'workflow_runs')
        runs = [run for run in runs if run['name'] == 'Claude PR Review' and run['head_sha'] == head]
        if not runs:
            return None, threads
        latest = max(runs, key=lambda run: (run['created_at'], run['id'], run.get('run_attempt', 1)))
        result = {'id': latest['id'], 'status': latest['status'], 'conclusion': latest['conclusion'],
                  'url': latest['html_url'], 'createdAt': latest['created_at'], 'updatedAt': latest['updated_at']}
        if result['status'] != 'completed':
            return result, threads
        comments = {}
        def pages(path):
            values = self.pages(path)
            comments.update({comment['id']: comment for comment in values})
            return values
        review.gh_paginated = pages
        inline = review.inline_findings(repo, pr, head)
        conversation = review.conversation_findings(repo, pr, result)
        findings = [finding for finding in inline if not finding['answered']] + [finding for finding in conversation
                             if not clean_approval(comments[finding['id']]['body'])]
        return result, findings + threads

    def rate(self):
        return self.api('rate_limit')['resources']['core']

    def diagnostic(self, kind, record):
        if kind == 'RED' and record['repo'] in RED_TRIAGE:
            arguments = [sys.executable, '-I', str(Path(RED_TRIAGE[record['repo']]).expanduser()), str(record['pr']), '--sha', record['head']]
        elif kind == 'CONFLICT' and (BOTS / 'bin/base-drift').exists():
            arguments = [str(BOTS / 'bin/base-drift'), record['repo'], str(record['pr'])]
        else:
            return None
        try:
            result = subprocess.run(arguments, capture_output=True, text=True, timeout=300)
            return f'exit {result.returncode}: {result.stdout.strip()}'
        except (OSError, subprocess.TimeoutExpired) as error:
            return f'diagnostic unavailable: {type(error).__name__}'


class Store:
    def __init__(self, root=STATE, bots=BOTS, github=None, clock=time.time, sleep=time.sleep, wake=WAKE):
        self.root = Path(root)
        self.bots = Path(bots)
        self.wake = Path(wake)
        self.github = github or GitHub()
        self.clock = clock
        self.sleep = sleep

    def pull_showing(self, repo, pr, head, attempts=10):
        pull = self.github.pull(repo, pr)
        for _ in range(attempts):
            if pull['head']['sha'] == head or pull['state'] != 'open':
                break
            self.sleep(3)
            pull = self.github.pull(repo, pr)
        return pull

    @contextlib.contextmanager
    def locked(self, deadline=None):
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / 'lock').open('a') as stream:
            while True:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TimeoutError from None
                    time.sleep(0.1)
            yield

    def directory(self, repo, pr):
        return self.root / 'records' / digest(f'{repo}#{pr}')

    def records(self):
        return [json.loads(path.read_text()) for path in sorted((self.root / 'records').glob('*/record.json'))]

    def load(self, repo, pr):
        path = self.directory(repo, pr) / 'record.json'
        if not path.exists():
            return None
        record = json.loads(path.read_text())
        record.setdefault('review_since', None)
        return record

    def save(self, record):
        atomic(self.directory(record['repo'], record['pr']) / 'record.json', json.dumps(record, indent=2) + '\n')

    def events(self, record):
        path = self.directory(record['repo'], record['pr']) / 'events.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def save_events(self, record, events):
        atomic(self.directory(record['repo'], record['pr']) / 'events.jsonl',
               ''.join(json.dumps(event, sort_keys=True) + '\n' for event in events))

    def event_id(self, record, kind):
        key = f'{record["repo"]}#{record["pr"]}:{record["head"]}:{kind}'
        if record.get('review_since') is not None and kind in {'FINDINGS', 'NOT_REVIEWED', 'READY', 'RED'}:
            key += f':round:{record["round"]}'
        return digest(key)

    def emit(self, record, kind, **details):
        events = self.events(record)
        identity = self.event_id(record, kind)
        matching = next((i for i, event in enumerate(events) if event['id'] == identity), None)
        if matching is not None and not events[matching].get('superseded'):
            return
        event = dict(id=identity, kind=kind, repo=record['repo'], pr=record['pr'], head=record['head'],
                     owner=record['owner'], at=self.clock(), acked=False, delivered=False,
                     context={key: record.get(key) for key in ('worktree', 'branch', 'brief', 'evidence', 'resume', 'round')},
                     details=details)
        if matching is None:
            events.append(event)
        else:
            events[matching] = event
        self.save_events(record, events)
        print(json.dumps(event), flush=True)

    def invalidate(self, record, reason, preserve=None, kinds=None):
        events = self.events(record)
        for event in events:
            if not event['acked'] and event['kind'] != preserve and (kinds is None or event['kind'] in kinds):
                event['superseded'] = reason
        self.save_events(record, events)

    def register(self, args):
        with self.locked():
            old = self.load(args.repo, args.pr)
            if old and not old.get('released'):
                if old['owner'] != args.owner and not args.takeover:
                    raise OwnerError(f'{args.repo}#{args.pr} is owned by {old["owner"]}; use --takeover', 2)
                if old['head'] != args.head:
                    raise OwnerError('head changed; use rearm to preserve the two-rearm budget')
                if old['owner'] == args.owner:
                    return old
                old['owner'] = args.owner
                for key in ('worktree', 'branch', 'brief', 'evidence', 'resume'):
                    if getattr(args, key) is not None:
                        old[key] = getattr(args, key)
                self.save(old)
                events = self.events(old)
                for event in events:
                    if not event['acked'] and not event.get('superseded'):
                        event['owner'] = args.owner
                        event['delivered'] = False
                self.save_events(old, events)
                return old
            spent, budget = (old['round'], old['rearm_budget']) if old else (0, 2)
            if spent >= budget:
                if not args.or_approved:
                    raise OwnerError(f'{args.repo}#{args.pr} spent its rearm budget; report the shared root cause to Or, '
                                     'then register with --or-approved "<his words>"')
                budget = spent + 2
            pull = self.pull_showing(args.repo, args.pr, args.head)
            if pull['head']['sha'] != args.head:
                raise OwnerError(f'expected head {args.head}, current {pull["head"]["sha"]}')
            if pull['state'] != 'open':
                raise OwnerError('register requires an open PR')
            now = self.clock()
            record = dict(repo=args.repo, pr=args.pr, head=args.head, owner=args.owner, base=pull['base']['ref'],
                          gates=self.github.gates(args.repo, pull['base']['ref']), registered_at=now,
                          head_since=min(now, self.github.head_time(args.repo, args.head)), round=spent, rearm_budget=budget,
                          review_deadline=args.review_deadline, head_timeout=args.head_timeout, done_when=args.done_when,
                          active=True, released=False, last_poll=None, next_poll=0, interval=120, errors=0,
                          snapshot=None, settled_since=None, verdict=None)
            record.update({key: getattr(args, key) for key in ('worktree', 'branch', 'brief', 'evidence', 'resume')})
            record['or_approvals'] = (old or {}).get('or_approvals', []) + ([args.or_approved] if args.or_approved else [])
            if old:
                self.invalidate(old, 'released registration replaced')
            self.save(record)
            return record

    def rearm(self, args):
        with self.locked():
            record = self.load(args.repo, args.pr)
            if not record or record.get('released') or not record['active']:
                raise OwnerError('no active registration')
            if record['round'] >= record['rearm_budget']:
                raise OwnerError('two-rearm budget exhausted; release, report the shared root cause to Or, and register with --or-approved')
            pull = self.pull_showing(args.repo, args.pr, args.head)
            if pull['head']['sha'] != args.head or pull['state'] != 'open':
                raise OwnerError('rearm requires the current head of an open PR')
            gates = self.github.gates(args.repo, pull['base']['ref'])
            same_head = args.head == record['head']
            head_since = record['head_since'] if same_head else min(self.clock(), self.github.head_time(args.repo, args.head))
            self.invalidate(record, 'new review round' if same_head else 'new head',
                            kinds={'FINDINGS', 'NOT_REVIEWED', 'READY', 'RED'} if same_head else None)
            record.update(head=args.head, round=record['round'] + 1, base=pull['base']['ref'], gates=gates,
                          head_since=head_since, review_since=self.clock() if same_head else None,
                          next_poll=0, interval=120, errors=0, last_poll=None,
                          snapshot=None, settled_since=None, verdict=None)
            self.save(record)
            return record

    def tick(self, record):
        repo, pr, head = record['repo'], record['pr'], record['head']
        pull = self.github.pull(repo, pr)
        if pull['state'] == 'closed':
            kind = 'MERGED' if pull.get('merged') else 'CLOSED'
            self.invalidate(record, 'PR closed', preserve=kind)
            self.emit(record, kind, url=pull['html_url'])
            record.update(active=False, verdict=kind)
            return
        if pull['head']['sha'] != head:
            self.invalidate(record, 'head moved', preserve='HEAD_MOVED')
            self.emit(record, 'HEAD_MOVED', current=pull['head']['sha'])
            observed = pull['head']['sha']
            interval = 120 if observed != record.get('observed_head') else min(300, record['interval'] * 1.5)
            record.update(verdict='HEAD_MOVED', observed_head=observed, interval=interval, snapshot=None, settled_since=None)
            return
        if pull['base']['ref'] != record['base']:
            record.update(base=pull['base']['ref'], gates=self.github.gates(repo, pull['base']['ref']),
                          snapshot=None, settled_since=None)
        checks = self.github.checks(repo, head)
        present = self.github.required_present(repo, head, record['gates'])
        run, findings = self.github.review(repo, pr, head)
        after = self.github.pull(repo, pr)
        if after['head']['sha'] != head or after['state'] != 'open' or after['base']['ref'] != record['base']:
            self.withdraw_ready(record)
            record.update(snapshot=None, settled_since=None, verdict=None)
            if after['head']['sha'] != head:
                self.invalidate(record, 'head moved during poll', preserve='HEAD_MOVED')
                self.emit(record, 'HEAD_MOVED', current=after['head']['sha'])
                record['verdict'] = 'HEAD_MOVED'
            return
        now = self.clock()
        merge_state = (after.get('mergeable_state') or 'unknown').upper()
        snapshot = dict(checks=checks, present=present, review=run, findings=findings,
                        merge_state=merge_state, mergeable=after.get('mergeable'), draft=after.get('draft', False))
        previous = record['snapshot'] or {}
        changed = any(snapshot[key] != previous.get(key) for key in ('checks', 'present', 'review', 'findings'))
        terminal = bool(checks) and all(check[2] for check in checks)
        if changed or not terminal or record['settled_since'] is None:
            record['settled_since'] = now if terminal else None
        record.update(snapshot=snapshot, interval=120 if changed else min(300, record['interval'] * 1.5), verdict=None)
        review_since = record.get('review_since') if record.get('review_since') is not None else record['head_since']
        if repo in CLAUDE_REVIEW_REPOS and run is None and now - review_since >= record['review_deadline']:
            self.emit(record, 'NOT_REVIEWED', deadline=stamp(review_since + record['review_deadline']))
        if merge_state in {'BEHIND', 'DIRTY'}:
            self.emit_diagnosed(record, 'CONFLICT', merge_state=merge_state)
        if findings:
            self.emit(record, 'FINDINGS', review=run, findings=findings)
        settled = record['settled_since'] is not None and now - record['settled_since'] >= 60
        if not settled:
            self.withdraw_ready(record)
            self.emit_timeout(record, now)
            return
        failed = [{'name': check[1], 'url': check[4]} for check in checks if not check[3]]
        review_failed = run and run['status'] == 'completed' and run['conclusion'] != 'success'
        if failed or review_failed:
            self.withdraw_ready(record)
            self.emit_diagnosed(record, 'RED', failures=failed, review=run)
            record['verdict'] = 'RED'
        elif present and not findings and (repo not in CLAUDE_REVIEW_REPOS or (run and run['status'] == 'completed')) \
                and after.get('mergeable') is True and merge_state in {'CLEAN', 'HAS_HOOKS', 'UNSTABLE'} \
                and not after.get('draft', False):
            if record['done_when'] == 'merge-ready':
                self.emit(record, 'READY', checks=len(checks), gates=record['gates'], review=run,
                          done_when=record['done_when'])
            record['verdict'] = 'READY'
        else:
            self.withdraw_ready(record)
        self.emit_timeout(record, now)

    def emit_timeout(self, record, now):
        if record['verdict'] != 'READY' and now - record['head_since'] >= record['head_timeout']:
            self.emit(record, 'TIMEOUT', seconds=record['head_timeout'])

    def withdraw_ready(self, record):
        events = self.events(record)
        changed = False
        for event in events:
            if event['head'] == record['head'] and event['kind'] == 'READY' and not event['acked'] and not event.get('superseded'):
                event['superseded'] = 'readiness changed'
                changed = True
        if changed:
            self.save_events(record, events)

    def emit_diagnosed(self, record, kind, **details):
        if any(event['id'] == self.event_id(record, kind) and not event.get('superseded')
               for event in self.events(record)):
            return
        details['diagnostic'] = self.github.diagnostic(kind, record)
        self.emit(record, kind, **details)

    def heartbeat(self, owner):
        return self.root / 'waiters' / (digest(owner) + '.json')

    def waiter_alive(self, owner):
        path = self.heartbeat(owner)
        if not path.exists():
            return False
        heartbeat = json.loads(path.read_text())
        try:
            os.kill(heartbeat['pid'], 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def deliver(self, record):
        events = self.events(record)
        now = self.clock()
        changed = False
        for event in events:
            if not event['acked'] and not event.get('superseded') and event['owner'] != record['owner']:
                event.update(owner=record['owner'], delivered=False, mailed=None)
                changed = True
            if event['acked'] or event['delivered'] or event.get('superseded'):
                if event.get('mailed') and (event['acked'] or event.get('superseded')):
                    self.unmail(event)
                    event['mailed'] = None
                    changed = True
                continue
            owner = event['owner']
            filename = f'{stamp(event["at"]).replace("-", "").replace(":", "")}-pr-owner-{event["id"]}.md'
            if owner.startswith('lead:'):
                if self.waiter_alive(owner):
                    continue
                mail = self.wake / owner.split(':', 1)[1] / filename
                if not event.get('mailed'):
                    self.unmail(event)
                    atomic(mail, self.note(record, event, f'act on it, then run pr-owner.py ack {event["id"]}'))
                    event['mailed'] = now
                    changed = True
                if now - event['at'] < 1800 or not mail.exists():
                    continue
                mail.unlink()
            name, slug = owner.split(':')[1:] if owner.startswith('bot:') else ('chief-of-staff', None)
            inbox = self.bots / name / 'inbox'
            inbox.mkdir(parents=True, exist_ok=True)
            if not any(inbox.rglob(filename)):
                ask = f'settle {slug}' if slug else f'settle {record["repo"]}#{record["pr"]}'
                atomic(inbox / filename, self.note(record, event, ask))
            event.update(delivered=True, delivered_at=now, delivery_path=str(inbox / filename))
            changed = True
        if changed:
            self.save_events(record, events)

    def unmail(self, event):
        if event['owner'].startswith('lead:'):
            for stale in (self.wake / event['owner'].split(':', 1)[1]).glob(f'*-pr-owner-{event["id"]}.md'):
                stale.unlink()

    def note(self, record, event, ask):
        return ('severity: act\n\n'
                f'pr-owner {event["kind"]}: https://github.com/{record["repo"]}/pull/{record["pr"]}\n'
                f'Owner: {event["owner"]}\nHead: {event["head"]}\nEvent: {event["id"]}\nAsk: {ask}\n\n'
                + json.dumps(event, indent=2) + '\n')

    def sweep(self):
        with self.locked():
            now = self.clock()
            records = self.records()
            control_path = self.root / 'sweep.json'
            control = json.loads(control_path.read_text()) if control_path.exists() else {'next_rate': 0, 'backoff_until': 0}
            rate_error = None
            due = [record for record in records if record['active'] and record['next_poll'] <= now]
            if due and now >= control['next_rate'] and now >= control['backoff_until']:
                try:
                    core = self.github.rate()
                    control.update(next_rate=now + 120, backoff_until=max(now + 300, core['reset']) if core['remaining'] < 500 else 0)
                except OwnerError as error:
                    rate_error = str(error)
                    control.update(next_rate=now + 300, backoff_until=now + 300)
                atomic(control_path, json.dumps(control) + '\n')
            polled = 0
            for record in records:
                if rate_error and record['active'] and record['next_poll'] <= now:
                    self.poll_failed(record, rate_error)
                    record['next_poll'] = now + 300
                    self.save(record)
                if record['active'] and record['next_poll'] <= now and now >= control['backoff_until']:
                    record['last_poll'] = now
                    record['next_poll'] = now + record['interval']
                    self.save(record)
                    try:
                        self.tick(record)
                        record['errors'] = 0
                        record.pop('last_error', None)
                    except (OwnerError, ValueError, KeyError, TypeError) as error:
                        self.poll_failed(record, str(error))
                    record['next_poll'] = max(record['next_poll'], self.clock() + record['interval'])
                    self.save(record)
                    polled += 1
                self.deliver(record)
            print(f'{stamp(self.clock())} sweep records={len(records)} polled={polled} '
                  f'active={sum(record["active"] for record in records)} backoff_until={control["backoff_until"]}', flush=True)

    def poll_failed(self, record, error):
        record.update(errors=record['errors'] + 1, settled_since=None, snapshot=None, verdict=None, last_error=error)
        self.withdraw_ready(record)
        if record['errors'] >= 5:
            self.emit(record, 'WATCH_ERROR', error=error, failed_ticks=record['errors'])

    def pending(self, record):
        return [dict(event, owner=record['owner']) for event in self.events(record)
                if not event['acked'] and not event.get('superseded')]

    def wait(self, owner, timeout):
        deadline = time.monotonic() + timeout
        try:
            while True:
                with self.locked(deadline):
                    atomic(self.heartbeat(owner), json.dumps({'pid': os.getpid(), 'at': self.clock()}) + '\n')
                    events = [event for record in self.records() for event in self.pending(record) if event['owner'] == owner]
                if events:
                    for event in events:
                        print(json.dumps(event), flush=True)
                    return 0
                if time.monotonic() >= deadline:
                    return 3
                time.sleep(min(1, max(0, deadline - time.monotonic())))
        except TimeoutError:
            return 3
        finally:
            try:
                with self.locked(time.monotonic() + 0.1):
                    path = self.heartbeat(owner)
                    if path.exists() and json.loads(path.read_text())['pid'] == os.getpid():
                        path.unlink()
            except TimeoutError:
                pass

    def ack(self, identities):
        with self.locked():
            found = set()
            for record in self.records():
                events = self.events(record)
                for event in events:
                    if event['id'] in identities:
                        event.update(acked=True, acked_at=event.get('acked_at', self.clock()))
                        found.add(event['id'])
                self.save_events(record, events)
            missing = set(identities) - found
            if missing:
                raise OwnerError('unknown event ids: ' + ', '.join(sorted(missing)))

    def release(self, repo, pr):
        with self.locked():
            record = self.load(repo, pr)
            if record:
                self.invalidate(record, 'released')
                record.update(active=False, released=True)
                self.save(record)

    def status(self, as_json):
        with self.locked():
            rows = [dict(repo=record['repo'], pr=record['pr'], owner=record['owner'], head=record['head'],
                         active=record['active'], released=record['released'], round=record['round'],
                         last_poll=stamp(record['last_poll']) if record['last_poll'] is not None else None,
                         verdict=record['verdict'], pending_events=[event['kind'] + ':' + event['id'] for event in self.pending(record)])
                    for record in self.records()]
        if as_json:
            print(json.dumps(rows, indent=2))
        else:
            for row in rows:
                print(f'{row["repo"]}#{row["pr"]} owner={row["owner"]} head={row["head"]} '
                      f'active={row["active"]} round={row["round"]} last_poll={row["last_poll"]} '
                      f'verdict={row["verdict"]} pending={",".join(row["pending_events"]) or "none"}')


def owner(value):
    if not re.fullmatch(r'(or|lead:[A-Za-z0-9_.-]+|bot:[A-Za-z0-9_-]+:[A-Za-z0-9_.-]+)', value):
        raise argparse.ArgumentTypeError('expected lead:<id>, bot:<name>:<slug>, or or')
    return value


def repository(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise argparse.ArgumentTypeError('expected owner/name')
    return value


def head_sha(value):
    if not re.fullmatch(r'[0-9a-fA-F]{40}', value):
        raise argparse.ArgumentTypeError('expected full 40-character head SHA')
    return value.lower()


def parser():
    result = argparse.ArgumentParser(description='Durable local PR tail ownership. GitHub operations are read-only.')
    sub = result.add_subparsers(dest='command', required=True)
    register = sub.add_parser('register')
    for name in ('register', 'rearm', 'release'):
        child = register if name == 'register' else sub.add_parser(name)
        child.add_argument('--repo', required=True, type=repository)
        child.add_argument('--pr', required=True, type=int)
        if name != 'release':
            child.add_argument('--head', required=True, type=head_sha)
    register.add_argument('--owner', required=True, type=owner)
    for name in ('worktree', 'branch', 'brief', 'evidence', 'resume'):
        register.add_argument('--' + name)
    register.add_argument('--done-when', choices=('merge-ready', 'merged'), default='merge-ready')
    register.add_argument('--takeover', action='store_true')
    register.add_argument('--or-approved', metavar='QUOTE')
    register.add_argument('--review-deadline', type=watch.seconds, default=1800, metavar='SECONDS')
    register.add_argument('--head-timeout', type=watch.seconds, default=21600, metavar='SECONDS')
    sub.add_parser('sweep')
    wait = sub.add_parser('wait')
    wait.add_argument('--owner', required=True, type=owner)
    wait.add_argument('--timeout', type=watch.seconds, default=21600)
    sub.add_parser('ack').add_argument('event_ids', nargs='+')
    sub.add_parser('status').add_argument('--json', action='store_true')
    sub.add_parser('self-test')
    return result


def self_tests():
    CLAUDE_REVIEW_REPOS.add('acme/app')
    import copy
    import io
    from unittest.mock import patch

    class FakeGitHub(GitHub):
        def __init__(self):
            self.head = 'a' * 40
            self.base = 'dev'
            self.required = [{'context': 'build', 'app_id': None}]
            self.current = [[1, 'build', True, True, 'https://checks/build']]
            self.run = {'id': 10, 'status': 'completed', 'conclusion': 'success', 'url': 'https://review/10'}
            self.findings = []
            self.threads = []
            self.state = 'open'
            self.merged = False
            self.merge_state = 'clean'
            self.fail = False
            self.calls = 0
            self.remaining = 5000
            self.move_after_checks = False
            self.rate_fail = False
            self.lagging = 0

        def pull(self, repo, pr):
            self.calls += 1
            if self.fail:
                raise OwnerError('injected API failure')
            shown = self.head
            if self.lagging:
                self.lagging -= 1
                shown = 'a' * 40
            return {'head': {'sha': shown}, 'base': {'ref': self.base}, 'state': self.state,
                    'merged': self.merged, 'html_url': 'https://github.test/pr',
                    'mergeable_state': self.merge_state, 'mergeable': True, 'draft': False}

        def gates(self, repo, base):
            return self.required

        def head_time(self, repo, head):
            return 1000

        def checks(self, repo, head):
            if self.move_after_checks:
                self.head = 'b' * 40
            return copy.deepcopy(self.current)

        def required_present(self, repo, head, gates):
            return all(any(check[1] == gate['context'] for check in self.current) for gate in gates or [])

        def graphql(self, query, **variables):
            return {'repository': {'pullRequest': {'reviewThreads': {
                'nodes': copy.deepcopy(self.threads), 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}}

        def review(self, repo, pr, head):
            return copy.deepcopy(self.run), copy.deepcopy(self.findings) + self.thread_findings(repo, pr)

        def rate(self):
            if self.rate_fail:
                raise OwnerError('injected rate API failure')
            return {'remaining': self.remaining, 'reset': 5000}

        def diagnostic(self, kind, record):
            return 'NOT YOURS: injected diagnostic' if kind == 'RED' else 'overlap: injected base drift'

    def args(repo='acme/app', pr=1, identity='lead:test', head='a' * 40):
        return parser().parse_args(['register', '--repo', repo, '--pr', str(pr), '--head', head, '--owner', identity])

    def setup(directory, identity='lead:test', required=None):
        now = [1000.0]
        fake = FakeGitHub()
        if required is not None:
            fake.required = required
        store = Store(Path(directory) / 'state', Path(directory) / 'bots', fake, lambda: now[0], wake=Path(directory) / 'wake')
        record = store.register(args(identity=identity))
        return store, fake, now, record

    def advance(store, now, seconds=301):
        now[0] += seconds
        store.sweep()

    def kinds(store, record):
        return [event['kind'] for event in store.events(record)]

    def concurrent_registers(directory):
        store, fake, now, record = setup(directory)
        store.release(record['repo'], record['pr'])
        read, write = os.pipe()
        children = []
        for identity in ('lead:first', 'lead:second'):
            pid = os.fork()
            if pid == 0:
                os.close(write)
                os.read(read, 1)
                try:
                    store.register(args(identity=identity))
                    os._exit(0)
                except OwnerError as error:
                    os._exit(error.code)
            children.append(pid)
        os.close(read)
        os.write(write, b'xx')
        os.close(write)
        codes = [os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]) for pid in children]
        assert sorted(codes) == [0, 2], codes
        winner = store.load('acme/app', 1)['owner']
        assert winner in {'lead:first', 'lead:second'}
        before = store.load('acme/app', 1)
        assert store.register(args(identity=winner)) == before
        assert store.register(parser().parse_args(['register', '--repo', 'acme/app', '--pr', '1',
                             '--head', 'a' * 40, '--owner', 'or', '--takeover']))['owner'] == 'or'

    def kill_after_event(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        now[0] += 301
        read, write = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read)
            original = store.save_events
            def crash_point(record, events):
                original(record, events)
                if events:
                    os.write(write, b'x')
                    signal.pause()
            store.save_events = crash_point
            store.sweep()
            os._exit(1)
        os.close(write)
        assert os.read(read, 1) == b'x'
        os.close(read)
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        store = Store(store.root, store.bots, fake, lambda: now[0], wake=store.wake)
        store.sweep()
        first, replay = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(first):
            assert store.wait('lead:test', 0.01) == 0
        with contextlib.redirect_stdout(replay):
            assert store.wait('lead:test', 0.01) == 0
        assert first.getvalue() == replay.getvalue()
        event = json.loads(first.getvalue())
        assert event['kind'] == 'READY'
        store.ack([event['id']])
        acked_at = store.events(record)[0]['acked_at']
        now[0] += 1
        store.ack([event['id']])
        assert store.events(record)[0]['acked_at'] == acked_at
        assert store.wait('lead:test', 0.01) == 3
        advance(store, now)
        advance(store, now)
        assert kinds(store, record) == ['READY']

    def new_head(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        advance(store, now)
        fake.head = 'b' * 40
        advance(store, now)
        advance(store, now)
        assert [event['kind'] for event in store.pending(record)] == ['HEAD_MOVED']
        changed = store.rearm(args(head=fake.head))
        assert changed['verdict'] is None and changed['snapshot'] is None and changed['round'] == 1
        assert not store.pending(record)
        store.sweep()
        assert not store.pending(record)
        advance(store, now)
        assert [event['kind'] for event in store.pending(record)] == ['READY']
        assert store.pending(record)[0]['head'] == fake.head

    def late_status(directory):
        store, fake, now, record = setup(directory, required=[{'context': 'build', 'app_id': None},
                                                           {'context': 'late-status', 'app_id': None}])
        store.sweep()
        advance(store, now)
        assert not store.events(record)
        fake.current.append([2, 'late-status', False, False, 'https://checks/late'])
        advance(store, now)
        assert not store.events(record)
        fake.current[1] = [3, 'late-status', True, True, 'https://checks/late']
        advance(store, now)
        assert not store.events(record)
        advance(store, now)
        assert kinds(store, record) == ['READY']

    def review_deadline(directory):
        store, fake, now, record = setup(directory)
        fake.run = None
        store.sweep()
        advance(store, now, 1800)
        assert kinds(store, record) == ['NOT_REVIEWED']
        advance(store, now)
        assert kinds(store, record) == ['NOT_REVIEWED']

    def replaced_registration_event(directory):
        store, fake, now, record = setup(directory)
        fake.run = None
        store.sweep()
        advance(store, now, 1800)
        old = store.pending(record)[0]
        store.release(record['repo'], record['pr'])
        now[0] += 1
        record = store.register(args())
        assert store.events(record)[0]['superseded'] == 'released registration replaced'
        store.sweep()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert store.wait('lead:test', 0.01) == 0
        event = json.loads(output.getvalue())
        assert event['kind'] == 'NOT_REVIEWED' and not event.get('superseded')
        assert event['at'] > old['at'] and not event['acked']
        events = store.events(record)
        assert len({item['id'] for item in events}) == len(events)
        store.ack([event['id']])
        assert store.events(record)[0]['acked'] and not store.pending(record)
        assert store.wait('lead:test', 0.01) == 3

    def ready_timeout(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        advance(store, now)
        assert store.load('acme/app', 1)['verdict'] == 'READY'
        store.ack([store.pending(record)[0]['id']])
        advance(store, now, 21600)
        assert store.load('acme/app', 1)['verdict'] == 'READY'
        assert 'TIMEOUT' not in kinds(store, record)
        fake.current[0][3] = False
        advance(store, now)
        assert store.load('acme/app', 1)['verdict'] != 'READY'
        assert 'TIMEOUT' in kinds(store, record)

    def rearm_budget(directory):
        store, fake, now, record = setup(directory)
        for head in ('b' * 40, 'c' * 40):
            fake.head = head
            store.rearm(args(head=head))
        fake.head = 'd' * 40
        try:
            store.rearm(args(head=fake.head))
        except OwnerError as error:
            assert error.code == 1 and 'budget exhausted' in str(error)
        else:
            raise AssertionError('third rearm was accepted')
        assert store.load('acme/app', 1)['head'] == 'c' * 40
        store.release('acme/app', 1)
        try:
            store.register(args(head=fake.head))
        except OwnerError as error:
            assert 'spent its rearm budget' in str(error)
        else:
            raise AssertionError('re-register after a spent budget was accepted without Or')
        approved = parser().parse_args(['register', '--repo', 'acme/app', '--pr', '1', '--head', fake.head,
                                        '--owner', 'lead:test', '--or-approved', 'one more round'])
        record = store.register(approved)
        assert (record['round'], record['rearm_budget'], record['or_approvals']) == (2, 4, ['one more round'])

    def head_lag(directory):
        store, fake, now, record = setup(directory)
        slept = []
        store.sleep = slept.append
        fake.head, fake.lagging = 'b' * 40, 2
        assert store.rearm(args(head=fake.head))['head'] == 'b' * 40 and slept == [3, 3]
        fake.head, fake.lagging = 'c' * 40, 11
        try:
            store.rearm(args(head=fake.head))
        except OwnerError as error:
            assert 'current head' in str(error)
        else:
            raise AssertionError('rearm accepted a head GitHub never showed')

    def same_head_rounds(directory):
        store, fake, now, record = setup(directory)
        fake.run = None
        store.sweep()
        advance(store, now, 1800)
        fake.run = {'id': 10, 'status': 'completed', 'conclusion': 'success', 'url': 'review'}
        fake.findings = [{'id': 1}]
        advance(store, now)
        fake.findings = []
        advance(store, now)
        advance(store, now)
        assert set(kinds(store, record)) == {'NOT_REVIEWED', 'FINDINGS', 'READY'}
        fake.state = 'closed'
        try:
            store.rearm(args())
            raise AssertionError('closed PR accepted')
        except OwnerError as error:
            assert 'open PR' in str(error)
        fake.state = 'open'
        fake.head = 'b' * 40
        try:
            store.rearm(args())
            raise AssertionError('stale head accepted')
        except OwnerError as error:
            assert 'current head' in str(error)
        fake.head = 'a' * 40
        changed = store.rearm(args())
        assert changed['round'] == 1 and changed['review_since'] == now[0]
        assert changed['snapshot'] is None and changed['settled_since'] is None and changed['verdict'] is None
        assert not store.pending(record)
        fake.run = None
        store.sweep()
        advance(store, now, 1799)
        assert kinds(store, record).count('NOT_REVIEWED') == 1
        advance(store, now, 301)
        assert kinds(store, record).count('NOT_REVIEWED') == 2
        fake.run = {'id': 11, 'status': 'completed', 'conclusion': 'success', 'url': 'review'}
        fake.findings = [{'id': 2}]
        advance(store, now)
        fake.findings = []
        advance(store, now)
        advance(store, now)
        assert all(kinds(store, record).count(kind) == 2 for kind in ('NOT_REVIEWED', 'FINDINGS', 'READY'))
        assert store.rearm(args())['round'] == 2
        for head in ('a' * 40, 'b' * 40):
            fake.head = head
            try:
                store.rearm(args(head=head))
                raise AssertionError('third rearm accepted')
            except OwnerError as error:
                assert 'budget exhausted' in str(error)

    def answered_findings(directory):
        store, fake, now, record = setup(directory)
        github = GitHub()
        runs = [{'name': 'Claude PR Review', 'head_sha': fake.head, 'created_at': '2026-01-01T00:00:00Z',
                 'updated_at': '2026-01-01T00:01:00Z', 'id': 1, 'status': 'completed', 'conclusion': 'success',
                 'html_url': 'review'}]
        finding = {'id': 8, 'user': {'login': 'claude[bot]'}, 'original_commit_id': fake.head,
                   'path': 'code.py', 'line': 1, 'body': 'Fix boundary', 'html_url': 'finding'}
        reply = {'id': 9, 'in_reply_to_id': 8, 'user': {'login': 'author'}}
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, [finding, reply], []]):
            fake.run, fake.findings = github.review('acme/app', 1, fake.head)
        store.sweep()
        advance(store, now)
        assert kinds(store, record) == ['READY'] and store.load('acme/app', 1)['verdict'] == 'READY'
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, [finding], []]):
            fake.run, fake.findings = github.review('acme/app', 1, fake.head)
        advance(store, now)
        advance(store, now)
        assert 'FINDINGS' in kinds(store, record) and store.load('acme/app', 1)['verdict'] is None
        assert not store.pending(record) or all(event['kind'] != 'READY' for event in store.pending(record))

    def bot_delivery(directory):
        store, fake, now, record = setup(directory, 'bot:test:fix-it')
        store.sweep()
        now[0] += 301
        read, write = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read)
            original = store.save_events
            def crash_point(record, events):
                if any(event['delivered'] for event in events):
                    os.write(write, b'x')
                    signal.pause()
                original(record, events)
            store.save_events = crash_point
            store.sweep()
            os._exit(1)
        os.close(write)
        assert os.read(read, 1) == b'x'
        os.close(read)
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        inbox = store.bots / 'test/inbox'
        notes = list(inbox.glob('*.md'))
        assert len(notes) == 1
        content = notes[0].read_text()
        assert content.startswith('severity: act\n') and 'Ask: settle fix-it' in content
        done = inbox / 'done'
        done.mkdir()
        notes[0].rename(done / notes[0].name)
        store.sweep()
        advance(store, now)
        assert len(list(inbox.rglob('*.md'))) == 1
        event = store.events(record)[0]
        assert event['delivered'] and not event['acked']
        store.ack([event['id']])
        assert store.events(record)[0]['acked']

    def errors_and_backoff(directory):
        store, fake, now, record = setup(directory)
        fake.fail = True
        for tick in range(5):
            store.sweep()
            now[0] += 301
        assert kinds(store, record) == ['WATCH_ERROR']
        assert store.load('acme/app', 1)['errors'] == 5
        fake.fail = False
        fake.remaining = 499
        store.sweep()
        calls = fake.calls
        advance(store, now, 301)
        assert fake.calls == calls
        assert store.load('acme/app', 1)['settled_since'] is None

    def interval_and_head_guard(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        calls = fake.calls
        store.sweep()
        assert fake.calls == calls
        advance(store, now)
        assert store.load('acme/app', 1)['interval'] == 180
        fake.move_after_checks = True
        advance(store, now)
        assert [event['kind'] for event in store.pending(record)] == ['HEAD_MOVED']
        assert store.load('acme/app', 1)['verdict'] == 'HEAD_MOVED'

    def terminal_events(directory):
        store, fake, now, record = setup(directory)
        fake.current[0][3] = False
        store.sweep()
        advance(store, now)
        red = store.events(record)[0]
        assert red['kind'] == 'RED' and red['details']['failures'][0]['url'] == 'https://checks/build'
        assert 'NOT YOURS' in red['details']['diagnostic']
        fake.merge_state = 'dirty'
        fake.findings = [{'id': 20, 'title': 'Fix this'}]
        advance(store, now)
        assert kinds(store, record) == ['RED', 'CONFLICT', 'FINDINGS']
        now[0] += 21600
        store.sweep()
        assert 'TIMEOUT' in kinds(store, record)
        fake.state = 'closed'
        fake.merged = True
        advance(store, now)
        assert kinds(store, record)[-1] == 'MERGED'
        assert not store.load('acme/app', 1)['active']
        calls = fake.calls
        advance(store, now)
        assert fake.calls == calls

    def orphan_delivery(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        advance(store, now)
        atomic(store.heartbeat('lead:test'), json.dumps({'pid': os.getpid(), 'at': now[0] + 1801}))
        advance(store, now, 1801)
        assert not list(store.bots.rglob('*.md'))
        assert len(list(store.wake.rglob('*.md'))) == 1
        store.heartbeat('lead:test').unlink()
        store.sweep()
        assert len(list((store.bots / 'chief-of-staff/inbox').glob('*.md'))) == 1
        assert not list(store.wake.rglob('*.md'))
        store.sweep()
        assert len(list(store.bots.rglob('*.md'))) == 1

    def lead_mail(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        advance(store, now)
        mail = list((store.wake / 'test').glob('*.md'))
        assert len(mail) == 1 and 'pr-owner.py ack' in mail[0].read_text()
        store.sweep()
        assert len(list((store.wake / 'test').glob('*.md'))) == 1
        kind = json.loads(mail[0].read_text().split('\n\n', 2)[2])['kind']
        store.invalidate(record, 'test supersede')
        store.sweep()
        assert not list((store.wake / 'test').glob('*.md'))
        now[0] += 60
        store.emit(store.load('acme/app', 1), kind)
        store.sweep()
        mail = list((store.wake / 'test').glob('*.md'))
        assert len(mail) == 1
        claimed = store.wake / 'test' / 'done' / mail[0].name
        claimed.parent.mkdir()
        mail[0].rename(claimed)
        advance(store, now, 1801)
        assert not list(store.bots.rglob('*.md'))
        assert not list((store.wake / 'test').glob('*.md'))

    def wait_until_merged(directory):
        store, fake, now, record = setup(directory)
        record['done_when'] = 'merged'
        store.save(record)
        store.sweep()
        advance(store, now)
        assert store.load('acme/app', 1)['verdict'] == 'READY'
        assert not store.events(record) and store.load('acme/app', 1)['active']
        fake.state = 'closed'
        fake.merged = True
        advance(store, now)
        assert kinds(store, record) == ['MERGED']
        assert not store.load('acme/app', 1)['active']

    def rate_failures(directory):
        store, fake, now, record = setup(directory)
        fake.rate_fail = True
        for tick in range(5):
            store.sweep()
            now[0] += 301
        assert kinds(store, record) == ['WATCH_ERROR']
        assert store.load('acme/app', 1)['errors'] == 5

    def busy_wait_timeout(directory):
        store, fake, now, record = setup(directory)
        read, write = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read)
            with store.locked():
                os.write(write, b'x')
                signal.pause()
            os._exit(1)
        os.close(write)
        try:
            assert os.read(read, 1) == b'x'
            started = time.monotonic()
            assert store.wait('lead:test', 0.05) == 3
            assert time.monotonic() - started < 1
        finally:
            os.close(read)
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)

    def ready_withdrawal(directory):
        store, fake, now, record = setup(directory)
        store.sweep()
        advance(store, now)
        assert [event['kind'] for event in store.pending(record)] == ['READY']
        fake.current.append([2, 'late-status', False, False, 'https://checks/late'])
        advance(store, now)
        assert not store.pending(record)
        assert store.load('acme/app', 1)['verdict'] is None

    def reviewer_threads(directory):
        for repo in ('acme/app', 'o/n'):
            for outcome in ('resolved', 'outdated', 'replied'):
                store, fake, now, record = setup(Path(directory) / repo / outcome)
                if repo != record['repo']:
                    store.release(record['repo'], record['pr'])
                    record = store.register(args(repo=repo))
                store.sweep()
                advance(store, now)
                assert [event['kind'] for event in store.pending(record)] == ['READY']
                thread = dict(id='thread', isResolved=False, isOutdated=False, comments={
                    'nodes': [{'author': {'login': 'chatgpt-codex-connector'}, 'body': 'Fix boundary\nDetails',
                               'url': 'https://github.test/thread'}],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None}})
                fake.threads = [thread]
                advance(store, now)
                advance(store, now)
                assert store.load(repo, 1)['verdict'] is None
                pending = store.pending(record)
                assert [event['kind'] for event in pending] == ['FINDINGS']
                assert pending[0]['details']['findings'] == [dict(
                    kind='thread', id='thread', author='chatgpt-codex-connector',
                    title='Fix boundary', url='https://github.test/thread')]
                if outcome == 'replied':
                    thread['comments']['nodes'].append({'author': {'login': 'author'}})
                else:
                    thread['isResolved' if outcome == 'resolved' else 'isOutdated'] = True
                advance(store, now)
                assert store.load(repo, 1)['verdict'] is None
                advance(store, now)
                assert store.load(repo, 1)['verdict'] == 'READY'

    def thread_pagination(directory):
        github = GitHub()
        page = lambda more, cursor: dict(hasNextPage=more, endCursor=cursor)
        first = dict(author={'login': 'chatgpt-codex-connector'}, body='Fix boundary', url='thread')
        thread = dict(id='thread', isResolved=False, isOutdated=False,
                      comments=dict(nodes=[first, first], pageInfo=page(True, 'reply-page')))
        claude = dict(id='claude', isResolved=False, isOutdated=False,
                      comments=dict(nodes=[dict(first, author={'login': 'claude'})], pageInfo=page(False, None)))
        responses = [
            {'repository': {'pullRequest': {'reviewThreads': dict(nodes=[thread], pageInfo=page(True, 'thread-page'))}}},
            {'node': {'comments': dict(nodes=[{'author': {'login': 'author'}}], pageInfo=page(False, None))}},
            {'repository': {'pullRequest': {'reviewThreads': dict(nodes=[claude], pageInfo=page(False, None))}}}]
        with patch.object(github, 'graphql', side_effect=responses) as call:
            assert github.thread_findings('acme/app', 1) == []
        assert call.call_args_list[1].kwargs == dict(id='thread', cursor='reply-page')
        assert call.call_args_list[2].kwargs['cursor'] == 'thread-page'
        thread['comments']['pageInfo'] = page(False, None)
        with patch.object(github, 'graphql', return_value=responses[0]):
            responses[0]['repository']['pullRequest']['reviewThreads']['pageInfo'] = page(False, None)
            assert len(github.thread_findings('acme/app', 1)) == 1
        with patch.object(github, 'graphql', return_value=responses[2]):
            assert len(github.thread_findings('o/n', 1)) == 1
        with patch.object(github, 'thread_findings', return_value=[{'id': 'thread'}]), \
                patch.object(github, 'pages', return_value=[]):
            assert github.review('acme/app', 1, 'a' * 40) == (None, [{'id': 'thread'}])
            assert github.review('o/n', 1, 'a' * 40) == (None, [{'id': 'thread'}])

    def github_predicates(directory):
        responses = [json.dumps([1, 7, 'build', 'completed', 'failure', 'old']) + '\n' +
                     json.dumps([2, 7, 'build', 'completed', 'success', 'new']),
                     json.dumps([3, 'late', 'pending', 'status']) + '\n' +
                     json.dumps([4, 'late', 'success', 'latest'])]
        github = GitHub()
        with patch(__name__ + '.command', side_effect=responses) as call:
            checks = github.checks('o/n', 'a' * 40)
        assert checks == [[2, 'build', True, True, 'new'], [4, 'late', True, True, 'latest']]
        assert call.call_count == 2
        assert github.required_present('o/n', 'a' * 40, [{'context': 'build', 'app_id': 7}, {'context': 'late'}])
        assert not github.required_present('o/n', 'a' * 40, [{'context': 'build', 'app_id': 8}])
        runs = [{'name': 'Claude PR Review', 'head_sha': 'a' * 40, 'created_at': '2026-01-01T00:00:00Z',
                 'updated_at': '2026-01-01T00:01:00Z', 'id': 1, 'status': 'completed', 'conclusion': 'success',
                 'html_url': 'review'}]
        inline = [{'id': 8, 'user': {'login': 'claude[bot]'}, 'original_commit_id': 'a' * 40,
                   'path': 'code.py', 'line': 1, 'body': 'Fix boundary', 'html_url': 'finding'}]
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, inline, []]):
            run, findings = github.review('acme/app', 1, 'a' * 40)
        assert run['id'] == 1 and [finding['id'] for finding in findings] == [8]
        approval = {'id': 9, 'user': {'login': 'claude[bot]'}, 'body': '✅ Approve — checked the code',
                    'created_at': '2026-01-01T00:00:30Z', 'html_url': 'approval'}
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, [], [approval]]):
            run, findings = github.review('acme/app', 1, 'a' * 40)
        assert not findings
        approval['body'] = '**✅ Approve** — checked the code'
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, [], [approval]]):
            run, findings = github.review('acme/app', 1, 'a' * 40)
        assert not findings
        approval['body'] += '\n- 🟠 Important: a production defect'
        with patch.object(github, 'thread_findings', return_value=[]), \
                patch.object(github, 'pages', side_effect=[runs, [], [approval]]):
            run, findings = github.review('acme/app', 1, 'a' * 40)
        assert [finding['id'] for finding in findings] == [9]

    tests = [lead_mail, concurrent_registers, kill_after_event, new_head, late_status, review_deadline, rearm_budget, head_lag,
             bot_delivery, errors_and_backoff, interval_and_head_guard, terminal_events, orphan_delivery, github_predicates,
             rate_failures, busy_wait_timeout, ready_withdrawal, wait_until_merged, same_head_rounds, answered_findings,
             replaced_registration_event, ready_timeout, reviewer_threads, thread_pagination]
    failures = 0
    for test in tests:
        try:
            with tempfile.TemporaryDirectory(prefix='pr-owner-self-test-') as directory, contextlib.redirect_stdout(io.StringIO()):
                test(directory)
            print(f'PASS {test.__name__}')
        except Exception as error:
            failures += 1
            print(f'FAIL {test.__name__}: {type(error).__name__}: {error}')
    print(f'{len(tests) - failures} passed; {failures} failed (fake GitHub, temporary state only)')
    return 1 if failures else 0


def schedule_plist():
    log = str(STATE / 'sweep.log')
    return {
        'Label': SCHEDULE_LABEL,
        'ProgramArguments': [sys.executable, '-I', str(Path(__file__).resolve()), 'sweep'],
        'EnvironmentVariables': {'PATH': '/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
        'RunAtLoad': True,
        'StartInterval': 120,
        'StandardOutPath': log,
        'StandardErrorPath': log,
    }


def ensure_schedule():
    if platform.system() != 'Darwin':
        return
    wanted = schedule_plist()
    if SCHEDULE_PLIST.exists() and plistlib.loads(SCHEDULE_PLIST.read_bytes()) == wanted:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PLIST.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PLIST.write_bytes(plistlib.dumps(wanted))
    domain = f'gui/{os.getuid()}'
    subprocess.run(['launchctl', 'bootout', f'{domain}/{SCHEDULE_LABEL}'], capture_output=True)
    subprocess.run(['launchctl', 'bootstrap', domain, str(SCHEDULE_PLIST)], capture_output=True, check=True)


def main():
    args = parser().parse_args()
    store = Store()
    try:
        if args.command in {'register', 'rearm'}:
            print(json.dumps(getattr(store, args.command)(args), indent=2))
            ensure_schedule()
        elif args.command == 'sweep':
            store.sweep()
        elif args.command == 'wait':
            if not args.owner.startswith('lead:'):
                raise OwnerError('wait requires a lead:<id> owner')
            return store.wait(args.owner, args.timeout)
        elif args.command == 'ack':
            store.ack(args.event_ids)
        elif args.command == 'status':
            store.status(args.json)
        elif args.command == 'release':
            store.release(args.repo, args.pr)
        elif args.command == 'self-test':
            return self_tests()
        return 0
    except (OwnerError, OSError, ValueError) as error:
        print(f'pr-owner: {error}', file=sys.stderr)
        return error.code if isinstance(error, OwnerError) else 1


if __name__ == '__main__':
    sys.exit(main())
