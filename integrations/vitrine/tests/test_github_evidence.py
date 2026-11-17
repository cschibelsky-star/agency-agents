"""Synthetic tests of the GitHub-authenticated evidence audit policy."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_github_pr import evaluate, REQUIRED

REPO = "cschibelsky-star/agency-agents"
SHA = "a" * 40

def fixture():
    p = {"number": 1, "state": "open", "draft": False,
         "user": {"login": "developer"},
         "head": {"sha": SHA, "repo": {"full_name": REPO}}}
    r = [{"id": 100, "user": {"login": "reviewer"}, "state": "APPROVED",
          "commit_id": SHA}]
    w = [{"id": i + 1, "name": name, "head_sha": SHA,
          "event": "pull_request", "status": "completed", "conclusion": "success"}
         for i, name in enumerate(REQUIRED)]
    return p, r, w

class PolicyTests(unittest.TestCase):
    def assert_block(self, mutate, reason):
        p, r, w = copy.deepcopy(fixture())
        mutate(p, r, w)
        result = evaluate(REPO, 1, p, r, w)
        self.assertEqual(result["decision"], "blocked")
        self.assertIn(reason, result["failures"])
        self.assertIs(result["can_advance"], False)

    def test_complete_still_never_allows_dispatch(self):
        result = evaluate(REPO, 1, *fixture())
        self.assertEqual(result["decision"], "pending_via_supervision")
        for key in ("can_advance", "dispatch_allowed", "production_allowed",
                    "agent_identity_mapping_verified", "evidence_verified_by_via"):
            self.assertIs(result[key], False)

    def test_draft(self):
        self.assert_block(lambda p,r,w:p.update(draft=True),"pr_draft")

    def test_no_review(self):
        self.assert_block(lambda p,r,w:r.clear(),"no_independent_review_for_current_sha")

    def test_self_review(self):
        self.assert_block(lambda p,r,w:r[0]["user"].update(login="developer"),"no_independent_review_for_current_sha")

    def test_old_review(self):
        self.assert_block(lambda p,r,w:r[0].update(commit_id="b"*40),"no_independent_review_for_current_sha")

    def test_dismissal_overrides_approval(self):
        def mutate(p,r,w):
            r.append({"id": 200, "user": {"login":"reviewer"}, "state":"DISMISSED", "commit_id":SHA})
        self.assert_block(mutate,"no_independent_review_for_current_sha")

    def test_absent_check(self):
        self.assert_block(lambda p,r,w:w.pop(),"incomplete_workflow:"+REQUIRED[-1])

    def test_queued_check(self):
        self.assert_block(lambda p,r,w:w[0].update(status="queued",conclusion=None),"incomplete_workflow:"+REQUIRED[0])

    def test_failed_check(self):
        self.assert_block(lambda p,r,w:w[0].update(conclusion="failure"),"incomplete_workflow:"+REQUIRED[0])

    def test_stale_check(self):
        self.assert_block(lambda p,r,w:w[0].update(head_sha="b"*40),"incomplete_workflow:"+REQUIRED[0])

    def test_later_failure_overrides_old_success(self):
        def mutate(p,r,w):
            w.append({"id": 200, "name": REQUIRED[0], "head_sha": SHA,
                      "event": "pull_request", "status": "completed", "conclusion":"failure"})
        self.assert_block(mutate,"incomplete_workflow:"+REQUIRED[0])

    def test_wrong_repository(self):
        self.assert_block(lambda p,r,w:p["head"]["repo"].update(full_name="other/repo"),"wrong_repository")

    def test_pr_closed(self):
        self.assert_block(lambda p,r,w:p.update(state="closed"),"pr_not_open")

    def test_missing_author(self):
        self.assert_block(lambda p,r,w:p.update(user={}),"missing_author")

if __name__ == "__main__":
    unittest.main()
