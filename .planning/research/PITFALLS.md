# Domain Pitfalls

**Domain:** v2.0 Feature Additions — Pipeline Refactor, Auto-Publishing, Auth v2, Dashboard v2, Multi-Tenant
**Project:** Clip-Flow — Mago Mestre pipeline
**Researched:** 2026-03-24
**Confidence:** HIGH (grounded in codebase analysis + domain expertise)

---

## Critical Pitfalls

Mistakes that cause rewrites, data breaches, or major production incidents.

---

### Pitfall 1: Multi-Tenant Data Leakage — Queries Without user_id Filtering

**What goes wrong:** Every route uses `get_current_user` as a dependency but almost NO query actually filters by `current_user.id`. Characters, content packages, pipeline runs, scheduled posts, themes — all queries return ALL records regardless of who is logged in. When multi-tenant ships, User A sees User B's characters, memes, and scheduled posts.

**Why it happens:** v1 was single-user. `get_current_user` was added for auth gating (401 protection), not data isolation. The repositories (`schedule_repo`, `content_repo`, character queries) have no `user_id` parameter in their list/get methods.

**Consequences:**
- Data breach: users see each other's content, API keys, characters
- Users can cancel/modify each other's scheduled posts
- Users can trigger pipeline runs using other users' characters
- GDPR/LGPD violation if deployed with real users

**Evidence from codebase:**
- `src/api/routes/publishing.py` lines 49-61: `list_queue()` calls `repo.list_posts()` with no user_id filter
- `src/api/routes/publishing.py` line 28-33: `schedule_post()` accepts any `content_package_id` without verifying ownership
- `src/database/models.py`: `ScheduledPost` (line 463) has NO `user_id` column — only `character_id` and `content_package_id`
- `src/database/models.py`: `PipelineRun` (line 163) has NO `user_id` column
- `src/database/models.py`: `ContentPackage` (line 296) has NO `user_id` column
- Only `Character` model has `user_id` FK (confirmed via `characters: Mapped[list["Character"]]` on User)

**Prevention:**
1. Add `user_id` FK to ALL tables that contain user-owned data: `pipeline_runs`, `content_packages`, `scheduled_posts`, `batch_jobs`, `agent_stats` (single migration)
2. Create a `TenantFilterMixin` or repository base class that auto-injects `WHERE user_id = :current_user_id` on all list/get queries
3. Every repository method that lists/gets data MUST accept and enforce `user_id`
4. For cross-resource access (e.g., scheduling someone else's content_package), add explicit ownership check: `if pkg.user_id != current_user.id: raise 403`
5. Write integration tests: create 2 users, create data for each, assert User A cannot see User B's data
6. Consider SQLAlchemy event listeners (`before_insert`) to auto-set `user_id` on INSERT as a safety net

**Detection:** Create a test that registers 2 users, creates a character for each, then asserts GET /characters for User A returns only User A's characters. This test will FAIL today.

**Phase to address:** Multi-tenant phase (Phase 6). Must be the FIRST thing built in that phase — before billing, before API keys per user. However, the user_id column additions should be designed in Phase 1 so the migration is clean.

---

### Pitfall 2: Instagram Graph API — Token Lifecycle Trap

**What goes wrong:** Instagram Graph API requires a Facebook App with `instagram_content_publish` permission. This permission requires Facebook App Review, which takes 2-6 weeks and often gets rejected on first submission. Meanwhile, developers build against short-lived tokens (1 hour) that expire silently, causing the scheduler to fail at 3 AM with no recovery.

**Why it happens:** Instagram's API ecosystem is complex. The current path requires: Facebook Business account -> Facebook App -> Instagram Graph API -> App Review for `instagram_content_publish` + `pages_manage_posts`. Short-lived tokens are easy to get for testing but expire after 1 hour. Long-lived tokens last 60 days but still expire and need refresh.

**Consequences:**
- Scheduler publishes silently fail for hours/days with expired tokens
- Publishing works in dev (short-lived token) but breaks in prod after 1 hour
- App Review rejection blocks the entire auto-publishing feature for weeks
- Long-lived tokens (60 days) still expire — need a refresh mechanism
- The current `_publish_instagram` placeholder (publisher.py lines 146-162) has zero token management — it returns a hardcoded placeholder

**Evidence from codebase:**
- `src/services/publisher.py` lines 146-162: `_publish_instagram()` is a placeholder with no actual API call
- No Instagram token storage in the User model or any other model
- No token refresh mechanism anywhere in the codebase

**Prevention:**
1. Create an `instagram_tokens` table: `user_id`, `access_token` (encrypted), `token_type` (short/long), `expires_at`, `ig_user_id`, `page_id`
2. Build token refresh into the Instagram client from day 1 — exchange short-lived for long-lived token, then schedule refresh before expiry
3. Scheduler must check token validity BEFORE attempting publish (pre-flight check: `if token.expires_at < now + 5min: refresh or fail gracefully`)
4. On token expiry: mark all queued posts as `token_expired` (not `failed`), notify user via dashboard — this prevents retry logic from wasting attempts
5. Submit Facebook App Review EARLY — do it in parallel with development, not after. Requirements: privacy policy URL, business verification, demo video showing the publishing flow
6. For development: use the Graph API Explorer to generate test tokens, but never hard-code them
7. Store token alongside user_id from day 1 (even single-user) to avoid Phase 6 rewrite

**Detection:** Token expiry manifests as HTTP 190 ("access token has expired") or OAuthException from Graph API.

**Phase to address:** Auto-publishing phase (Phase 3). Token management is foundational — build it before the publisher.

---

### Pitfall 3: Instagram Graph API — Two-Step Container Publishing

**What goes wrong:** Developers assume Instagram publishing is a single API call. It is actually a two-step async process: (1) create a media container via POST, (2) poll until container status is `FINISHED`, (3) publish the container via a second POST. If you publish before the container finishes processing, you get a cryptic "media not ready" error.

**Why it happens:** Instagram processes images server-side (resizing, format conversion). The container creation returns immediately with an ID, but the media is not ready for ~5-30 seconds (longer for carousels/video).

**Consequences:**
- Race condition: publish fires before container is ready
- Carousel posts (already supported in v1 via `carousel_count`) require creating N child containers + 1 parent, all must finish processing before publish
- Retry logic retries the PUBLISH step when it should be retrying the POLL step
- Timeout on large images/carousels causes false failures
- The current `_mark_failed` logic (publisher.py lines 180-200) increments retry_count and re-queues — but if the container was already created, re-creating it wastes API quota

**Prevention:**
1. Implement proper async container polling: `GET /{container-id}?fields=status_code` until `FINISHED` or `ERROR`
2. Set polling timeout (60s for single image, 120s for carousel) with exponential backoff (2s, 4s, 8s)
3. Separate error handling for container-creation errors vs publish errors vs polling timeouts
4. For carousels: create all child containers, poll ALL until ready, then create parent container, poll parent, then publish
5. Store `container_id` in `scheduled_posts.publish_result` so retry can resume polling instead of re-uploading
6. Add a `container_status` column or use `publish_result` JSON to track: `container_created` -> `container_ready` -> `published`

**Detection:** Intermittent "media not ready" errors that succeed on retry, or "media already exists" errors on re-upload.

**Phase to address:** Auto-publishing phase (Phase 3). This is core Instagram publishing logic.

---

### Pitfall 4: OAuth Google + Existing JWT Auth — Session Confusion and Account Takeover

**What goes wrong:** Adding OAuth Google login to an existing email+password JWT system creates two parallel auth flows that produce the same JWT but with different guarantees. OAuth users have no password (so password-reset breaks). Email users who later link Google have two login paths that can desync. Worst case: attacker registers with victim's email via OAuth (if email not verified) and takes over the account.

**Why it happens:** The existing `AuthService.login()` (service.py line 51) requires `email` + `password`. OAuth users are created without a password. The User model has `hashed_password: Mapped[str]` as NOT nullable (models.py line 511), so you cannot even create an OAuth user without a schema change.

**Evidence from codebase:**
- `src/database/models.py` line 511: `hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)` — cannot be NULL
- `src/auth/service.py` line 37: `bcrypt.hashpw(password.encode("utf-8"), ...)` will crash on None
- `src/auth/service.py` line 59: `bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8"))` will crash if hashed_password is empty string
- No `auth_provider`, `google_id`, or `oauth_provider` column exists on User model
- No account linking logic exists

**Consequences:**
- OAuth user creation crashes because `hashed_password` is `nullable=False`
- If you set `hashed_password = ""` as a workaround, `bcrypt.checkpw("".encode(), "".encode())` behavior is undefined and may allow empty-password login
- OAuth user calls password-reset: gets a reset email, sets password, now has two auth methods that can conflict
- If email from OAuth matches existing user's email, auto-merge without verification = account takeover
- Refresh token rotation logic assumes single auth path

**Prevention:**
1. Add `auth_provider` column to User model: `"email"`, `"google"`, `"both"` (String(20), default="email")
2. Add `google_id` column: String(255), nullable, unique — stores Google's sub claim
3. Make `hashed_password` nullable (Alembic migration) — OAuth-only users have NULL password
4. Guard password login: `if user.hashed_password is None: raise ValueError("Use Google login")`
5. Guard password-reset: reject for OAuth-only users (`auth_provider == "google"`)
6. On OAuth login with existing email: require explicit account linking (NOT auto-merge). Show "This email is already registered. Log in with password to link your Google account."
7. CRITICAL: Verify `email_verified: true` from Google's ID token before trusting the email
8. Create separate `AuthService.register_oauth(email, google_id, display_name)` method

**Detection:** Try to create a User with `hashed_password=None` — SQLAlchemy will raise IntegrityError. Try with `hashed_password=""` — login with empty password may succeed.

**Phase to address:** Auth v2 phase (Phase 4). Schema changes MUST come before OAuth implementation.

---

### Pitfall 5: Pipeline Refactor — Breaking the Monolithic Orchestrator

**What goes wrong:** The v2 goal is to simplify the pipeline (decouple agents, manual mode with static backgrounds, zero Gemini Image calls). But `AsyncPipelineOrchestrator` (async_orchestrator.py) is a monolith with 30+ constructor parameters, 9 hardcoded agent imports, and tightly coupled layers. Refactoring it risks breaking the existing `manual_topics` flow that already works.

**Why it happens:** The orchestrator grew organically from v1. It imports all 9 agents at module level (lines 19-29), instantiates workers inline, and passes character config as 15+ individual parameters instead of a config object.

**Evidence from codebase:**
- `src/pipeline/async_orchestrator.py` lines 43-75: 30+ constructor parameters including `character_system_prompt`, `character_max_chars`, `character_reference_dir`, `character_dna`, `character_negative_traits`, `character_composition`, `character_rendering`, `character_refs_priority`, `character_watermark`, `character_name`, `character_handle`, `character_branded_hashtags`, `character_caption_prompt`
- Lines 19-29: Direct imports of all 9 agents at module level — importing the module means loading all agent dependencies
- `manual_topics` parameter (line 74) exists but the code path still instantiates the full orchestrator with all its dependencies

**Consequences:**
- Refactoring the orchestrator breaks the API routes in `pipeline.py` that construct it
- Removing agent imports breaks the agent-based pipeline mode
- Changing the constructor signature breaks every call site
- Silent regressions: the manual_topics path stops working because a refactored layer changes its contract

**Prevention:**
1. Do NOT rewrite the orchestrator. Create a NEW `SimplePipelineOrchestrator` for the manual/static flow
2. Keep `AsyncPipelineOrchestrator` as-is for agent-based runs (freeze it)
3. Route selection in API: `mode=manual` -> `SimplePipelineOrchestrator`, `mode=agents` -> `AsyncPipelineOrchestrator`
4. Extract character config into a `PipelineConfig` dataclass — both orchestrators accept it
5. Write integration tests for the manual flow BEFORE refactoring: given topics + character, expect composed images
6. Feature flag: `PIPELINE_VERSION=v1|v2` in `.env` for gradual rollout with instant rollback

**Detection:** Run the existing pipeline with `manual_topics=["test"]` before and after refactor, compare outputs.

**Phase to address:** Pipeline refactor phase (Phase 1). This is the foundation — get it right before building on top.

---

### Pitfall 6: Stripe Webhook Signature Verification — FastAPI Raw Body Trap

**What goes wrong:** Stripe webhooks arrive at a public endpoint (no JWT). FastAPI automatically parses JSON request bodies, but Stripe webhook signature verification requires the RAW body bytes. If you use `request.json()` or a Pydantic model parameter, the re-serialized JSON may differ from the original bytes (whitespace, key ordering), and HMAC signature verification fails silently.

**Why it happens:** FastAPI's dependency injection encourages Pydantic models as parameters. Developers write `async def stripe_webhook(event: dict, request: Request)` which triggers JSON parsing before they can read raw bytes. By the time they call `stripe.Webhook.construct_event()`, the raw body is consumed.

**Consequences:**
- Without verification: anyone can POST fake events (subscription created, payment succeeded) — free premium access
- With incorrect verification: signatures never match, all real webhooks are rejected, billing is broken
- Attacker sends fake `customer.subscription.created` event, gets free tier upgrade
- In production with live money: fake `invoice.paid` events credit accounts without payment

**Prevention:**
1. Webhook endpoint signature: `async def stripe_webhook(request: Request)` — NO Pydantic body parameter
2. Read raw body FIRST: `raw_body = await request.body()`
3. Verify: `stripe.Webhook.construct_event(payload=raw_body, sig_header=request.headers.get("stripe-signature"), secret=STRIPE_WEBHOOK_SECRET)`
4. Webhook endpoint must NOT have `get_current_user` dependency (it is called by Stripe, not users)
5. Store `STRIPE_WEBHOOK_SECRET` separately from `STRIPE_SECRET_KEY` in `.env`
6. Return 200 quickly (within 5 seconds) — do heavy processing in background task
7. Handle duplicate events idempotently: store processed `event.id` in a `stripe_events` table, skip if already seen
8. In dev: use `stripe listen --forward-to localhost:8000/api/webhooks/stripe`

**Detection:** Test by sending a valid webhook payload with a tampered signature header — it should be rejected with 400, not processed.

**Phase to address:** Multi-tenant/billing phase (Phase 6). Build webhook handler with verification from the start — never "add it later."

---

## Moderate Pitfalls

---

### Pitfall 7: Scheduler Worker — Double-Publishing Race Condition

**What goes wrong:** The `scheduler_worker.py` uses APScheduler with a module-level singleton. If FastAPI runs with multiple uvicorn workers (`--workers 4`), each worker process gets its own scheduler instance. All instances query the same DB for due posts, and all process the same posts — causing double, triple, or quadruple publishing.

**Evidence from codebase:**
- `src/services/scheduler_worker.py` line 18: `_scheduler: AsyncIOScheduler | None = None` — module-level singleton per process
- `start_scheduler()` called in FastAPI lifespan — each uvicorn worker calls it independently
- `process_due_posts()` in publisher.py lines 95-96: queries due posts with `get_due_posts()` — no locking mechanism
- Status update to "publishing" (line 105) happens AFTER the query, not atomically — window for race condition

**Prevention:**
1. Use `SELECT ... FOR UPDATE SKIP LOCKED` pattern in `get_due_posts()`: claims rows atomically, other workers skip claimed rows
2. OR: run the scheduler as a separate process (`python -m src.services.scheduler_worker`), not in FastAPI lifespan — only one instance ever runs
3. Add `processing_started_at` and `processing_worker_id` columns to `scheduled_posts` — claim the post before processing
4. If staying with APScheduler in FastAPI: use `--workers 1` and scale horizontally with separate scheduler process
5. Consider replacing APScheduler with a DB-polling pattern: a single cron-like task that uses `FOR UPDATE SKIP LOCKED`

**Detection:** Run 2 uvicorn workers, schedule a post, observe if it gets processed twice.

**Phase to address:** Auto-publishing phase (Phase 3). This must be solved before going to production.

---

### Pitfall 8: Password Reset Token — Insecure Implementation Patterns

**What goes wrong:** Password reset is implemented with tokens that are too long-lived, stored in plaintext, reusable, or sent via unencrypted email without rate limiting. The existing `refresh_tokens` table pattern (hashed, with expiry) is good — but developers often take shortcuts for reset tokens.

**Prevention:**
1. Token must be cryptographically random (32+ bytes via `secrets.token_urlsafe(32)`), hashed with SHA-256 in DB (like refresh tokens do)
2. Short expiry: 15-30 minutes max — not hours, not days
3. Single-use: delete token row on successful password change
4. Rate limit: max 3 reset emails per hour per email address (prevent abuse as spam vector)
5. Do NOT reveal if email exists: always respond "if an account exists, we sent a reset email" (prevents email enumeration)
6. Use a real transactional email service (Resend, SendGrid, AWS SES) — not SMTP from the app server (deliverability will be terrible)
7. Reset token URL must use HTTPS, include a nonce, and expire the URL after first click (not just first use)

**Phase to address:** Auth v2 phase (Phase 4).

---

### Pitfall 9: 2FA TOTP — Recovery Flow Amnesia

**What goes wrong:** TOTP implementation without recovery codes. User enables 2FA, loses phone, account is permanently locked. No admin bypass, no recovery path. This is the single most common 2FA implementation failure.

**Prevention:**
1. At 2FA setup time: generate 8-10 one-time recovery codes (e.g., `secrets.token_hex(4)` each)
2. Store recovery codes HASHED in DB (bcrypt or SHA-256) — never plaintext
3. Show recovery codes ONCE during setup, force user to acknowledge they saved them
4. Each recovery code is single-use: delete after use, show remaining count
5. 2FA verification must happen AFTER password verification (not instead of) — it is a second factor, not a replacement
6. Rate limit TOTP attempts: 5 failures = 15 minute lockout (prevents brute force of 6-digit codes)
7. Encrypt TOTP secret at rest (use Fernet, not just hash — you need to decrypt to generate expected code for verification)
8. Admin "disable 2FA" endpoint for support cases (with audit log)
9. Store 2FA state on User model: `totp_enabled: bool`, `totp_secret: str (encrypted)`, `totp_verified_at: datetime`

**Phase to address:** Auth v2 phase (Phase 4). Recovery codes are NOT optional — they are part of the 2FA feature.

---

### Pitfall 10: Dashboard 30-Day History — N+1 Query and Date Column Ambiguity

**What goes wrong:** Building a 30-day usage chart by querying `api_usage` table day-by-day (30 separate queries), or loading all 30 days of records into Python and aggregating in-memory. Additionally, the `date` column type causes subtle bugs.

**Evidence from codebase:**
- `src/database/models.py` line 564: `date: Mapped[datetime] = mapped_column(DateTime, nullable=False)` — this is DateTime, NOT Date
- Line 572: `UniqueConstraint("user_id", "service", "tier", "date", ...)` — the constraint includes time component, meaning the "uniqueness" depends on exact timestamp matching, which may not work as intended if time varies by microseconds
- The column is named `date` but stores `datetime` — this will confuse every developer who touches it

**Prevention:**
1. Use SQL `GROUP BY DATE(date)` aggregation, not Python loops — single query
2. For the 30-day chart: `SELECT DATE(date) as day, service, SUM(usage_count) FROM api_usage WHERE user_id = :uid AND date >= NOW() - INTERVAL 30 DAY GROUP BY day, service`
3. Consider renaming `date` column to `recorded_at` (DateTime) or changing type to `Date` if time is not needed — the current naming is misleading
4. Verify the UniqueConstraint actually works: if two usage records have the same date but different times, they are NOT considered duplicates
5. Add index on `(user_id, date)` — already exists (`idx_api_usage_user_id`, `idx_api_usage_date`) but a composite index would be faster
6. If api_usage grows large (>100k rows): add a materialized daily summary table refreshed by a background job

**Phase to address:** Dashboard v2 phase (Phase 5). Fix the date ambiguity early to avoid downstream bugs.

---

### Pitfall 11: JWT SECRET_KEY Is 31 Bytes — Amplified by OAuth and 2FA

**What goes wrong:** The project documents this tech debt: "JWT SECRET_KEY is 31 bytes (below 32-byte HS256 minimum)." Adding OAuth and 2FA on top of a weak JWT foundation amplifies the risk — more tokens, more claims, more attack surface, same weak key.

**Evidence from codebase:**
- `PROJECT.md` line 33: "JWT SECRET_KEY is 31 bytes (below 32-byte HS256 minimum)"
- The `jose` library (python-jose) may silently accept a short key without warning

**Prevention:**
1. Generate a new 64-byte SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Add startup validation in `src/auth/jwt.py`: `assert len(SECRET_KEY) >= 32, "SECRET_KEY must be at least 32 bytes for HS256"`
3. Rotate the key as part of v2 launch (invalidates all existing sessions — acceptable at this stage)
4. Document in `.env.example` that SECRET_KEY must be 32+ bytes

**Phase to address:** Auth v2 phase (Phase 4). Fix BEFORE adding OAuth/2FA — this is a 5-minute fix with outsized security impact.

---

### Pitfall 12: API Key Encryption — Plaintext Storage in Multi-Tenant Context

**What goes wrong:** User API keys (`gemini_free_key`, `gemini_paid_key`) are stored as plaintext Text columns. In a multi-tenant system, a SQL injection, admin panel bug, or DB dump exposes every user's Gemini API keys. One compromised key could run up thousands of dollars in API charges.

**Evidence from codebase:**
- `src/database/models.py` lines 517-518: `gemini_free_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` — plaintext
- `PROJECT.md` line 34: "User API keys stored as plaintext (encryption deferred to v2)"

**Prevention:**
1. Encrypt with `cryptography.fernet.Fernet` using a separate `ENCRYPTION_KEY` env var (not the JWT secret)
2. Create `encrypt_api_key(key: str) -> str` and `decrypt_api_key(encrypted: str) -> str` utility functions
3. Encrypt before INSERT, decrypt on read — transparent to the rest of the codebase
4. Never log decrypted keys — mask in all API responses (show only last 4 characters: `...xYz1`)
5. Migration: encrypt all existing plaintext keys in a one-time Alembic migration with data transform
6. Key rotation: if `ENCRYPTION_KEY` is compromised, re-encrypt all keys with new key (store key version alongside encrypted data)

**Phase to address:** Multi-tenant phase (Phase 6), or earlier if any phase adds more user-stored secrets.

---

### Pitfall 13: Instagram Image Requirements — Silent Rejection

**What goes wrong:** Instagram has strict image requirements. Images that violate them are silently rejected or degraded during container creation. The error message is vague ("An unknown error has occurred") without indicating the real issue.

**Evidence from codebase:**
- Pipeline generates images at 1080x1350 (4:5) — this is within Instagram's ratio range (good)
- Images are composed via Pillow — output format depends on save call, may be PNG
- No image validation step exists before publishing
- Carousel mode (`carousel_count` up to 5 slides) requires all images to have identical aspect ratios

**Prevention:**
1. Add pre-publish validation function: check format, dimensions, file size, color mode
2. Convert to JPEG before upload: `image.convert("RGB").save(path, "JPEG", quality=95)` — JPEG required, PNG not accepted for feed posts
3. Convert RGBA to RGB before JPEG save (JPEG does not support alpha channel — Pillow will crash)
4. Strip EXIF metadata (privacy) but keep ICC color profile
5. Max file size: 8MB for images, 100MB for video — compress if needed
6. For carousels: validate all images have the same aspect ratio before creating containers
7. Validate in the publisher (not the composer) — separation of concerns

**Phase to address:** Auto-publishing phase (Phase 3).

---

### Pitfall 14: Alembic Migration Conflicts Across Parallel Features

**What goes wrong:** Multiple phases add migrations simultaneously (multi-tenant adds user_id columns, auth v2 adds auth_provider, dashboard adds summary tables). If developed on branches, Alembic revision chains create a "multiple heads" conflict on merge that blocks deployment.

**Prevention:**
1. Establish convention: each phase gets a migration version range (e.g., 006-009 for pipeline, 010-012 for auth, 013-015 for multi-tenant)
2. Always run `alembic heads` before creating a new migration — if there are multiple heads, merge first with `alembic merge heads`
3. Test migrations on a fresh DB AND on the current production schema (forward) AND test downgrade (backward)
4. Never edit a migration that has been applied to production — create a new migration to fix mistakes
5. Keep migrations small and focused — one logical change per migration (not "add 5 tables and 10 columns")
6. Since phases are sequential (not parallel branches), this risk is lower — but still establish the convention early

**Phase to address:** All phases. Establish convention in Phase 1 (pipeline refactor).

---

### Pitfall 15: process_due_posts Commits Inside a Loop — Partial Failure State

**What goes wrong:** The current `process_due_posts()` method (publisher.py lines 90-133) commits after EACH post (`await self.session.commit()` on lines 107, 113, 126, 131). If the process crashes mid-loop, some posts are marked "published" and some are still "queued" — but there is no way to know which ones actually published to Instagram and which just had their status updated.

**Evidence from codebase:**
- `publisher.py` line 105: `update_status(post.id, "publishing")` then `commit()` on line 107
- `publisher.py` line 112: `_mark_published(post.id, result)` then `commit()` on line 113
- If the process crashes between line 107 (status = "publishing") and line 113 (status = "published"), the post is stuck in "publishing" state forever
- No cleanup job for stuck "publishing" posts

**Prevention:**
1. Add a `publishing_started_at` timestamp — if a post has been in "publishing" state for >5 minutes, consider it stuck
2. Add a cleanup job: `UPDATE scheduled_posts SET status = 'queued' WHERE status = 'publishing' AND updated_at < NOW() - INTERVAL 5 MINUTE`
3. Store the Instagram container_id and publication_id in `publish_result` immediately after each API call — so retry can check if it actually published
4. Consider processing one post per scheduler tick instead of batching — simpler error handling, no partial-batch failures

**Phase to address:** Auto-publishing phase (Phase 3). Fix the stuck-state problem before going to production.

---

## Minor Pitfalls

---

### Pitfall 16: Instagram Rate Limits — 25 Posts Per Day Per Account

**What goes wrong:** Instagram Graph API limits to 25 media publishes per 24-hour rolling window per Instagram account. The scheduler does not track this, and heavy users (or multi-character setups with one Instagram account) hit the limit silently.

**Prevention:**
1. Track daily publish count per Instagram account in DB (not per user — a user could have multiple IG accounts)
2. Pre-flight check before publish: if at 24/25, warn; if at 25, defer to next window
3. Dashboard shows remaining daily capacity
4. For multi-character setups: enforce that characters mapped to the same IG account share the 25/day limit

**Phase to address:** Auto-publishing phase (Phase 3).

---

### Pitfall 17: OAuth State Parameter — CSRF Attack Vector

**What goes wrong:** OAuth flows without a `state` parameter are vulnerable to CSRF. An attacker crafts a URL that links their Google account to the victim's session, gaining access to the victim's account.

**Prevention:**
1. Generate cryptographic `state` parameter: `secrets.token_urlsafe(32)`, store in HTTP-only cookie (not just memory)
2. Verify `state` on callback matches the stored value — reject if missing or mismatched
3. Use `nonce` in the OpenID Connect ID token request for replay protection
4. Set `state` expiry to 10 minutes — reject stale callbacks
5. PKCE (Proof Key for Code Exchange) is now recommended even for server-side OAuth — use it

**Phase to address:** Auth v2 phase (Phase 4).

---

### Pitfall 18: Multi-Character Pipeline — Background Pool Contamination

**What goes wrong:** When running pipeline for multiple characters, static backgrounds from one character's directory are accidentally used for another character if the directory resolution uses a shared/cached path or falls back to a global default.

**Prevention:**
1. Character backgrounds must be fully namespaced: `assets/backgrounds/{character_slug}/`
2. Pipeline must receive explicit `background_dir` per character, never use a global fallback
3. If a character has zero backgrounds, fail loudly ("Character X has no backgrounds") rather than falling back to another character's pool
4. Test: run pipeline for 2 characters in sequence, verify zero cross-contamination in output

**Phase to address:** Multi-character pipeline phase (Phase 2).

---

### Pitfall 19: Stripe Customer/Subscription Sync — Eventual Consistency and Out-of-Order Events

**What goes wrong:** Stripe webhook says "subscription active" but the DB update fails. User sees "free tier" even though they paid. Or: webhook events arrive out of order (`subscription.updated` before `subscription.created`). Or: the same event is delivered twice (Stripe retries on timeout).

**Prevention:**
1. Store Stripe `customer_id` and `subscription_id` on User model — always fetch current state from Stripe API on critical paths (login, feature gate checks)
2. Handle out-of-order events: use `event.created` timestamp, ignore events older than the last processed event for that resource
3. Idempotency: store processed `event.id` in a `stripe_webhook_events` table, skip duplicates
4. On webhook failure: Stripe retries for up to 3 days — design for eventual consistency, not immediate consistency
5. Dashboard "subscription" status should have a "refresh from Stripe" button for support edge cases
6. Use Stripe's `checkout.session.completed` event (not `customer.subscription.created`) for the primary subscription activation flow — it is more reliable

**Phase to address:** Multi-tenant/billing phase (Phase 6).

---

### Pitfall 20: Environment Variable Sprawl — Secret Management at Scale

**What goes wrong:** v1 has ~5 env vars (DATABASE_URL, GOOGLE_API_KEY, SECRET_KEY, etc.). v2 adds: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, ENCRYPTION_KEY, GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, EMAIL_API_KEY (for password reset). That is 13+ secrets, all in `.env`, none validated at startup.

**Prevention:**
1. Add a startup config validator: load all required env vars at app init, fail fast with clear error messages for missing vars
2. Group secrets by feature: `AUTH_*`, `STRIPE_*`, `INSTAGRAM_*`, `EMAIL_*` prefix convention
3. Document every env var in `.env.example` with descriptions and dummy values
4. For production: use a secrets manager (not `.env`) — even a simple encrypted file is better than plaintext `.env` on disk
5. Never log env var values — log only which vars are present/missing

**Phase to address:** Phase 1 (pipeline refactor) — establish the config validation pattern early so all subsequent phases follow it.

---

## Phase-Specific Warnings

| Phase | Feature | Likely Pitfall | Severity | Mitigation |
|-------|---------|---------------|----------|------------|
| 1 - Pipeline Refactor | Decouple agents | Breaking manual_topics flow (P5) | Critical | New orchestrator, keep old one |
| 1 - Pipeline Refactor | Config foundation | Env var sprawl (P20) | Minor | Startup validator pattern |
| 1 - Pipeline Refactor | Migration convention | Alembic conflicts (P14) | Moderate | Version range convention |
| 2 - Multi-Character | Per-character runs | Background cross-contamination (P18) | Minor | Namespace directories strictly |
| 3 - Auto-Publishing | Instagram tokens | Token expiry (P2) | Critical | Build token manager + async refresh |
| 3 - Auto-Publishing | Instagram API | Container polling (P3) | Critical | Two-step publish with polling |
| 3 - Auto-Publishing | Scheduler | Double-publish race (P7) | Moderate | FOR UPDATE SKIP LOCKED or separate process |
| 3 - Auto-Publishing | Image upload | Silent rejection (P13) | Moderate | Pre-publish JPEG validation |
| 3 - Auto-Publishing | Rate limits | 25/day limit (P16) | Minor | Track daily count per IG account |
| 3 - Auto-Publishing | Crash recovery | Stuck "publishing" state (P15) | Moderate | Timeout cleanup job |
| 4 - Auth v2 | JWT foundation | Weak SECRET_KEY (P11) | Moderate | Fix to 32+ bytes FIRST |
| 4 - Auth v2 | OAuth Google | Session confusion + account takeover (P4) | Critical | auth_provider column, nullable password |
| 4 - Auth v2 | OAuth CSRF | Missing state parameter (P17) | Minor | Crypto state + PKCE |
| 4 - Auth v2 | Password reset | Insecure token patterns (P8) | Moderate | Hashed, single-use, short-lived |
| 4 - Auth v2 | 2FA | Recovery lockout (P9) | Moderate | Recovery codes at setup time |
| 5 - Dashboard v2 | 30-day chart | N+1 queries + date ambiguity (P10) | Moderate | SQL aggregation, fix date column |
| 6 - Multi-Tenant | Data isolation | Full data leakage (P1) | Critical | user_id on ALL tables, filter ALL queries |
| 6 - Multi-Tenant | API key storage | Plaintext keys exposed (P12) | Moderate | Fernet encryption |
| 6 - Multi-Tenant | Stripe webhooks | Signature bypass (P6) | Critical | Raw body verification from day 1 |
| 6 - Multi-Tenant | Stripe sync | Out-of-order events (P19) | Minor | Idempotent handler, event store |

---

## Integration Pitfalls (Cross-Phase)

### The Auth-Publishing-Tenant Triangle

When auto-publishing (Phase 3) goes multi-tenant (Phase 6), each user needs their OWN Instagram tokens stored securely. But if Phase 3 stores Instagram tokens globally (single-account assumption), Phase 6 requires a complete rewrite of the token storage layer.

**Prevention:** Even in Phase 3 (single user), store Instagram tokens in a `social_tokens` table with `user_id` FK. Use the same Fernet encryption planned for API keys. This costs minutes now and saves a rewrite later. Table schema: `id, user_id, platform, access_token (encrypted), refresh_token (encrypted), expires_at, platform_user_id, platform_page_id, created_at, updated_at`.

### The Pipeline-Character-Tenant Chain

Pipeline runs create content_packages linked to characters. Characters have user_id. But pipeline_runs, content_packages, and scheduled_posts do NOT have user_id. When multi-tenant arrives, you need to JOIN through character to get user_id, which is slow and error-prone (what if character_id is NULL on a pipeline_run?).

**Prevention:** Add `user_id` FK directly to `pipeline_runs`, `content_packages`, and `scheduled_posts` in the multi-tenant migration. Do not rely on JOIN chains for tenant filtering — denormalize `user_id` for query performance and safety.

### The 2FA-OAuth-Password Reset Interaction

Users with 2FA + OAuth + password create a complex auth state machine. What happens when: OAuth user enables 2FA, then tries to disable it via password-reset? What if a user has 2FA enabled and tries to link Google? The permutation matrix is large.

**Prevention:** Define auth state machine explicitly before implementing:
- `email_only` -> can add 2FA, can add Google
- `google_only` -> can add password (becomes `both`), cannot add 2FA until password is set
- `both` -> can add 2FA, can unlink Google (reverts to `email_only`)
- `email_with_2fa` -> password reset requires 2FA verification first, then disables 2FA as part of reset
- Write tests for EVERY state transition, not just the happy paths

---

## Sources

- Codebase analysis: `src/database/models.py`, `src/api/deps.py`, `src/api/routes/publishing.py`, `src/services/publisher.py`, `src/services/scheduler_worker.py`, `src/pipeline/async_orchestrator.py`, `src/auth/service.py`
- Instagram Graph API Content Publishing documentation (training data, MEDIUM confidence — Meta changes API requirements frequently)
- Stripe Webhook best practices (training data, HIGH confidence — well-established, stable patterns)
- OAuth 2.0 / OpenID Connect security considerations (training data, HIGH confidence — mature standards)
- OWASP authentication cheat sheet (training data, HIGH confidence — industry standard)
- APScheduler distributed execution limitations (training data, HIGH confidence)

**Confidence note:** Instagram API specifics (rate limits, container publishing flow, token refresh mechanics) are based on training data up to early 2025. These SHOULD be verified against current Instagram Graph API documentation before implementation, as Meta frequently changes API requirements and review processes. All other pitfalls are grounded in codebase analysis and well-established security/architecture patterns with HIGH confidence.
