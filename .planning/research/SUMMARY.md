# Project Research Summary

**Project:** Clip-Flow v2.0 — Pipeline Simplification, Auto-Publishing & Multi-Tenant
**Domain:** Meme automation SaaS — content pipeline, Instagram publishing, auth hardening, analytics, billing
**Researched:** 2026-03-24
**Confidence:** HIGH (all recommendations grounded in direct codebase analysis)

## Executive Summary

Clip-Flow v2.0 is a content automation SaaS with a substantial working codebase — research revealed that roughly 85-90% of the required backend infrastructure already exists in some form. The path forward is predominantly a wiring and isolation problem, not a greenfield build. `InstagramClient` is fully implemented but not wired into the publishing service. Auth flows work but lack password reset, 2FA, and OAuth. The pipeline runs but has no user-scoping. The biggest investment is multi-tenant isolation: nearly every database table and repository method must be retrofitted with `user_id` filtering before the product can safely serve more than one user.

The recommended approach is a strict phase ordering driven by dependency safety: pipeline refactoring first (establishes patterns), tenant isolation second (prevents data leaks as features ship), auth hardening third (security baseline before exposing sensitive features), then auto-publishing, analytics, and billing in that order. Only 6 new libraries are needed across the entire v2 scope — the stack is essentially locked. The main external blockers are outside code: Cloudflare R2 CDN setup (required for Instagram image URLs) and Facebook App Review for `instagram_content_publish` permission (takes 2-6 weeks, must start immediately in parallel with development).

The most dangerous risks are silent ones: the current codebase has zero tenant data isolation despite having authentication, meaning User A can already read User B's data if multiple users existed. Instagram's token lifecycle is similarly silent — tokens expire and fail at 3 AM with no recovery if not designed correctly from the start. Both risks have clear preventions documented in the research and must be addressed before any multi-user production deployment.

---

## Key Findings

### Recommended Stack

The existing stack is mature and should not be extended beyond what is strictly necessary. See `.planning/research/STACK.md` for full rationale and alternatives rejected.

**New Python backend packages (5 total):**
- `aiosmtplib>=2.0.0` — async SMTP for password reset emails; native asyncio, no blocking
- `pyotp>=2.9.0` — TOTP 2FA; de facto Python RFC 6238 library, zero dependencies
- `qrcode[pil]>=8.0` — QR code generation for authenticator setup; reuses Pillow (already installed)
- `authlib>=1.3.0` — Google OAuth 2.0; native httpx integration via `AsyncOAuth2Client`
- `stripe>=11.0.0` — official Stripe billing SDK with webhook signature verification

**New frontend package (1 total):**
- `recharts>=2.15.0` — dashboard charts; React-native D3 components, ~45KB gzipped

**Critical gap in requirements.txt:** `PyJWT` is used in `src/auth/jwt.py` but is not listed in `requirements.txt`. Must add `PyJWT>=2.8.0` immediately in Phase 1.

**What NOT to add:** Celery, Redis, next-auth, `@stripe/react-stripe-js`, passlib, python-jose, `@tanstack/react-query`, fastapi-mail, Jinja2. The existing stack covers everything. Each rejected library has a specific documented reason.

---

### Expected Features

See `.planning/research/FEATURES.md` for full dependency graph, user flows, and existing code leverage map.

**Must have (table stakes):**
- Manual pipeline mode (no Gemini Image) — core v2 value prop, reduce API costs
- Per-character pipeline runs with visual DNA isolation
- Instagram Graph API auto-publishing — the product's primary new capability
- Image CDN / public URL (Cloudflare R2) — hard blocker for Instagram publishing
- Instagram token lifecycle management — tokens expire every 60 days, must auto-refresh
- Scheduling calendar UI and post queue management — publishing frontend
- Password reset via email — standard auth, users lock themselves out
- TOTP 2FA with recovery codes — security expectation for SaaS handling API keys
- 30-day usage history chart — users need consumption trend visibility
- User data isolation — each user sees only their own content

**Should have (differentiators):**
- Google OAuth login — reduces signup friction
- Auto-schedule from pipeline output — pipeline generates, auto-queues to best-time slots
- Character-aware caption generation — captions match character personality
- Limit alerts at 80%/95% thresholds — proactive quota warnings
- Cost report (estimated spend per service/tier)
- Publishing analytics via Instagram Insights

**Defer to v3+:**
- OAuth providers beyond Google (GitHub, Facebook)
- Engagement feedback loop (ML-based content scoring from Insights data)
- Bulk drag-and-drop scheduling calendar
- Usage-based metered billing (start with flat tier pricing)
- Team workspaces and collaborative editing
- Multi-platform publishing (TikTok, Twitter)

**Anti-features (explicitly do not build):**
- Gemini Image in pipeline — keep as standalone notebook tool only
- Instagram DM automation — ToS violation, ban risk
- Follower growth tools — grey-area, Instagram bans automation aggressively
- SMS-based 2FA — cost per message, carrier issues in BR; TOTP authenticator apps only
- Custom payment forms — use Stripe Checkout hosted page; never handle card numbers directly

---

### Architecture Approach

The architecture is defined by two cross-cutting concerns: tenant isolation (applied at repository layer via `TenantContext` dependency injection) and the two-phase Instagram publishing flow (CDN upload then container-based Graph API publish). All other changes are additive — new modules, new routes, new tables — rather than rewrites of existing components. See `.planning/research/ARCHITECTURE.md` for complete component map, data flows, and anti-patterns to avoid.

**Major components:**

1. **TenantContext** (`src/api/deps.py`) — FastAPI dependency wrapping `get_current_user`; provides `user_id`, `role`, and `plan` to all downstream services and repositories; the single enforcement point for tenant isolation; admin bypass via `is_admin` flag
2. **Tenant-Scoped Repositories** (all 8 existing repos modified + 2 new) — every list/get method gains a `user_id` filter via `_scoped()` pattern; this is the highest-risk change in v2 (miss one = data leak)
3. **Auth Extension Modules** (`src/auth/totp.py`, `src/auth/oauth.py`, `src/auth/email.py`) — new files added to existing auth module; two-phase login flow for 2FA (temp token with 5min TTL + TOTP verification); no rewrite of existing login
4. **CDNService** (`src/services/cdn_service.py`) — uploads local Pillow-generated images to Cloudflare R2 before Instagram publishing; returns public URL consumed by existing `InstagramClient.get_public_image_url()`
5. **StripeService** (`src/services/stripe_service.py`) — Checkout Session creation, webhook handler with idempotency table (`stripe_events`), plan enforcement
6. **DashboardRoutes** (`src/api/routes/dashboard.py`) + **DashboardRepo** — pure SQL aggregation on existing `api_usage`, `pipeline_runs`, `scheduled_posts` tables; no new data collection needed

**New files:** 14 total. **Modified files:** All 8 repositories + all 11 route modules (to pass TenantContext).

**v2.0 simplified pipeline flow:**
```
POST /pipeline/run (manual_topics, background_mode="static")
  -> TenantContext extracts user_id
  -> SimplePipelineOrchestrator(user_id, character_id)  [NEW — separate from AsyncPipelineOrchestrator]
  -> L4 only: PhraseWorker (Gemini text) + ImageWorker (static BG) + Pillow compose
  -> ContentPackages saved WITH user_id
```

---

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for 13 pitfalls with codebase evidence (file + line number) and full prevention strategies.

1. **Multi-tenant data leakage (CRITICAL)** — `get_current_user` gates 401s but NO repository filters by user_id. Five tables (`pipeline_runs`, `content_packages`, `scheduled_posts`, `batch_jobs`, `work_orders`) have no `user_id` column at all. Prevention: add `user_id` FK to all 5 tables in one migration, implement `_scoped()` pattern in every repository, write cross-user isolation tests before Phase 2 is declared complete.

2. **Instagram token lifecycle trap (CRITICAL)** — Facebook App Review for `instagram_content_publish` takes 2-6 weeks. Long-lived tokens (60 days) expire silently at 3 AM. The current `_publish_instagram()` (publisher.py lines 146-162) is a placeholder with zero token management. Prevention: start App Review immediately, build token refresh automation before wiring the publisher, store `expires_at` per token with pre-flight check in scheduler.

3. **Instagram two-step container publishing (HIGH)** — Publishing is not one API call. It requires: create container, poll until `FINISHED` (5-30 seconds), then publish. Race conditions and premature publish attempts cause "media not ready" errors. Prevention: implement container polling with exponential backoff; store `container_id` in `scheduled_posts.publish_result` so retries resume polling rather than re-uploading.

4. **OAuth account takeover via email collision (HIGH)** — `hashed_password` is `NOT NULL` in the User model, so OAuth user creation crashes. If email auto-merge is implemented without verification, an attacker creates an OAuth account with a victim's email and takes over the account. Prevention: make `hashed_password` nullable, verify `email_verified: true` from Google ID token, require explicit account linking — never auto-merge.

5. **Pipeline monolith refactor risk (MEDIUM)** — `AsyncPipelineOrchestrator` has 30+ constructor parameters and 9 hardcoded agent imports. Refactoring it breaks the existing `manual_topics` flow. Prevention: do NOT rewrite — create a new `SimplePipelineOrchestrator` for manual/static mode; keep existing orchestrator frozen; route by `mode=` parameter in the API.

6. **Stripe webhook raw body trap (HIGH)** — FastAPI parses JSON before you can read raw bytes; Stripe signature verification needs raw bytes. If a Pydantic body parameter is added, HMAC verification fails and fake events (free upgrades, fake payments) are processed. Prevention: `async def stripe_webhook(request: Request)` with no body parameter; read raw bytes first; store processed `event.id` in `stripe_events` table for idempotency.

---

## Implications for Roadmap

Based on combined research findings, the recommended phase structure has 6 phases. Ordering is driven by dependency chains and risk sequencing: establish patterns first, isolate data second, harden security third, ship user-facing features fourth and fifth, monetize sixth.

### Phase 1: Pipeline Simplification + Multi-Character

**Rationale:** Zero new external dependencies. Pure architectural restructuring using existing tools. Establishes the `character_id` + `user_id` threading pattern that all downstream phases inherit. The `SimplePipelineOrchestrator` created here is the foundation for per-user pipeline runs. Must be done first because it freezes the existing orchestrator (preventing regressions) and defines the config object pattern.

**Delivers:** Manual pipeline mode (no Gemini Image), per-character visual DNA isolation, content preview gallery with approve/reject workflow, `SimplePipelineOrchestrator` with static background composition.

**Addresses:** Manual pipeline, per-character runs, content preview (FEATURES.md table stakes)

**Avoids:** Pitfall 5 (pipeline monolith refactor) — create new orchestrator, do not rewrite existing one

**Research flag:** Standard patterns. No deeper research needed. Risk is LOW.

---

### Phase 2: Tenant Isolation

**Rationale:** The most invasive change in the entire v2 scope. Must happen before any user-facing feature ships to prevent data leaks. The repository `_scoped()` pattern established here is used by all subsequent phases. Better to pay this cost once, early, than retrofit it across half-built features.

**Delivers:** Complete user data isolation — every user sees only their own characters, pipeline runs, content packages, scheduled posts, batch jobs. Admin bypass via `TenantContext.is_admin`. Alembic migration adds `user_id` FK to 5 tables (nullable first, backfill, then NOT NULL).

**Addresses:** User data isolation (FEATURES.md multi-tenant table stakes)

**Avoids:** Pitfall 1 (multi-tenant data leakage) — this entire phase exists to prevent it

**Research flag:** High-risk but standard pattern. No deeper research needed. Requires comprehensive cross-user integration tests before phase is declared complete.

---

### Phase 3: Auth v2 (Password Reset + TOTP 2FA + Google OAuth)

**Rationale:** Security baseline required before exposing billing, per-user Instagram tokens, and API key management to real users. OAuth establishes the external provider token exchange pattern that Instagram connecting (Phase 4) will reuse. JWT SECRET_KEY rotation (5-minute task) must happen at the start of this phase before adding 2FA/OAuth attack surface.

**Delivers:** Password reset via email (aiosmtplib), TOTP 2FA with QR code and recovery codes (pyotp + qrcode), Google OAuth login (authlib), API key encryption at rest (Fernet), JWT SECRET_KEY rotated to 64 bytes.

**Addresses:** Password reset, TOTP 2FA, Google OAuth, API key encryption (FEATURES.md auth v2)

**Avoids:** Pitfall 4 (OAuth account takeover), Pitfall 8 (insecure reset tokens), Pitfall 9 (2FA recovery flow amnesia), Pitfall 11 (JWT key too short), Pitfall 12 (plaintext API key storage)

**Research flag:** Needs phase-level research for Facebook/Instagram token exchange pattern (the OAuth flow established here is reused for IG connecting in Phase 4). TOTP and Google OAuth flows are well-documented standards.

---

### Phase 4: Instagram Auto-Publishing

**Rationale:** Highest user-value feature after the foundation phases. Depends on Phase 2 (per-user credentials require tenant isolation) and Phase 3 (OAuth token pattern reused for Facebook token exchange). The CDN setup and Facebook App Review must start in parallel with Phase 3 development — App Review takes 2-6 weeks and will gate Phase 4 production readiness.

**Delivers:** Cloudflare R2 CDN setup (CDNService), Facebook App Review completion, Instagram token lifecycle management (short-lived to long-lived exchange, 60-day refresh automation), publisher wired with real InstagramClient, scheduling calendar UI, post queue management, best-time suggestions (static data per day-of-week initially).

**Addresses:** Instagram Graph API integration, image CDN, token lifecycle, scheduling calendar UI, post queue (FEATURES.md auto-publishing table stakes)

**Avoids:** Pitfall 2 (token lifecycle trap), Pitfall 3 (two-step container publishing), Pitfall 7 (double-publishing via `SELECT FOR UPDATE SKIP LOCKED`), Pitfall 13 (image format validation — JPEG + RGB conversion before CDN upload)

**Research flag:** Needs phase-level research. Instagram Graph API specifics (rate limits, exact container polling behavior, App Review requirements) must be verified against current Meta developer documentation before planning this phase.

---

### Phase 5: Dashboard v2

**Rationale:** Pure SQL aggregation on existing tables — lowest risk phase in the entire roadmap. Requires Phase 2 (user-scoped metrics) but has no other blockers. Provides usage visibility needed to make billing decisions in Phase 6. The `api_usage.date` column DateTime vs Date type ambiguity must be resolved at the start of this phase.

**Delivers:** 30-day usage history chart (recharts LineChart), limit alerts at 80%/95% (frontend calculation on existing data), cost report by service/tier (price map config file), pipeline run history table, publishing analytics via existing `InstagramClient.get_media_insights()`.

**Addresses:** 30-day history chart, limit alerts, cost report, publishing analytics (FEATURES.md dashboard v2)

**Avoids:** Pitfall 10 (N+1 query and DateTime column ambiguity — fix `date` column name to `recorded_at`, use SQL `GROUP BY DATE(date)`)

**Research flag:** Standard patterns. recharts documentation is comprehensive. No deeper research needed. Risk is LOW.

---

### Phase 6: Multi-Tenant Billing (Stripe)

**Rationale:** Monetization layer comes last because it gates access to all previous features and needs plan enforcement across every feature built in Phases 1-5. Stripe Checkout hosted page means zero frontend Stripe SDK is needed. The `stripe_events` idempotency table must be built from the start — never retroactively.

**Delivers:** Plans table (Free/Pro/Enterprise), Stripe Checkout integration, 5 critical webhook handlers with idempotency, Stripe Customer Portal for self-service billing, plan limit enforcement middleware, API key encryption migration for any remaining plaintext keys.

**Addresses:** Stripe subscription billing, plan limits enforcement, Customer Portal, complete multi-tenant billing (FEATURES.md)

**Avoids:** Pitfall 6 (Stripe webhook raw body trap — raw bytes, no Pydantic body parameter), Pitfall 1 (plan enforcement must check TenantContext), double-processing via `stripe_events` idempotency table

**Research flag:** Needs phase-level research for Stripe API v2025+ webhook event schema and Brazilian payment method support (PIX, Boleto compatibility). Standard Checkout/webhook pattern is well-documented.

---

### Phase Ordering Rationale

- **Dependency order:** Each phase creates infrastructure the next phase requires. Pipeline establishes user_id threading -> Tenant isolation enforces it -> Auth establishes security baseline -> Publishing uses per-user credentials -> Dashboard uses user-scoped metrics -> Billing uses all of the above.
- **Risk sequencing:** High-risk pervasive changes (tenant isolation) happen before user-facing features. This prevents having to retrofit isolation across half-built features in production.
- **External blockers front-loaded:** Facebook App Review (2-6 weeks) must start during Phase 3 in parallel with auth work. Cloudflare R2 setup is straightforward (1-2 hours) but must be completed before Phase 4 testing begins.
- **New library introduction staged:** Only libraries needed for each phase are introduced when the phase starts. Reduces integration risk and makes requirements changes explicit.

### Research Flags

**Phases needing `/gsd:research-phase` during planning:**
- **Phase 4 (Auto-Publishing):** Instagram Graph API specifics must be verified against current Meta docs. Token exchange flow, container polling behavior, App Review requirements, and rate limits can change. Training data confidence is MEDIUM on Instagram API details.
- **Phase 6 (Billing):** Stripe API v2025+ changes, Brazilian payment methods (PIX, Boleto), and current webhook event schema should be verified against Stripe docs before planning.
- **Phase 3 (Auth v2):** Facebook/Instagram token exchange pattern (reused from OAuth flow) needs verification before planning Phase 4.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Pipeline):** Pure code restructuring with existing stack. No external APIs. Well-understood domain.
- **Phase 2 (Tenant Isolation):** SQLAlchemy filtering patterns are well-established. Repository `_scoped()` pattern is standard practice.
- **Phase 5 (Dashboard):** recharts documentation is comprehensive. SQL aggregation patterns are standard.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 6 new library recommendations verified against existing stack compatibility. Alternatives documented with specific rejection reasons. Direct `requirements.txt` and `package.json` review confirms no conflicts. |
| Features | HIGH | Derived from direct codebase analysis of existing models, routes, and services. Instagram API details are MEDIUM confidence (training data, no live API verification available). |
| Architecture | HIGH | All component boundaries and integration points verified against actual source files. Risk assessment based on real code evidence with specific file and line number citations. |
| Pitfalls | HIGH | All critical pitfalls backed by codebase evidence (specific file + line number citations). Instagram API-specific behavior (container timing, rate limits) is MEDIUM confidence. |

**Overall confidence:** HIGH for everything verifiable in the codebase. MEDIUM for external API specifics (Instagram Graph API, Stripe v2025+, Facebook App Review process).

### Gaps to Address

- **Instagram Graph API rate limits and container timing:** Training data cites 25 API calls/user/hour and 5-30s container processing. These must be verified against current Meta developer docs before Phase 4 planning. Container polling timeout strategy depends on actual processing times.
- **Facebook App Review current requirements:** The 2-6 week timeline and required materials (privacy policy, demo video, business verification) should be verified before submitting the app. Requirements change frequently.
- **Stripe Brazilian payment methods:** Research did not verify whether Stripe Checkout supports PIX or Boleto for Brazilian users. If the target market is BR-based SaaS, this must be checked before Phase 6 planning to avoid discovering a blocker late.
- **Cloudflare R2 public URL configuration:** R2 requires a custom domain or public bucket URL for Instagram Graph API. The exact DNS and CORS policy setup for Instagram's servers should be verified during Phase 4 planning.
- **`api_usage.date` column type:** Currently stored as `DateTime` but named `date`. The `UniqueConstraint` including this column may not work as intended (time component varies). Research recommends renaming to `recorded_at` or changing to `Date` type. Coordinate this migration with Phase 5 planning.

---

## Sources

### Primary (HIGH confidence — direct codebase analysis)

- `src/services/instagram_client.py` — full Graph API client review; confirmed publish_image, publish_carousel, publish_reel, get_media_insights, get_public_image_url all implemented
- `src/services/publisher.py` — confirmed placeholder at lines 146-162; zero token management; dispatch pattern present
- `src/services/scheduler_worker.py` — confirmed APScheduler singleton per process; race condition window identified
- `src/database/models.py` — all 14 ORM models reviewed; confirmed missing user_id FKs on 5 tables, plaintext API keys, NOT NULL hashed_password
- `src/api/routes/publishing.py` — confirmed current_user received but never used for filtering in any query
- `src/auth/jwt.py` — confirmed PyJWT usage; missing from requirements.txt
- `src/api/deps.py`, `src/auth/service.py`, `src/auth/schemas.py` — full auth module review
- `memelab/package.json` — confirmed current frontend deps; recharts not yet installed

### Secondary (MEDIUM confidence — training data, multiple sources agree)

- Instagram Graph API publishing flow — container-based two-step publish, token lifecycle, App Review requirements
- Stripe Checkout + webhook patterns — Checkout Session, 5 critical webhook events, idempotency requirement
- TOTP 2FA standards — RFC 6238, pyotp library, QR code provisioning URI format
- Google OAuth 2.0 OIDC flow — authorization code flow, ID token claims, email_verified requirement

### Tertiary (LOW confidence — needs verification before implementation)

- Instagram Graph API current rate limits (25 calls/user/hour) — verify against Meta docs before Phase 4
- Facebook App Review timeline (2-6 weeks) — verify current process and requirements before submitting
- Stripe Brazilian payment methods (PIX, Boleto) — verify Stripe regional support before Phase 6
- Cloudflare R2 public URL DNS configuration — verify exact setup for Instagram CDN use case

---

*Research completed: 2026-03-24*
*Ready for roadmap: yes*
