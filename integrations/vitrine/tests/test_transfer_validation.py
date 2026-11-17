"""Tests use fabricated offline fixtures; no live API/identity is authenticated."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_transfer import audit

A, B = "a" * 40, "b" * 40
REPO = "cschibelsky-star/agency-agents"
BRANCH = "feature/pilot"
URL = f"https://github.com/{REPO}/actions/runs/12345"
REVIEW = "review-reference-mock-only"


def fixture():
    h = {
        "schema_version": "1.0", "task_id": "P-1", "repository": REPO, "branch": BRANCH,
        "agent_id": "factory-developer", "specialty": "development", "objective": "offline check",
        "authorization": {"scope": "isolated", "approved_for_branch_write": True, "production_approved": False},
        "base_sha": A, "result_sha": B, "changed_files": ["some-file.md"],
        "checks": [{"id": "suite", "required": True, "status": "passed", "command": "python -m unittest", "evidence": URL}],
        "review": {"reviewer_agent_id": "vitrine-reality-checker", "status": "approved", "evidence": REVIEW},
        "risks": [], "next_owner": "VIA", "state": "ready_for_via",
    }
    def stage(role, agent, sha, evidence):
        return {"role": role, "agent_id": agent, "sha": sha, "evidence": evidence,
                "task_id": "P-1", "repository": REPO, "branch": BRANCH}
    stages = [
        stage("architecture", "vitrine-multi-agent-architect", A, "architecture-plan"),
        stage("quality_evidence", "vitrine-evidence-collector", B, URL),
        stage("independent_review", "vitrine-reality-checker", B, REVIEW),
    ]
    snapshot = {
        "task_id": "P-1", "repository": REPO, "branch": BRANCH, "base_sha": A, "result_sha": B,
        "author_agent_id": "factory-developer", "author_login": "dev-login",
        "checks": [{"id": "suite", "sha": B, "conclusion": "success",
                    "source": "github_actions", "run_id": 12345, "run_url": URL}],
        "review": {"reviewer_agent_id": "vitrine-reality-checker", "reviewer_login": "reviewer-login",
                   "status": "approved", "sha": B, "evidence": REVIEW},
    }
    return h, stages, snapshot


class TransferTests(unittest.TestCase):
    def check_fail(self, mutate, expected):
        h, stages, snap = copy.deepcopy(fixture())
        mutate(h, stages, snap)
        out = audit(h, stages, snap)
        self.assertEqual(out["decision"], "blocked")
        self.assertIn(expected, out["failures"])
        self.assertFalse(out["can_advance"])
        self.assertFalse(out["dispatch_allowed"])
        self.assertFalse(out["evidence_verified"])

    def test_consistent_claims_do_not_authorize(self):
        out = audit(*fixture())
        self.assertEqual(out["decision"], "pending_external_verification")
        for k in ("can_advance", "dispatch_allowed", "production_allowed",
                  "evidence_verified", "authenticated_externally"):
            self.assertIs(out[k], False)

    def test_draft_blocked(self):
        self.check_fail(lambda h,s,o: h.update(state="blocked"), "handoff_not_ready")

    def test_main_branch_blocked(self):
        self.check_fail(lambda h,s,o: h.update(branch="main"), "unisolated_branch")

    def test_missing_authorization(self):
        self.check_fail(lambda h,s,o: h["authorization"].update(approved_for_branch_write=False), "authorization_missing")

    def test_repository_mismatch(self):
        self.check_fail(lambda h,s,o: h.update(repository="other/repo"), "snapshot_target_or_sha")

    def test_branch_mismatch(self):
        self.check_fail(lambda h,s,o: o.update(branch="other/branch"), "snapshot_target_or_sha")

    def test_old_sha(self):
        self.check_fail(lambda h,s,o: o.update(result_sha=A), "snapshot_target_or_sha")

    def test_identical_shas(self):
        self.check_fail(lambda h,s,o: h.update(result_sha=A), "sha_invalid")

    def test_stage_removed(self):
        self.check_fail(lambda h,s,o: s.pop(), "wrong_stage_count")

    def test_stage_order(self):
        self.check_fail(lambda h,s,o: s.reverse(), "stage_order_or_identity")

    def test_stage_agent_identity(self):
        self.check_fail(lambda h,s,o: s[1].update(agent_id="fake-qa"), "stage_order_or_identity")

    def test_stage_replayed_sha(self):
        self.check_fail(lambda h,s,o: s[1].update(sha=A), "stage_sha_mismatch")

    def test_stage_wrong_task(self):
        self.check_fail(lambda h,s,o: s[1].update(task_id="P-2"), "stage_target_mismatch")

    def test_stage_evidence_absent(self):
        self.check_fail(lambda h,s,o: s[0].update(evidence=""), "stage_evidence_missing")

    def test_check_failed(self):
        self.check_fail(lambda h,s,o: h["checks"][0].update(status="failed"), "required_check_failed_or_missing_evidence")

    def test_check_not_run(self):
        self.check_fail(lambda h,s,o: h["checks"][0].update(status="not_run"), "required_check_failed_or_missing_evidence")

    def test_check_absent(self):
        self.check_fail(lambda h,s,o: o.update(checks=[]), "required_check_not_observed")

    def test_check_old_sha(self):
        self.check_fail(lambda h,s,o: o["checks"][0].update(sha=A), "check_origin_sha_or_evidence_mismatch")

    def test_check_fake_source(self):
        self.check_fail(lambda h,s,o: o["checks"][0].update(source="agent_report"), "check_origin_sha_or_evidence_mismatch")

    def test_check_bad_link(self):
        self.check_fail(lambda h,s,o: h["checks"][0].update(evidence="fake-link"), "check_origin_sha_or_evidence_mismatch")

    def test_check_duplicate(self):
        self.check_fail(lambda h,s,o: h["checks"].append(copy.deepcopy(h["checks"][0])), "check_duplicate")

    def test_self_review(self):
        self.check_fail(lambda h,s,o: h["review"].update(reviewer_agent_id="factory-developer"), "review_not_independent")

    def test_same_login(self):
        self.check_fail(lambda h,s,o: o["review"].update(reviewer_login="dev-login"), "review_not_independent")

    def test_review_old_sha(self):
        self.check_fail(lambda h,s,o: o["review"].update(sha=A), "review_sha_identity_or_evidence_mismatch")

    def test_review_evidence_mismatch(self):
        self.check_fail(lambda h,s,o: o["review"].update(evidence="other"), "review_sha_identity_or_evidence_mismatch")

    def test_review_pending(self):
        self.check_fail(lambda h,s,o: h["review"].update(status="pending"), "review_unapproved")

    def test_privileged_field(self):
        self.check_fail(lambda h,s,o: h.update(can_advance=True), "privileged_field")

    def test_optional_checks_are_not_required(self):
        self.check_fail(lambda h,s,o: h["checks"][0].update(required=False), "required_checks_missing")

    def test_invalid_input(self):
        self.assertEqual(audit({}, {}, {})["decision"], "blocked")


if __name__ == "__main__":
    unittest.main()
