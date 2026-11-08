# 营销工作台界面优化：设计与实施计划

> For agentic workers: use the implementation tasks below and keep the entire change within apps/web/, docs/frontend/, tests/frontend/.

## Goal
以成熟营销产品的真实界面为母版，交付清爽、一致、操作完整的非遗商家工作台。用户已授权自行选择和实施，只需最终结果。

## Architecture and spec
继续使用 React 19 / TypeScript / Vite 与既有 Cookie 会话 API；不增加生产依赖，不改后端、AI 或共享契约。以 Mixpost 真实完整后台的浅灰导航、白色内容面、偏紫主操作、紧凑分组、细线面板作为全站几何和视觉母版；以 Planable 真实内容编辑、版本审核和就地预览为内容工作区母版。第三方品牌、文案、照片不进入产品资产。

## Baseline
- Issue #25，唯一负责人 MiniDiva8。
- 最新已 fetch main：2132fa30164d984e5de92c79420783ee6bd73dbd。
- 完整业务依赖 PR #22：33d913723090798bae65ed13b972c16b09fbaa5c（包含 #20/#18/#16/#14/#12）。
- 开发分支 codex/MiniDiva8/issue-25-marketing-workspace，独立 worktree marketing-ui-20261108。
- PR #24 是独立协作政策改动，本次不纳入。

## Global constraints
- Only apps/web/, docs/frontend/, tests/frontend/ are modified.
- Keep existing API fields, merchant isolation, route identity, history navigation, keyboard shortcuts, form names and accessible labels.
- Approval binds a specific version; generated content is not approved content. Revisions require review again.
- Asset body is authoritative for reading, editing and export; never render stale content.storyboard as current edited content.
- Photo rights confirmation, checks and manual-publication labels stay visible by the relevant action.
- No invented data, automatic publishing, synchronization, model success, marketing causality or missing-as-zero claims.
- No production dependencies, backend/AI/contract/config changes, secrets, runtime data or copied third-party brand/media assets.
- 375/768/1440 layouts and keyboard access must remain usable; reduced-motion preference is respected.

## Review focus
- Long names, body text and source messages must wrap; controls must remain reachable on narrow screens.
- A workspace change must not leave another merchant's current content or attachment visible.
- Loading, errors and no records must not look like confirmed zero business results.
- Content formatting must preserve every character of the authoritative body and use text rendering rather than untrusted HTML.
- Old version details and approval eligibility must not be mixed with the selected version.

## Task 1: shell, design system, overview and login
Files: apps/web/src/workspace.css, App.tsx, pages/Overview.tsx, pages/Auth.tsx; docs/frontend/2026-11-08-reference-notes.md.
- [x] Run existing frontend tests/build and service baseline; preserve failures if any.
- [x] Rewrite the existing visual layer around a light sidebar, white/gray work surfaces, 14px Chinese body, 20-28px headings, 8-12px radii, thin neutral borders and restrained purple accents. Remove decorative English eyebrows on business pages and oversized ornamental hero sections.
- [x] Keep all existing routes and named navigation entries. Use consistent header/search/workspace selection, active state and responsive mobile navigation.
- [x] Reorder overview around pending work and recent campaigns, contextual next actions and preparation. Keep financial data and AI/manual connection facts truthful, lower-priority metrics compact.
- [x] Make login use the same system with a compact branded editorial composition, retaining all auth behavior.
- [x] Build and inspect actual desktop/mobile screens; adjust observed layout defects.

## Task 2: content reading and activity workspace
Files: apps/web/src/pages/Campaigns.tsx; new components/ContentPreview.tsx, content-preview.css, content.mjs; apps/web/tests/content.test.mjs; tests/frontend/marketing_workspace_acceptance.py as needed.
Consumes: Asset.body/title/kind/checks and existing plan/asset versions; existing source evidence.
Produces: ContentPreview({body: string, kind: string}) that displays full body, with safe optional reading structure; existing edit/export remain authoritative.
- [x] Write meaningful failing tests for a pure paragraph/section utility: complete text preservation, consecutive/blank lines, CRLF and empty body; do not infer stale storyboard.
- [x] Add reusable reading presentation for long copy/scripts, readable whitespace and collapsible complete body where useful; keep all characters accessible and no HTML injection.
- [x] Group checks into clear severity-labelled feedback beside the content, preserving full level/message. Do not hide errors needed to review.
- [x] Remove redundant flow navigation and use existing working tabs with clear current context; preserve existing browser acceptance labels/actions.
- [x] Render review evidence as readable labelled entries, with safe unknown-value fallback; never display raw JSON as the only view or imply unavailable metrics.
- [x] Run unit/build and relevant browser regression.

## Task 3: poster, channels and full acceptance
Files: apps/web/src/components/PosterDesigner.tsx, pages/Channels.tsx, workspace.css; relevant tests/frontend scripts; docs/frontend/2026-11-08-verification.md.
- [x] Keep poster editor/preview parallel on desktop and clear on mobile. Use existing templates with visual selectors while retaining accessible native select, rights confirmation, explicit preview and save-new-version semantics. Outdated previews remain clearly marked and cannot masquerade as current.
- [x] Give channel cards concise latest snapshot summaries, with all existing historical data accessible and null distinct from zero.
- [x] Run all frontend unit tests, production build, service AI/backend/e2e suite and existing browser smoke/regressions. Run a full real API closed loop and actual PNG export against an isolated synthetic QA DB with no real model key.
- [x] Inspect desktop/mobile screenshots for every page and important modal, root overflow, text wrapping, keyboard focus and controls. Verify direct route/refresh/back.
- [x] Obtain independent whole-change review; fix material findings and rerun affected checks.
- [x] Record verified evidence and real limitations; stage only explicit scoped files, preserve unmerged dependencies and manual review/merge. No deployment.

## References
- https://mixpost.app/img/pages/home/home-dashboard-2026-10-2.webp
- https://mixpost.app/img/pages/home/post-2026-10-2.webp
- https://help.planable.io/hc/article_attachments/21715292673820
- https://help.planable.io/hc/article_attachments/21715306305180

## Execution ledger
- User delegated final design decisions and implementation; no additional design confirmation required.
- Native collaboration start succeeded with verified Issue #25; latest business dependency fast-forwarded on the new task branch only.

- Task 1: complete. Light product shell, overview, existing login and all component surfaces aligned to the observed references.
- Task 2: complete. Full body and version review, labelled evidence and check grouping; 17 unit tests pass, safe-content browser checks pass.
- Task 3: complete. Poster visual selection and channel history, 57 actual layout cases, real closed loop and PNG, existing mock regressions pass.
- Ruling: the workspace-wide pending reminder opens activity selection, not a default activity publication page; regression reproduced RED and passed GREEN.
- Independent review: initial one P2 corrected; final spec compliance and quality PASS.
- No real model calls, actual publishing, deployment, merge or collaborator permission changes.
