"""PR readiness is a current-state read gate; fixtures do not claim live GitHub validation."""
import copy
import importlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collab_lib import CollabError, policy_scope

HEAD = "a"*40
MAIN = "b"*40
TEAM = {
    "repository": "MiniDiva8/feiyi-xuanchuan", "base_branch": "main", "required_check": "collab-quality",
    "members": {
        "a": {"login": "MiniDiva8", "paths": ["apps/web/", "docs/frontend/", "tests/frontend/"]},
        "b": {"login": "donghaochen45-pixel", "paths": ["services/api/", "docs/backend/", "tests/backend/"]},
        "c": {"login": "zhupaifan", "paths": ["services/marketing-ai/", "docs/ai/", "tests/ai/"]},
    },
    "shared_paths": ["packages/contracts/", "docs/", "tests/"],
}

class PullRequestGateTests(unittest.TestCase):
    def setUp(self):
        try:
            self.module = importlib.import_module("check_pr")
        except ModuleNotFoundError:
            self.fail("The PR readiness gate has not been implemented.")
        self.pr = {
            "number": 1, "state": "open", "draft": False, "mergeable": True, "mergeable_state": "clean",
            "head": {"sha": HEAD, "ref": "codex/MiniDiva8/issue-1-demo"},
            "base": {"sha": MAIN, "ref": "main"}, "user": {"login": "MiniDiva8"},
            "html_url": "https://github.com/MiniDiva8/feiyi-xuanchuan/pull/1",
        }
        self.checks = [{"name": "collab-quality", "bucket": "pass", "state": "SUCCESS",
                        "workflow": "collaboration", "event": "pull_request", "link": "https://github.com/example/check/1"}]
        self.reviews = [{"id": 1, "user": {"login": "donghaochen45-pixel"}, "state": "APPROVED",
                         "commit_id": HEAD, "submitted_at": "2026-10-30T01:00:00Z"}]

    def evaluate(self, **kwargs):
        return self.module.evaluate_pr(self.pr, self.checks, self.reviews, MAIN, TEAM,
                                       up_to_date=kwargs.get("up_to_date", True),
                                       shared_scope=kwargs.get("shared_scope", False))

    def test_unknown_mergeability_is_not_ready(self):
        self.pr["mergeable"] = None
        result = self.evaluate()
        self.assertFalse(result["ready"])
        self.assertIn("mergeability unknown", result["reasons"])

    def test_current_checks_and_other_developer_review_can_be_ready(self):
        self.assertTrue(self.evaluate()["ready"])

    def test_no_checks_is_not_a_pass(self):
        self.checks = []
        result = self.evaluate()
        self.assertFalse(result["ready"])
        self.assertIn("required CI check missing", result["reasons"])

    def test_pending_check_blocks_readiness(self):
        self.checks[0].update(bucket="pending", state="IN_PROGRESS")
        self.assertFalse(self.evaluate()["ready"])

    def test_a_failed_additional_check_blocks_readiness(self):
        self.checks.append({"name": "application-test", "bucket": "fail", "state": "FAILURE",
                            "workflow": "application", "event": "pull_request", "link": "https://github.com/example/check/2"})
        self.assertFalse(self.evaluate()["ready"])

    def test_approval_of_old_head_does_not_cover_new_commits(self):
        self.reviews[0]["commit_id"] = "c"*40
        self.assertFalse(self.evaluate()["ready"])

    def test_authors_self_approval_is_not_a_peer_review(self):
        self.reviews[0]["user"]["login"] = "MiniDiva8"
        self.assertFalse(self.evaluate()["ready"])

    def test_bot_or_unknown_reviewer_does_not_replace_team_approval(self):
        self.reviews[0]["user"]["login"] = "chatgpt-codex-connector[bot]"
        self.assertFalse(self.evaluate()["ready"])

    def test_later_request_changes_overrides_earlier_approval(self):
        self.reviews.append({"id": 2, "user": {"login": "donghaochen45-pixel"}, "state": "CHANGES_REQUESTED",
                             "commit_id": HEAD, "submitted_at": "2026-10-30T02:00:00Z"})
        self.assertFalse(self.evaluate()["ready"])

    def test_shared_scope_requires_both_other_developers(self):
        self.assertFalse(self.evaluate(shared_scope=True)["ready"])
        self.reviews.append({"id": 3, "user": {"login": "zhupaifan"}, "state": "APPROVED",
                             "commit_id": HEAD, "submitted_at": "2026-10-30T03:00:00Z"})
        self.assertTrue(self.evaluate(shared_scope=True)["ready"])

    def test_draft_or_closed_pr_is_not_ready(self):
        for changes in [{"draft": True}, {"state": "closed"}, {"mergeable": False}]:
            with self.subTest(changes=changes):
                old = copy.deepcopy(self.pr)
                self.pr.update(changes)
                self.assertFalse(self.evaluate()["ready"])
                self.pr = old

    def test_main_advancing_during_snapshot_blocks_readiness(self):
        self.pr["base"]["sha"] = "d"*40
        self.assertFalse(self.evaluate()["ready"])

    def test_nonconflicting_stale_branch_still_needs_sync(self):
        self.assertFalse(self.evaluate(up_to_date=False)["ready"])

    def test_branch_cannot_claim_an_unknown_developer(self):
        self.pr["head"]["ref"] = "codex/outsider/issue-1-demo"
        self.assertFalse(self.evaluate()["ready"])

    def test_invalid_owner_path_and_traversal_are_refused(self):
        for path in ["apps/web/../../.aws/config", "/etc/passwd", "services/api/main.py", "apps/web/.env"]:
            with self.subTest(path=path), self.assertRaises(CollabError):
                policy_scope(TEAM, "a", [path], True)

if __name__ == "__main__":
    unittest.main()
