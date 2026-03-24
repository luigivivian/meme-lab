# Roadmap: Clip-Flow Auth, Rate Limiting & Gemini Image Fix

## Overview

This milestone adds authentication and Gemini API quota control to Clip-Flow's existing multi-agent meme pipeline. Starting from two blocking pre-conditions (broken CORS and bad Gemini model names), the work progresses through auth backend, route protection, frontend auth, and finally quota control with graceful fallback — so the pipeline never stops generating content regardless of API limits.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Pre-Conditions** - Fix CORS wildcard and Gemini model names so credentialed requests and image generation actually work
- [ ] **Phase 2: Users Table** - Add users table to MySQL via Alembic migration (DB foundation for all auth)
- [ ] **Phase 3: Auth Backend** - Register, login, JWT tokens, roles, bcrypt hashing
- [ ] **Phase 4: Route Protection** - Retrofit all 50+ API routes with JWT dependency injection
- [ ] **Phase 5: Frontend Auth Pages** - Login page, register page, AuthContext, API header injection
- [ ] **Phase 6: Frontend Route Protection** - Client-side auth guard redirecting unauthenticated visitors
- [x] **Phase 7: Usage Tracking Table** - Add api_usage table to MySQL with timezone-correct daily reset logic (completed 2026-03-24)
- [ ] **Phase 8: Atomic Counter** - Atomic usage increment, daily limit config, usage read endpoint
- [ ] **Phase 9: Dual Key Management** - UsageAwareKeySelector choosing free vs paid Gemini key
- [x] **Phase 10: Static Fallback** - Automatic fallback to static backgrounds when both keys exhausted (completed 2026-03-24)
- [ ] **Phase 11: Usage Dashboard** - Widget showing daily consumption, source indicator per image

## Phase Details

### Phase 1: Pre-Conditions
**Goal**: API accepts credentialed requests and Gemini Image calls succeed
**Depends on**: Nothing (first phase)
**Requirements**: PRE-01, PRE-02, PRE-03
**Success Criteria** (what must be TRUE):
  1. A fetch request with `credentials: "include"` from `localhost:3000` to the API returns 200 (not CORS error)
  2. A direct call to `GeminiImageClient.generate()` returns an image without a 400 error
  3. API startup logs show `"key: ***"` instead of the actual key value
  4. `GET /health` response includes Gemini model validation status
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — CORS fix, log sanitizer, test scaffold
- [x] 01-02-PLAN.md — Gemini model discovery, health endpoint

### Phase 2: Users Table
**Goal**: MySQL has a users table that can store accounts, roles, and encrypted API keys
**Depends on**: Phase 1
**Requirements**: AUTH-07
**Success Criteria** (what must be TRUE):
  1. `alembic upgrade head` runs without error and creates the `users` table
  2. The `users` table contains columns: id, email, hashed_password, role, is_active, gemini_free_key, gemini_paid_key, active_key_tier, created_at
  3. A seed admin user exists after running the migration (email from env var)
  4. Rolling back the migration (`alembic downgrade -1`) drops the table cleanly
**Plans:** 1 plan

Plans:
- [ ] 02-01-PLAN.md — User model, migration 006, seed admin, Character FK

### Phase 3: Auth Backend
**Goal**: Users can register, log in, receive JWT tokens, and refresh or invalidate their session
**Depends on**: Phase 2
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-06
**Success Criteria** (what must be TRUE):
  1. `POST /auth/register` with a new email/password creates a user and returns a 201 with no password in the response
  2. `POST /auth/login` with valid credentials returns an access token and a refresh token
  3. `POST /auth/refresh` with a valid refresh token returns a new access token without re-entering credentials
  4. `POST /auth/logout` invalidates the refresh token so a subsequent refresh returns 401
  5. Admin and user roles exist; a seed admin account is functional after migration
**Plans:** 1/2 plans executed

Plans:
- [x] 03-01-PLAN.md — RefreshToken model, migration 007, UserRepository, JWT utils, AuthService
- [x] 03-02-PLAN.md — Auth routes (/auth/*), get_current_user dependency, integration tests

### Phase 4: Route Protection
**Goal**: Every API route (except /auth/* and /health) requires a valid JWT to respond
**Depends on**: Phase 3
**Requirements**: AUTH-05
**Success Criteria** (what must be TRUE):
  1. `GET /pipeline/run` without an Authorization header returns 401
  2. `GET /pipeline/run` with a valid Bearer token returns 200 (or its normal response)
  3. `GET /health` and `POST /auth/login` return 200 without any token
  4. A script enumerating all app routes confirms every non-exempt route has `get_current_user` in its dependency chain
**Plans:** 1 plan

Plans:
- [ ] 02-01-PLAN.md — User model, migration 006, seed admin, Character FK

### Phase 5: Frontend Auth Pages
**Goal**: Users can log in and register through the memeLab UI, and all API calls carry the JWT automatically
**Depends on**: Phase 3
**Requirements**: FAUTH-01, FAUTH-02, FAUTH-04, FAUTH-05
**Success Criteria** (what must be TRUE):
  1. Visiting `/login` shows a form with email, password fields and a submit button with loading and error states
  2. Submitting valid credentials on `/login` stores the token and redirects to the dashboard
  3. Visiting `/register` shows a form; submitting it creates an account and logs the user in
  4. An authenticated fetch to any API endpoint from the browser includes the `Authorization: Bearer <token>` header automatically
  5. Calling `AuthContext.logout()` clears the stored token
**Plans:** 2 plans

Plans:
- [x] 05-01-PLAN.md — AuthContext, API header injection, AuthProvider wrapping
- [ ] 05-02-PLAN.md — Login page, Register page, visual verification
**UI hint**: yes

### Phase 6: Frontend Route Protection
**Goal**: Unauthenticated visitors cannot access any dashboard page — they are always redirected to login
**Depends on**: Phase 5
**Requirements**: FAUTH-03
**Success Criteria** (what must be TRUE):
  1. Visiting `/dashboard` without a stored token redirects to `/login` before the page renders
  2. Visiting `/login` with a valid stored token redirects to `/dashboard`
  3. The redirect happens at Edge Runtime (visible in network tab as a 307 before any HTML loads)
**Plans:** 1 plan

Plans:
- [x] 06-01-PLAN.md — Auth guard in (app) layout, authenticated-user redirect on login/register
**UI hint**: yes

### Phase 7: Usage Tracking Table
**Goal**: MySQL has an api_usage table that records per-user per-day API consumption with timezone-correct reset
**Depends on**: Phase 2
**Requirements**: QUOT-01, QUOT-07
**Success Criteria** (what must be TRUE):
  1. `alembic upgrade head` creates the `api_usage` table with columns: id, user_id (FK), service, tier, date, usage_count, status, created_at
  2. The daily reset logic uses Pacific Time (America/Los_Angeles) — a record created at 23:59 PT and another at 00:01 PT the next day are in different date buckets
  3. Rolling back the migration drops the table cleanly
**Plans:** 1/1 plans complete

Plans:
- [x] 07-01-PLAN.md — ApiUsage model, migration 008, schema tests

### Phase 8: Atomic Counter
**Goal**: API usage increments atomically without race conditions, daily limits are configurable, and usage is readable via API
**Depends on**: Phase 7
**Requirements**: QUOT-02, QUOT-03
**Success Criteria** (what must be TRUE):
  1. Ten concurrent image generation calls do not result in a usage count above 10 in `api_usage`
  2. Setting `GEMINI_IMAGE_DAILY_LIMIT_FREE=5` via env var causes the 6th call of the day to be rejected (not the 5th or 7th)
  3. `GET /auth/me/usage` returns `{used: N, limit: M, tier: "free", remaining: M-N}` for today
**Plans:** 1 plan

Plans:
- [x] 08-01-PLAN.md — UsageRepository (atomic upsert), limit config, GET /auth/me/usage endpoint, tests

### Phase 9: Dual Key Management
**Goal**: Image generation automatically uses the free Gemini key until the daily limit, then switches to the paid key
**Depends on**: Phase 8
**Requirements**: QUOT-04, QUOT-05
**Success Criteria** (what must be TRUE):
  1. When free-tier usage is below the daily limit, `UsageAwareKeySelector.resolve()` returns the free key
  2. When free-tier usage is at or above the daily limit, `UsageAwareKeySelector.resolve()` returns the paid key
  3. The key switch is logged to `api_usage` with the correct tier value (`gemini_free` or `gemini_paid`)
  4. A `GOOGLE_API_KEY_PAID` env var that differs from `GOOGLE_API_KEY` is used for paid-tier calls
**Plans:** 2 plans

Plans:
- [x] 09-01-PLAN.md — TDD: UsageAwareKeySelector with KeyResolution dataclass and full test coverage
- [x] 09-02-PLAN.md — Wire selector into GeminiImageClient and generation routes with force_tier admin param

### Phase 10: Static Fallback
**Goal**: When both Gemini keys are exhausted, image generation falls back to static backgrounds automatically
**Depends on**: Phase 9
**Requirements**: QUOT-06
**Success Criteria** (what must be TRUE):
  1. When both free and paid daily limits are exhausted, `ImageWorker` produces a valid image using a static background instead of returning an error
  2. The `ContentPackage` metadata for a statically-generated image has `background_source: "static"`
  3. The pipeline completes a full run end-to-end even when `GEMINI_IMAGE_DAILY_LIMIT_FREE=0` and `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`
**Plans:** 2/2 plans complete

Plans:
- [x] 10-01-PLAN.md — Exhaustion detection in UsageAwareKeySelector.resolve()
- [x] 10-02-PLAN.md — Wire static fallback into ImageWorker.compose() and GenerationLayer



### Phase 11: Usage Dashboard
**Goal**: Users can see how much Gemini API quota they have used today and what source produced each image
**Depends on**: Phase 10
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. The dashboard shows a widget with "N / M requests used today (free tier)" and a visual fill indicator
  2. Each generated image in the pipeline results list shows a badge: "gemini free", "gemini paid", or "static"
  3. `GET /auth/me/usage` returns data the widget consumes (used, limit, tier, remaining)
**Plans:** 2 plans

Plans:
- [ ] 11-01-PLAN.md — Data layer (TS interfaces, useUsage hook, SOURCE_COLORS) + Usage Card widget
- [ ] 11-02-PLAN.md — Backend tier metadata in image_worker + tier-aware badge rendering
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11

Note: Phase 7 (Usage Tracking Table) can start in parallel with Phase 3 once Phase 2 is complete, as it only depends on Phase 2. Phases 4, 5/6, and 7/8/9/10 form two independent tracks after Phase 3.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pre-Conditions | 0/2 | Planning complete | - |
| 2. Users Table | 0/1 | Planning complete | - |
| 3. Auth Backend | 1/2 | In Progress|  |
| 4. Route Protection | 0/TBD | Not started | - |
| 5. Frontend Auth Pages | 0/2 | Planning complete | - |
| 6. Frontend Route Protection | 0/1 | Planning complete | - |
| 7. Usage Tracking Table | 1/1 | Complete   | 2026-03-24 |
| 8. Atomic Counter | 0/1 | Planning complete | - |
| 9. Dual Key Management | 0/TBD | Not started | - |
| 10. Static Fallback | 2/2 | Complete    | 2026-03-24 |
| 11. Usage Dashboard | 0/2 | Planning complete | - |
