#!/usr/bin/env python3
"""Cross-check the actual pinned Factory PHP handoff gate in offline CI.

All data are synthetic fixtures. This NEVER authenticates GitHub evidence,
executes a Factory mission, or authorizes the next agent.
"""
import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from prepare_task import prepare

ROOT = Path(__file__).resolve().parents[1]


def fixture_base():
    task = json.loads((ROOT / "examples/task.example.json").read_text(encoding="utf-8"))
    _, blocked = prepare(task, "architect")
    return blocked


def verifier_result(verifier, payload):
    with tempfile.TemporaryDirectory() as root:
        file = Path(root) / "handoff.json"
        file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        process = subprocess.run(
            ["php", str(verifier), str(file)],
            capture_output=True, text=True, check=False, timeout=15,
        )
    try:
        output = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError("Factory returned no JSON verdict") from exc
    if not isinstance(output, dict):
        raise AssertionError("Factory verdict is not an object")
    return process.returncode, output


def assert_result(verifier, name, payload, exit_code, decision):
    code, output = verifier_result(verifier, payload)
    assert code == exit_code, (name, "wrong exit", code, output)
    assert output.get("decision") == decision, (name, output)
    assert output.get("can_advance") is False, (name, "unexpected advancement")
    assert output.get("evidence_verified") is False, (name, "unexpected proof")
    assert isinstance(output.get("failures"), list), (name, "failures not array")
    print(f"{name}: {decision}, exit={code}, can_advance=false, evidence_verified=false")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifier", required=True, type=Path)
    args = parser.parse_args()
    verifier = args.verifier.resolve(strict=True)
    baseline = fixture_base()
    assert_result(verifier, "generated_draft", baseline, 1, "blocked")
    valid = copy.deepcopy(baseline)
    valid.update({
        "agent_id": "factory-developer",
        "specialty": "development",
        "base_sha": "a" * 40,
        "result_sha": "b" * 40,
        "changed_files": ["integrations/vitrine/README.md"],
        "checks": [{
            "id": "test-fixture-only", "required": True, "status": "passed",
            "command": "python -m unittest", "evidence": "synthetic-ci-reference",
        }],
        "review": {
            "reviewer_agent_id": "vitrine-reality-checker",
            "status": "approved",
            "evidence": "synthetic-review-reference",
        },
        "state": "ready_for_via",
    })
    valid["authorization"]["approved_for_branch_write"] = True
    assert_result(verifier, "synthetic_metadata_only", valid, 3, "pending_external_verification")

    bad_cases = {
        "identical_shas": lambda x: x.update(result_sha=x["base_sha"]),
        "stale_review_identity": lambda x: x["review"].update(reviewer_agent_id=x["agent_id"]),
        "pending_review": lambda x: x["review"].update(status="pending"),
        "missing_review_evidence": lambda x: x["review"].update(evidence=""),
        "check_failed": lambda x: x["checks"][0].update(status="failed"),
        "check_not_run": lambda x: x["checks"][0].update(status="not_run"),
        "missing_checks": lambda x: x.update(checks=[]),
        "bad_sha_format": lambda x: x.update(result_sha="not-a-sha"),
        "main_branch": lambda x: x.update(branch="main"),
        "missing_authorization": lambda x: x["authorization"].update(approved_for_branch_write=False),
        "changed_files_missing": lambda x: x.update(changed_files=[]),
    }
    for name, mutation in bad_cases.items():
        candidate = copy.deepcopy(valid)
        mutation(candidate)
        assert_result(verifier, name, candidate, 1, "blocked")
    print("SUMMARY: 13 synthetic handoff cases passed against pinned Factory PHP verifier; no dispatch")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, AssertionError, subprocess.TimeoutExpired) as exc:
        print(f"FACTORY CONTRACT CHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
