#!/usr/bin/env python3
"""Real Git three-clone simulation in a disposable local bare repository, never GitHub."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]

def command(argv, cwd=None, expected=0):
    result = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if result.returncode != expected:
        raise RuntimeError(f"Command failed ({result.returncode}, expected {expected}): {argv[0]}\n{result.stderr}\n{result.stdout}")
    return result

def git(place, *args):
    return command(["git", "-C", place, *args]).stdout.strip()

def identity(place, label):
    git(place, "config", "user.name", "Local Simulation " + label)
    git(place, "config", "user.email", "simulation-" + label + "@example.invalid")

def cli(place, *args, expected=0):
    return command([sys.executable, place / "scripts/collab.py", *args], place, expected)

def clone(area, origin, name):
    place = area / name
    command(["git", "clone", origin, place])
    identity(place, name)
    return place

def simulate():
    report = {
        "kind": "local-real-git-simulation", "github_prs_created": False,
        "cloud_accounts_tested": False, "independent_clones": 3,
        "feature_branches_pushed": 0, "simulated_integrations": 0,
        "notice": "Synthetic local identities and simulated integration are not three-person GitHub/Codex Cloud acceptance.",
    }
    with tempfile.TemporaryDirectory(prefix="heritage-team-simulation-") as dirname:
        area = Path(dirname).resolve()
        # Only the TemporaryDirectory created here is recursively cleaned by its context manager.
        assert area.parent == Path(tempfile.gettempdir()).resolve()
        assert area.name.startswith("heritage-team-simulation-")
        origin = area / "origin.git"
        command(["git", "init", "--bare", "--initial-branch=main", origin])
        seed = area / "integrator"
        seed.mkdir()
        git(seed, "init", "--initial-branch=main")
        identity(seed, "integrator")
        (seed / "scripts").mkdir()
        for path in (KIT / "scripts").glob("*.py"):
            shutil.copy2(path, seed / "scripts" / path.name)
        policy = json.loads((KIT / "collab/team.json").read_text(encoding="utf-8"))
        policy["checks"] = []  # This fixture tests Git transport; the real kit tests run separately.
        (seed / "collab").mkdir()
        (seed / "collab/team.json").write_text(json.dumps(policy), encoding="utf-8")
        (seed / ".gitignore").write_text(".collab/\n__pycache__/\n", encoding="utf-8")
        for relative in ["apps/web/README.md", "services/api/README.md",
                         "services/marketing-ai/README.md", "packages/contracts/schema.txt"]:
            p = seed / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fixture baseline\n", encoding="utf-8")
        git(seed, "add", "--", ".")
        git(seed, "commit", "-m", "simulation baseline")
        git(seed, "remote", "add", "origin", str(origin))
        git(seed, "push", "-u", "origin", "main")
        baseline = git(seed, "rev-parse", "HEAD")

        branches = []
        changed = []
        # All three clones start before any integration, so they genuinely have independent workspaces.
        for index, (key, member) in enumerate(policy["members"].items(), 1):
            place = clone(area, origin, "developer-" + key)
            cli(place, "start", "--offline", "--member", key, "--issue", str(100+index), "--slug", "smoke")
            relative = member["paths"][0] + "collaboration-smoke.txt"
            (place / relative).write_text(f"independent delivery {key}\n", encoding="utf-8")
            cli(place, "save", "--message", "test: independent delivery " + key)
            branch = git(place, "branch", "--show-current")
            git(place, "push", "-u", "origin", branch)
            branches.append({"member": key, "branch": branch, "head": git(place, "rev-parse", "HEAD")})
            changed.append(relative)
            report["feature_branches_pushed"] += 1
        report["baseline_main_sha"] = baseline
        report["branches"] = branches

        # These are local simulated PR integrations, not GitHub PRs and never the user's real main.
        for item in branches:
            git(seed, "fetch", "origin", item["branch"])
            git(seed, "merge", "--no-ff", "--no-edit", "FETCH_HEAD")
            git(seed, "push", "origin", "main")
            report["simulated_integrations"] += 1

        next_task = clone(area, origin, "next-task")
        cli(next_task, "start", "--offline", "--member", "a", "--issue", "201", "--slug", "latest-main")
        report["new_task_main_sha"] = git(next_task, "rev-parse", "HEAD")
        report["new_task_contains_all_changes"] = (
            report["new_task_main_sha"] == git(seed, "rev-parse", "HEAD")
            and all((next_task / relative).is_file() for relative in changed)
        )
        assert report["new_task_contains_all_changes"]

        one = clone(area, origin, "shared-one")
        two = clone(area, origin, "shared-two")
        cli(one, "start", "--offline", "--member", "a", "--issue", "301", "--slug", "contract-a", "--allow-shared")
        cli(two, "start", "--offline", "--member", "b", "--issue", "302", "--slug", "contract-b", "--allow-shared")
        shared = "packages/contracts/schema.txt"
        (one / shared).write_text("first shared contract\n", encoding="utf-8")
        cli(one, "save", "--message", "test: first shared contract")
        branch = git(one, "branch", "--show-current")
        git(one, "push", "origin", branch)
        git(seed, "fetch", "origin", branch)
        git(seed, "merge", "--no-ff", "--no-edit", "FETCH_HEAD")
        git(seed, "push", "origin", "main")
        (two / shared).write_text("conflicting shared contract\n", encoding="utf-8")
        cli(two, "save", "--message", "test: conflicting shared contract")
        before = git(two, "rev-parse", "HEAD")
        preflight = cli(two, "preflight", expected=2)
        syncing = cli(two, "sync", expected=2)
        report["intentional_conflict_blocked_without_changes"] = (
            "[CONFLICT]" in preflight.stderr and "[CONFLICT]" in syncing.stderr
            and git(two, "rev-parse", "HEAD") == before
            and git(two, "status", "--porcelain") == ""
            and not (two / ".git/MERGE_HEAD").exists()
            and (two / shared).read_text(encoding="utf-8") == "conflicting shared contract\n"
        )
        assert report["intentional_conflict_blocked_without_changes"]
        report["conflict_scenario_integrations"] = 1
        report["conflict_head_preserved"] = before
    report["temporary_directory_removed"] = not area.exists()
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = simulate()
    serialized = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    if args.output:
        destination = args.output.resolve()
        if destination.exists():
            raise RuntimeError("Existing report will not be overwritten; choose a new output filename.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized, encoding="utf-8")
    print(serialized, end="")

if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, AssertionError) as exc:
        print(f"Simulation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
