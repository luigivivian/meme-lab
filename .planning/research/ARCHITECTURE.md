# Architecture Patterns

**Domain:** SaaS meme generation platform -- auto-publishing, advanced auth, multi-tenant, billing, analytics
**Researched:** 2026-03-24
**Overall confidence:** MEDIUM (codebase analysis verified, web research unavailable)

## Current Architecture Snapshot

```
[Next.js 15 Frontend]  --(JWT Bearer)-->  [FastAPI Backend]
     13 app pages                            11 route modules
     AuthContext.tsx                          src/api/deps.py (get_current_user)
                                                |
                           +--------------------+-------------------+
                           |                    |                   |
                      [Auth Service        [APScheduler        [Pipeline
                       register/login       singleton            Orchestrator
                       refresh/logout       60s interval]        5 layers]
                       JWT HS256]               |                   |
                           |                    |                   |
                      [SQLAlchemy 2.0 async + MySQL (aiomysql)]
                      [14 tables, 8 repos, 8 migrations]
```

### Critical Gap Identified: Zero Tenant Isolation

The `get_current_user` dependency authenticates requests but **no repository filters data by user_id**. Verified by grep:

- `publishing.py` routes: `current_user` received but never used for filtering
- `ScheduledPostRepository.list_posts()`: no user_id parameter
- `ContentPackageRepository`: no user_id filtering
- `pipeline.py` routes: pipeline runs visible to all users

Only usage tracking (`UsageRepository.get_user_usage(user_id)`) and key resolution (`UsageAwareKeySelector.resolve(user_id)`) are user-scoped. The `Character.user_id` FK exists but is nullable and not enforced in queries.

This is the single biggest architectural change needed.

## Recommended Architecture (v2.0)

### Design Principle: Dependency Injection Over Middleware

Use FastAPI's `Depends()` chain for tenant context rather than ASGI middleware. This keeps the pattern consistent with existing `get_current_user` and allows granular control (some endpoints like Stripe webhooks must bypass auth).

### Component Boundary Map

```
                    FRONTEND (Next.js 15)
    +--------------------------------------------------+
    | (app)/dashboard/   -- Dashboard v2 (charts, cost) |
    | (app)/publishing/  -- Calendar + queue + IG setup  |
    | (app)/settings/    -- 2FA, OAuth, API keys         |
    | (app)/billing/     -- Plans, checkout, invoices     |
    | auth/forgot-password/ -- Password reset             |
    | auth/reset-password/  -- New password form          |
    +--------------------------------------------------+
                          |  JWT Bearer
                          v
                    BACKEND (FastAPI)
    +--------------------------------------------------+
    | src/api/deps.py     -- MODIFY: add TenantContext   |
    |                                                    |
    | src/api/routes/                                    |
    |   auth.py           -- MODIFY: +reset, +2fa,      |
    |                        +oauth endpoints             |
    |   publishing.py     -- MODIFY: +user_id scoping    |
    |   [all 11 modules]  -- MODIFY: pass TenantContext  |
    |   dashboard.py      -- NEW: analytics endpoints    |
    |   billing.py        -- NEW: Stripe endpoints       |
    +--------------------------------------------------+
    | src/auth/                                          |
    |   service.py        -- MODIFY: +reset, +2fa,      |
    |                        +oauth methods               |
    |   jwt.py            -- MODIFY: +temp_token for 2FA |
    |   totp.py           -- NEW: TOTP logic             |
    |   oauth.py          -- NEW: Google OAuth flow      |
    |   email.py          -- NEW: reset email dispatch   |
    +--------------------------------------------------+
    | src/services/                                      |
    |   publisher.py      -- MODIFY: wire real IG client |
    |   instagram_client.py -- MODIFY: per-user tokens   |
    |   scheduler_worker.py -- MODIFY: load user tokens  |
    |   stripe_service.py -- NEW: Stripe integration     |
    |   email_service.py  -- NEW: transactional email    |
    |   cdn_service.py    -- NEW: image upload for IG    |
    +--------------------------------------------------+
    | src/database/                                      |
    |   models.py         -- MODIFY: new tables+columns  |
    |   repositories/     -- MODIFY: all add user_id     |
    |     dashboard_repo.py -- NEW: aggregation queries  |
    |     billing_repo.py   -- NEW: subscriptions        |
    +--------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **TenantContext** (deps.py) | Wraps `get_current_user`, provides `user_id` + `role` + `plan` to all downstream | All route handlers, all services |
| **AuthService (extended)** | Password reset flow, TOTP setup/verify, OAuth code exchange | UserRepo, EmailService, JWT module |
| **TOTPModule** (totp.py) | Generate base32 secrets, produce provisioning URIs, verify 6-digit codes, manage backup codes | AuthService, User model |
| **OAuthModule** (oauth.py) | Google OAuth authorization URL generation, code-to-token exchange, account linking/creation | AuthService, User model |
| **EmailService** | Send password reset links, 2FA backup codes, alert notifications | AuthService, DashboardService |
| **StripeService** | Create Checkout Sessions, handle webhook events, manage plan enforcement | BillingRoutes, Subscription model |
| **DashboardRepo** | 30-day aggregation queries on api_usage, pipeline_runs, scheduled_posts | DashboardRoutes |
| **PublishingService (extended)** | Per-user Instagram tokens, CDN upload, real Graph API publish calls | InstagramClient, CDNService, ScheduledPostRepo |
| **CDNService** | Upload local images to S3/R2, return public URLs for Instagram Graph API | PublishingService |

## Integration Analysis by Feature

### 1. Auto-Publishing Instagram

**Current state:** 90% infrastructure exists. `PublishingService`, `SchedulerWorker`, `InstagramClient`, `ScheduledPost` model, publishing routes, calendar endpoint -- all built. The only placeholder is `_publish_instagram()` (returns fake success).

**Integration points to wire:**

```
publisher.py._publish_instagram(post)
    |
    +--> Load content_package (image_path, caption, hashtags)
    +--> CDNService.upload(image_path) -> public_url
    +--> Load user's Instagram token (encrypted in DB)
    +--> InstagramClient(access_token=user_token, business_id=user_biz_id)
    +--> client.publish_image(public_url, caption)
         OR client.publish_carousel(urls, caption)
    +--> Store publish_result (permalink, media_id)
```

**What changes:**

| File | Change | Risk |
|------|--------|------|
| `publisher.py` lines 146-162 | Replace placeholder with real InstagramClient call | MEDIUM |
| `instagram_client.py` | Already complete, no changes needed | -- |
| `scheduler_worker.py` | Must load per-user IG tokens when processing due posts | MEDIUM |
| NEW `cdn_service.py` | Upload local images to public URL (S3/R2/serve) | LOW |
| NEW `user_instagram_accounts` table | Per-user IG credentials (encrypted) | LOW |

**Image URL problem:** Instagram Graph API requires publicly accessible URLs. The existing `InstagramClient.get_public_image_url()` already handles CDN vs local fallback. For production, use Cloudflare R2 (free egress, S3-compatible API) because images need to persist beyond request lifetime.

**What stays unchanged:** All 8 publishing routes, ScheduledPost model, ScheduledPostRepository, scheduler_worker tick interval, APScheduler singleton pattern.

### 2. Two-Factor Authentication (TOTP)

**Current auth flow:**
```
POST /auth/login {email, password}
  -> verify password
  -> create_access_token + create_refresh_token
  -> return {access_token, refresh_token}
```

**New 2FA flow (two-phase login):**
```
POST /auth/login {email, password}
  -> verify password
  -> IF user.totp_enabled:
       create_temp_token(user_id, purpose="2fa", ttl=5min)
       return {requires_2fa: true, temp_token: "..."}
     ELSE:
       return {access_token, refresh_token}  (unchanged)

POST /auth/login/2fa {temp_token, totp_code}
  -> verify temp_token (not expired, purpose="2fa")
  -> verify TOTP code against user.totp_secret
  -> create_access_token + create_refresh_token
  -> return {access_token, refresh_token}
```

**Implementation details:**

```python
# src/auth/totp.py
import pyotp
import qrcode
from cryptography.fernet import Fernet

def generate_totp_secret() -> str:
    """Generate base32 secret for TOTP."""
    return pyotp.random_base32()

def get_provisioning_uri(secret: str, email: str) -> str:
    """Generate otpauth:// URI for QR code scanning."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name="MemeLab")

def verify_totp(secret: str, code: str) -> bool:
    """Verify a 6-digit TOTP code. Allows 1 window of tolerance."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate one-time-use backup codes."""
    import secrets
    return [secrets.token_hex(4).upper() for _ in range(count)]
```

**What changes:**

| File | Change | Risk |
|------|--------|------|
| `auth/service.py` | Add `setup_2fa()`, `verify_2fa_login()`, `disable_2fa()` | MEDIUM |
| `auth/jwt.py` | Add `create_temp_token()` with purpose claim and short TTL | LOW |
| `auth/schemas.py` | Add 2FA request/response schemas | LOW |
| `routes/auth.py` | Add `POST /auth/2fa/setup`, `POST /auth/2fa/verify-setup`, `POST /auth/login/2fa`, `DELETE /auth/2fa` | LOW |
| `models.py` (User) | Add `totp_secret_encrypted`, `totp_enabled`, `totp_backup_codes` columns | LOW |
| NEW `auth/totp.py` | TOTP generation/verification | LOW |

**Backward compatibility:** Existing login flow unchanged for users without 2FA. The `POST /auth/login` response shape changes (adds optional `requires_2fa` field), which is additive.

### 3. Google OAuth

**Flow:**
```
Frontend: "Sign in with Google" button
  -> redirect to Google OAuth consent screen
  -> Google redirects to /auth/oauth/google/callback?code=...
  -> Backend exchanges code for Google tokens
  -> Extract email + google_id from ID token
  -> Find or create user
  -> Issue JWT tokens
  -> Redirect to frontend with tokens
```

**What changes:**

| File | Change | Risk |
|------|--------|------|
| NEW `auth/oauth.py` | Google OAuth flow (httpx + manual or authlib) | MEDIUM |
| `auth/service.py` | Add `oauth_login(provider, oauth_id, email)` | LOW |
| `routes/auth.py` | Add `GET /auth/oauth/google` (redirect), `GET /auth/oauth/google/callback` | LOW |
| `models.py` (User) | Add `google_oauth_id` column | LOW |

**Design decision:** Use raw httpx for Google OAuth rather than authlib/httpx-oauth. Google's OAuth flow is simple (exchange code at token endpoint, decode ID token), and adding a large dependency for one provider is unnecessary. The existing httpx dependency (used in InstagramClient) suffices.

**Account linking:** If OAuth email matches existing user, link accounts. If new email, create user with `hashed_password=""` (OAuth-only user cannot use password login).

### 4. Password Reset

**Flow:**
```
POST /auth/forgot-password {email}
  -> Find user by email (return 200 regardless -- prevent enumeration)
  -> Generate reset token (secrets.token_urlsafe)
  -> Store hash in password_reset_tokens table (expires 1 hour)
  -> Send email with reset link (async, non-blocking)
  -> return {message: "If email exists, reset link sent"}

POST /auth/reset-password {token, new_password}
  -> Hash token, look up in password_reset_tokens
  -> Verify not expired, not used
  -> Update user's hashed_password
  -> Mark token as used
  -> Invalidate all refresh tokens for user
  -> return {message: "Password updated"}
```

**What changes:**

| File | Change | Risk |
|------|--------|------|
| NEW `password_reset_tokens` table | token_hash, user_id, expires_at, used_at | LOW |
| `auth/service.py` | Add `request_reset(email)`, `reset_password(token, new_pw)` | LOW |
| `routes/auth.py` | Add `POST /auth/forgot-password`, `POST /auth/reset-password` | LOW |
| NEW `services/email_service.py` | Send emails via SMTP or Resend API | MEDIUM |

**Email service choice:** Use Resend (simple REST API, generous free tier 100 emails/day) over raw SMTP. Simpler integration, better deliverability. Fallback: `aiosmtplib` for self-hosted SMTP.

### 5. Multi-Tenant Isolation

**This is the most invasive change.** It touches every repository, every route module, and every service.

**Strategy: TenantContext dependency**

```python
# src/api/deps.py
from dataclasses import dataclass

@dataclass
class TenantContext:
    user_id: int
    role: str
    plan: str
    is_admin: bool

    def can_access(self, resource_user_id: int | None) -> bool:
        """Admin can access all, users only their own."""
        if self.is_admin:
            return True
        return resource_user_id == self.user_id

async def get_tenant(user=Depends(get_current_user)) -> TenantContext:
    return TenantContext(
        user_id=user.id,
        role=user.role,
        plan=getattr(user, 'plan', 'free'),
        is_admin=user.role == "admin",
    )
```

**Repository changes -- every repo gets user_id filtering:**

| Repository | Current | After |
|-----------|---------|-------|
| CharacterRepository | `list_all()` returns all chars | `list_for_user(user_id)` filters by user_id |
| ContentPackageRepository | No user filtering | Filter via content_package.pipeline_run.user_id OR add direct user_id FK |
| ScheduledPostRepository | No user filtering | Add user_id FK, filter in all queries |
| PipelineRunRepository | No user filtering | Add user_id FK, filter in all queries |
| JobRepository | No user filtering | Filter via character.user_id |
| ThemeRepository | Global themes + user themes | is_builtin=True visible to all, custom filtered by user |

**Migration strategy (two-step):**
1. Migration 009a: Add `user_id` columns as NULLABLE + FK
2. Backfill script: SET user_id = 1 for all existing data (admin/seed user)
3. Migration 009b: ALTER to NOT NULL (for tables that require it)

**Tables needing user_id FK addition:**

| Table | Has user_id? | Action |
|-------|-------------|--------|
| characters | YES (nullable) | Make required for new records |
| pipeline_runs | NO | ADD user_id FK |
| scheduled_posts | NO | ADD user_id FK |
| content_packages | NO (has pipeline_run_id) | ADD user_id FK for direct queries |
| batch_jobs | NO | ADD user_id FK |

### 6. Stripe Billing

**Webhook endpoint -- unauthenticated, signature-verified:**

```python
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(db_session),
):
    """Stripe calls this directly. No JWT auth. Verify via signature."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid webhook signature")

    service = StripeService(session)
    await service.handle_event(event)
    return {"status": "ok"}
```

**Events to handle:**

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create/activate subscription, set user.plan |
| `invoice.paid` | Extend subscription period |
| `invoice.payment_failed` | Mark subscription as past_due |
| `customer.subscription.updated` | Sync plan changes |
| `customer.subscription.deleted` | Downgrade to free plan |

**Idempotency:** Store processed `event.id` values. Skip duplicates. Stripe retries failed webhooks.

**New tables:**

```python
class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(100))
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    plan: Mapped[str] = mapped_column(String(30), default="free")
    status: Mapped[str] = mapped_column(String(30), default="active")
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

class StripeEvent(Base):
    """Idempotency table for processed webhook events."""
    __tablename__ = "stripe_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True)
    event_type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### 7. Dashboard v2 Analytics

**Pure aggregation -- no new data collection needed.** Existing tables have all required data.

**Endpoints:**

| Endpoint | Source Tables | Query Pattern |
|----------|-------------|---------------|
| `GET /dashboard/usage-history?days=30` | api_usage | GROUP BY date, SUM(usage_count) WHERE user_id=X |
| `GET /dashboard/pipeline-stats?days=30` | pipeline_runs | COUNT, AVG(duration), SUM(packages_produced) WHERE user_id=X |
| `GET /dashboard/publishing-stats?days=30` | scheduled_posts | COUNT by status WHERE user_id=X |
| `GET /dashboard/cost-report?days=30` | api_usage | usage_count * price_per_unit by service/tier |
| `GET /dashboard/alerts` | api_usage | Check % of daily limit used |

**What stays:** The existing `GET /auth/me/usage` endpoint (today's snapshot) remains. Dashboard adds time-series history.

## Data Flow Changes

### Current Flow (v1.0)
```
User -> POST /pipeline/run -> BackgroundTask -> AsyncPipelineOrchestrator
  L1: 9 agents fetch trends (unscoped)
  L2: Broker dedup
  L3: Curator selects topics via LLM
  L4: PhraseWorker + ImageWorker (Gemini/static) + Pillow compose
  L5: CaptionWorker + HashtagWorker + QualityWorker
  -> ContentPackages saved (no user_id)
```

### v2.0 Pipeline Flow
```
User -> POST /pipeline/run (manual_topics, background_mode="static")
  -> TenantContext extracts user_id
  -> AsyncPipelineOrchestrator(user_id=X, character_id=Y)
  L1-L3: SKIPPED (manual topics provided)
  L4: PhraseWorker (Gemini text, user's API key) + ImageWorker (static BG ONLY) + Pillow compose
  L5: CaptionWorker + HashtagWorker + QualityWorker
  -> ContentPackages saved WITH user_id
  -> Optional: auto-schedule for publishing
```

### v2.0 Auto-Publishing Flow
```
ContentPackage exists -> User POST /publishing/schedule
  -> ScheduledPost(user_id=X, status=queued, scheduled_at=T)
  -> APScheduler tick every 60s
  -> PublishingService.process_due_posts()
  -> For each due post:
      -> Load user's IG credentials (decrypt)
      -> CDNService.upload(image_path) -> public_url
      -> InstagramClient(access_token=user_token).publish_image(url, caption)
      -> Update status=published, store permalink
```

### v2.0 Login Flow (with 2FA)
```
POST /auth/login {email, password}
  -> Verify password ✓
  -> user.totp_enabled == True?
     YES -> return {requires_2fa: true, temp_token: "eyJ..."}
     NO  -> return {access_token, refresh_token}

POST /auth/login/2fa {temp_token, totp_code}
  -> Verify temp_token (5min TTL, purpose="2fa")
  -> Verify TOTP code (pyotp, valid_window=1)
  -> return {access_token, refresh_token}
```

## Patterns to Follow

### Pattern 1: Tenant-Scoped Repository

**What:** Every repository method that reads user data filters by `user_id`. Admin bypasses filter.
**When:** All data-access operations on user-owned resources.

```python
class ScheduledPostRepository:
    def __init__(self, session: AsyncSession, user_id: int | None = None):
        self.session = session
        self.user_id = user_id

    def _scoped(self, stmt):
        """Apply tenant filter if user_id is set."""
        if self.user_id is not None:
            stmt = stmt.where(ScheduledPost.user_id == self.user_id)
        return stmt

    async def list_posts(self, limit=50, offset=0, **filters):
        stmt = select(ScheduledPost).order_by(ScheduledPost.scheduled_at.asc())
        stmt = self._scoped(stmt)  # tenant filter
        # ... apply other filters
```

### Pattern 2: Encrypted Secrets at Rest

**What:** User tokens (Instagram, TOTP secrets) encrypted with Fernet. Server-side key in env.
**When:** Storing any credential that must be decrypted (not hashed like passwords).

```python
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.environ["ENCRYPTION_KEY"]  # Fernet.generate_key()
_fernet = Fernet(ENCRYPTION_KEY)

def encrypt_token(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()

def decrypt_token(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
```

### Pattern 3: Two-Phase Login for 2FA

**What:** Login returns temp token if 2FA enabled. Second endpoint exchanges temp + TOTP for real JWT.
**When:** Users with `totp_enabled = True`.

The temp token is a standard JWT with `{"purpose": "2fa", "sub": user_id, "exp": now+5min}`. It cannot be used as a normal access token because `get_current_user` checks `type == "access"`.

### Pattern 4: Webhook Signature Verification

**What:** Stripe webhook endpoint bypasses JWT auth. Verify using HMAC from `stripe-signature` header.
**When:** `POST /billing/webhook`.

Must be excluded from `get_current_user` dependency. Register the route directly, not under the auth-protected prefix.

### Pattern 5: Gradual Multi-Tenant Migration

**What:** Add user_id columns as nullable first, backfill, then make non-nullable.
**When:** Retrofitting tenant isolation on existing tables with data.

```python
# Migration 009a: nullable
op.add_column("pipeline_runs", sa.Column("user_id", sa.Integer, nullable=True))
op.create_foreign_key(None, "pipeline_runs", "users", ["user_id"], ["id"])

# Migration 009b: after backfill
op.alter_column("pipeline_runs", "user_id", nullable=False)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Filtering in Routes Instead of Repositories

**What:** Adding `WHERE user_id = x` in route handlers.
**Why bad:** Easy to forget in one route = data leak. 11 route files, dozens of endpoints.
**Instead:** Tenant filtering always in repository layer. Routes pass TenantContext to service/repo. Single audit point.

### Anti-Pattern 2: Synchronous Email in Request Path

**What:** Sending password reset email synchronously during API request.
**Why bad:** SMTP is slow (2-5s). Also reveals whether email exists (timing side-channel).
**Instead:** `asyncio.create_task(send_email(...))`. Return 200 immediately. Log failures separately.

### Anti-Pattern 3: Plaintext TOTP Secrets

**What:** Storing TOTP base32 secret directly in DB column.
**Why bad:** DB breach exposes all 2FA secrets, making 2FA worthless.
**Instead:** Encrypt with Fernet. Attacker needs both DB dump AND server key.

### Anti-Pattern 4: Processing Stripe Webhooks Without Idempotency

**What:** Handling `checkout.session.completed` without checking if already processed.
**Why bad:** Stripe retries. Double-processing creates duplicate subscriptions.
**Instead:** `stripe_events` table with unique `event_id`. Skip if already seen.

### Anti-Pattern 5: Global Instagram Token

**What:** Current `config.INSTAGRAM_ACCESS_TOKEN` is a single global env var.
**Why bad:** Multi-tenant means each user has their own Instagram Business account.
**Instead:** Per-user encrypted tokens in `user_instagram_accounts` table. Global token only for admin/testing.

### Anti-Pattern 6: Global Config Mutation

**What:** `_run_pipeline_task` mutates global config objects.
**Why bad:** Race condition when two users run pipelines simultaneously.
**Instead:** Pass configuration as parameters through the call chain.

## New vs Modified Summary

### NEW Components (14 files)

| File | Phase | Purpose |
|------|-------|---------|
| `src/auth/totp.py` | Auth v2 | TOTP secret gen, verify, backup codes |
| `src/auth/oauth.py` | Auth v2 | Google OAuth code exchange |
| `src/auth/email.py` | Auth v2 | Password reset token + email dispatch |
| `src/services/stripe_service.py` | Multi-tenant | Checkout, webhook handler, plan enforcement |
| `src/services/email_service.py` | Auth v2 | SMTP/Resend transactional email |
| `src/services/cdn_service.py` | Auto-publish | Upload images to S3/R2 for public URLs |
| `src/api/routes/billing.py` | Multi-tenant | Stripe checkout, portal, webhook |
| `src/api/routes/dashboard.py` | Dashboard v2 | Analytics aggregation endpoints |
| `src/database/repositories/dashboard_repo.py` | Dashboard v2 | Time-series aggregation queries |
| `src/database/repositories/billing_repo.py` | Multi-tenant | Subscriptions CRUD |
| `password_reset_tokens` model | Auth v2 | Reset token storage |
| `user_instagram_accounts` model | Auto-publish | Per-user IG credentials |
| `subscriptions` model | Multi-tenant | Stripe subscription sync |
| `stripe_events` model | Multi-tenant | Webhook idempotency |

### MODIFIED Components (risk-ordered)

| File | Change | Risk |
|------|--------|------|
| ALL 8 repositories | Add user_id filtering to all query methods | **HIGH** -- pervasive, miss one = data leak |
| ALL 11 route modules | Pass TenantContext to services | **HIGH** -- pervasive |
| `src/api/deps.py` | Add TenantContext dependency | LOW -- additive |
| `src/auth/service.py` | Add reset, 2FA, OAuth methods | MEDIUM -- core auth |
| `src/auth/jwt.py` | Add temp_token creation for 2FA flow | MEDIUM -- affects auth flow |
| `src/auth/schemas.py` | New request/response schemas | LOW -- additive |
| `src/database/models.py` (User) | Add totp, oauth, stripe, plan columns | LOW -- additive ALTER |
| `src/database/models.py` (new tables) | 4 new ORM models | LOW -- additive |
| `publisher.py` lines 146-162 | Wire real InstagramClient | MEDIUM |
| `scheduler_worker.py` | Load per-user IG tokens | MEDIUM |
| `instagram_client.py` | Accept per-user tokens (already parameterized) | LOW |
| Migration 009 | Schema changes for all new tables + columns | LOW |

## Suggested Build Order

```
Phase 1: Pipeline Refactor + Multi-Character
  Rationale: Establishes user_id threading pattern, foundation for all features.
  Dependencies: None
  Risk: LOW -- extends existing code, no new external integrations

Phase 2: Tenant Isolation
  Rationale: Must happen before user-facing features to prevent data leakage.
  Dependencies: Phase 1 (user_id on pipeline_runs)
  Risk: HIGH -- touches every repo and route, regression testing critical

Phase 3: Auth v2 (Reset + 2FA + OAuth)
  Rationale: Security foundation needed before exposing billing/publishing to users.
  Dependencies: Phase 2 (tenant context infrastructure)
  Risk: MEDIUM -- new auth flows, must not break existing login

Phase 4: Auto-Publishing Instagram
  Rationale: Core product value. Depends on tenant isolation for per-user IG tokens.
  Dependencies: Phase 2 (per-user credentials), Phase 3 (OAuth pattern reuse for IG)
  Risk: MEDIUM -- external API integration, image CDN setup

Phase 5: Dashboard v2
  Rationale: Monitoring and cost visibility. Pure SQL aggregation, low risk.
  Dependencies: Phase 2 (user-scoped metrics)
  Risk: LOW -- read-only aggregation, no new external dependencies

Phase 6: Multi-Tenant Billing (Stripe)
  Rationale: Monetization layer. Last because it needs plan enforcement across all features.
  Dependencies: Phase 2 (tenant context), Phase 5 (usage data for billing)
  Risk: MEDIUM -- Stripe webhooks, payment handling requires careful testing
```

**Why this order:**
1. Pipeline refactor is the foundation -- establishes patterns everything else needs
2. Tenant isolation early prevents data leakage as features are added
3. Auth v2 before user-facing features ensures security baseline
4. Auto-publishing is the highest user-value feature after the foundation
5. Dashboard provides visibility needed for billing decisions
6. Billing last because it gates access to all previous features

## Key Libraries Required

| Library | Purpose | Confidence |
|---------|---------|------------|
| `pyotp` | TOTP generation/verification (RFC 6238) | HIGH |
| `cryptography` (Fernet) | Encrypt user secrets at rest | HIGH |
| `stripe` | Stripe API SDK + webhook verification | HIGH |
| `qrcode[pil]` | Generate QR codes for TOTP setup | HIGH |
| `resend` | Transactional email (password reset, alerts) | MEDIUM |
| `boto3` or `httpx` | S3/R2 image upload for CDN | MEDIUM |

## Scalability Considerations

| Concern | At 10 users | At 1K users | At 10K users |
|---------|-------------|-------------|--------------|
| DB queries | No concern | Add composite indexes on (user_id, created_at) | Read replicas or move to Postgres |
| Instagram API | 1-10 accounts | Each user's own rate limits | No server concern |
| Scheduler | Single APScheduler, 60s | Fine | Batch per-user, distributed lock |
| Stripe webhooks | ~10/day | ~1K/day | Async queue (Redis) |
| Image storage | Local disk | S3/R2, ~10GB | S3/R2 with lifecycle policies |
| Email | Direct SMTP | Resend/SES | SES with queue |
| Pipeline runs | Sequential BackgroundTasks | asyncio.gather per user | Task queue (ARQ/Celery) |

## Sources

- **Codebase analysis (HIGH confidence):** All 14 ORM models, 11 route modules, AuthService, PublishingService, InstagramClient, SchedulerWorker, config.py, deps.py, jwt.py
- **Existing infrastructure verified:** APScheduler singleton, httpx for Instagram Graph API, SQLAlchemy 2.0 async session factory, bcrypt passwords, SHA-256 refresh token hashing
- **Training data (MEDIUM confidence):** Stripe webhook patterns, pyotp TOTP flow, Google OAuth OIDC flow, Fernet encryption pattern, S3-compatible upload
- **Not verified (LOW confidence):** Exact Stripe API v2025+ changes, Instagram Graph API v21.0 specifics, Resend SDK current API
