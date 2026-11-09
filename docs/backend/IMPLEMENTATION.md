# Backend implementation and verification

## Running

Use the repository virtual environment, then from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8010
```

`GET /api/health` returns `{ "ok": true }`. If `apps/web/dist` exists, the API serves the compiled frontend and its browser routes. Unknown `/api/*` paths always return API errors, never the HTML app. `create_app(database_url=None, storage_path=None)` creates an isolated app for tests; `storage_path` is accepted for integration compatibility, while attachments are persisted in the database.

The default database is `.data/platform.db` and starts empty. Registering creates only the account, session and an empty workspace. No fake campaigns, publications or operating figures are seeded. `DATABASE_URL=postgresql+psycopg://...` selects PostgreSQL. Its driver is included; the actual PostgreSQL server path has not been exercised in this local verification. SQLAlchemy `create_all` initializes this first schema; it is not an upgrade/migration system. Back up the complete database before any later schema migration. Uploaded file bytes are part of the database backup.

Use one application process/worker for this initial implementation. Jobs run synchronously inside the initiating HTTP request with persistent running/succeeded/failed records; this is not a distributed background queue. AI I/O starts after committing job state and runs without retaining the ORM transaction. Retries atomically claim failed tasks with a conditional database update and permit at most three total attempts. Startup marks interrupted queued/running jobs failed and retryable within that cap. Per-process rate limits cover account creation/login and workspace generation; generation is limited to 30 requests/hour/workspace. They reset when the process restarts.

## Environment and trust

`SESSION_SECURE=true` requires HTTPS for browser cookies and belongs behind the TLS deployment gateway. Session cookies are HttpOnly, SameSite=Lax, expire after seven days, and are revoked on logout. Passwords use unique random salts and PBKDF2-HMAC-SHA256 with 600,000 iterations. Only hashed session tokens are stored. Mutating API calls reject cross-site fetches and untrusted Origin headers; the actual same origin is always accepted, plus comma-separated `TRUSTED_ORIGINS`. Requests without browser Origin headers are supported for authenticated local API clients.

AI configuration is read exclusively from the documented `MARKETING_AI_*` environment variables by the AI-owned module. Missing credentials produce explicitly labeled template drafts. Configured provider failures persist failed tasks and return visible errors; they never silently become successful templates. Token usage is recorded per successful task; no dollar-cost or production effectiveness claim is inferred from token counts. Secrets, provider response bodies and internal exception text are excluded from errors and settings.

## Business invariants

All private routes enforce server-side workspace membership, including individual IDs, attachments, tasks, exports and filtered analytics. Owners/editors can modify; owners/reviewers can approve or reject. Only owners add existing registered accounts as editor/reviewer; no email is sent and there is no public workspace self-enrollment.

Plans and assets create immutable content versions. An approval belongs to exactly one latest version and cannot be reused by a revision. Confirmed marketing-permitted sources, linked offerings and campaign inputs are hashed for freshness; full original source/campaign/offering data is preserved privately on each plan. Source/offer/campaign edits carry before/after audit details, and source deletions retain the deleted data in audit. Changing sources, offerings or campaign inputs invalidates old export/publication eligibility while preserving past publication records.

Sales approvals require an available product; registration approvals require an available course. Both need positive stock/seats and a real HTTP(S) conversion link. Awareness campaigns can omit an offering. Asset channels must belong to both the campaign and approved plan. Manual plan revisions are checked for nested field types, allowed channels, activity dates, budget ceiling and confirmed source references. Blocked content checks prevent approval. `PATCH /campaigns/{id}` supports complete validation of partial input and preserves identity, status and previous-round linkage, enabling the next round to adjust dates/budget before generation.

Exports require approved current plan/asset versions and fresh sources. TXT, HTML and SVG attachments escape user text; HTML/SVG have restrictive response policies. Exporting is distinct from manual publication registration. Publication links are HTTP(S) and the recorded publication fixes the actual plan/asset IDs. This product has no automatic publishing API or payment processing.

Uploads are limited to 10 MiB each and to UTF-8 TXT/CSV, PNG, JPEG and WebP. Image signatures are checked, names are sanitized, and all downloads are authenticated attachments. Executables, HTML, SVG and PDF are rejected; PDF active-content safety is not claimed. Files are not fetched or executed by the server.

Metrics validate nonnegative numeric values, integer counts, refunds not above revenue and check-ins not above registrations. CSV preflight validates all rows and associations before transactional insertion. Exact normalized duplicates are counted, while the same external ID with conflicting data becomes a row error and prevents the complete import. Manual duplicates return 409. Analytics aggregate stored input only, keep unknown-attribution revenue separate, and do not present revenue as profit or proven marketing contribution.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest tests/backend tests/e2e tests/ai -q -p no:cacheprovider
.venv\Scripts\python.exe -m black --check services/api/app tests/backend
```

Backend tests cover empty state, sessions/logout/restart, tenant ID attacks, roles, origin handling, file restrictions, immutable approval freshness, offering/campaign changes, publication history, immutable source/audit evidence, CSV validation/atomicity/conflicts/idempotency, true analytics, visible provider failure, bounded retries and a deterministic simultaneous-final-retry race. AI and end-to-end tests are maintained by their respective owners. Full repository regression and browser acceptance are reported by the controller.

Implementation follows the agreed spec/contract; no commits, push, release, deployment or external merchant actions were performed by the backend implementer.

Final scoped verification (2026-10-31): `pytest tests/backend tests/e2e tests/ai -q -p no:cacheprovider` completed with **43 passed** in 15.12 seconds (22 backend, 2 shared E2E, 19 AI). One upstream Starlette warning recommends httpx2 for its test client; current httpx tests passed. A Black check on the 11 backend implementation files plus backend tests completed cleanly. Tests used disposable SQLite databases and the real template engine; configured-provider failure was exercised through a controlled failure adapter, not through a live paid provider. Actual PostgreSQL server operation, production TLS and real provider generation remain unverified here.
