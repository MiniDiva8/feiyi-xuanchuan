"""Behavior tests run the real CLI against temporary repositories; no GitHub writes."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def git(cwd, *args, check=True):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode:
        raise AssertionError(f"git {args}: {result.stderr}")
    return result


class GitLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="heritage-collab-test-")
        self.addCleanup(self.tmp.cleanup)
        self.area = Path(self.tmp.name)
        self.origin = self.area / "origin.git"
        subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(self.origin)],
                       check=True, capture_output=True)
        self.seed = self.area / "seed"
        self.seed.mkdir()
        git(self.seed, "init", "--initial-branch=main")
        git(self.seed, "config", "user.name", "Fixture Maintainer")
        git(self.seed, "config", "user.email", "fixture@example.invalid")
        policy = json.loads((KIT / "collab/team.json").read_text(encoding="utf-8"))
        policy["checks"] = []
        (self.seed / "collab").mkdir()
        (self.seed / "collab/team.json").write_text(json.dumps(policy), encoding="utf-8")
        (self.seed / ".gitignore").write_text(".collab/\n__pycache__/\n.env\n*.pem\n", encoding="utf-8")
        (self.seed / "scripts").mkdir()
        for script in (KIT / "scripts").glob("*.py"):
            shutil.copy2(script, self.seed / "scripts" / script.name)
        for name, value in {
            "apps/web/page.txt": "web baseline\n",
            "services/api/app.txt": "api baseline\n",
            "services/marketing-ai/worker.txt": "ai baseline\n",
            "packages/contracts/schema.txt": "contract baseline\n",
        }.items():
            path = self.seed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
        git(self.seed, "add", "--", ".")
        git(self.seed, "commit", "-m", "fixture baseline")
        git(self.seed, "remote", "add", "origin", str(self.origin))
        git(self.seed, "push", "-u", "origin", "main")
        self.clone = self.new_clone("alice")

    def new_clone(self, name):
        target = self.area / name
        subprocess.run(["git", "clone", str(self.origin), str(target)], check=True, capture_output=True)
        git(target, "config", "user.name", "Fixture Developer")
        git(target, "config", "user.email", "developer@example.invalid")
        return target

    def cli(self, *args, cwd=None):
        place = cwd or self.clone
        return subprocess.run([sys.executable, str(place / "scripts/collab.py"), *args],
                              cwd=place, capture_output=True, text=True, encoding="utf-8")

    def ok(self, result):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def refused(self, result, code):
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertIn(f"[{code}]", result.stderr)

    def begin(self, member="a", issue=1, slug="landing", *extra, cwd=None):
        result = self.cli("start", "--offline", "--member", member, "--issue", str(issue),
                          "--slug", slug, *extra, cwd=cwd)
        self.ok(result)

    def advance(self, relative, value):
        path = self.seed / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        git(self.seed, "add", "--", relative)
        git(self.seed, "commit", "-m", "advance main")
        git(self.seed, "push", "origin", "main")

    def test_start_fetches_latest_main_and_creates_member_branch(self):
        self.advance("services/api/new.txt", "new main\n")
        self.begin()
        self.assertEqual(git(self.clone, "branch", "--show-current").stdout.strip(),
                         "codex/MiniDiva8/issue-1-landing")
        self.assertEqual((self.clone / "services/api/new.txt").read_text(), "new main\n")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout,
                         git(self.clone, "rev-parse", "origin/main").stdout)

    def test_start_refuses_dirty_tree_without_stashing(self):
        path = self.clone / "apps/web/page.txt"
        path.write_text("unfinished work\n")
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.refused(self.cli("start", "--offline", "--member", "a", "--issue", "2", "--slug", "new"), "DIRTY")
        self.assertEqual(path.read_text(), "unfinished work\n")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertFalse(git(self.clone, "stash", "list").stdout.strip())

    def test_save_commits_owned_files_and_leaves_ignored_secret_untracked(self):
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("new landing\n")
        (self.clone / ".env").write_text("DUMMY_TEST_VALUE=not-a-secret\n")
        self.ok(self.cli("save", "--message", "feat: landing"))
        self.assertEqual(git(self.clone, "log", "-1", "--format=%s").stdout.strip(), "feat: landing")
        self.assertNotIn(".env", git(self.clone, "ls-files").stdout.splitlines())
        self.assertEqual((self.clone / ".env").read_text(), "DUMMY_TEST_VALUE=not-a-secret\n")

    def test_scope_violation_keeps_head_index_and_all_files(self):
        self.begin()
        before = git(self.clone, "rev-parse", "HEAD").stdout
        (self.clone / "apps/web/page.txt").write_text("own edit\n")
        (self.clone / "services/api/app.txt").write_text("other edit\n")
        self.refused(self.cli("save", "--message", "wrong scope"), "SCOPE")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(git(self.clone, "diff", "--cached", "--name-only").stdout, "")
        self.assertEqual((self.clone / "services/api/app.txt").read_text(), "other edit\n")

    def test_cross_module_rename_checks_the_old_and_new_path(self):
        self.begin()
        git(self.clone, "mv", "services/api/app.txt", "apps/web/copied.txt")
        staged_before = git(self.clone, "diff", "--cached", "--name-status").stdout
        self.refused(self.cli("save", "--message", "move foreign file"), "SCOPE")
        self.assertEqual(git(self.clone, "diff", "--cached", "--name-status").stdout, staged_before)

    def test_shared_flag_never_grants_another_members_owned_path(self):
        self.begin("a", 1, "landing", "--allow-shared")
        (self.clone / "docs/backend").mkdir(parents=True)
        (self.clone / "docs/backend/private.md").write_text("another module\n")
        self.refused(self.cli("save", "--message", "wrong docs"), "SCOPE")

    def test_shared_changes_require_explicit_approved_scope(self):
        self.begin()
        (self.clone / "packages/contracts/schema.txt").write_text("new contract\n")
        self.refused(self.cli("save", "--message", "contract"), "SCOPE")

    def test_confirmed_shared_scope_can_commit_contract(self):
        self.begin("a", 1, "landing", "--allow-shared")
        (self.clone / "packages/contracts/schema.txt").write_text("agreed contract\n")
        self.ok(self.cli("save", "--message", "feat: shared contract"))

    def test_preflight_detects_conflict_without_changing_worktree(self):
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("feature version\n")
        self.ok(self.cli("save", "--message", "feat: change page"))
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.advance("apps/web/page.txt", "main version\n")
        self.refused(self.cli("preflight"), "CONFLICT")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(git(self.clone, "status", "--porcelain").stdout, "")
        self.assertEqual((self.clone / "apps/web/page.txt").read_text(), "feature version\n")

    def test_sync_refuses_conflict_before_attempting_merge(self):
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("feature version\n")
        self.ok(self.cli("save", "--message", "feat: change page"))
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.advance("apps/web/page.txt", "main version\n")
        self.refused(self.cli("sync"), "CONFLICT")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertFalse((self.clone / ".git/MERGE_HEAD").exists())

    def test_sync_preserves_feature_commit_and_integrates_latest_main(self):
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("feature version\n")
        self.ok(self.cli("save", "--message", "feat: page"))
        old = git(self.clone, "rev-parse", "HEAD").stdout.strip()
        self.advance("services/api/new.txt", "main update\n")
        self.ok(self.cli("sync"))
        self.assertEqual(git(self.clone, "merge-base", "--is-ancestor", old, "HEAD").returncode, 0)
        self.assertEqual(git(self.clone, "merge-base", "--is-ancestor", "origin/main", "HEAD").returncode, 0)
        self.assertEqual((self.clone / "apps/web/page.txt").read_text(), "feature version\n")
        self.assertEqual((self.clone / "services/api/new.txt").read_text(), "main update\n")

    def test_save_refuses_main_branch(self):
        (self.clone / "apps/web/page.txt").write_text("no direct main commit\n")
        self.refused(self.cli("save", "--message", "bad main commit"), "BRANCH")

    def test_offline_publication_never_pushes_a_remote_branch(self):
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("local only\n")
        self.ok(self.cli("save", "--message", "feat: local"))
        self.refused(self.cli("publish", "--title", "local test"), "OFFLINE")
        refs = subprocess.run(["git", "--git-dir", str(self.origin), "for-each-ref",
                               "--format=%(refname)", "refs/heads/codex/"],
                              capture_output=True, text=True, check=True).stdout
        self.assertEqual(refs, "")

    def test_offline_mode_refuses_a_github_remote(self):
        git(self.clone, "remote", "set-url", "origin", "https://github.com/MiniDiva8/feiyi-xuanchuan.git")
        self.refused(self.cli("start", "--offline", "--member", "a", "--issue", "3", "--slug", "unsafe"), "OFFLINE")

    def test_a_second_member_cannot_save_on_the_first_members_branch(self):
        self.begin()
        context = self.clone / ".collab/task.json"
        data = json.loads(context.read_text())
        data["member"] = "b"
        context.write_text(json.dumps(data))
        (self.clone / "services/api/app.txt").write_text("wrong branch\n")
        self.refused(self.cli("save", "--message", "wrong person"), "BRANCH")

    def test_failed_project_checks_prevent_staging_and_commit(self):
        policy_path = self.clone / "collab/team.json"
        policy = json.loads(policy_path.read_text())
        policy["checks"] = [["{python}", "-c", "raise SystemExit(7)"]]
        policy_path.write_text(json.dumps(policy))
        git(self.clone, "add", "--", "collab/team.json")
        git(self.clone, "commit", "-m", "fixture failing checks")
        git(self.clone, "push", "origin", "main")
        self.begin()
        (self.clone / "apps/web/page.txt").write_text("unchecked feature\n")
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.refused(self.cli("save", "--message", "must not commit"), "CHECKS")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(git(self.clone, "diff", "--cached", "--name-only").stdout, "")


    def test_owned_rename_is_committed_as_a_rename(self):
        self.begin()
        git(self.clone, "mv", "apps/web/page.txt", "apps/web/home.txt")
        self.ok(self.cli("save", "--message", "refactor: rename owned page"))
        self.assertFalse((self.clone / "apps/web/page.txt").exists())
        self.assertEqual((self.clone / "apps/web/home.txt").read_text(), "web baseline\n")
        self.assertEqual(git(self.clone, "status", "--porcelain").stdout, "")


    def test_hidden_staged_foreign_edit_is_refused_without_mutating_index(self):
        self.begin()
        foreign = self.clone / "services/api/app.txt"
        foreign.write_text("foreign staged edit\n")
        git(self.clone, "add", "--", "services/api/app.txt")
        foreign.write_text("api baseline\n")
        (self.clone / "apps/web/page.txt").write_text("frontend change\n")
        before_head = git(self.clone, "rev-parse", "HEAD").stdout
        before_index = git(self.clone, "diff", "--cached", "--binary").stdout
        self.refused(self.cli("save", "--message", "must not leak staged edit"), "SCOPE")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before_head)
        self.assertEqual(git(self.clone, "diff", "--cached", "--binary").stdout, before_index)
        self.assertEqual(foreign.read_text(), "api baseline\n")

    def test_partially_staged_owned_file_is_preserved_for_explicit_resolution(self):
        self.begin()
        path = self.clone / "apps/web/page.txt"
        path.write_text("staged version\n")
        git(self.clone, "add", "--", "apps/web/page.txt")
        path.write_text("unstaged version\n")
        before_head = git(self.clone, "rev-parse", "HEAD").stdout
        before_index = git(self.clone, "diff", "--cached", "--binary").stdout
        self.refused(self.cli("save", "--message", "preserve partial staging"), "INDEX")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before_head)
        self.assertEqual(git(self.clone, "diff", "--cached", "--binary").stdout, before_index)
        self.assertEqual(path.read_text(), "unstaged version\n")

    def test_fetch_url_cannot_hide_unapproved_or_multiple_push_urls(self):
        import os
        sys.path.insert(0, str(KIT / "scripts"))
        from collab_lib import Project, CollabError
        approved = "https://github.com/MiniDiva8/feiyi-xuanchuan.git"
        git(self.clone, "remote", "set-url", "origin", approved)
        git(self.clone, "config", "remote.origin.pushurl", "https://github.com/example/unapproved.git")
        previous = Path.cwd()
        try:
            os.chdir(self.clone)
            project = Project(root=self.clone)
            with self.assertRaises(CollabError) as caught:
                project.check_remote()
            self.assertEqual(caught.exception.code, "REMOTE")
            git(self.clone, "config", "--unset-all", "remote.origin.pushurl")
            git(self.clone, "config", "--add", "remote.origin.pushurl", approved)
            git(self.clone, "config", "--add", "remote.origin.pushurl", "https://github.com/example/second.git")
            with self.assertRaises(CollabError):
                project.check_remote()
        finally:
            os.chdir(previous)

    def test_start_preserves_ignored_file_that_main_newly_tracks(self):
        local = self.clone / ".env"
        local.write_text("LOCAL_FIXTURE=keep\n")
        (self.seed / ".env").write_text("MAIN_FIXTURE=tracked\n")
        git(self.seed, "add", "-f", "--", ".env")
        git(self.seed, "commit", "-m", "fixture ignored collision")
        git(self.seed, "push", "origin", "main")
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.refused(self.cli("start", "--offline", "--member", "a", "--issue", "8", "--slug", "collision"), "IGNORED")
        self.assertEqual(local.read_text(), "LOCAL_FIXTURE=keep\n")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(git(self.clone, "branch", "--show-current").stdout.strip(), "main")

    def test_sync_preserves_ignored_file_that_main_newly_tracks(self):
        self.begin()
        local = self.clone / ".env"
        local.write_text("LOCAL_FIXTURE=keep\n")
        (self.seed / ".env").write_text("MAIN_FIXTURE=tracked\n")
        git(self.seed, "add", "-f", "--", ".env")
        git(self.seed, "commit", "-m", "fixture ignored collision")
        git(self.seed, "push", "origin", "main")
        before = git(self.clone, "rev-parse", "HEAD").stdout
        self.refused(self.cli("sync"), "IGNORED")
        self.assertEqual(local.read_text(), "LOCAL_FIXTURE=keep\n")
        self.assertEqual(git(self.clone, "rev-parse", "HEAD").stdout, before)
        self.assertFalse((self.clone / ".git/MERGE_HEAD").exists())


if __name__ == "__main__":
    unittest.main()
