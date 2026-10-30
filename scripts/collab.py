#!/usr/bin/env python3
"""Safe one-command collaboration workflows; remote writes occur only on explicit commands."""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from collab_lib import CollabError, Project, emit, run

def doctor(project, _args):
    result = {
        "repository": project.policy["repository"],
        "root": str(project.root),
        "branch": project.branch(),
        "git": project.git("--version").stdout.strip(),
        "python": sys.version.split()[0],
        "gh_installed": bool(shutil.which("gh")),
        "working_tree_clean": not bool(project.git("status", "--porcelain").stdout),
    }
    if result["gh_installed"]:
        auth = project.gh.invoke(["api", "user", "--jq", ".login"], check=False)
        result["gh_authenticated"] = auth.returncode == 0
        result["gh_login"] = auth.stdout.strip() if auth.returncode == 0 else None
    else:
        result["gh_authenticated"] = False
    emit(result)

def start(project, args):
    if args.issue < 1 or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.slug):
        raise CollabError("INPUT", "Use a positive Issue number and a lowercase ASCII slug of up to 64 characters.")
    if args.member not in project.policy["members"]:
        raise CollabError("CONFIG", "Unknown member.")
    project.clean()
    mode = "offline" if args.offline else ("native" if args.native else "online")
    project.check_remote(args.offline)
    login = project.policy["members"][args.member]["login"]
    current = project.branch()
    if current.startswith("codex/") and not current.startswith(f"codex/{login}/"):
        raise CollabError("BRANCH", "Do not switch away from another member's task branch.")
    if mode == "online":
        project.gh.require_actor(login)
        project.use_gh_credentials = True
        project.gh.private_repository()
        project.gh.require_issue(args.issue, login, args.allow_shared)
    elif mode == "native" and not args.native_issue_verified:
        raise CollabError("ISSUE", "Use the native GitHub connector to verify the open Issue and its single assignee first, then pass --native-issue-verified.")
    project.fetch()
    branch = f"codex/{login}/issue-{args.issue}-{args.slug}"
    if project.git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
        raise CollabError("BRANCH", "Branch already exists. Resume its task/context rather than recreating it.")
    project.guard_ignored_collisions(f"origin/{project.base}")
    project.git("switch", "-c", branch, f"origin/{project.base}")
    data = {
        "member": args.member, "login": login, "issue": args.issue, "branch": branch,
        "mode": mode, "allow_shared": args.allow_shared,
        "base_sha": project.git("rev-parse", "HEAD").stdout.strip(),
    }
    project.state.parent.mkdir(exist_ok=True)
    project.state.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    emit({**data, "notice": "Native mode relies on the connector's Issue verification and CI; offline is local simulation only."})

def save(project, args):
    data = project.active()
    staged = set(project.paths("--cached", "HEAD"))
    working = set(project.paths(untracked=True))
    paths = sorted(staged | working)
    if not paths:
        emit({"changed": False, "message": "No changes to commit."})
        return
    project.guard_files(data, paths)
    partial = staged.intersection(working)
    if partial:
        raise CollabError("INDEX", "Files have both staged and unstaged changes. Inspect and resolve staging explicitly; nothing was changed: " + ", ".join(sorted(partial)))
    identity = project.git("var", "GIT_AUTHOR_IDENT", check=False)
    if identity.returncode:
        raise CollabError("IDENTITY", "Set your own repository-local Git user.name and user.email first; no global identity is changed by this kit.")
    checks = project.checks()
    # Explicit path list only. Never git add -A, auto-stash, reset, or force push.
    stage_paths = [
        p for p in paths
        if (project.root / p).exists()
        or project.git("ls-files", "--error-unmatch", "--", p, check=False).returncode == 0
    ]
    if stage_paths:
        project.git("add", "--", *stage_paths)
    project.git("commit", "-m", args.message)
    emit({"commit": project.git("rev-parse", "HEAD").stdout.strip(), "files": paths, "checks": checks})

def preflight(project, args):
    data = project.active()
    project.clean()
    project.fetch()
    paths = project.paths(f"origin/{project.base}...HEAD")
    project.guard_files(data, paths)
    emit({**project.inspect_merge(), "files": paths, "member": data["member"]})

def sync(project, args):
    project.active()
    project.clean()
    project.fetch()
    inspection = project.inspect_merge()
    if inspection["needs_sync"]:
        project.guard_ignored_collisions(f"origin/{project.base}")
        project.git("merge", "--no-edit", "--no-overwrite-ignore", f"origin/{project.base}")
    emit({**inspection, "synced": True, "head_sha": project.git("rev-parse", "HEAD").stdout.strip()})

def publish(project, args):
    data = project.active(online=False)
    if data["mode"] == "offline":
        raise CollabError("OFFLINE", "Simulation tasks cannot publish GitHub PRs or push through this command.")
    project.gh.require_actor(data["login"])
    project.use_gh_credentials = True
    project.gh.private_repository()
    project.gh.require_issue(data["issue"], data["login"], data["allow_shared"])
    project.clean()
    project.fetch()
    paths = project.paths(f"origin/{project.base}...HEAD")
    project.guard_files(data, paths)
    result = project.inspect_merge()
    if result["needs_sync"]:
        raise CollabError("STALE", "main advanced. Run sync, re-run checks, then publish.")
    if not paths:
        raise CollabError("EMPTY", "There are no task changes relative to main.")
    project.checks()
    branch = project.branch()
    project.git("push", "--set-upstream", "origin", branch)
    prior = project.gh.invoke(["pr", "list", "--repo", project.policy["repository"], "--head", branch,
                              "--base", project.base, "--state", "open", "--json", "number,url"])
    existing = json.loads(prior.stdout)
    if existing:
        emit({"created": False, "pr": existing[0], "notice": "Existing PR reused; its human-edited body was preserved. No merge."})
        return
    reviewers = [m["login"] for key, m in project.policy["members"].items() if key != data["member"]]
    if not data["allow_shared"]:
        reviewers = project.policy["members"][data["member"]].get("reviewers", reviewers[:1])
    temporary = None
    try:
        if args.body_file:
            body_path = Path(args.body_file).resolve()
            if not body_path.is_file():
                raise CollabError("INPUT", "--body-file must name a readable file.")
        else:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False) as handle:
                handle.write(f"Closes #{data['issue']}\n\n## Change\n{args.title}\n\n## Scope\n")
                handle.write("\n".join("- "+p for p in paths))
                handle.write("\n\n## Validation\nConfigured project checks passed before push. See Actions for server results.\n\n## Review\nHuman review and explicit merge are required. This command never merges.\n")
                temporary = Path(handle.name)
            body_path = temporary
        cmd = ["pr", "create", "--repo", project.policy["repository"], "--base", project.base,
               "--head", branch, "--title", args.title, "--body-file", str(body_path), "--draft"]
        for login in reviewers:
            cmd += ["--reviewer", login]
        created = project.gh.invoke(cmd)
        emit({"created": True, "url": created.stdout.strip(), "draft": True, "merged": False})
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def board(project, _args):
    project.check_remote()
    project.gh.private_repository()
    issues = project.gh.invoke(["issue", "list", "--repo", project.policy["repository"], "--state", "open",
                               "--limit", "100", "--json", "number,title,assignees,labels,url"])
    prs = project.gh.invoke(["pr", "list", "--repo", project.policy["repository"], "--state", "open",
                            "--limit", "100", "--json", "number,title,headRefName,isDraft,mergeable,reviewDecision,url"])
    emit({"issues": json.loads(issues.stdout), "pull_requests": json.loads(prs.stdout),
          "limit_per_list": 100, "notice": "GitHub is authoritative. No local lockfile or shared account."})

def check_pr(project, args):
    from check_pr import live_check
    result = live_check(project, args.pr)
    emit(result)
    if not result["ready"]:
        raise CollabError("NOT_READY", "; ".join(result["reasons"]))

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    q = sub.add_parser("start")
    q.add_argument("--member", required=True, choices=["a", "b", "c"])
    q.add_argument("--issue", type=int, required=True)
    q.add_argument("--slug", required=True)
    mode = q.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Local bare-repository simulation only.")
    mode.add_argument("--native", action="store_true", help="Use Cloud native GitHub connector instead of assuming gh auth.")
    q.add_argument("--native-issue-verified", action="store_true")
    q.add_argument("--allow-shared", action="store_true")
    q = sub.add_parser("save")
    q.add_argument("--message", required=True)
    sub.add_parser("preflight")
    sub.add_parser("sync")
    q = sub.add_parser("publish")
    q.add_argument("--title", required=True)
    q.add_argument("--body-file")
    sub.add_parser("board")
    q = sub.add_parser("check-pr")
    q.add_argument("--pr", type=int, required=True)
    return p

def main():
    args = parser().parse_args()
    project = Project()
    {"doctor": doctor, "start": start, "save": save, "preflight": preflight, "sync": sync,
     "publish": publish, "board": board, "check-pr": check_pr}[args.command](project, args)

if __name__ == "__main__":
    try:
        main()
    except CollabError as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        raise SystemExit(2)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        raise SystemExit(2)
