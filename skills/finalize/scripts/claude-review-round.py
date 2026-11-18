#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
import time

CLAUDE_LOGINS = {"claude", "claude[bot]"}
POLL_SECONDS = 30


class RoundError(Exception):
    pass


def gh(*arguments):
    result = subprocess.run(["gh", *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RoundError(result.stderr.strip())
    return result.stdout


def gh_json(*arguments):
    return json.loads(gh(*arguments) or "null")


def gh_paginated(path):
    pages = gh("api", "--paginate", "--slurp", path)
    return [item for page in json.loads(pages) for item in page]


def resolve_pull_request(target, repo):
    arguments = ["pr", "view", target, "--json", "number,headRefOid,url"]
    if repo:
        arguments += ["--repo", repo]
    pull_request = gh_json(*arguments)
    owner_and_name = "/".join(pull_request["url"].split("/")[3:5])
    return owner_and_name, pull_request["number"], pull_request["headRefOid"]


def review_runs_for(repo, head, workflow):
    return gh_json(
        "run", "list", "--repo", repo, "--commit", head, "--workflow", workflow,
        "--json", "databaseId,status,conclusion,event,createdAt,updatedAt,url",
    )


def wait_for_round(repo, head, workflow, deadline, await_run, grace_deadline, started):
    while True:
        runs = review_runs_for(repo, head, workflow)
        if not runs and not await_run and time.monotonic() >= grace_deadline:
            return None
        latest = max(runs, key=lambda run: run["createdAt"]) if runs else None
        if latest and (started or latest["status"] == "completed"):
            return latest
        pending = f"review run {latest['url']} {latest['status']}" if latest else f"no review run for {head}"
        if time.monotonic() > deadline:
            raise RoundError(f"{pending} at timeout")
        print(f"{pending}; waiting", file=sys.stderr)
        time.sleep(POLL_SECONDS)


def first_line(body):
    return next((line.strip() for line in body.splitlines() if line.strip()), "")[:200]


def inline_findings(repo, number, head):
    comments = gh_paginated(f"repos/{repo}/pulls/{number}/comments?per_page=100")
    answered = {comment["in_reply_to_id"] for comment in comments if comment.get("in_reply_to_id")}
    return [
        {
            "kind": "inline",
            "id": comment["id"],
            "path": comment["path"],
            "line": comment.get("line") or comment.get("original_line"),
            "title": first_line(comment["body"]),
            "answered": comment["id"] in answered,
            "url": comment["html_url"],
        }
        for comment in comments
        if comment["user"]["login"] in CLAUDE_LOGINS
        and not comment.get("in_reply_to_id")
        and comment["original_commit_id"] == head
    ]


def conversation_findings(repo, number, run):
    comments = gh_paginated(f"repos/{repo}/issues/{number}/comments?per_page=100")
    return [
        {
            "kind": "conversation",
            "id": comment["id"],
            "title": first_line(comment["body"]),
            "url": comment["html_url"],
        }
        for comment in comments
        if comment["user"]["login"] in CLAUDE_LOGINS
        and run["createdAt"] <= comment["created_at"] <= run["updatedAt"]
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Wait for the Claude review run on a PR's head commit to finish, then print every finding it posted on that head."
    )
    parser.add_argument("pr", help="PR number, URL, or branch")
    parser.add_argument("--repo", help="owner/name when not run inside the PR's checkout")
    parser.add_argument("--workflow", default="Claude PR Review")
    parser.add_argument("--await-run", action="store_true", help="wait for a run to appear instead of reporting not_reviewed")
    parser.add_argument("--timeout-min", type=float, default=40)
    parser.add_argument("--grace-sec", type=float, default=0, help="wait this long for a run to appear before reporting not_reviewed")
    parser.add_argument("--started", action="store_true", help="report as soon as a run exists on the head instead of waiting for it to finish")
    arguments = parser.parse_args()

    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        print(json.dumps({"pr": arguments.pr, "state": "cloud_session", "next": "the session's PR subscription delivers the review run and its findings"}, indent=2))
        return 0

    try:
        repo, number, head = resolve_pull_request(arguments.pr, arguments.repo)
        run = wait_for_round(repo, head, arguments.workflow, time.monotonic() + arguments.timeout_min * 60, arguments.await_run,
                             time.monotonic() + arguments.grace_sec, arguments.started)
        if run is None:
            print(json.dumps({"pr": number, "head": head, "state": "not_reviewed"}, indent=2))
            return 0
        if arguments.started:
            print(json.dumps({"pr": number, "head": head, "state": "started", "run": {"id": run["databaseId"], "event": run["event"], "status": run["status"], "url": run["url"]}}, indent=2))
            return 0
        findings = inline_findings(repo, number, head) + conversation_findings(repo, number, run)
        print(json.dumps({
            "pr": number,
            "head": head,
            "state": "reviewed",
            "run": {"id": run["databaseId"], "event": run["event"], "conclusion": run["conclusion"], "url": run["url"]},
            "findings": findings,
        }, indent=2))
        return 0
    except RoundError as error:
        print(f"claude-review-round: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
