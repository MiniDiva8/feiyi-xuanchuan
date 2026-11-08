#!/usr/bin/env python3
"""Explicit-confirm administrator operations. Default plan never contacts GitHub."""
import argparse
import json
import sys
from collab_lib import CollabError, Project, emit, repository_visibility, scope_mode

def plan(project):
    return {
        "repository": project.policy["repository"], "visibility": repository_visibility(project.policy),
        "operations_available": ["create", "publish-initial", "configure", "invite", "protect"],
        "collaborators": [
            {"login": m["login"], "permission": "push"}
            for m in project.policy["members"].values()
            if m["login"].lower() != project.policy["repository"].split("/")[0].lower()
        ],
        "merge_policy": {"method": "squash", "human_merge": True, "auto_merge": False},
        "required_check": project.policy["required_check"], "minimum_peer_reviews": 1,
        "shared_change_peer_reviews": 2 if scope_mode(project.policy) == "partitioned" else 1,
        "protection_notice": "Branch protection/CODEOWNERS enforcement depends on repository settings and plan. Failure is reported; configured visibility is never changed.",
        "credentials": "Every developer uses their own account. No credentials are written to this repository.",
    }

def require_confirmation(project, args):
    if not args.apply or args.confirm != project.policy["repository"]:
        raise CollabError("CONFIRM", "Remote writes require --apply --confirm " + project.policy["repository"])
    owner = project.policy["repository"].split("/")[0]
    project.gh.require_actor(owner)
    project.use_gh_credentials = True

def create(project):
    repo = project.policy["repository"]
    probe = project.gh.invoke(["api", "repos/" + repo], check=False)
    if probe.returncode == 0:
        raise CollabError("EXISTS", "Repository already exists. It was not changed; inspect it before choosing a configuration operation.")
    if "404" not in probe.stderr:
        raise CollabError("GITHUB", "Repository absence could not be confirmed; no repository was created.")
    result = project.gh.invoke(["repo", "create", repo, "--" + repository_visibility(project.policy), "--description",
                                "非遗宣传：三人独立账号协作的 AI 营销平台", "--disable-wiki"])
    metadata = project.gh.require_repository(repository_visibility(project.policy))
    emit({"created": True, "repository": metadata["full_name"], "private": metadata["private"],
          "url": metadata["html_url"], "notice": "No collaborators, code push or merges are implied by creation."})

def publish_initial(project):
    metadata = project.gh.require_repository(repository_visibility(project.policy))
    head = project.git("rev-parse", "--verify", "HEAD", check=False)
    if head.returncode:
        raise CollabError("EMPTY", "Create and review a local kit commit before first publication.")
    project.clean()
    expected = "https://github.com/" + project.policy["repository"] + ".git"
    remote = project.git("remote", "get-url", "origin", check=False)
    if remote.returncode:
        project.git("remote", "add", "origin", expected)
    project.check_remote()
    probe = project.git("ls-remote", "--heads", "origin", check=False)
    if probe.returncode:
        raise CollabError("GITHUB", "Cannot inspect remote refs; no push attempted.")
    if probe.stdout.strip():
        raise CollabError("EXISTS", "Remote already has branches. First publication refuses to overwrite an existing project.")
    project.checks()
    project.git("push", "origin", f"HEAD:refs/heads/{project.base}")
    project.gh.api("repos/" + project.policy["repository"], method="PATCH",
                   payload={"default_branch": project.base})
    project.fetch()
    emit({"published": True, "branch": project.base, "commit": head.stdout.strip(), "merged": False,
          "notice": "Initial commit published to previously empty configured repository; no existing code merged."})

def configure(project):
    project.gh.require_repository(repository_visibility(project.policy))
    project.gh.api("repos/" + project.policy["repository"], method="PATCH", payload={
        "has_issues": True, "has_wiki": False, "allow_merge_commit": False,
        "allow_squash_merge": True, "allow_rebase_merge": False, "allow_auto_merge": False,
        "delete_branch_on_merge": True,
    })
    definitions = [
        ("area:frontend", "1D76DB"), ("area:backend", "0E8A16"), ("area:ai", "5319E7"),
        ("status:ready", "C2E0C6"), ("status:in-progress", "FBCA04"), ("status:blocked", "B60205"),
        ("scope:shared-approved", "D4C5F9"),
    ]
    known = project.gh.api(f"repos/{project.policy['repository']}/labels?per_page=100")
    names = {x["name"] for x in known}
    for name, color in definitions:
        if name not in names:
            project.gh.api(f"repos/{project.policy['repository']}/labels", method="POST",
                           payload={"name": name, "color": color})
    emit({"configured": True, "auto_merge": False, "merge_method": "squash", "labels": [n for n, _ in definitions]})

def invite(project):
    project.gh.require_repository(repository_visibility(project.policy))
    repo = project.policy["repository"]
    collaborators = project.gh.api(f"repos/{repo}/collaborators?per_page=100")
    pending = project.gh.api(f"repos/{repo}/invitations?per_page=100")
    active = {x["login"].lower() for x in collaborators}
    waiting = {x["invitee"]["login"].lower() for x in pending if x.get("invitee")}
    outcomes = []
    for member in plan(project)["collaborators"]:
        login = member["login"]
        if login.lower() in active:
            outcomes.append({"login": login, "status": "already has access"})
        elif login.lower() in waiting:
            outcomes.append({"login": login, "status": "invitation already pending"})
        else:
            project.gh.api(f"repos/{repo}/collaborators/{login}", method="PUT", payload={"permission": "push"})
            outcomes.append({"login": login, "status": "invited; recipient must accept", "permission": "write"})
    emit({"collaborators": outcomes, "credentials_shared": False})

def protect(project):
    project.gh.require_repository(repository_visibility(project.policy))
    result = project.gh.invoke(
        ["api", f"repos/{project.policy['repository']}/branches/{project.base}/protection",
         "--method", "PUT", "--input", "-"], check=False, payload={
            "required_status_checks": {"strict": True, "contexts": [project.policy["required_check"]]},
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": True, "require_code_owner_reviews": True,
                "required_approving_review_count": 1,
            },
            "restrictions": None, "required_linear_history": True,
            "allow_force_pushes": False, "allow_deletions": False,
            "required_conversation_resolution": True,
        })
    if result.returncode:
        raise CollabError("PROTECTION", "GitHub did not enable branch protection. Check plan eligibility, admin permission and main existence. No privacy/billing change was made. " + result.stderr[-1000:])
    verified = project.gh.api(f"repos/{project.policy['repository']}/branches/{project.base}/protection")
    emit({"protected": True, "enforce_admins": verified.get("enforce_admins", {}).get("enabled"),
          "required_check": project.policy["required_check"], "auto_merge": False})

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["plan", "create", "publish-initial", "configure", "invite", "protect"], nargs="?", default="plan")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm")
    args = p.parse_args()
    project = Project()
    if args.operation == "plan":
        emit(plan(project))
        return
    require_confirmation(project, args)
    {"create": create, "publish-initial": publish_initial, "configure": configure,
     "invite": invite, "protect": protect}[args.operation](project)

if __name__ == "__main__":
    try:
        main()
    except CollabError as exc:
        print(f"[{exc.code}] {exc}", file=sys.stderr)
        raise SystemExit(2)
    except (OSError, ValueError, KeyError) as exc:
        print(f"[CONFIG] {exc}", file=sys.stderr)
        raise SystemExit(2)
