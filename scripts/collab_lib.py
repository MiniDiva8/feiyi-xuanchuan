"""Shared, dependency-free Git/gh helpers. No credentials are persisted by this kit."""
from __future__ import annotations
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

class CollabError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

def run(argv, cwd, *, check=True, input_text=None):
    try:
        result = subprocess.run([str(a) for a in argv], cwd=cwd, input=input_text,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise CollabError("TOOLS", f"Required command is unavailable: {argv[0]}")
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        detail = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", detail)
        raise CollabError("COMMAND", f"{argv[0]} failed ({result.returncode}): {detail[-4000:]}")
    return result

def emit(value):
    print(json.dumps(value, ensure_ascii=True, indent=None))

def valid_repo(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", value):
        raise CollabError("CONFIG", "Repository must be OWNER/ASCII-REPOSITORY; Chinese belongs in description/README.")
    return value

def normalized_path(value):
    value = value.replace("\\", "/")
    if value.startswith("/") or any(p in {"", ".", ".."} for p in value.rstrip("/").split("/")) or ":" in value:
        raise CollabError("SCOPE", f"Unsafe repository-relative path: {value!r}")
    return value

def policy_scope(policy, member, paths, allow_shared=False):
    if member not in policy["members"]:
        raise CollabError("CONFIG", "Unknown member key.")
    denied = []
    for raw in paths:
        path = normalized_path(raw)
        pieces = path.split("/")
        protected = {".git", ".aws", ".ssh", ".codex", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        basename = pieces[-1].lower()
        secret = basename == ".env" or (basename.startswith(".env.") and basename != ".env.example")
        secret = secret or any(fnmatch.fnmatch(basename, p) for p in
                               ["*.pem", "*.key", "*.pfx", "*.p12", "id_rsa*", "auth.json"])
        if protected.intersection(pieces) or secret:
            denied.append(path)
            continue
        owner = None
        for key, record in policy["members"].items():
            if any(path.startswith(prefix) for prefix in record["paths"]):
                owner = key
                break
        if owner is not None:
            if owner != member:
                denied.append(path)
            continue
        shared = any(path.startswith(p) if p.endswith("/") else path == p
                     for p in policy["shared_paths"])
        if not (shared and allow_shared):
            denied.append(path)
    if denied:
        raise CollabError("SCOPE", "Out-of-scope or protected files: " + ", ".join(denied))
    return paths

class GhClient:
    def __init__(self, root, repository):
        self.root = root
        self.repository = valid_repo(repository)

    def invoke(self, args, *, check=True, payload=None):
        return run(["gh", *args], self.root, check=check,
                   input_text=json.dumps(payload) if payload is not None else None)

    def api(self, endpoint, *, method="GET", payload=None, check=True):
        args = ["api", endpoint, "--method", method]
        if payload is not None:
            args += ["--input", "-"]
        result = self.invoke(args, check=check, payload=payload)
        if not check and result.returncode:
            return result
        try:
            return json.loads(result.stdout) if result.stdout.strip() else None
        except json.JSONDecodeError:
            raise CollabError("GITHUB", "GitHub returned a non-JSON response.")

    def actor(self):
        result = self.invoke(["api", "user", "--jq", ".login"], check=False)
        if result.returncode:
            failure = (result.stderr + result.stdout).lower()
            if any(word in failure for word in ["error connecting", "timeout", "timed out", "could not resolve", "network is unreachable", "tls handshake"]):
                raise CollabError("NETWORK", "GitHub could not be reached. Check network/sandbox access before changing login credentials.")
            raise CollabError("AUTH", "gh is not authenticated. Use your own official GitHub login, or the Cloud native GitHub/PR interface. Never copy another member's credentials.")
        return result.stdout.strip()

    def require_actor(self, login):
        actual = self.actor()
        if actual.lower() != login.lower():
            raise CollabError("IDENTITY", f"Authenticated account is {actual}; this task belongs to {login}.")
        return actual

    def private_repository(self):
        data = self.api("repos/" + self.repository)
        if data.get("full_name", "").lower() != self.repository.lower() or not data.get("private"):
            raise CollabError("VISIBILITY", "Expected private repository does not match. No write was performed.")
        return data

    def issue(self, number):
        return self.api(f"repos/{self.repository}/issues/{number}")

    def require_issue(self, number, login, allow_shared=False):
        issue = self.issue(number)
        if issue.get("pull_request") or issue.get("state") != "open":
            raise CollabError("ISSUE", "Task must be an open GitHub Issue.")
        assignees = [a["login"].lower() for a in issue.get("assignees", [])]
        if assignees != [login.lower()]:
            raise CollabError("ISSUE", "Issue must have exactly one assignee: this task's developer.")
        labels = {a["name"] if isinstance(a, dict) else a for a in issue.get("labels", [])}
        if allow_shared and "scope:shared-approved" not in labels:
            raise CollabError("ISSUE", "Shared changes need the scope:shared-approved label agreed in the Issue.")
        return issue

class Project:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1]).resolve()
        result = run(["git", "rev-parse", "--show-toplevel"], Path.cwd(), check=False)
        if result.returncode or Path(result.stdout.strip()).resolve() != self.root:
            raise CollabError("ROOT", "Run this project's scripts from this project's Git checkout; parent or unrelated repositories are refused.")
        self.policy = json.loads((self.root / "collab/team.json").read_text(encoding="utf-8"))
        valid_repo(self.policy["repository"])
        logins = [m["login"].lower() for m in self.policy["members"].values()]
        if len(logins) != 3 or len(set(logins)) != 3:
            raise CollabError("CONFIG", "Exactly three different developer logins are required.")
        for member in self.policy["members"].values():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", member["login"]):
                raise CollabError("CONFIG", "Invalid GitHub login in policy.")
            for prefix in member["paths"]:
                normalized_path(prefix)
                if not prefix.endswith("/"):
                    raise CollabError("CONFIG", "Owned paths must be directory prefixes ending in '/'.")
        self.base = self.policy["base_branch"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_-]*", self.base):
            raise CollabError("CONFIG", "Invalid base branch.")
        self.use_gh_credentials = False
        self.state = self.root / ".collab/task.json"
        self.gh = GhClient(self.root, self.policy["repository"])

    def git(self, *args, check=True):
        prefix = ["git"]
        if self.use_gh_credentials and args and args[0] in {"fetch", "push", "ls-remote"}:
            # Per-command helper only: match the checked gh actor without persisting credentials/config.
            prefix += ["-c", "credential.https://github.com.helper=",
                       "-c", "credential.https://github.com.helper=!gh auth git-credential"]
        return run([*prefix, "-C", self.root, *args], self.root, check=check)

    def branch(self):
        return self.git("branch", "--show-current").stdout.strip()

    def clean(self):
        if self.git("status", "--porcelain=v1", "--untracked-files=all").stdout:
            raise CollabError("DIRTY", "Working tree/index is not clean. Commit your task changes first; no automatic stash/reset is used.")

    def remote_is_local_bare(self):
        result = self.git("remote", "get-url", "origin", check=False)
        if result.returncode:
            return False
        value = result.stdout.strip()
        candidate = Path(value)
        if not candidate.is_absolute() or not candidate.is_dir():
            return False
        return run(["git", "--git-dir", candidate, "rev-parse", "--is-bare-repository"],
                   self.root, check=False).stdout.strip() == "true"

    def check_remote(self, offline=False):
        if offline:
            if not self.remote_is_local_bare():
                raise CollabError("OFFLINE", "Offline mode is simulation-only and requires a local bare origin. GitHub remotes cannot bypass identity/Issue checks.")
            return
        value = self.git("remote", "get-url", "origin").stdout.strip()
        parsed = urlsplit(value)
        expected = self.policy["repository"].lower()
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        if (parsed.scheme != "https" or parsed.hostname != "github.com" or
            parsed.username or parsed.password or parsed.query or parsed.fragment or path.lower() != expected):
            raise CollabError("REMOTE", "origin must be the configured GitHub repository over credential-free HTTPS.")

    def fetch(self):
        self.git("fetch", "--prune", "origin",
                 f"refs/heads/{self.base}:refs/remotes/origin/{self.base}")

    def active(self, *, online=True):
        branch = self.branch()
        if not branch.startswith("codex/") or branch in {self.base, "master", "main"}:
            raise CollabError("BRANCH", "Only your codex/<login>/issue-<number>-<slug> task branch can be changed.")
        if not self.state.is_file():
            raise CollabError("CONTEXT", "No task context. Start a new task with the start command.")
        data = json.loads(self.state.read_text(encoding="utf-8"))
        key = data.get("member")
        if key not in self.policy["members"]:
            raise CollabError("BRANCH", "Task member is not in team policy.")
        login = self.policy["members"][key]["login"]
        issue = data.get("issue")
        if not isinstance(issue, int) or issue < 1:
            raise CollabError("CONTEXT", "Task Issue must be a positive integer.")
        if data.get("branch") != branch or not branch.startswith(f"codex/{login}/issue-{issue}-"):
            raise CollabError("BRANCH", "Current branch does not belong to the selected member and Issue.")
        offline = data.get("mode") == "offline"
        self.check_remote(offline)
        if online and data.get("mode") == "online":
            self.gh.require_actor(login)
            self.use_gh_credentials = True
            self.gh.require_issue(issue, login, data.get("allow_shared", False))
        return data

    def paths(self, *diff_args, untracked=False):
        raw = self.git("diff", "--name-status", "-z", "--find-renames", *diff_args).stdout.split("\0")
        paths, index = [], 0
        while index < len(raw) and raw[index]:
            status = raw[index]
            count = 2 if status.startswith(("R", "C")) else 1
            paths.extend(raw[index+1:index+1+count])
            index += count+1
        if untracked:
            paths.extend(p for p in self.git("ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0") if p)
        return sorted(set(paths))

    def guard_files(self, data, paths):
        policy_scope(self.policy, data["member"], paths, data.get("allow_shared", False))
        for relative in paths:
            target = self.root / relative
            if target.is_symlink():
                raise CollabError("SCOPE", "Symlink changes require explicit manual review: " + relative)
            if target.is_file() and target.stat().st_size > 5*1024*1024:
                raise CollabError("SIZE", "File exceeds the 5 MiB source-file limit: " + relative)

    def checks(self):
        outcomes = []
        for argv in self.policy.get("checks", []):
            if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
                raise CollabError("CONFIG", "checks must be arrays of command arguments, not shell strings.")
            argv = [sys.executable if a == "{python}" else a for a in argv]
            result = run(argv, self.root, check=False)
            if result.returncode:
                raise CollabError("CHECKS", f"Project checks failed ({result.returncode}); no staging/commit was done.\n{(result.stdout+result.stderr)[-5000:]}")
            outcomes.append({"command": argv, "passed": True})
        return outcomes

    def inspect_merge(self):
        result = self.git("merge-tree", "--write-tree", "HEAD", f"origin/{self.base}", check=False)
        if result.returncode == 1:
            raise CollabError("CONFLICT", "Merge conflicts detected without modifying the working tree:\n" + result.stdout[-4000:])
        if result.returncode:
            raise CollabError("TOOLS", "git merge-tree failed; Git >=2.38 is required: " + result.stderr)
        behind = self.git("merge-base", "--is-ancestor", f"origin/{self.base}", "HEAD", check=False).returncode != 0
        return {"conflicts": False, "needs_sync": behind,
                "main_sha": self.git("rev-parse", f"origin/{self.base}").stdout.strip(),
                "head_sha": self.git("rev-parse", "HEAD").stdout.strip()}
