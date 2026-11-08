# Team-wide Access Implementation Plan

User-approved scope: all3 members can edit all code; keep PR review/testing. Execute inline, one final independent reviewer.
Spec: docs/superpowers/specs/2026-11-08-team-wide-access-design.md
Base: origin/main 2132fa30164d984e5de92c79420783ee6bd73dbd. Issue23, branch codex/MiniDiva8/issue-23-team-wide-access.

## Review Focus
- Team-wide mode never bypasses secret/path protection, identity, current-head review or required CI.
- Legacy partitioned policies remain strict; CI continues using BASE policy, not HEAD authorization.
- Public repository support validates exact configured identity and visibility; no incidental public/private mutation.
- Existing task branches and staged/untracked work remain unchanged.

## Task 1: Baseline and failing regressions
Read actual GitHub collaborators/rules, isolate worktree and run baseline unittest. Add team-wide and visibility regression tests; run and observe expected failures before implementation.

## Task 2: Implement narrow policy changes
Add validated scope_mode/visibility; update CLI/admin/readiness entry points; preserve legacy mode, peer review and credential guards. Add real Git CLI cross-module and mocked online-public lifecycle checks. Expected: new tests and full suite pass.

## Task 3: Make instructions consistent and deliver
Update root/own-module instructions, prompts, README, workflow docs, CODEOWNERS and task template to explain equal code access. Run suite and local three-clone simulation, live read-only board, independent whole-branch review and one targeted fix pass. Push own branch and draft PR to main; verify actual CI and share pending human-merge boundary.

Progress: Task1 complete (45 baseline + RED scope/visibility regressions); Task2 complete (10 new regressions GREEN); Task3 full-suite/simulation/review/publication in progress.
