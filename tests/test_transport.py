"""Command-boundary tests for selecting the authenticated developer without global Git config."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collab_lib import Project

class GitAuthenticationRoutingTests(unittest.TestCase):
    def test_online_git_uses_current_gh_login_without_persisting_credentials(self):
        project = SimpleNamespace(root=Path("/project"), use_gh_credentials=True)
        captured = []
        def transport(argv, cwd, **kwargs):
            captured.append(argv)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("collab_lib.run", side_effect=transport):
            Project.git(project, "push", "origin", "codex/MiniDiva8/issue-1-demo")
        self.assertEqual(captured, [[
            "git", "-c", "credential.https://github.com.helper=",
            "-c", "credential.https://github.com.helper=!gh auth git-credential",
            "-C", Path("/project"), "push", "origin", "codex/MiniDiva8/issue-1-demo",
        ]])

    def test_native_and_local_git_do_not_override_environment_credentials(self):
        project = SimpleNamespace(root=Path("/project"), use_gh_credentials=False)
        captured = []
        def transport(argv, cwd, **kwargs):
            captured.append(argv)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("collab_lib.run", side_effect=transport):
            Project.git(project, "fetch", "origin", "main")
        self.assertEqual(captured, [["git", "-C", Path("/project"), "fetch", "origin", "main"]])

class GitHubConnectionErrorTests(unittest.TestCase):
    def test_network_failure_is_not_misreported_as_bad_credentials(self):
        from collab_lib import GhClient, CollabError
        client = GhClient(Path("/project"), "MiniDiva8/feiyi-xuanchuan")
        failed = SimpleNamespace(returncode=1, stdout="", stderr="error connecting to api.github.com")
        with patch.object(client, "invoke", return_value=failed):
            with self.assertRaises(CollabError) as caught:
                client.actor()
        self.assertEqual(caught.exception.code, "NETWORK")


if __name__ == "__main__":
    unittest.main()
