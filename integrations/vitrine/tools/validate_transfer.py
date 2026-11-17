#!/usr/bin/env python3
"""Offline-only consistency auditor. Never authenticates GitHub or dispatches."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("architecture", "quality_evidence", "independent_review")
SHA = re.compile(r"^[a-fA-F0-9]{40}$")


def audit(h, stages, snapshot):
    errors = []
    def fail(reason):
        if reason not in errors:
            errors.append(reason)
    def txt(x):
        return isinstance(x, str) and bool(x.strip())
    def sha(x):
        return isinstance(x, str) and bool(SHA.fullmatch(x))
    if not isinstance(h, dict) or not isinstance(snapshot, dict) or not isinstance(stages, list):
        return result(["invalid_input"])
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    policy = manifest["governance"]
    if manifest["execution_enabled"] is not False or manifest["supervisor_mode"] != "OBSERVER" or any(policy.get(k) is not False for k in ("can_advance", "dispatch_allowed", "production_allowed", "api_calls_allowed")):
        fail("manifest_not_fail_closed")
    if any(k in h or k in snapshot for k in ("can_advance", "dispatch_allowed", "production_allowed", "evidence_verified")):
        fail("privileged_field")
    for field in ("task_id", "repository", "branch", "agent_id", "specialty", "objective", "next_owner"):
        if not txt(h.get(field)):
            fail("missing_" + field)
    if h.get("schema_version") != "1.0":
        fail("schema_version")
    branch = h.get("branch")
    if not txt(branch) or branch in ("main", "master", "prod", "production") or ".." in branch or "//" in branch or branch.startswith("/") or branch.endswith("/"):
        fail("unisolated_branch")
    base, head = h.get("base_sha"), h.get("result_sha")
    if not sha(base) or not sha(head) or base == head:
        fail("sha_invalid")
    if any(snapshot.get(k) != h.get(k) for k in ("task_id", "repository", "branch", "base_sha", "result_sha")):
        fail("snapshot_target_or_sha")
    auth = h.get("authorization")
    if not isinstance(auth, dict) or not txt(auth.get("scope")) or auth.get("approved_for_branch_write") is not True or auth.get("production_approved") is not False:
        fail("authorization_missing")
    if h.get("state") != "ready_for_via":
        fail("handoff_not_ready")
    if not isinstance(h.get("changed_files"), list) or not h["changed_files"] or not all(txt(f) for f in h["changed_files"]):
        fail("changed_files_missing")
    if not isinstance(h.get("risks"), list):
        fail("risks_missing")
    if snapshot.get("author_agent_id") != h.get("agent_id") or not txt(snapshot.get("author_login")):
        fail("author_identity_mismatch")
    checks, observed = h.get("checks"), snapshot.get("checks")
    if not isinstance(checks, list) or not isinstance(observed, list):
        fail("checks_missing")
        checks, observed = [], []
    by_id = {}
    for item in observed:
        if not isinstance(item, dict) or not txt(item.get("id")):
            fail("observed_check_invalid")
            continue
        if item["id"] in by_id:
            fail("observed_check_duplicate")
        by_id[item["id"]] = item
    seen = set()
    required = 0
    for check in checks:
        if not isinstance(check, dict) or not txt(check.get("id")):
            fail("check_invalid")
            continue
        cid = check["id"]
        if cid in seen:
            fail("check_duplicate")
        seen.add(cid)
        if check.get("status") not in ("passed", "failed", "not_run"):
            fail("check_status_invalid")
        if check.get("required") is not True:
            continue
        required += 1
        if check.get("status") != "passed" or not txt(check.get("command")) or not txt(check.get("evidence")):
            fail("required_check_failed_or_missing_evidence")
        obs = by_id.get(cid)
        if not obs:
            fail("required_check_not_observed")
            continue
        rid = obs.get("run_id")
        valid_run = isinstance(rid, int) and not isinstance(rid, bool) and rid > 0
        expected_url = f"https://github.com/{h.get('repository')}/actions/runs/{rid}" if valid_run else ""
        if (obs.get("sha") != head or obs.get("conclusion") != "success" or obs.get("source") != "github_actions"
                or not valid_run or obs.get("run_url") != expected_url or check.get("evidence") != expected_url):
            fail("check_origin_sha_or_evidence_mismatch")
    if required == 0:
        fail("required_checks_missing")
    review, independent = h.get("review"), snapshot.get("review")
    if not isinstance(review, dict) or not isinstance(independent, dict):
        fail("review_missing")
        review, independent = {}, {}
    if review.get("status") != "approved" or not txt(review.get("reviewer_agent_id")) or not txt(review.get("evidence")):
        fail("review_unapproved")
    if (review.get("reviewer_agent_id") == h.get("agent_id") or not txt(independent.get("reviewer_login"))
            or independent.get("reviewer_login") == snapshot.get("author_login")):
        fail("review_not_independent")
    if (independent.get("sha") != head or independent.get("status") != "approved"
            or independent.get("reviewer_agent_id") != review.get("reviewer_agent_id")
            or independent.get("evidence") != review.get("evidence")):
        fail("review_sha_identity_or_evidence_mismatch")
    agents = {x["role"]: x["id"] for x in manifest["agents"]}
    if len(stages) != 3:
        fail("wrong_stage_count")
    seen_agents = set()
    for i, role in enumerate(ROLES):
        if i >= len(stages) or not isinstance(stages[i], dict):
            fail("stage_missing")
            continue
        stage = stages[i]
        if stage.get("role") != role or stage.get("agent_id") != agents.get(role):
            fail("stage_order_or_identity")
        if stage.get("agent_id") in seen_agents:
            fail("stage_duplicate_identity")
        seen_agents.add(stage.get("agent_id"))
        if any(stage.get(k) != h.get(k) for k in ("task_id", "repository", "branch")):
            fail("stage_target_mismatch")
        if stage.get("sha") != (base if i == 0 else head):
            fail("stage_sha_mismatch")
        if not txt(stage.get("evidence")):
            fail("stage_evidence_missing")
        if role == "independent_review" and (stage.get("agent_id") != review.get("reviewer_agent_id") or stage.get("evidence") != review.get("evidence")):
            fail("stage_review_mismatch")
    return result(errors)


def result(errors):
    return {"decision": "blocked" if errors else "pending_external_verification",
            "can_advance": False, "dispatch_allowed": False, "production_allowed": False,
            "evidence_verified": False, "authenticated_externally": False, "failures": errors}


def main():
    p = argparse.ArgumentParser()
    for name in ("handoff", "stages", "snapshot"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    try:
        def load(path):
            if path.stat().st_size > 131072:
                raise ValueError("oversized_json")
            return json.loads(path.read_text(encoding="utf-8"))
        outcome = audit(load(args.handoff), load(args.stages), load(args.snapshot))
        code = 1 if outcome["decision"] == "blocked" else 3
    except (OSError, ValueError, TypeError, KeyError):
        outcome, code = result(["invalid_file_or_json"]), 2
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
