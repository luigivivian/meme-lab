# Feature Landscape: Auth + Rate Limiting + API Management

**Domain:** SaaS dashboard auth + external API usage control for meme generation pipeline
**Researched:** 2026-03-23
**Confidence:** HIGH (well-established domain patterns, no cutting-edge unknowns)

---

## Context

This milestone adds auth and API quota control to an existing pipeline (Clip-Flow / memeLab). The system currently has no auth, no usage tracking, and a broken Gemini Image API key. The core problem is twofold:

1. **Auth**: The memeLab dashboard is open to anyone. As multi-tenant use approaches, routes must be protected.
2. **API quota control**: Gemini Image free tier has hard limits. Blowing the daily quota stops all image generation. The pipeline must degrade gracefully (free key → paid key → static backgrounds).

This is NOT a general-purpose auth product. It is auth-as-infrastructure for a single-app dashboard, sized for v1 with the foundation for multi-tenant v2.

---

## Table Stakes

Features users expect. Missing = system is broken or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Email + password login | Basic access control — open dashboard is unacceptable | Low | bcrypt hash, no plaintext ever |
| JWT session tokens | Stateless auth for FastAPI + Next.js; industry standard | Low | Access token (short TTL) + refresh token (longer TTL) |
| Persistent session (remember me) | Users don't want to log in every browser restart | Low | HttpOnly cookie or localStorage with refresh token |
| Route protection on API | All `/pipeline`, `/generate`, `/content` routes must require auth | Low | FastAPI `Depends(get_current_user)` middleware |
| Protected pages in frontend | Login redirect for unauthenticated visitors | Low | Next.js middleware or layout-level auth check |
| Login page UI | Entry point to the dashboard | Low | Email + password form, error states, loading state |
| Gemini API key dual-tier | Free key as default, paid key as fallback — the whole point of this milestone | Medium | Config-driven, never expose keys in responses |
| Per-day API usage counter | Track how many Gemini Image calls were made today | Low | MySQL counter keyed by `(api_service, date)` — reset midnight |
| Threshold-based fallback trigger | When free key hits N% of daily quota, switch to paid key | Medium | Configurable threshold (e.g. 80% = switch, 100% = static) |
| Fallback to static backgrounds | Pipeline must not halt when both keys are exhausted | Low | Existing static BG logic already works — just needs to be wired into the quota check |
| Usage visible in dashboard | Operator needs to see "used 340/500 Imagen requests today" | Medium | Simple counter widget on dashboard home or settings page |

---

## Differentiators

Features that go beyond minimum and add real value for this specific system.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Quota budget per pipeline run | Each run declares how many Gemini Image calls it needs; system pre-checks budget before starting | Medium | Prevents mid-run failures; better UX than "run failed at step 4" |
| Background source indicator in output | Each generated image records whether BG came from `gemini_free`, `gemini_paid`, or `static` | Low | Already partially tracked in `generated_images.source`; just needs quota context |
| Usage history chart (7/30 days) | Visual trend of API consumption over time | Medium | Helps operator decide if paid tier is justified; chart.js or recharts |
| Manual quota reset / override | Admin can reset daily counter (e.g. after midnight issue) or set a manual ceiling | Low | Simple admin endpoint, not exposed to regular users |
| Paid key only-mode toggle | Force all requests through paid key regardless of free quota (e.g. important batch run) | Low | Single config flag, exposed in settings UI |
| Session invalidation endpoint | Allow operator to force-logout all sessions (security incident response) | Low | Increment token version in DB; JWT check includes version |
| Audit log for key switches | Record every time fallback from free → paid → static occurred, with reason | Low | Append to `api_usage_logs` table; visible in settings |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| OAuth / social login (Google, GitHub) | Adds OAuth library, callback routes, state management — 3x complexity for zero marginal benefit at single-operator scale | Email + password is sufficient for v1; add OAuth in v2 if multi-tenant needs it |
| 2FA / TOTP | Same complexity argument; this is an internal tool, not a bank | Defer to post-multi-tenant when real end-users exist |
| Password reset via email | Requires SMTP/transactional email service (SendGrid, SES), domain setup, email templates | Out of scope per PROJECT.md; add in v2 |
| Per-user API keys (user brings own Gemini key) | Multi-tenant concern — each user managing their own key is a different product | Design the schema with `user_id` foreign keys, but don't implement per-user keys yet |
| Rate limiting per HTTP endpoint (e.g. 10 req/min per IP) | Overkill for a single-operator tool; adds Redis dependency or complex in-memory state | Not needed until public-facing SaaS; DDoS protection belongs at infrastructure layer |
| Role-based access control (RBAC) beyond admin/user | Permission matrices, resource ownership checks — complexity without a real use case yet | Two roles max: `admin` (full access) + `user` (read + run pipeline) |
| Billing integration | Entire separate milestone (Sprint 9 per roadmap) | Do not mix payment logic with auth infrastructure |
| Quota alerts via email/SMS | Requires notification infra; not justified for one operator checking a dashboard | Dashboard indicator is sufficient; add push notifications when multi-tenant |

---

## Feature Dependencies

```
Login page UI → JWT session tokens
JWT session tokens → Route protection on API
JWT session tokens → Protected pages in frontend
Route protection on API → [all existing pipeline/generate/content routes]

Gemini dual-tier config → Per-day API usage counter
Per-day API usage counter → Threshold-based fallback trigger
Threshold-based fallback trigger → Fallback to static backgrounds (wire-up)
Threshold-based fallback trigger → Usage visible in dashboard

[Differentiators]
Per-day API usage counter → Usage history chart (requires historical rows, not just today's counter)
Per-day API usage counter → Quota budget per pipeline run (pre-flight check reads same counter)
Per-day API usage counter → Audit log for key switches
```

---

## MVP Recommendation

Build in this order within the milestone:

**Phase 1 — Fix the broken API key first (unblocks everything)**
1. New Google API key configured, `GOOGLE_API_KEY` updated in `.env`
2. Verify Gemini Image works with a single test call before touching auth

**Phase 2 — Auth foundation**
3. `users` table migration (id, email, hashed_password, role, created_at)
4. `api_usage` table migration (id, service, date, free_count, paid_count)
5. JWT utilities (create_access_token, decode_token, get_current_user dependency)
6. `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` endpoints
7. Route protection applied to all existing API routes

**Phase 3 — Frontend auth**
8. Login page in memeLab
9. Auth context / hook for session state
10. Protected route wrapper / middleware

**Phase 4 — Quota control**
11. Dual-key config (`GEMINI_FREE_KEY`, `GEMINI_PAID_KEY`, `GEMINI_PAID_THRESHOLD_PCT`)
12. Usage counter increment on every Gemini Image call
13. Pre-call check: select free vs paid key based on counter
14. Fallback to static when both keys exhausted
15. Usage widget in dashboard

**Defer to v2:**
- Usage history chart (needs data accumulation first anyway)
- Quota budget per pipeline run
- Audit log for key switches
- Password reset

---

## Complexity Notes by Area

| Area | Estimated Complexity | Dominant Risk |
|------|----------------------|---------------|
| Users table + migration | Low | None — existing Alembic setup, straightforward schema |
| JWT auth (FastAPI) | Low | Token expiry edge cases; handle refresh token correctly |
| Protected routes FastAPI | Low | Retrofit Depends() to 50+ existing routes — tedious but mechanical |
| Protected routes Next.js | Low | Middleware pattern is well-established in Next.js 15 |
| Dual API key switching | Medium | Race condition if two concurrent requests both read "under limit" before either increments; needs DB-level atomic increment or a mutex |
| Usage counter accuracy | Medium | Timezone handling for "reset at midnight" — use UTC consistently |
| Dashboard usage widget | Low | Read one DB row, display two numbers |

---

## Critical Implementation Note: Atomic Counter

The usage counter for Gemini API calls **must be atomic**. Two concurrent pipeline workers can simultaneously read "count=498" (under the 500 limit) and both proceed, resulting in 500+N calls.

Use MySQL `UPDATE api_usage SET free_count = free_count + 1 WHERE ... RETURNING free_count` (or equivalent SELECT FOR UPDATE) to ensure only one request gets slot 500. This is the single most likely bug in the quota system if not handled explicitly.

SQLAlchemy 2.0 async supports this via `with_for_update()` on the select or a raw `UPDATE ... RETURNING` statement.

---

## Sources

- Project requirements: `.planning/PROJECT.md` (confirmed 2026-03-23)
- Existing ORM schema: `src/database/models.py` — informed table gap analysis
- FastAPI auth patterns: established FastAPI docs conventions (python-jose, passlib, OAuth2PasswordBearer)
- JWT best practices: RFC 7519, FastAPI security docs
- SQLAlchemy atomic update: SQLAlchemy 2.0 Core docs (`update().values().returning()`)
- Confidence: HIGH for auth patterns (no research needed, canonical FastAPI patterns); MEDIUM for exact Gemini Image quota numbers (PROJECT.md cites 50 RPM / ~500/day for Imagen 3 — verify against current Google AI Studio docs before hardcoding limits)
