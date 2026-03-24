# Project Research Summary

**Project:** Clip-Flow — Auth, Rate Limiting & API Usage Control Milestone
**Domain:** Auth-as-infrastructure + external API quota management on an existing FastAPI + Next.js pipeline
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

This milestone adds authentication and Gemini API quota control to Clip-Flow's existing multi-agent meme pipeline. The system currently has no auth (the memeLab dashboard is fully open), a broken Gemini Image API key, and no usage tracking — meaning any quota exhaustion silently halts image generation. The recommended approach is to build auth as thin infrastructure on top of what already exists: FastAPI's `Depends()` system, SQLAlchemy 2.0 async, and MySQL. Two new Python packages (`passlib[bcrypt]`, `python-jose[cryptography]`) plus one frontend package (`js-cookie`) are all that's required. No Redis, no external auth services, no new frameworks.

The Gemini API key problem must be fixed before auth work begins. The existing `gemini_client.py` uses unverified model names for image generation — 400 errors from invalid model names look identical to 400 errors from invalid API keys, creating a diagnostic trap that has likely wasted time already. Additionally, the current `allow_origins=["*"]` CORS config is a latent bug that will surface immediately the moment any JWT token is sent with a request; this must be fixed as the very first task. Both issues are pre-conditions for any auth work to succeed.

The architecture pattern is a layered dependency injection approach: a new `routes/auth.py` module handles token issuance, `deps.py` gains a `get_current_user` dependency that all protected routes use via `Depends()`, and a `UsageAwareKeySelector` sits above the existing `GeminiImageClient` to select free vs. paid key before each image generation attempt. The key risks are a race condition in concurrent quota checking (requires atomic MySQL `UPDATE ... SET count = count + 1`) and MySQL write contention if usage is tracked per-event rather than in-memory with a flush at run end.

---

## Key Findings

### Recommended Stack

The constraint is "maintain stack" — no new frameworks, no Redis, no external auth services. The additions are minimal by design. `passlib[bcrypt]` is the explicit recommendation in FastAPI's official security docs; `python-jose[cryptography]` reuses the already-installed `cryptography>=42.0` transitive dependency. Rate limiting is implemented as a custom MySQL sliding-window counter rather than `slowapi` (which requires Redis or per-process in-memory state, both unacceptable). API key encryption uses `cryptography.Fernet` — already available, AES-128-CBC + HMAC-SHA256, stored per user in the `users` table.

**Core technologies:**
- `passlib[bcrypt] >= 1.7.4`: password hashing — FastAPI official recommendation, stable API with automatic salting
- `python-jose[cryptography] >= 3.3.0`: JWT creation and validation — reuses existing `cryptography` package, matches FastAPI docs exactly
- `FastAPI.security.OAuth2PasswordBearer`: OAuth2 password flow — built into FastAPI stdlib, appears as Authorize button in Swagger UI
- `cryptography.fernet.Fernet`: API key encryption at rest — already installed as transitive dep, symmetric encryption for `users.gemini_free_key` and `users.gemini_paid_key`
- `js-cookie >= 3.0.5` (frontend): JWT storage in httpOnly-compatible cookie — 800 bytes, persistent login across page refreshes
- Custom MySQL counter via SQLAlchemy: rate limiting without Redis — serves double duty as usage dashboard data

**New environment variables required:**
```
JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
FERNET_KEY, GOOGLE_API_KEY_PAID
GEMINI_IMAGE_DAILY_LIMIT_FREE, GEMINI_IMAGE_DAILY_LIMIT_PAID
ALLOWED_ORIGINS
```

### Expected Features

**Must have (table stakes):**
- Email + password login — open dashboard is currently unacceptable for any multi-tenant future
- JWT session tokens with persistent login (httpOnly cookie) — stateless, no server-side session store needed
- Route protection on all FastAPI API routes via `Depends(get_current_user)` — applied at router level, not per-route
- Protected pages in Next.js via `middleware.ts` — redirect unauthenticated visitors to /login
- Login page UI with error states and loading state
- Gemini API dual-tier key management (free key as default, paid key as fallback)
- Per-day API usage counter with timezone-correct daily reset
- Threshold-based fallback: free key → paid key → static backgrounds
- Usage visible in dashboard (used N/500 Imagen requests today)

**Should have (differentiators):**
- Quota budget pre-check per pipeline run (prevents mid-run failures)
- Background source indicator in generated image metadata (gemini_free / gemini_paid / static)
- Manual quota reset / override admin endpoint
- Paid-key-only mode toggle for important batch runs
- Audit log for key switches in `api_usage_logs`

**Defer to v2+:**
- Usage history chart (needs data accumulation first anyway)
- OAuth / social login
- 2FA / TOTP
- Password reset via email (requires SMTP infrastructure)
- Per-user API key management (multi-tenant concern)
- HTTP endpoint rate limiting per IP (belongs at infrastructure layer)
- Billing integration (separate Sprint 9 milestone)

### Architecture Approach

The integration follows FastAPI's existing dependency injection pattern rather than adding global ASGI middleware. A hybrid approach is used: a lightweight middleware extracts the JWT token and attaches it to `request.state`, while route-level `Depends(get_current_user)` performs the typed DB lookup and returns a `User` object. This means health/docs endpoints remain public without special configuration. On the frontend, Next.js `middleware.ts` at the Edge Runtime redirects unauthenticated visitors before any page renders. A new `UsageAwareKeySelector` class sits above the existing `GeminiImageClient` — the orchestrator never needs to know about users; it only receives a resolved `background_mode` parameter.

**Major components:**
1. `routes/auth.py` (NEW) — JWT token issuance, bcrypt verification, `/auth/login`, `/auth/me`, `/auth/refresh`
2. `deps.py` additions — `get_current_user`, `get_usage_stats` dependencies used by all protected routes
3. `users` table (NEW) — id, email, hashed_password, role, is_active, gemini_free_key (encrypted), gemini_paid_key (encrypted), active_key_tier
4. `api_usage_logs` table (NEW) — per-user per-call log, serves rate limiting + dashboard + fallback audit; composite index on `(user_id, used_at)`
5. `UsageAwareKeySelector` (NEW in `image_gen/`) — reads `api_usage_logs`, selects free/paid key, returns `KeyResult{api_key, tier, remaining}`
6. `middleware.ts` (NEW in Next.js) — Edge Runtime route protection, redirects to /login
7. `AuthContext` (NEW in Next.js) — global JWT state, auto-refresh, exposes login/logout
8. `api.ts` modification — inject `Authorization: Bearer <token>` header on every request

**Build order constraint:** DB layer → auth backend → route protection → usage tracking → dual key → frontend auth → usage dashboard. Steps 4-6 can run parallel with steps 7-8 once DB is ready.

### Critical Pitfalls

1. **CORS wildcard kills all credentialed requests** — Fix `allow_origins=["*"]` to an explicit origin list before writing a single auth route. This is the first task, not an afterthought. Current config is already invalid; auth makes it visibly broken.

2. **Gemini 400 is model name, not API key** — `gemini_client.py` lists model names that do not match the Imagen 3 API (`imagen-3.0-generate-002` via `generate_images()`, not `generate_content()`). Log the full 400 response body; `INVALID_ARGUMENT` means model name problem, `UNAUTHENTICATED` means key problem. Run `list_models()` on startup to validate.

3. **Missed unprotected route in auth retrofit** — 50+ routes across 9 modules. Apply `dependencies=[Depends(get_current_user)]` to the `APIRouter()` constructor in each route file, not to individual routes. Audit with `python -c "from src.api.app import app; [print(r.path, r.dependencies) for r in app.routes]"`.

4. **Atomic counter race condition** — Two concurrent Gemini calls both read `count=498`, both proceed, resulting in quota overrun. Use MySQL `UPDATE api_usage SET usage_count = usage_count + 1 WHERE ... RETURNING usage_count` or `SELECT ... FOR UPDATE`. This is the single most likely production bug if not handled.

5. **Daily usage counter never resets** — Storing counts without timezone-correct daily reset means the free key appears permanently exhausted after the first day of heavy use. Compare against `date.today()` UTC; note that Google's quota resets at midnight Pacific (`zoneinfo.ZoneInfo("America/Los_Angeles")`), not UTC.

6. **bcrypt blocks the asyncio event loop** — `bcrypt.hashpw()` is synchronous CPU-intensive work. Wrap with `await asyncio.to_thread(bcrypt.hashpw, ...)` — same pattern already used by `SyncAgentAdapter` in this codebase.

7. **Background pipeline tasks lose user context** — FastAPI `BackgroundTasks` run after the response is closed; the `Depends(get_current_user)` context is gone. Pass `user_id` as an explicit integer argument to `_run_pipeline_task`, not via dependency injection.

---

## Implications for Roadmap

Based on combined research, the phase structure has clear hard dependencies that dictate order.

### Phase 1: Unblock — Fix Gemini Key and CORS

**Rationale:** Nothing else can be validated until Gemini Image actually works and the API is not breaking all credentialed requests. These are pre-conditions, not features.
**Delivers:** Verified working Gemini Image API call; CORS config that allows credentials; API key startup validation
**Addresses:** Table stakes — Gemini dual-tier key management (prerequisite); FEATURES.md "Fix broken API key first" MVP recommendation
**Avoids:** Pitfall 3 (model name misdiagnosis), Pitfall 1 (CORS wildcard), Pitfall 11 (API key in startup logs)
**Tasks:**
- Fix log masking for API keys in `_log_config_summary` and `llm_client.py`
- Fix CORS `allow_origins` to explicit list; add `allow_credentials=True`, `allow_methods` including PATCH/DELETE
- Validate correct Gemini Imagen 3 model name via `list_models()`; update `MODELOS_IMAGEM` in `gemini_client.py`
- Add startup health-check call to confirm key + model combination works

### Phase 2: Auth Foundation — Backend

**Rationale:** All subsequent features depend on knowing who the current user is. DB schema must be locked in before any code that references `user_id`.
**Delivers:** Working `POST /auth/login`, `GET /auth/me`, JWT middleware, all existing routes protected
**Uses:** `passlib[bcrypt]`, `python-jose[cryptography]`, existing SQLAlchemy 2.0 async, Alembic migration 006
**Implements:** `users` table, `routes/auth.py`, `deps.py` additions, router-level `Depends(get_current_user)`
**Avoids:** Pitfall 2 (missed routes — router-level auth), Pitfall 6 (JWT secret rotation plan), Pitfall 7 (bcrypt async), Pitfall 10 (background task user context), Pitfall 12 (MySQL JSON column trap), Pitfall 14 (MissingGreenlet)

### Phase 3: Auth Frontend — Login Page and Route Protection

**Rationale:** Backend auth must be complete and testable before the frontend is wired up. Frontend auth has no internal dependencies; it is purely a consumer of the backend.
**Delivers:** Login page, AuthContext, Next.js `middleware.ts` protecting all dashboard routes, `api.ts` injecting Bearer tokens
**Uses:** `js-cookie`, Next.js 15 Edge Runtime middleware, existing `api.ts` fetch pattern
**Avoids:** Pitfall 8 (httpOnly cookie vs localStorage — decision made here), Pitfall 9 (rate limit on `/auth/login`)

### Phase 4: Quota Control — Dual Key + Usage Tracking

**Rationale:** Auth must be in place first so usage logs are associated with a `user_id`. The `api_usage_logs` table requires a `users.id` FK. This phase unlocks the core feature of the milestone: graceful Gemini quota degradation.
**Delivers:** `api_usage_logs` table, `UsageAwareKeySelector`, atomic counter, timezone-correct daily reset, fallback to static backgrounds when both keys exhausted
**Uses:** `GOOGLE_API_KEY_PAID` env var, `cryptography.Fernet` for key encryption, existing fallback chain in `image_worker.py`
**Avoids:** Pitfall 4 (daily reset timezone), Pitfall 5 (write storm — use in-memory counter with flush), atomic counter race condition (Pitfall per FEATURES.md critical note)

### Phase 5: Usage Dashboard

**Rationale:** Last because it requires data in `api_usage_logs` to display. Purely additive — does not change any existing behavior.
**Delivers:** Dashboard widget showing today's usage (free used N/500, paid used N/2000), source indicator on generated images (gemini_free / gemini_paid / static)
**Uses:** Existing Next.js dashboard, new `GET /auth/me/usage` endpoint, recharts or equivalent

### Phase Ordering Rationale

- Phases 1 and 2 have a strict dependency chain: CORS and key validity must be verified before auth routes can be tested; auth must exist before usage logs can reference `user_id`
- Phase 3 (frontend) and Phase 4 (quota) can run in parallel once Phase 2 is complete — they are independent consumers of the auth foundation
- Phase 5 requires data produced by Phase 4 and is therefore always last
- The FEATURES.md MVP recommendation aligns exactly with this order ("Fix broken API key first, then auth foundation, then frontend, then quota control")

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** Gemini Imagen 3 model names and API methods — the correct model ID and SDK call signature need verification against current Google AI docs before implementation. MEDIUM confidence on current model names.
- **Phase 4:** Exact Google AI Studio free tier limits — FEATURES.md and STACK.md both note these should be treated as configurable defaults, not hardcoded. Verify against https://ai.google.dev/pricing at implementation time.

Phases with standard patterns (skip research-phase):
- **Phase 2:** JWT auth in FastAPI is a canonical, well-documented pattern. FastAPI official docs are the implementation guide.
- **Phase 3:** Next.js 15 `middleware.ts` with JWT is a standard pattern with official docs support.
- **Phase 5:** Simple DB aggregation query + React component; no domain-specific research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries are FastAPI official recommendations. Codebase already uses passlib-compatible patterns. Only LOW confidence item is exact Gemini free tier daily limits — treat as configurable. |
| Features | HIGH | Auth + quota control is a well-understood domain. Feature list derived from direct codebase gap analysis, not speculation. Anti-features are clear and well-reasoned. |
| Architecture | HIGH | All patterns derived from direct code inspection of existing `src/api/`, `src/database/`, and `memelab/src/`. No inferences — verified against actual files. |
| Pitfalls | HIGH | Every pitfall is grounded in actual code patterns found in the codebase. One MEDIUM item: Gemini image model names (Pitfall 3) need validation against current Google docs. |

**Overall confidence:** HIGH

### Gaps to Address

- **Gemini Imagen 3 model name:** `gemini_client.py` lists model names that appear incorrect for image generation. Exact current model ID (`imagen-3.0-generate-002` or similar) must be verified against Google AI Studio docs before Phase 1 is considered complete. Do not guess — use `client.models.list()` to enumerate available models at runtime.
- **Exact free tier daily limits:** Google's Imagen 3 free tier limits cited in PROJECT.md (~500/day) should be confirmed against current pricing page before hardcoding `GEMINI_IMAGE_DAILY_LIMIT_FREE`. Store as config, not constant.
- **Google quota timezone:** Google AI Studio quotas reset at midnight Pacific Time. The `api_usage_logs` daily reset logic must use `zoneinfo.ZoneInfo("America/Los_Angeles")` for correct alignment, not UTC. This is underdocumented in Google's API docs — validate during Phase 4 implementation.

---

## Sources

### Primary (HIGH confidence)
- FastAPI Security documentation: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — python-jose, passlib, OAuth2PasswordBearer patterns
- SQLAlchemy 2.0 async docs: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html — async session, `with_for_update()`, relationship loading
- Direct codebase analysis: `src/api/app.py`, `src/api/deps.py`, `src/api/routes/*.py`, `src/database/models.py`, `src/database/session.py`, `src/image_gen/gemini_client.py`, `memelab/src/lib/api.ts`, `memelab/next.config.ts`
- `.planning/PROJECT.md` — explicit constraints ("Manter Python + FastAPI + MySQL + Next.js")
- `.planning/codebase/CONCERNS.md` — Security Considerations, Performance Bottlenecks

### Secondary (MEDIUM confidence)
- Google AI Studio pricing/quotas: https://ai.google.dev/pricing — cited limits (~500 Imagen images/day free tier) are estimates; validate at implementation time
- CORS specification behavior with `allow_credentials=True` + wildcard — well-established browser behavior, confirmed by MDN CORS docs

### Tertiary (LOW confidence)
- Gemini Imagen 3 model names — current model IDs in `gemini_client.py` appear incorrect based on SDK changelog analysis; exact valid names require verification against https://ai.google.dev/api/generate-content#v1beta.models
- Google quota reset timezone (Pacific midnight) — inferred from general Google API documentation patterns; confirm during Phase 4 implementation

---

*Research completed: 2026-03-23*
*Ready for roadmap: yes*
