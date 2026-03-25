# Feature Landscape

**Domain:** Meme automation SaaS -- pipeline simplification, auto-publishing, auth hardening, analytics, multi-tenant billing
**Researched:** 2026-03-24
**Confidence:** MEDIUM (training data + thorough codebase verification, no live web verification)

## Table Stakes

Features users expect. Missing = product feels incomplete.

### Pipeline & Content

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Manual pipeline (no Gemini Image) | Core v2 value prop: compose backgrounds + phrases without API costs | Med | Existing orchestrator, Pillow compositor | Decouple L1 agents from pipeline flow; pipeline takes topic+phrase input, picks theme/background, composes image. Already have `background_mode` param and static fallback path. |
| Theme/background picker in pipeline | Users need to choose visual style per content | Low | Existing themes table, character style JSON | Frontend dropdown to select theme; backend already supports `theme_tags` on PipelineRunRequest |
| Per-character pipeline runs | Each character has own visual DNA, system prompt, refs | Med | Character model (has `user_id` FK), pipeline orchestrator | `character_id` already threaded through pipeline_runs, content_packages, generated_images. Need worker-level character context isolation. |
| Content preview before publish | Users must see composed meme before scheduling | Low | Existing `/drive/images/` endpoint | Frontend gallery with approve/reject already partially exists via content packages list |

### Instagram Auto-Publishing

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Instagram Graph API integration | Core auto-publish feature; users expect one-click publish | High | Instagram Business Account, Facebook App, long-lived token management | `InstagramClient` fully implemented in `src/services/instagram_client.py` (image, carousel, reel, insights). `PublishingService` in `src/services/publisher.py` has placeholder `_publish_instagram`. Missing: wire client into service, token refresh flow (tokens expire 60 days), public URL for images. |
| Image CDN / public URL | Instagram Graph API requires publicly accessible image URLs | Med | S3/Cloudflare R2 or ngrok tunnel | **Critical blocker.** `InstagramClient.get_public_image_url()` already supports CDN via `INSTAGRAM_CDN_BASE` env var or local fallback via `INSTAGRAM_API_PUBLIC_URL`. Needs real CDN setup. Options: (1) Cloudflare R2 (free egress, S3-compatible), (2) S3 presigned URLs, (3) ngrok for dev. |
| Scheduling calendar UI | Visual calendar to see what posts when | Med | Existing `/publishing/calendar` endpoint, `ScheduledPost` model | Backend API complete in `publishing.py` routes. Need frontend calendar component (month/week views). |
| Post queue management | View, cancel, retry scheduled posts | Low | Existing `/publishing/queue`, cancel, retry endpoints | Backend complete. Need frontend queue list with action buttons. |
| Best-time suggestions | Users expect smart scheduling recommendations | Low | Currently static data per day-of-week | Start static (already done), upgrade to Instagram Insights data later via `get_account_insights()` which is already coded. |
| Token lifecycle management | Long-lived tokens expire every 60 days; must auto-refresh | Med | Facebook Graph API token exchange endpoint | Flow: short-lived token (1h) -> exchange for long-lived (60d) -> cron to refresh before expiry. Need `instagram_tokens` table (token, expires_at, user_id) or columns on User. |

**Instagram Publishing -- Expected User Flow:**

1. User connects Instagram Business Account (OAuth-like flow via Facebook Login)
2. App receives short-lived token, exchanges for long-lived token (60 days), stores encrypted
3. User creates content via pipeline -> approves in gallery
4. User clicks "Schedule" -> picks date/time (or "Publish Now")
5. Image uploaded to CDN (R2/S3), public URL generated
6. At scheduled time, `scheduler_worker` calls `PublishingService.process_due_posts()`
7. Service calls `InstagramClient.publish_image(public_url, caption)`
8. Graph API creates container -> publishes -> returns permalink
9. Post marked "published" in DB, permalink stored in `publish_result` JSON
10. Dashboard shows published/failed/queued counts

**Instagram API Requirements (training data, MEDIUM confidence):**

- Business or Creator account linked to Facebook Page
- Facebook App with `instagram_basic`, `instagram_content_publish`, `pages_show_list` permissions
- App Review required for `instagram_content_publish` permission (takes 1-5 business days)
- Rate limits: 25 API calls per user per hour for content publishing (container creation + publish)
- Images: JPEG/PNG, max 8MB, must be publicly accessible URL
- Captions: max 2200 characters, up to 30 hashtags
- Carousel: 2-10 items
- Container-based flow: create container -> (poll if video) -> publish container

### Auth v2

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Password reset via email | Standard auth feature, users lock themselves out | Med | SMTP provider (Resend or SES), reset token table | Flow: request reset -> validate email exists -> generate token (expires 1h) -> send email with link -> user clicks link -> frontend shows new password form -> validate token -> update password -> invalidate token. Need email sending service + `password_reset_tokens` table. |
| TOTP 2FA (authenticator app) | Security expectation for SaaS with API keys | Med | `pyotp` library, `qrcode` for QR generation, backup codes | Flow: user enables 2FA -> backend generates TOTP secret -> returns QR code (otpauth:// URI) -> user scans with Google Authenticator/Authy -> user enters first code to verify -> backend stores encrypted `totp_secret` on User. Login adds second step: after email+password validated, require 6-digit TOTP code. Need `totp_secret`, `totp_enabled`, `totp_backup_codes` on User model. |
| OAuth Google login | Convenience, reduces friction for Gmail users | Med | `authlib` or `httpx-oauth`, Google Cloud Console OAuth2 credentials | Flow: frontend redirects to Google consent screen -> user approves -> Google redirects to callback with auth code -> backend exchanges code for tokens -> gets user profile (email, name, avatar) -> creates or links user account -> issues JWT. Need `oauth_provider` + `oauth_id` columns on User. Password is optional for OAuth users. |
| API key encryption at rest | Tech debt from v1: `gemini_free_key`/`gemini_paid_key` stored as plaintext `Text` | Low | `cryptography` lib (Fernet symmetric encryption) | Encrypt at write, decrypt at read. Need `ENCRYPTION_KEY` in env vars. Non-breaking migration: encrypt existing keys in-place. |

**2FA/TOTP -- Expected User Flow:**

1. User goes to Security Settings -> clicks "Enable 2FA"
2. Backend generates random TOTP secret (base32, 20 bytes via `pyotp.random_base32()`)
3. Frontend shows QR code encoding `otpauth://totp/ClipFlow:{email}?secret={secret}&issuer=ClipFlow`
4. User scans with authenticator app (Google Authenticator, Authy, 1Password, etc.)
5. User enters 6-digit code from app to verify setup works
6. Backend stores encrypted secret, generates 8-10 backup codes (one-time use), shows to user once
7. On next login: email+password validates -> if 2FA enabled, return `{ requires_2fa: true, temp_token: "..." }`
8. Frontend shows TOTP input -> user enters code -> backend verifies with `pyotp.TOTP(secret).verify(code, valid_window=1)`
9. If valid, issue real JWT. If user lost device, can use backup code (single-use, mark as used)

**OAuth Google -- Expected User Flow:**

1. Frontend shows "Sign in with Google" button
2. Click redirects to: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=openid+email+profile&response_type=code`
3. User approves on Google's consent screen
4. Google redirects to `{app_url}/auth/callback/google?code=...`
5. Backend exchanges `code` for tokens via `https://oauth2.googleapis.com/token`
6. Backend calls `https://www.googleapis.com/oauth2/v2/userinfo` to get email, name, picture
7. If email exists in DB with `oauth_provider=google` -> login (issue JWT)
8. If email exists without OAuth -> prompt to link account (verify password first)
9. If email doesn't exist -> auto-register (no password needed, `hashed_password` set to unusable value)
10. Issue JWT + refresh token as normal

### Dashboard v2

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| 30-day usage history chart | Users need to see consumption trends, not just today | Med | Existing `api_usage` table with `user_id`, `service`, `tier`, `date`, `usage_count` | Query: `SELECT date, SUM(usage_count) FROM api_usage WHERE user_id=? AND date >= NOW()-30 GROUP BY date`. Frontend: line/bar chart (recharts or chart.js). |
| Limit alerts (80%/95% thresholds) | Users need warning before hitting quotas | Low | Existing usage tracking, notification UI | Compare daily usage vs tier limits, show banner/toast at thresholds. Can be frontend-only calculation initially. |
| Cost report (estimated $ spent) | SaaS users care about costs | Med | Price-per-call mapping, usage data | Map service+tier to known pricing (Gemini Flash: ~$0.001/call text, ~$0.02/call image). Show daily/monthly totals. Store price map in config, not DB. |
| Pipeline run history | Users want to see past runs and their results | Low | Existing `/pipeline/runs` endpoint | Frontend table with status badges, click-through to run detail with content packages. |
| Publishing analytics | Published posts need engagement tracking | Med | Instagram Insights API (already coded in `InstagramClient.get_media_insights`) | Show impressions, reach, likes, comments, shares per published post. Fetch on demand or periodic sync. |

### Multi-Tenant & Billing

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| User data isolation | Each user sees only their data | Med | `user_id` FK on characters (exists), need on pipeline_runs, content_packages, themes | Add `user_id` to all tenant-scoped tables. Filter ALL queries by `current_user.id`. Middleware or repository-level enforcement. |
| Per-user API key management | Users bring their own Gemini keys | Low | Existing `gemini_free_key`/`gemini_paid_key` on User model | Already partially built. Need encrypted storage (Fernet) + key validation endpoint (test key against Gemini API). |
| Stripe subscription billing | Standard SaaS monetization | High | Stripe account, `stripe` Python SDK, webhook handler, Stripe Customer Portal | Flow: user selects plan -> Stripe Checkout Session -> redirect to Stripe-hosted payment page -> webhook `checkout.session.completed` -> activate subscription in DB. Need `plans` table, `stripe_customer_id` + `stripe_subscription_id` + `plan_id` on User. |
| Plan limits enforcement | Free vs Pro vs Enterprise tiers | Med | Plans table, middleware to check limits | Check plan limits before pipeline run, image generation, scheduled posts. Return 403 with upgrade prompt when exceeded. |
| Stripe Customer Portal | Users self-manage billing (change plan, update card, cancel) | Low | Stripe Customer Portal (hosted by Stripe) | One endpoint: create portal session -> redirect. Stripe handles everything. |

**Stripe Billing -- Expected User Flow:**

1. Define plans: Free (0/mo, 10 posts/day, 1 character), Pro ($19/mo, 100 posts/day, 10 characters), Enterprise ($49/mo, unlimited)
2. User clicks "Upgrade to Pro" -> backend creates Stripe Checkout Session with `price_id`
3. User redirected to Stripe-hosted checkout page (card entry, billing address)
4. On success, Stripe redirects to `{app_url}/billing/success?session_id=...`
5. Webhook `checkout.session.completed` fires -> backend creates/updates subscription in DB
6. Webhook `invoice.paid` fires monthly -> backend renews subscription period
7. Webhook `customer.subscription.updated` -> handle plan changes
8. Webhook `customer.subscription.deleted` -> downgrade to Free
9. User clicks "Manage Billing" -> backend creates Customer Portal session -> redirect to Stripe portal
10. Stripe portal handles: update payment method, change plan, view invoices, cancel subscription

**Critical Stripe Webhooks (must handle):**

| Webhook Event | Action |
|---------------|--------|
| `checkout.session.completed` | Activate subscription, set plan on user |
| `invoice.paid` | Renew subscription period |
| `invoice.payment_failed` | Send warning email, grace period (3-7 days) |
| `customer.subscription.updated` | Update plan tier |
| `customer.subscription.deleted` | Downgrade to Free tier |

**Multi-Tenant -- Tables Needing `user_id`:**

| Table | Has `user_id`? | Action |
|-------|---------------|--------|
| `characters` | YES (nullable) | Make NOT NULL for new records, backfill existing |
| `themes` | NO | Add `user_id` FK + migration |
| `pipeline_runs` | NO | Add `user_id` FK + migration |
| `content_packages` | NO | Add `user_id` FK + migration |
| `generated_images` | NO | Add `user_id` FK + migration |
| `scheduled_posts` | NO | Add `user_id` FK + migration |
| `trend_events` | NO (shared) | Keep shared -- trends are global, not per-user |
| `agent_stats` | NO (shared) | Keep shared -- system-level stats |
| `work_orders` | NO | Add `user_id` FK + migration |
| `batch_jobs` | NO | Add `user_id` FK + migration |


## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Auto-schedule from pipeline output | Pipeline generates -> auto-queues to best-time slots | Low | Pipeline + scheduler integration | After pipeline completes, optionally auto-schedule all approved packages to next available best-time slots. Unique workflow shortcut. |
| Character-aware caption generation | Captions match character personality automatically | Low | Character `caption_prompt` already on model | Already have the field and persona data; wire into L5 post-production. Each character speaks in their own voice. |
| Engagement feedback loop | Instagram Insights feed back into content scoring | High | `InstagramClient.get_media_insights()` already implemented, ML scoring | Wire insights data (impressions, reach, likes) back to `quality_score` on content packages. Over time, learn which themes/phrases perform best. |
| Bulk scheduling with drag-and-drop | Visual calendar where you drag content packages to time slots | Med | Calendar UI, drag-and-drop library (e.g., dnd-kit) | Much better UX than individual scheduling. Differentiator vs manual scheduling tools. |
| Multi-platform scheduling (future prep) | TikTok, Twitter in addition to Instagram | High | Platform-specific APIs, different content formats | Architecture already supports `platform` field on ScheduledPost. `_dispatch_publish` already has `publishers` dict pattern. Keep extensible but Instagram-only for v2. |
| Content recycling / evergreen detection | Auto-identify posts that can be re-posted (e.g., timeless humor) | Med | Content tagging, date-awareness | Tag content as "trending" vs "evergreen". Re-queue evergreen content after 30+ days. Low-effort content multiplication. |


## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Gemini Image generation in pipeline | v2 goal is zero API image costs; Gemini Image is a separate tool | Keep as standalone notebook/tool. Pipeline uses only pre-existing backgrounds + Pillow composition. |
| Real-time collaborative editing | Massive complexity, not needed for meme automation | Single-user edit with optimistic locking (last-write-wins). Defer team features to v3. |
| Custom payment gateway | Stripe handles everything including PCI compliance | Use Stripe Checkout + Customer Portal. NEVER handle card numbers directly. |
| In-app email builder for marketing | Scope creep, not core value | Use Resend/Mailgun for transactional only (reset, alerts). |
| Instagram DM automation | Violates Instagram ToS, high ban risk | Focus on feed publishing only (posts, carousels, reels). |
| Follower growth tools (follow/unfollow, like bots) | Grey-area features, Instagram aggressively bans automation | Focus on content quality and scheduling. Organic growth only. |
| SMS-based 2FA | Cost per message, maintenance burden, phone number storage, carrier issues in BR | TOTP authenticator apps only (Google Authenticator, Authy, 1Password). Free, no per-message cost, works offline. |
| OAuth providers beyond Google | Diminishing returns for BR-focused meme SaaS | Google covers 90%+ of target audience. Add GitHub/Facebook only if user demand proves it. |
| Redis for session/rate limiting | Over-engineering for current scale | MySQL-based counters are sufficient. Current `api_usage` table pattern works. Revisit only at 10K+ concurrent users. |
| Usage-based metered billing (v2) | Complex to implement and confusing UX for small creators | Start with flat tier pricing (Free/Pro/Enterprise). Metered billing is v3 if enterprise demand exists. |
| Direct Instagram login (non-Business) | Instagram Basic API deprecated for new apps, publishing requires Business API | Only support Instagram Business/Creator accounts linked to Facebook Page. |


## Feature Dependencies

```
Pipeline Refactor
  -> Manual Pipeline (decouple agents, topic+phrase input)
    -> Per-character pipeline runs (character context isolation)
      -> Auto-schedule from pipeline output

Auth v2
  -> API Key Encryption (independent, quick win)
  -> Password Reset (needs email service -- Resend/SES setup)
  -> TOTP 2FA (independent of password reset, needs pyotp + qrcode)
  -> OAuth Google (independent, but shares User model changes with 2FA)

Instagram Publishing
  -> Image CDN/Public URL (BLOCKER: Instagram API needs public URLs)
    -> Wire InstagramClient into PublishingService (token management)
      -> Scheduling Calendar UI (frontend)
      -> Post Queue Management (frontend)
      -> Best-time suggestions (static then dynamic)
  -> Facebook App Review for instagram_content_publish (BLOCKER: 1-5 business days)

Dashboard v2
  -> 30-day history chart (needs api_usage query + recharts)
  -> Limit alerts (needs usage thresholds, can be frontend-only initially)
  -> Cost report (needs price mapping config)
  -> Publishing analytics (needs Instagram Insights sync)

Multi-Tenant
  -> User data isolation (add user_id FKs to 6+ tables, filter ALL queries)
    -> Plan limits enforcement (needs plans table + middleware)
      -> Stripe subscription billing (needs Stripe account + SDK + webhooks)
        -> Customer Portal integration (needs Stripe customer ID)
```

## Critical Path Analysis

**Longest dependency chain:** Image CDN -> Instagram Client wiring -> Calendar UI -> Auto-schedule = 4 steps

**Biggest blocker:** Image CDN/public URL. Without publicly accessible images, Instagram Graph API publishing is completely impossible. `InstagramClient.get_public_image_url()` already has the CDN path ready -- just needs real infrastructure (Cloudflare R2 recommended).

**Second blocker:** Facebook App Review. The `instagram_content_publish` permission requires App Review which takes 1-5 business days. Start this process early, in parallel with CDN setup.

**Third blocker:** Email sending service. Without SMTP/Resend setup, password reset is dead. This is a one-time setup that unblocks all transactional email features.

**User model migrations:** 2FA and OAuth both add columns to User. Plan carefully to batch into a single migration: `totp_secret`, `totp_enabled`, `totp_backup_codes`, `oauth_provider`, `oauth_id`, `stripe_customer_id`, `stripe_subscription_id`, `plan_id`.


## MVP Recommendation

### Phase 1: Pipeline Simplification + Multi-Character
Prioritize:
1. **Manual pipeline mode** -- decouple agents, accept topic+phrase, compose with Pillow only
2. **Per-character pipeline isolation** -- workers use character's visual DNA, system prompt
3. **Content preview gallery** -- approve/reject before scheduling

Defer: Agent refactoring to separate microservice (unnecessary; just make agents optional in pipeline flow)

### Phase 2: Auth v2
Prioritize:
1. **API key encryption** -- quick win, addresses tech debt, Fernet symmetric
2. **Password reset via email** -- set up Resend (free tier: 100 emails/day), implement token flow
3. **TOTP 2FA** -- pyotp + qrcode, backup codes, second step in login

Defer: OAuth Google to Phase 2b (nice-to-have, not blocking anything critical)

### Phase 3: Instagram Auto-Publishing
Prioritize:
1. **Cloudflare R2 setup** -- free egress, S3-compatible, solve the CDN blocker
2. **Facebook App Review** -- submit early, runs in parallel (1-5 business days)
3. **Wire InstagramClient into PublishingService** -- replace placeholder, add token management
4. **Token refresh automation** -- long-lived token management (60-day cycle)
5. **Calendar UI** -- frontend for existing `/publishing/calendar` endpoint

Defer: Instagram Insights feedback loop (v3 feature), multi-platform publishing

### Phase 4: Dashboard v2
Prioritize:
1. **30-day history chart** -- recharts line chart, simple GROUP BY query on existing `api_usage`
2. **Limit alerts** -- threshold banners at 80%/95% of plan limits
3. **Cost report** -- price mapping for Gemini tiers
4. **Publishing analytics** -- wire `get_media_insights()` for published posts

Defer: Advanced analytics, ML-based insights, A/B test results dashboard

### Phase 5: Multi-Tenant + Billing
Prioritize:
1. **User data isolation** -- add `user_id` FKs to 6 tables, filter all queries, single Alembic migration
2. **Plans table + limit enforcement** -- Free/Pro/Enterprise tiers, middleware checks
3. **Stripe Checkout integration** -- subscription creation + 4 critical webhooks
4. **Stripe Customer Portal** -- self-service billing management

Defer: Usage-based metered billing (start with flat tier pricing), team workspaces


## Existing Code Leverage

| New Feature | Existing Code to Leverage | Gap |
|-------------|--------------------------|-----|
| Manual pipeline | `AsyncPipelineOrchestrator`, `background_mode`, `manual_topics` param | Skip L1 agents in manual mode, accept pre-selected backgrounds |
| Per-character runs | `character_id` on PipelineRun, ContentPackage, all image models | Worker-level character context isolation (currently global config) |
| Instagram publish | `InstagramClient` fully implemented (image/carousel/reel/insights), `PublishingService` scaffolded with dispatch pattern | Wire client into `_publish_instagram()`, CDN setup, token refresh |
| Scheduling | `ScheduledPost` model (complete with retry logic), `publishing.py` routes (schedule/cancel/retry/calendar/queue) | Frontend calendar component, auto-schedule logic |
| Scheduler worker | `scheduler_worker.py` with APScheduler, polls every 60s, calls `process_due_posts()` | Already working, just needs real publisher instead of placeholder |
| Password reset | `AuthService`, `User` model, bcrypt hashing | Email service, reset token table, reset endpoints |
| 2FA | `AuthService.login()` returning JWT | `totp_secret` on User, second verification step, QR code generation |
| OAuth | `AuthService.register()` | OAuth flow endpoints, `oauth_provider`/`oauth_id` on User |
| Usage history | `api_usage` table with daily records, `user_id` FK, service/tier/date | 30-day aggregation endpoint, frontend chart |
| User isolation | `user_id` FK on Character (already exists, nullable) | Add `user_id` to 6 more tables, query filtering |
| Billing | None | Greenfield: Stripe SDK, plans table, webhook handler, customer portal |


## Sources

- Codebase analysis: `src/database/models.py` -- 14 ORM models, User has plaintext API keys, Character has `user_id` FK
- Codebase analysis: `src/services/instagram_client.py` -- full Graph API client with publish_image, publish_carousel, publish_reel, get_media_insights, get_account_insights, get_public_image_url
- Codebase analysis: `src/services/publisher.py` -- PublishingService with queue management, dispatch pattern, retry logic, placeholder Instagram publisher
- Codebase analysis: `src/services/scheduler_worker.py` -- APScheduler-based worker, 60s interval, standalone or FastAPI lifespan
- Codebase analysis: `src/api/routes/publishing.py` -- schedule, queue, cancel, retry, calendar endpoints with auth
- Training data: Instagram Graph API publishing flow (container-based, MEDIUM confidence)
- Training data: Stripe billing patterns (Checkout + webhooks, MEDIUM confidence)
- Training data: TOTP 2FA standards (RFC 6238, pyotp library, MEDIUM confidence)
- Training data: OAuth2 authorization code flow (HIGH confidence -- well-established standard)
- Note: Web search and web fetch were unavailable; all API-specific details (rate limits, token expiry, webhook events) are from training data and should be verified against current official documentation before implementation
