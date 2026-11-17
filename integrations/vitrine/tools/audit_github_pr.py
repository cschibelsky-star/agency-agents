#!/usr/bin/env python3
"""GitHub authenticated read-only PR evidence check; NEVER authorizes execution."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REQUIRED = (
    "Check Divisions Consistency",
    "Check Hermes Config Rewrite",
    "Check Runbooks Consistency",
    "Check Tools Consistency",
    "Test Installer",
    "Vitrine Agent Overlay — Offline Tests",
)

def get(repo, path, token):
    request = urllib.request.Request(
        "https://api.github.com/repos/" + repo + path,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "vitrine-agency-read-only"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError("unexpected_http_status")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("response_too_large")
        return json.loads(raw.decode("utf-8"))

def evaluate(repo, number, pr, reviews, runs):
    errors = []
    def block(code):
        if code not in errors:
            errors.append(code)
    if not isinstance(pr, dict) or not isinstance(reviews, list) or not isinstance(runs, list):
        return verdict(repo, number, None, ["malformed_evidence"], [])
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    author = pr.get("user") if isinstance(pr.get("user"), dict) else {}
    head_repo = head.get("repo") if isinstance(head.get("repo"), dict) else {}
    sha, login = head.get("sha"), author.get("login")
    if not isinstance(sha, str) or len(sha) != 40:
        block("invalid_sha")
    if head_repo.get("full_name") != repo:
        block("wrong_repository")
    if pr.get("number") != number or pr.get("state") != "open":
        block("pr_not_open")
    if pr.get("draft") is not False:
        block("pr_draft")
    if not isinstance(login, str) or not login:
        block("missing_author")
    latest = {}
    for run in runs:
        if not isinstance(run, dict):
            block("invalid_run")
            continue
        name, run_id = run.get("name"), run.get("id")
        if name in REQUIRED and run.get("head_sha") == sha and run.get("event") == "pull_request":
            if not isinstance(run_id, int) or isinstance(run_id, bool):
                block("invalid_run_id")
                continue
            if name not in latest or run_id > latest[name]["id"]:
                latest[name] = run
    statuses = []
    for name in REQUIRED:
        run = latest.get(name)
        state = ("missing" if not run else
                 "pending" if run.get("status") != "completed" else run.get("conclusion"))
        if state != "success":
            block("incomplete_workflow:" + name)
        statuses.append({"name": name, "conclusion": state, "run_id": run.get("id") if run else None})
    last = {}
    for review in reviews:
        if not isinstance(review, dict):
            block("invalid_review")
            continue
        user = review.get("user") if isinstance(review.get("user"), dict) else {}
        account, review_id = user.get("login"), review.get("id")
        if (not isinstance(account, str) or not account or
                not isinstance(review_id, int) or isinstance(review_id, bool)):
            block("invalid_review_identity")
            continue
        if review.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            if account not in last or review_id > last[account]["id"]:
                last[account] = review
    approved = sum(1 for account, r in last.items()
                   if account != login and r.get("state") == "APPROVED"
                   and r.get("commit_id") == sha)
    if not approved:
        block("no_independent_review_for_current_sha")
    return verdict(repo, number, sha, errors, statuses, approved)

def verdict(repo, number, sha, errors, checks, approved=0):
    return {
        "repository": repo, "pr_number": number, "head_sha": sha,
        "decision": "blocked" if errors else "pending_via_supervision",
        "checks": checks, "current_sha_review_count": approved,
        "github_api_read": True, "agent_identity_mapping_verified": False,
        "evidence_verified_by_via": False, "can_advance": False,
        "dispatch_allowed": False, "production_allowed": False,
        "failures": errors,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN", "")
    if args.repo != os.getenv("GITHUB_REPOSITORY") or not token or args.pr <= 0:
        print(json.dumps({"decision":"blocked", "can_advance": False,
                          "failures":["missing_readonly_github_context"]}))
        return 2
    try:
        pr = get(args.repo, "/pulls/" + str(args.pr), token)
        sha = pr["head"]["sha"]
        reviews = get(args.repo, "/pulls/" + str(args.pr) + "/reviews?per_page=100", token)
        listing = get(args.repo, "/actions/runs?event=pull_request&head_sha=" +
                      urllib.parse.quote(sha, safe="") + "&per_page=100", token)
        if (not isinstance(reviews, list) or len(reviews) >= 100 or
                not isinstance(listing, dict) or
                not isinstance(listing.get("total_count"), int) or
                listing["total_count"] > 100 or
                not isinstance(listing.get("workflow_runs"), list)):
            raise ValueError("pagination_incomplete_or_untrusted")
        result = evaluate(args.repo, args.pr, pr, reviews, listing["workflow_runs"])
    except (OSError, KeyError, TypeError, ValueError, urllib.error.URLError,
            json.JSONDecodeError) as err:
        # Keep sensitive responses and token out of output/logs.
        print(json.dumps({"decision": "blocked", "github_api_read": False,
                          "can_advance": False, "dispatch_allowed": False,
                          "failures": ["github_api_incomplete_or_unavailable"],
                          "error_type": type(err).__name__}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # A successful read is NOT permission to advance. Read 'decision' in JSON.
    return 0

if __name__ == "__main__":
    sys.exit(main())
