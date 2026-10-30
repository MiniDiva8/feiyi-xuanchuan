# Three-person GitHub + Codex Cloud Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. The user requested direct execution; do not add a plan-approval gate for authorized local work.

**Goal:** Deliver a tested, isolated, Chinese-language collaboration kit for three independent accounts.
**Architecture:** One private GitHub repository is authoritative. Python stdlib wraps Git/gh safely; isolated Cloud tasks use individual identities. PR review and human merge connect independent branches.
**Tech Stack:** Python >=3.11, Git >=2.38, GitHub CLI, GitHub Actions, Windows PowerShell/Bash.
**Spec:** docs/superpowers/specs/2026-10-30-three-person-collaboration-design.md

## Global Constraints
- Never modify the pre-existing AI创新大赛 checkout.
- Never expose/share credentials, make a public repository, auto-merge, or deploy servers.
- Only create remote repository after user approval; exact target MiniDiva8/feiyi-xuanchuan.
- Independent environments; no promise of shared filesystem or fully automatic Cloud provisioning.
- Github writes, collaboration invitations and first publication require the permissions stated in the spec.
- Tests and demo use temporary isolated repositories; their merges never touch the real project main.

## Review Focus
- Renames across ownership boundaries must inspect both old and new paths.
- A dirty tree, existing staged files, or ignored secrets must survive refusal unchanged.
- A nonconflicting stale branch still needs sync before publication; conflicts must not touch the worktree.
- No CI or unknown mergeability must never be reported as ready.
- Offline simulation must not permit bypassing identity checks on a GitHub remote.

### Task 1: Safe Git lifecycle
**Files:** scripts/collab.py, scripts/collab_lib.py; tests/test_collab.py.
**Interfaces:** CLI outputs JSON summaries; errors carry stable [ROOT], [SCOPE], [DIRTY], [CONFLICT], [OFFLINE], [BRANCH] codes. team.json owns member paths.
- [ ] Write integration tests with real temporary bare origin and clones; run and observe missing commands fail.
- [ ] Implement doctor/start/save/preflight/sync with strict root, branch, scope and clean-tree guards.
- [ ] Run integration suite; verify conflict and rename cases preserve files and HEAD.
- [ ] Commit scoped kit files only after checking actual repository root.

### Task 2: GitHub and CI gates
**Files:** scripts/github_admin.py, scripts/check_pr.py, .github/workflows/collaboration.yml; tests/test_policy.py.
**Interfaces:** GhClient uses argument arrays and JSON payload stdin; read gates return explicit reasons; default admin is dry-run.
- [ ] Write tests for Issue owner and scope, current-head reviews, fail/pending/no checks, unknown mergeability and unexpected repository visibility.
- [ ] Observe test failures, implement read-only PR gate and explicit-confirm admin operations.
- [ ] Add draft PR publication, no force push/no merge, idempotent PR reuse, board view.
- [ ] Run full suite and record actual GitHub verification boundaries.

### Task 3: Templates and onboarding
**Files:** AGENTS.md, module instructions, CODEOWNERS, Issue/PR templates, collab.ps1, collab.sh, scripts/cloud-install.sh, docs guides and README.
**Interfaces:** All examples match actual CLI flags and team.json; current Cloud UI follows official docs checked 2026-10-30.
- [ ] Create Chinese quickstart, three account guides, ownership and review rules, native-connector fallback, private-plan limits and administrator checklist.
- [ ] Run PowerShell and Bash smoke checks; validate workflow YAML and templates.
- [ ] Keep usernames and source links; do not include secrets or claims of real Cloud acceptance.

### Task 4: End-to-end simulation and delivery
**Files:** scripts/simulate_team.py, docs/verification.md; external output report.
- [ ] Run real three-clone lifecycle and intentional conflict case in temporary repositories.
- [ ] Get one fresh-context whole-kit code review; address material findings with failing regression test then green full suite.
- [ ] Record local, GitHub and Cloud evidence separately; report all unverified/manual steps.
- [ ] Publish remote setup only when its explicit consent is available; do not merge.
