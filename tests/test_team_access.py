"""Team-wide access keeps identity, credential, review and visibility boundaries."""
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collab_lib import CollabError, GhClient, Project, policy_scope
from check_pr import scope_check
from test_policy import TEAM
import test_collab as fixtures
from test_collab import git

class TeamWidePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = copy.deepcopy(TEAM)
        self.policy["scope_mode"] = "team-wide"

    def test_all_three_members_can_edit_all_code_and_shared_files(self):
        paths = ["apps/web/page.tsx", "services/api/main.py", "services/marketing-ai/worker.py", "packages/contracts/schema.json", "docs/backend/runbook.md", "AGENTS.md", ".github/workflows/check.yml", "new-feature/config.json"]
        for member in ["a", "b", "c"]:
            with self.subTest(member=member):
                self.assertEqual(policy_scope(self.policy, member, paths), paths)

    def test_protected_files_and_traversal_still_fail_for_every_member(self):
        paths = [".env", "services/api/.env.local", ".git/config", ".aws/credentials", ".data/platform.db", ".artifacts/session.json", "node_modules/pkg/index.js", "apps/web/../../secret", "/etc/passwd", "apps/web/auth.json"]
        for member in ["a", "b", "c"]:
            for path in paths:
                with self.subTest(member=member, path=path), self.assertRaises(CollabError):
                    policy_scope(self.policy, member, [path], True)

    def test_unknown_member_and_unknown_scope_mode_fail_closed(self):
        with self.assertRaises(CollabError):
            policy_scope(self.policy, "outsider", ["apps/web/page.tsx"])
        self.policy["scope_mode"] = "typo"
        with self.assertRaises(CollabError) as caught:
            policy_scope(self.policy, "a", ["apps/web/page.tsx"])
        self.assertEqual(caught.exception.code, "CONFIG")

    def test_teamwide_pr_does_not_need_a_cross_directory_exception(self):
        api = Mock(return_value=[{"filename": "services/api/main.py"}, {"filename": "apps/web/page.tsx"}])
        issue = Mock(return_value={"html_url": "https://github.com/example/issues/23"})
        project = SimpleNamespace(policy=self.policy, gh=SimpleNamespace(api=api, require_issue=issue))
        result = scope_check(project, {"number": 24, "changed_files": 2, "head": {"ref": "codex/MiniDiva8/issue-23-team-wide-access"}})
        self.assertFalse(result["shared_scope"])
        issue.assert_called_once_with(23, "MiniDiva8")

class RepositoryVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.client = GhClient(Path("/project"), "MiniDiva8/feiyi-xuanchuan")

    def test_explicitly_configured_public_repository_is_accepted(self):
        metadata = {"full_name": "MiniDiva8/feiyi-xuanchuan", "private": False, "visibility": "public"}
        with patch.object(self.client, "api", return_value=metadata):
            self.assertEqual(self.client.require_repository("public"), metadata)

    def test_wrong_visibility_wrong_repository_and_invalid_config_are_refused(self):
        for metadata, expected in [({"full_name": self.client.repository, "private": False}, "private"), ({"full_name": self.client.repository, "private": True}, "public"), ({"full_name": "someone/else", "private": False}, "public")]:
            with self.subTest(metadata=metadata), patch.object(self.client, "api", return_value=metadata), self.assertRaises(CollabError):
                self.client.require_repository(expected)
        with patch.object(self.client, "api") as api, self.assertRaises(CollabError):
            self.client.require_repository("pubic")
        api.assert_not_called()

    def test_unconfigured_policy_keeps_private_as_the_default(self):
        metadata = {"full_name": self.client.repository, "private": True}
        with patch.object(self.client, "api", return_value=metadata):
            self.assertEqual(self.client.require_repository(), metadata)

class TeamWideGitLifecycleTests(unittest.TestCase):
    setUpFixture = fixtures.GitLifecycleTests.setUp
    new_clone = fixtures.GitLifecycleTests.new_clone
    cli = fixtures.GitLifecycleTests.cli
    ok = fixtures.GitLifecycleTests.ok
    refused = fixtures.GitLifecycleTests.refused
    begin = fixtures.GitLifecycleTests.begin
    advance = fixtures.GitLifecycleTests.advance

    def setUp(self):
        self.setUpFixture()
        policy = json.loads((self.seed / "collab/team.json").read_text())
        policy.update(scope_mode="team-wide", visibility="public")
        self.advance("collab/team.json", json.dumps(policy))

    def test_each_member_can_save_changes_across_all_three_modules(self):
        for member in ["a", "b", "c"]:
            place = self.new_clone("teamwide-" + member)
            self.begin(member, 501, "all-code", cwd=place)
            for path in ["apps/web/page.txt", "services/api/app.txt", "services/marketing-ai/worker.txt", "packages/contracts/schema.txt"]:
                (place / path).write_text("cross-module change by " + member)
            self.ok(self.cli("save", "--message", "test: cross-module " + member, cwd=place))
            changed = git(place, "show", "--pretty=", "--name-only", "HEAD").stdout.splitlines()
            self.assertEqual(len(changed), 4)

    def test_staged_secret_is_refused_without_mutating_the_index(self):
        self.begin()
        (self.clone / ".env").write_text("DUMMY_TEST_VALUE=fixture-only")
        git(self.clone, "add", "-f", "--", ".env")
        before = git(self.clone, "diff", "--cached").stdout
        self.refused(self.cli("save", "--message", "must refuse secret"), "SCOPE")
        self.assertEqual(git(self.clone, "diff", "--cached").stdout, before)

    def test_online_start_accepts_the_configured_public_repo(self):
        import collab
        # Real Git transport uses a local bare repository; GitHub responses are mocked.
        with patch("pathlib.Path.cwd", return_value=self.clone):
            project = Project(root=self.clone)
        # Fetch the policy into the fixture before the online path checks it.
        git(self.clone, "fetch", "origin", "main")
        git(self.clone, "merge", "--ff-only", "origin/main")
        with patch("pathlib.Path.cwd", return_value=self.clone):
            project = Project(root=self.clone)
        args = SimpleNamespace(member="a", issue=501, slug="public-start", offline=False, native=False, native_issue_verified=False, allow_shared=False)
        metadata = {"full_name": project.policy["repository"], "private": False, "visibility": "public"}
        with patch.object(project, "check_remote"), patch.object(project.gh, "require_actor"), patch.object(project.gh, "require_issue"), patch.object(project.gh, "api", return_value=metadata):
            collab.start(project, args)
        self.assertEqual(project.branch(), "codex/MiniDiva8/issue-501-public-start")

if __name__ == "__main__":
    unittest.main()
