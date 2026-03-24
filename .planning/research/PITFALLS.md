# Domain Pitfalls

**Domain:** Auth + Rate Limiting + API Key Management on Existing FastAPI App
**Project:** Clip-Flow — Mago Mestre pipeline
**Researched:** 2026-03-23
**Confidence:** HIGH (grounded in actual codebase analysis)

---

## Critical Pitfalls

Mistakes that cause rewrites, security incidents, or production pipeline stoppages.

---

### Pitfall 1: CORS Wildcard Breaks When Credentials Are Added

**What goes wrong:** `app.py` currently has `allow_origins=["*"]` with `allow_credentials=True`. This combination is already invalid per the CORS spec — browsers reject credentialed requests to wildcard origins. Adding JWT auth (which requires `Authorization` headers or cookies) will surface this latent bug immediately: the Next.js 15 frontend will silently fail all authenticated API calls.

**Why it happens:** The wildcard was added for development convenience before auth existed. With no auth, no credentials are ever sent, so the invalid config never fires. The moment a `Bearer` token is attached, browsers enforce the CORS spec.

**Consequences:** Every authenticated route returns a CORS error in the browser. Not a 401 — a network error. Very hard to diagnose if you don't know to look here first.

**Prevention:**
1. Before adding any auth middleware, change `allow_origins` in `app.py` to an explicit list: `["http://localhost:3000", "http://127.0.0.1:3000"]`
2. Keep `allow_credentials=True`
3. Add `allow_headers=["Authorization", "Content-Type"]` explicitly

**Detection:** Open browser devtools → Network tab → any API call shows `Access-Control-Allow-Origin` as `*` but the request includes `Authorization`. Console shows: `"The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*'"`

**Phase:** Must be fixed before implementing any auth — Phase 1 / first task.

---

### Pitfall 2: Retrofitting Auth Across 50+ Routes — The Missed Route

**What goes wrong:** The app has 9 router modules (`generation`, `jobs`, `themes`, `pipeline`, `content`, `agents`, `drive`, `characters`, `publishing`) plus an inline `/llm/status` route on the app root. Adding a FastAPI `Depends(get_current_user)` to each route individually means one missed route becomes an unauthenticated endpoint in production.

**Why it happens:** Developers add auth to the routes they actively test. The `/drive/*` endpoint serving generated images, `/agents` listing agent status, `/llm/status`, and background-task status polling routes are easy to forget. Each route file needs to be audited independently.

**Consequences:** Content leakage (generated images publicly accessible), pipeline status readable without auth, agent configuration exposed.

**Prevention:**
1. Apply auth at the **router level**, not the individual route level — add `dependencies=[Depends(get_current_user)]` to the `APIRouter()` constructor in each route file
2. Maintain an explicit whitelist of public routes (`/docs`, `/openapi.json`, `/health`, `POST /auth/login`, `POST /auth/register`) — everything else is auth-required by default
3. Add an integration test that scans all registered routes and asserts each one either has auth dependency or is on the whitelist

**Detection:** Run `python -c "from src.api.app import app; [print(r.path, r.dependencies) for r in app.routes]"` — any route with empty dependencies that is not on the public whitelist is a leak.

**Phase:** Phase with auth implementation. Do not defer the route audit.

---

### Pitfall 3: Gemini API 400 Error — Model Name vs. API Key Issue

**What goes wrong:** `gemini_client.py` defines `MODELOS_IMAGEM` as `["gemini-2.5-flash-image", "gemini-2.0-flash-exp-image-generation", "gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"]`. None of these are confirmed valid model IDs for the Imagen/image generation API. The actual Gemini image generation model (as of early 2026) is `imagen-3.0-generate-002` accessed via the `generate_images()` method of the `google.genai` client, not `generate_content()`. Confusing text-generation model names with image-generation model names causes 400 errors that look like key problems.

**Why it happens:** Gemini's image generation API and text generation API use different client methods and different model namespaces. The `google-genai` SDK's changelog is sparse and model deprecations are announced with short notice. A 400 response body may say "model not found" or "invalid argument" — both are easy to misread as "bad API key."

**Consequences:** Wasted time rotating API keys when the real issue is an invalid model name. New key will also 400 with the same model name. Fallback to ComfyUI or static backgrounds kicks in permanently even though the API key is valid.

**Prevention:**
1. On startup, run a single cheap validation call (1x1 pixel generation or `list_models()`) to confirm the key is valid and the model name resolves, before the pipeline runs
2. Log the full 400 response body — the error detail distinguishes "invalid key" (`UNAUTHENTICATED`) from "invalid model" (`INVALID_ARGUMENT`) from "quota exceeded" (`RESOURCE_EXHAUSTED`)
3. Store the validated model name in config at runtime rather than hardcoding a list of guesses
4. Check Google AI Studio model list at: https://ai.google.dev/api/generate-content#v1beta.models (verify model names before using)

**Detection:** 400 error with `status: INVALID_ARGUMENT` and message containing "model" → model name problem, not key problem. 400 with `status: UNAUTHENTICATED` → key problem.

**Phase:** Phase with Gemini key fix (immediate, first task).

---

### Pitfall 4: Dual API Key Strategy — Free Key Drains Before Fallback Triggers

**What goes wrong:** The plan is "free key as default, paid key as fallback." If the rate limiter checks quota and switches to the paid key only at request time — without a time-aware reset window — the free key's daily limit (e.g., 500 images/day for Imagen 3) depletes by midday, paid key handles the afternoon, and next morning the free key is available again but the system remembers it as "exhausted" (no reset logic). Within days the system is permanently on the paid key.

**Why it happens:** Usage counters stored in-memory or in DB without a reset schedule tied to Google's quota window (midnight Pacific Time for Google AI Studio quotas). `datetime.now()` comparisons without timezone awareness make reset logic unreliable.

**Consequences:** Unexpected billing charges as paid key handles load that free key could cover. Over-spending on the paid tier.

**Prevention:**
1. Store `(date, count)` per key in the `api_key_usage` table — always compare against `date.today()` UTC, then reset on date change
2. Google quota windows reset at midnight Pacific — use `pytz` or Python's `zoneinfo` for correct timezone math, not naive `datetime.now()`
3. Implement a `KeySelector` class: check free key remaining quota before every image request, not just "is it over limit?"
4. Add a daily cron reset of the in-DB counter to match Google's actual reset cycle

**Detection:** Check the DB counter at 9:00 AM — if it shows yesterday's exhausted count but requests are being routed to paid key, the reset is broken.

**Phase:** Phase implementing dual-key management.

---

### Pitfall 5: Usage Tracking Writes on Every Pipeline Event — MySQL Write Storm

**What goes wrong:** The pipeline runs L1→L5 producing ~227 trend events per run, each potentially triggering a DB write if usage tracking is naively implemented (e.g., `UPDATE api_usage SET count = count + 1` per event). At 5 images per run with semaphore(5) Gemini concurrency, that is 5 concurrent `UPDATE` statements on the same row — causing lock contention on MySQL's `api_usage` table, slowing the entire pipeline.

**Why it happens:** Developers implement usage tracking as "write on every call" because it's simple and feels safe. In a single-user system the lock contention is invisible at low volume. It becomes visible at the exact moment you add concurrent Gemini calls.

**Consequences:** Pipeline run times increase 2-5x. MySQL `LOCK WAIT TIMEOUT` errors under concurrent load. Semaphore(5) for Gemini becomes effectively Semaphore(1) due to DB lock serialization.

**Prevention:**
1. Use in-memory counters (a simple `dict` or `asyncio.Lock`-protected counter) during pipeline execution, then flush to DB in a single write after the run completes
2. For the dashboard, read from DB — it doesn't need real-time accuracy, daily totals are fine
3. If real-time tracking is needed, use MySQL's `INSERT ... ON DUPLICATE KEY UPDATE count = count + 1` which is atomic without a separate SELECT
4. Index `api_usage` on `(key_id, date)` — without this index, every UPDATE scans the table

**Detection:** Enable MySQL slow query log (`long_query_time = 0.1`). If `UPDATE api_usage` appears in the slow log during pipeline runs, contention is occurring.

**Phase:** Phase implementing usage tracking.

---

### Pitfall 6: JWT Secret in Config Without Rotation Plan

**What goes wrong:** JWT tokens signed with a static secret stored in `.env` are valid forever until the secret changes. If the secret is the same across dev/prod (common when `.env` is copy-pasted), a dev token works in production. When you eventually need to invalidate all sessions (security incident, secret rotation), there is no mechanism — you must change the secret and log out every user.

**Why it happens:** JWT is stateless by design. The simplicity that makes it attractive also means there is no server-side session to invalidate.

**Consequences:** Dev tokens work in production. Compromised tokens cannot be revoked without rotating the secret (logging out all users). A leaked `.env` means all existing sessions are compromised.

**Prevention:**
1. Use different `JWT_SECRET` values in `.env` for dev vs production — never copy the same secret
2. Set short expiry (`ACCESS_TOKEN_EXPIRE_MINUTES=60`) with a refresh token flow — short-lived tokens limit exposure windows
3. Add a `jti` (JWT ID) claim and a `token_blacklist` table in MySQL to support forced logout — even if you don't use it initially, the schema slot is cheap to add now
4. Store `JWT_SECRET` as minimum 32 random bytes: `python -c "import secrets; print(secrets.token_hex(32))"`

**Detection:** If the same JWT token works in both `localhost:8000` and production — the secret is shared. Warning sign.

**Phase:** Phase implementing auth. Add the `jti` column to the users table at migration time.

---

## Moderate Pitfalls

---

### Pitfall 7: bcrypt Async Blocking — Freezing the Event Loop

**What goes wrong:** `bcrypt.hashpw()` is CPU-intensive and synchronous. Called directly in a FastAPI async route (e.g., `POST /auth/register`), it blocks the asyncio event loop for 100-300ms. During that window, no other requests are processed — the pipeline status polling, agent status checks, and concurrent pipeline runs all freeze.

**Why it happens:** FastAPI routes are async, but "async" only helps with I/O waiting. CPU-bound operations block regardless.

**Prevention:**
1. Always wrap bcrypt calls with `await asyncio.to_thread(bcrypt.hashpw, password, salt)` — same pattern already used by `SyncAgentAdapter` in this codebase
2. Alternatively use `passlib[bcrypt]` which is designed to work with FastAPI's thread pool
3. `argon2-cffi` is a faster alternative that can be run in a thread pool more efficiently

**Detection:** Add timing logs around password operations. Any hash taking >10ms in an async route is a blocking call.

**Phase:** Auth implementation phase.

---

### Pitfall 8: Next.js 15 JWT Storage — localStorage vs httpOnly Cookie

**What goes wrong:** Storing JWT in `localStorage` in the Next.js frontend (the quick/obvious approach) exposes the token to XSS attacks. Any injected script can read `localStorage` and exfiltrate the token. The memeLab frontend uses third-party UI libraries and chart components — any supply-chain compromise of those packages could harvest tokens.

**Why it happens:** `localStorage` is the first thing developers reach for because it's simple and persists across tabs. httpOnly cookies require more setup (CSRF protection, SameSite config, API to issue cookies).

**Prevention:**
1. Use httpOnly cookies with `SameSite=Strict` and `Secure` for token storage — the token is then inaccessible to JavaScript
2. For the API: FastAPI sets the cookie via `response.set_cookie(key="access_token", value=token, httponly=True, samesite="strict")`
3. If localStorage is used (acceptable for single-user local deployment): document the risk explicitly, add Content-Security-Policy headers
4. For a single-user local tool (this project's current scope), the risk is much lower — but build the pattern right since multi-tenant is the stated future direction

**Detection:** Open browser devtools → Application tab → Local Storage. If `access_token` is visible there, it is XSS-vulnerable.

**Phase:** Auth implementation phase — decision on cookie vs localStorage must be made before writing the login page.

---

### Pitfall 9: Missing Rate Limit on Auth Endpoints — Brute Force on Login

**What goes wrong:** Adding rate limiting to protect Gemini API quotas but forgetting to rate-limit `POST /auth/login` and `POST /auth/register`. A bot can attempt thousands of passwords per second against any known email address.

**Why it happens:** Developers focus rate limiting on the business logic (image generation, pipeline runs) and treat auth endpoints as "simple."

**Prevention:**
1. Apply `slowapi` (FastAPI-compatible rate limiter) to `POST /auth/login` with a tight limit: 5 requests per IP per minute
2. Add progressive delay after failed attempts (100ms, 200ms, 400ms) — this is a constant-time defense
3. Log all failed login attempts with IP address — even without blocking, this creates an audit trail

**Detection:** Check if `/auth/login` has a rate limit dependency. If not, run `ab -n 1000 -c 10 http://localhost:8000/auth/login` — if it handles 1000 requests without throttling, it is vulnerable.

**Phase:** Auth implementation phase. Rate limit auth endpoints before any other endpoint.

---

### Pitfall 10: Pipeline Background Tasks Run Without User Context

**What goes wrong:** `POST /pipeline/run` launches a `BackgroundTask` (`_run_pipeline_task`) that runs after the request returns. When auth is added, the user's identity is available during the request handler, but `BackgroundTasks` in FastAPI do not receive the dependency-injected `current_user`. The background task runs without knowing which user triggered it — making per-user usage tracking and result isolation impossible.

**Why it happens:** FastAPI's `BackgroundTasks` mechanism runs the function after the response is sent. The dependency injection context (including `Depends(get_current_user)`) has already been closed. This is a documented FastAPI limitation that surprises developers.

**Prevention:**
1. Pass `user_id` as an explicit argument to the background task function: `background_tasks.add_task(_run_pipeline_task, run_id, request, user_id=current_user.id)`
2. Do NOT pass the `AsyncSession` to background tasks — the session from the request will be closed. Create a new session inside the background task using `get_session_factory()`
3. The existing code in `_run_pipeline_task` already creates its own session (`get_session_factory()`) — follow this same pattern for user context

**Detection:** Add a debug print of `user_id` inside `_run_pipeline_task`. If it is None or the dependency injection value, the context is not being passed correctly.

**Phase:** Auth implementation phase, specifically when adding user_id to pipeline_runs table.

---

### Pitfall 11: API Key Exposure in Startup Logs (Existing Bug Compounded)

**What goes wrong:** `CONCERNS.md` already identifies that `async_orchestrator.py:217-228` (`_log_config_summary`) and `llm_client.py` can print API keys in logs. Adding a second API key (paid tier) doubles the exposure surface. If the new `GOOGLE_API_KEY_PAID` is added to `config.py` and the log-config function is not updated, the paid key will be printed in plaintext on every startup.

**Why it happens:** The existing masking oversight will be copy-pasted when adding the second key.

**Prevention:**
1. Fix the existing log masking before adding the second key: `key_display = f"...{key[-4:]}"` for any key in `_log_config_summary`
2. Add a `sanitize_config_for_log(config_dict)` helper in `config.py` that masks any key containing "KEY", "SECRET", "PASSWORD", or "TOKEN"
3. Search for both key variable names in all logging calls before shipping: `grep -r "GOOGLE_API_KEY" src/ | grep -v ".env"`

**Detection:** Start the server with a known API key, capture stdout/stderr. If the full key appears anywhere in logs, the masking is incomplete.

**Phase:** Gemini key fix phase (immediate). Fix before adding the paid key.

---

## Minor Pitfalls

---

### Pitfall 12: Alembic Migration for `users` Table — MySQL JSON Column Trap

**What goes wrong:** The existing `CONCERNS.md` documents that `TEXT`/`JSON` columns without `server_default` cause MySQL migration inconsistencies. A `users` table will likely include a `preferences` JSON column or `roles` JSON column. If written the same way as `catchphrases: Mapped[list] = mapped_column(JSON, default=list, nullable=False)` without following the established `nullable=False` + ORM `default=` pattern, the migration will fail on MySQL.

**Prevention:** Follow the established pattern in `models.py`: use `nullable=False` with `default=list` or `default=dict` at the ORM level, never `server_default` for JSON columns. Document this as the project's MySQL JSON pattern in a code comment at the top of `models.py`.

**Phase:** Auth implementation phase, during users table migration.

---

### Pitfall 13: `allow_origins=["*"]` in CORS Breaks Auth Preflight for DELETE/PATCH

**What goes wrong:** Even after fixing the credentials issue (Pitfall 1), forgetting to include `DELETE` and `PATCH` in `allow_methods` means the publishing queue (`DELETE /publishing/{id}`) and character update (`PATCH /characters/{id}`) routes will fail CORS preflight after auth is added. These routes work today because no credentials are sent, so the preflight is simpler.

**Prevention:** Set `allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` explicitly. Do not rely on `["*"]` — it is valid here but explicit is better when debugging.

**Phase:** Auth implementation phase, same fix as Pitfall 1.

---

### Pitfall 14: `sqlalchemy.exc.MissingGreenlet` Under Async Load

**What goes wrong:** If a new `users` table relationship is added to existing models (e.g., `Character` gets a `user_id` FK, `PipelineRun` gets `user_id`) and lazy-loading relationships are accessed outside an async context, SQLAlchemy raises `MissingGreenlet`. This is an existing risk in the codebase but becomes more likely when auth adds user relationships to every major table.

**Prevention:** Always use `selectinload()` or `joinedload()` for relationship loading in async contexts. Never access `character.refs` or `pipeline_run.content_packages` without explicit loading. The existing code in `characters.py` and `serializers.py` should be audited when adding `user_id` relationships.

**Phase:** Auth implementation phase, when adding user_id FKs to existing tables.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Gemini key fix (Phase 1) | 400 is model name, not key — Pitfall 3 | Log full 400 body, validate model with `list_models()` |
| Gemini key fix (Phase 1) | New paid key printed in startup logs — Pitfall 11 | Fix log masking first, then add key |
| Auth implementation | CORS blocks all credentialed requests — Pitfall 1 | Fix CORS before writing a single auth route |
| Auth implementation | One missed unprotected route — Pitfall 2 | Auth at router level, not route level; automated audit |
| Auth implementation | bcrypt blocks event loop — Pitfall 7 | `asyncio.to_thread()` wrapper |
| Auth implementation | Background tasks lose user context — Pitfall 10 | Pass `user_id` as explicit argument |
| Auth implementation | JWT shared between dev/prod — Pitfall 6 | Different secret per environment |
| Auth implementation | MySQL JSON column in users table — Pitfall 12 | Follow established ORM default pattern |
| Dual key management | Free key exhaustion not resetting — Pitfall 4 | Timezone-aware reset, timezone = Pacific |
| Usage tracking | Write storm on MySQL — Pitfall 5 | In-memory counter, flush at run end |
| Login page (Next.js) | Token stored in localStorage — Pitfall 8 | httpOnly cookie or document risk explicitly |
| Login page (Next.js) | Brute force on /auth/login — Pitfall 9 | slowapi rate limit before shipping |

---

## Sources

- Codebase analysis: `src/api/app.py`, `src/api/deps.py`, `src/api/routes/*.py`, `src/database/models.py`, `src/image_gen/gemini_client.py`, `config.py`
- `.planning/codebase/CONCERNS.md` — Security Considerations, Performance Bottlenecks sections
- `.planning/PROJECT.md` — Requirements, Key Decisions, Constraints
- Confidence: HIGH — all pitfalls are grounded in actual code patterns found in the codebase, not generic advice
- Note: Gemini API model name validation (Pitfall 3) is MEDIUM confidence — model names in `gemini_client.py` look incorrect but exact current model IDs for Imagen 3 require verification against official Google AI docs
