# Frontend Refresh Implementation Plan

> Execute inline with superpowers:executing-plans; one independent final reviewer.

Goal: Rebuild the merchant interface around collaborator PR12, preserving all real product flows.
Architecture: Keep React/Vite and exact server APIs. Shared UI and CSS set the visual system; page components retain trusted data/actions. Pure navigation helpers support real browser history.
Spec: docs/frontend/2026-11-01-refresh-design.md
Base: 8e765d8f088e057c6da7704ebf2879c5d16e0c7f

## Constraints / review focus

- Frontend-owned paths only; collaborator service contracts unchanged.
- Workspace switch clears state; late requests/uploads cannot attach to another workspace or record.
- Missing channel metrics stay unknown; every cumulative total uses latest snapshot, no fake growth.
- Model state is configuration status, not connectivity; required approval and photo consent remain effective.
- Preserve existing tests as behavior evidence; selector updates allowed only where visible UX changes.

## Tasks

- [x] Task1: Baseline npm6tests/build and backend/AI50tests; implement tested native hash navigation, grouped accessible app shell, keyboard quick navigation; no API changes.
- [x] Task2: Rebuild overview and shared design system; clarify creation actions, real metrics, guide states; refresh login brand composition and add original decorative asset.
- [x] Task3: Refine resource/catalog/campaign/channel/analytics/publishing/settings pages; wide photo-poster designer with stable preview; preserve all async and approval invariants.
- [ ] Task4: Browser fullflow+partner preparation/photo/channel suites+async regression; responsive page/dialog checks; independent review and targeted fixes; final build/test; stage frontend-only files and publish dependent draft PR.

Files: apps/web/src/{App,styles,context}.tsx/ts/css; components/{UI,Preparation,PosterDesigner,QuickNavigation,AttachmentPreview}; pages/_; navigation.mjs and tests/navigation.test.mjs; public/images; tests/frontend/_; docs/frontend/*.

Validation: npm test && npm run build; root Python backend/AI/E2E tests with shared project venv; Playwright fresh QA database and mocked error scenarios. No live provider or merchant data.
