#!/usr/bin/env python3
"""Read-only GitHub PR and CI policy checks. No merge operation is implemented."""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from collab_lib import CollabError, Project, emit, policy_scope, repository_visibility, scope_mode

def branch_task(branch, policy):
    match = re.fullmatch(r"codex/([A-Za-z0-9-]+)/issue-([1-9][0-9]*)-([a-z0-9][a-z0-9-]{0,63})", branch)
    if not match:
        raise CollabError("BRANCH", "PR branch must be codex/<login>/issue-<number>-<slug>.")
    login, number = match.group(1), int(match.group(2))
    matches = [key for key, value in policy["members"].items() if value["login"].lower() == login.lower()]
    if len(matches) != 1:
        raise CollabError("BRANCH", "PR branch developer is not one of the three configured members.")
    return matches[0], number

def evaluate_pr(pr, checks, reviews, current_main_sha, policy, *, up_to_date=False, shared_scope=False):
    """Pure decision on a snapshot. Ready is evidence for human review, not an authorization to merge."""
    reasons = []
    if pr.get("state") != "open":
        reasons.append("PR is not open")
    if pr.get("draft"):
        reasons.append("PR is still a draft")
    if pr.get("mergeable") is None:
        reasons.append("mergeability unknown")
    elif pr.get("mergeable") is not True:
        reasons.append("merge conflicts exist")
    if pr.get("base", {}).get("ref") != policy["base_branch"]:
        reasons.append("unexpected base branch")
    if pr.get("base", {}).get("sha") != current_main_sha:
        reasons.append("main changed during snapshot")
    if not up_to_date:
        reasons.append("branch needs latest main")
    try:
        member, _ = branch_task(pr.get("head", {}).get("ref", ""), policy)
    except CollabError:
        member = None
        reasons.append("branch does not identify an allowed developer and Issue")
    required = [c for c in checks if c.get("name") == policy["required_check"]]
    if not required:
        reasons.append("required CI check missing")
    else:
        expected_workflow = policy.get("required_workflow", "collaboration")
        pr_checks = [c for c in required
                     if c.get("event") == "pull_request" and c.get("workflow") == expected_workflow]
        if not pr_checks:
            reasons.append("required CI check is not from the expected PR workflow")
        elif not all(c.get("bucket") == "pass" for c in pr_checks):
            reasons.append("required CI check has not passed")
    if any(c.get("bucket") not in {"pass", "skipping"} for c in checks):
        reasons.append("some CI checks are pending, failed, or cancelled")
    known = {m["login"].lower() for m in policy["members"].values()}
    author = policy["members"][member]["login"].lower() if member else ""
    latest = {}
    for review in sorted(reviews, key=lambda r: (r.get("submitted_at") or "", r.get("id", 0))):
        login = review.get("user", {}).get("login", "").lower()
        if login in known and login != author and review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[login] = review
    if any(r.get("state") == "CHANGES_REQUESTED" for r in latest.values()):
        reasons.append("a teammate requested changes")
    head = pr.get("head", {}).get("sha")
    approved = sorted(login for login, r in latest.items()
                      if r.get("state") == "APPROVED" and r.get("commit_id") == head)
    required_reviews = 2 if shared_scope else 1
    if len(approved) < required_reviews:
        reasons.append(f"need {required_reviews} current-head peer approval(s)")
    return {"ready": not reasons, "reasons": reasons, "head_sha": head,
            "main_sha": current_main_sha, "approved_by": approved, "merged": False,
            "url": pr.get("html_url")}

def api_pages(gh, endpoint):
    all_items = []
    for page in range(1, 101):
        join = "&" if "?" in endpoint else "?"
        batch = gh.api(f"{endpoint}{join}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise CollabError("GITHUB", "Expected a paginated list from GitHub.")
        all_items.extend(batch)
        if len(batch) < 100:
            return all_items
    raise CollabError("GITHUB", "Pagination exceeded 10,000 entries; inspect this PR manually.")

def scope_check(project, pr):
    member, issue_number = branch_task(pr["head"]["ref"], project.policy)
    login = project.policy["members"][member]["login"]
    issue = project.gh.require_issue(issue_number, login)
    files = api_pages(project.gh, f"repos/{project.policy['repository']}/pulls/{pr['number']}/files")
    # GitHub returns at most 3,000 PR files. Never interpret a truncated scope scan as passing.
    if pr.get("changed_files", len(files)) != len(files):
        raise CollabError("SCOPE", "PR file list was truncated or changed during inspection.")
    paths = []
    for entry in files:
        paths.append(entry["filename"])
        if entry.get("previous_filename"):
            paths.append(entry["previous_filename"])
    shared = False
    try:
        policy_scope(project.policy, member, paths, False)
    except CollabError:
        if scope_mode(project.policy) == "team-wide":
            raise
        project.gh.require_issue(issue_number, login, True)
        policy_scope(project.policy, member, paths, True)
        shared = True
    return {"member": member, "issue": issue_number, "files": sorted(set(paths)),
            "shared_scope": shared, "issue_url": issue.get("html_url")}

def trusted_review_policy(project, pr):
    """Read authorization from the PR's pinned BASE, never from local HEAD."""
    sha = pr.get("base", {}).get("sha", "")
    if not re.fullmatch(r"[a-fA-F0-9]{40}", sha):
        raise CollabError("GITHUB", "PR base commit could not be verified.")
    response = project.gh.api(f"repos/{project.policy['repository']}/contents/collab/team.json?ref={sha}")
    try:
        if response.get("encoding") != "base64":
            raise ValueError("Unsupported policy encoding")
        encoded = "".join(response["content"].split())
        policy = json.loads(base64.b64decode(encoded, validate=True))
    except (KeyError, TypeError, ValueError):
        raise CollabError("GITHUB", "Trusted base policy could not be decoded; readiness was not approved.")
    if (not isinstance(policy, dict) or not isinstance(policy.get("repository"), str)
            or policy["repository"].lower() != project.policy["repository"].lower()):
        raise CollabError("REMOTE", "Trusted base policy names a different repository.")
    scope_mode(policy)
    return policy


def live_check(project, number):
    if number < 1:
        raise CollabError("INPUT", "PR number must be positive.")
    project.check_remote()
    project.gh.require_repository(repository_visibility(project.policy))
    prefix = f"repos/{project.policy['repository']}"
    pr = project.gh.api(f"{prefix}/pulls/{number}")
    authority = trusted_review_policy(project, pr)
    scope = scope_check(SimpleNamespace(policy=authority, gh=project.gh), pr)
    base_branch = authority["base_branch"]
    main = project.gh.api(f"{prefix}/branches/{base_branch}")["commit"]["sha"]
    comparison = project.gh.api(f"{prefix}/compare/{main}...{pr['head']['sha']}")
    check_response = project.gh.invoke(
        ["pr", "checks", str(number), "--repo", project.policy["repository"],
         "--json", "name,bucket,state,workflow,event,link"], check=False)
    # Exit 8 is GitHub CLI's documented "pending". A no-checks response may be exit 1.
    try:
        checks = json.loads(check_response.stdout) if check_response.stdout.strip() else []
    except json.JSONDecodeError:
        raise CollabError("GITHUB", "CI status could not be read; never assume success.")
    if check_response.returncode not in {0, 1, 8}:
        raise CollabError("GITHUB", "CI status query failed.")
    reviews = api_pages(project.gh, f"{prefix}/pulls/{number}/reviews")
    result = evaluate_pr(pr, checks, reviews, main, authority,
                         up_to_date=comparison.get("status") in {"ahead", "identical"},
                         shared_scope=scope["shared_scope"])
    # Re-read identities after gathering checks/reviews to catch a concurrent push/main update.
    latest_pr = project.gh.api(f"{prefix}/pulls/{number}")
    latest_main = project.gh.api(f"{prefix}/branches/{base_branch}")["commit"]["sha"]
    if latest_pr["head"]["sha"] != pr["head"]["sha"] or latest_main != main:
        result["ready"] = False
        result["reasons"].append("repository changed during inspection; rerun check")
    result["scope"] = scope
    result["notice"] = "Read-only snapshot; a human must review and explicitly merge on GitHub."
    return result

def ci_check():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    pr = event["pull_request"]
    project = Project(root=Path.cwd())
    # Evaluate module ownership using the BASE policy, not a policy rewritten by this PR.
    baseline = project.git("show", f"{pr['base']['sha']}:collab/team.json").stdout
    project.policy = json.loads(baseline)
    if event["repository"]["full_name"].lower() != project.policy["repository"].lower():
        raise CollabError("REMOTE", "CI repository does not match the base policy.")
    project.gh.repository = project.policy["repository"]
    fresh = project.gh.api(f"repos/{project.policy['repository']}/pulls/{pr['number']}")
    if fresh["head"]["sha"] != pr["head"]["sha"]:
        raise CollabError("STALE", "PR changed while this workflow was queued; use the newest run.")
    emit({"policy_passed": True, **scope_check(project, fresh)})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()
    try:
        if not args.ci:
            raise CollabError("INPUT", "Use collab.py check-pr --pr NUMBER, or --ci inside GitHub Actions.")
        ci_check()
    except CollabError as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        raise SystemExit(2)
