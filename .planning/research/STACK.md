# Technology Stack -- v2.0 New Feature Additions

**Project:** Clip-Flow v2.0 (Pipeline Simplification, Auto-Publishing, Multi-Tenant)
**Researched:** 2026-03-24
**Overall confidence:** HIGH -- all recommendations verified against codebase; version pins use >= to let pip resolve latest compatible

---

## Existing Stack (reference only -- NOT re-researched)

- Python 3.14, FastAPI, SQLAlchemy 2.0 async, MySQL/aiomysql, Alembic (8 migrations)
- Next.js 15, TypeScript, Tailwind CSS v4, Radix UI, SWR 2.x, Framer Motion, Lucide React
- Google Gemini API (text), Pillow, bcrypt, PyJWT (`import jwt`), httpx, APScheduler
- cryptography (Fernet for API key encryption), PyYAML, feedparser
- 14 ORM tables, users + refresh_tokens + api_usage already exist

**Gap found:** PyJWT is used in `src/auth/jwt.py` but NOT listed in `requirements.txt`. Add `PyJWT>=2.8.0` to requirements.txt during next phase.

---

## Recommended Stack

### New Python Backend Libraries (5 packages)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **aiosmtplib** | >=2.0.0 | Async SMTP for password reset emails | Native asyncio, works with FastAPI without blocking. ~50KB. Universal: swap SMTP provider by changing env vars. |
| **pyotp** | >=2.9.0 | TOTP 2FA generation/verification | De facto Python TOTP library. RFC 6238 compliant. Zero dependencies. Works with Google Authenticator, Authy, 1Password. |
| **qrcode[pil]** | >=8.0 | QR code for authenticator app setup | Generates PNG QR codes users scan to set up 2FA. `[pil]` extra uses Pillow (already installed). |
| **authlib** | >=1.3.0 | Google OAuth 2.0 / OpenID Connect | Full OAuth2+OIDC. Integrates natively with httpx (already in stack) via `AsyncOAuth2Client`. Handles Google login flow. |
| **stripe** | >=11.0.0 | Stripe billing SDK (official) | Official Python SDK. Subscriptions, invoices, webhooks, customer portal. Supports BRL. |

### New Frontend Libraries (1 package)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **recharts** | >=2.15.0 | Dashboard charts (usage history, cost reports) | Built on D3, React-native components. Declarative API. ~45KB gzipped. Most popular React chart library. |

### Infrastructure (no new services)

No new infrastructure needed. MySQL handles everything. No Redis, no message queue, no new databases.

---

## Detailed Rationale by Feature Area

### 1. Instagram Auto-Publishing

**No new libraries needed.** Existing code fully covers this.

| Component | File | Status |
|-----------|------|--------|
| Instagram Graph API client | `src/services/instagram_client.py` | COMPLETE -- async httpx, image/carousel/reel/insights |
| Publishing service | `src/services/publisher.py` | COMPLETE -- queue processing, retry logic, platform dispatch |
| Scheduler worker | `src/services/scheduler_worker.py` | COMPLETE -- APScheduler 60s interval |

**What needs wiring (zero new deps):**
- Connect `InstagramClient` into `PublishingService._publish_instagram()` (currently returns placeholder -- line 146)
- Facebook long-lived token exchange via httpx (standard HTTP calls to `graph.facebook.com/oauth/access_token`)
- Per-user `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_BUSINESS_ID` storage in users table (multi-tenant)
- Image URL exposure: configure `INSTAGRAM_CDN_BASE` or use FastAPI static files + ngrok/tunnel

**Calendar UI:** recharts handles timeline visualization, existing Radix components handle date inputs.

**Confidence:** HIGH -- code reviewed directly, all methods implemented.

---

### 2. SMTP for Password Reset Emails

**Use aiosmtplib because** it is the standard async SMTP client for Python. Direct use, no framework wrapper needed for 2 email types (password reset + optional verification).

| Rejected | Reason |
|----------|--------|
| `smtplib` (stdlib) | Synchronous. Would need `asyncio.to_thread()` for every send. |
| `fastapi-mail` | Wraps aiosmtplib + Jinja2. Overkill for 2 email types. |
| SendGrid/Mailgun SDK | Vendor lock-in. SMTP is universal: swap provider by changing 4 env vars. |

**Implementation pattern:**
```python
import aiosmtplib
from email.message import EmailMessage

async def send_reset_email(to: str, reset_token: str):
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = "Redefinir senha - Clip-Flow"
    msg.set_content(f"Link: {FRONTEND_URL}/reset-password?token={reset_token}")

    await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT,
                          username=SMTP_USER, password=SMTP_PASS, use_tls=True)
```

**DB addition:** `password_reset_tokens` table (token_hash, user_id, expires_at, used_at). Tokens expire in 1 hour, single-use.

**Confidence:** HIGH

---

### 3. TOTP for Two-Factor Authentication (2FA)

**Use pyotp because** there is no competing library worth considering. pyotp IS the Python TOTP library (~3.5k GitHub stars, actively maintained, zero deps, RFC 6238).

**Implementation pattern:**
```python
import pyotp, qrcode, io

def setup_2fa(email: str) -> tuple[str, bytes]:
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="Clip-Flow")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return secret, buf.getvalue()

def verify_2fa(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)  # +/- 30s tolerance
```

**DB additions on `users` table:**
- `totp_secret` VARCHAR(64) nullable -- encrypted with Fernet (cryptography already installed)
- `totp_enabled` BOOLEAN default false
- New `backup_codes` table -- hashed recovery codes (10 codes, bcrypt-hashed)

**Auth flow change:** After successful password login, if `totp_enabled=true`, return a temporary `2fa_required` response instead of the JWT. Frontend shows TOTP input. Second request with code completes login and returns JWT.

**Confidence:** HIGH

---

### 4. OAuth Google Login

**Use authlib because** it provides full OAuth2+OIDC with native httpx integration (`AsyncOAuth2Client`). Handles Google, GitHub, any provider. Well-maintained (~4k stars).

| Rejected | Reason |
|----------|--------|
| `python-social-auth` | Heavy Django-oriented framework. Brings its own ORM, pipelines, session management. Overkill. |
| Manual OAuth (python-jose) | Requires building entire flow: state, PKCE, token exchange, JWKS verification. Error-prone. |
| `fastapi-sso` | Thin wrapper, limited providers, less maintained than authlib. |

**Note:** authlib does NOT replace PyJWT. authlib handles the Google OAuth dance; PyJWT continues to issue app JWTs.

**Implementation pattern:**
```python
from authlib.integrations.httpx_client import AsyncOAuth2Client

google = AsyncOAuth2Client(
    client_id=GOOGLE_OAUTH_CLIENT_ID,
    client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
    redirect_uri=f"{API_URL}/auth/google/callback",
)

# Route: /auth/google -> redirect to Google consent screen
# Route: /auth/google/callback -> exchange code, get user info, create/link account, issue JWT
```

**DB additions on `users` table:**
- `oauth_provider` VARCHAR(20) nullable -- "google" or null for email/password
- `oauth_id` VARCHAR(255) nullable -- Google unique user ID
- `password_hash` becomes nullable (OAuth-only users have no password)

**Confidence:** HIGH

---

### 5. Stripe for Billing/Payment (Multi-Tenant)

**Use Stripe Checkout (hosted), not custom payment forms.** This means:
- Backend creates a Checkout Session URL, frontend redirects to it
- Zero frontend Stripe SDK needed (`@stripe/react-stripe-js` NOT required)
- Stripe handles PCI compliance, card input, 3D Secure
- Customer Portal for subscription management (self-service, less backend code)

**Implementation pattern:**
```python
import stripe
stripe.api_key = STRIPE_SECRET_KEY

# Checkout session for subscription
session = stripe.checkout.Session.create(
    customer=customer_stripe_id,
    mode="subscription",
    line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
    success_url=f"{FRONTEND_URL}/billing?success=true",
    cancel_url=f"{FRONTEND_URL}/billing?canceled=true",
)
# Return session.url to frontend -> frontend does window.location.href = url

# Webhook handler (critical for subscription state)
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers["stripe-signature"]
    event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    match event.type:
        case "customer.subscription.created": ...
        case "customer.subscription.updated": ...
        case "customer.subscription.deleted": ...
        case "invoice.payment_failed": ...
```

**DB additions:**
- `stripe_customer_id` VARCHAR(255) on `users` table
- New `subscriptions` table: stripe_subscription_id, user_id, plan, status, current_period_start, current_period_end

**Confidence:** HIGH -- official SDK, architecture pattern well-established.

---

### 6. Dashboard Charts (Frontend)

**Use recharts because** it is built on D3, uses React-native components with declarative API, and is the most popular React charting library. ~45KB gzipped.

| Rejected | Reason |
|----------|--------|
| `chart.js` + `react-chartjs-2` | Canvas-based, harder to style with Tailwind, imperative API. |
| `@nivo/core` | Heavier (~100KB+). Overkill for usage/cost charts. |
| `visx` (Airbnb) | Low-level D3 wrapper. Maximum flexibility but too much effort for standard dashboard charts. |
| `tremor` | Full dashboard component library. Would conflict with existing Radix UI components. |

**Dashboard v2 charts needed:**
- 30-day usage history: `LineChart` (API calls per day)
- Limit alerts (80%/95%): horizontal `ReferenceLine` on the line chart
- Cost report: `BarChart` (cost per service per period)

**Confidence:** HIGH

---

### 7. Pipeline Simplification & Multi-Character

**No new libraries needed.** Pure architectural refactoring using existing tools.

| Change | Uses |
|--------|------|
| Decouple trend agents | Code restructuring only |
| Manual pipeline trigger | FastAPI (existing) |
| Skip Gemini Image | Pillow (existing) |
| Theme-based composition | PyYAML (existing) |
| Per-character pipeline | SQLAlchemy queries filtered by character_id (existing) |

**Confidence:** HIGH

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| SMTP | aiosmtplib | fastapi-mail | Only 2 email types; direct SMTP is simpler |
| SMTP | aiosmtplib | SendGrid SDK | Vendor lock-in; SMTP is universal |
| OAuth | authlib | python-social-auth | Django-heavy, brings own ORM models |
| OAuth | authlib | fastapi-sso | Less maintained, fewer providers |
| TOTP | pyotp | Manual HMAC | pyotp is the standard; no reason to reimplement RFC 6238 |
| Charts | recharts | @nivo/core | Overkill for simple dashboard charts |
| Charts | recharts | tremor | Conflicts with existing Radix UI design system |
| Payments | Stripe Checkout (hosted) | Custom Stripe Elements | Checkout avoids PCI scope, needs zero frontend SDK |
| Task Queue | APScheduler (keep) | Celery/Dramatiq | Would add Redis + worker process; APScheduler handles publishing loop fine |

---

## Complete New Dependencies Summary

### Python Backend (5 new packages)

```
aiosmtplib>=2.0.0        # Async SMTP for password reset emails
pyotp>=2.9.0             # TOTP 2FA generation/verification
qrcode[pil]>=8.0         # QR code for authenticator setup (uses Pillow, already installed)
authlib>=1.3.0           # Google OAuth 2.0 client (uses httpx, already installed)
stripe>=11.0.0           # Stripe billing SDK
```

**Also add (missing from requirements.txt):**
```
PyJWT>=2.8.0             # Already used in src/auth/jwt.py but not listed in requirements.txt
```

**Total new install footprint:** ~2MB (stripe is the largest at ~1.5MB)

### Frontend (1 new package)

```
recharts>=2.15.0         # Dashboard charts (line, bar, area)
```

**Bundle impact:** ~45KB gzipped

### Installation Commands

```bash
# Backend -- add to requirements.txt and install
pip install "aiosmtplib>=2.0.0" "pyotp>=2.9.0" "qrcode[pil]>=8.0" "authlib>=1.3.0" "stripe>=11.0.0" "PyJWT>=2.8.0"

# Frontend
cd memelab && npm install recharts
```

---

## What NOT to Add

| Library | Why Not |
|---------|---------|
| `celery` / `dramatiq` | APScheduler already handles the 60s publishing loop. A task queue adds Redis + worker process complexity. Revisit only if job volume exceeds what APScheduler handles. |
| `redis` | PROJECT.md: "MySQL-based counter suficiente." Redis adds infrastructure. Not needed until APScheduler proves insufficient. |
| `fastapi-mail` | Wraps aiosmtplib + Jinja2 templates. Project has 2 email types. Direct aiosmtplib is simpler. |
| `python-social-auth` | Heavy Django framework. authlib handles OAuth cleanly. |
| `next-auth` / `Auth.js` | Project has working custom JWT auth. Introducing next-auth means rewriting entire frontend auth. Add Google OAuth within existing pattern instead. |
| `@stripe/react-stripe-js` | Only needed for custom payment forms. Stripe Checkout (hosted page) needs zero frontend SDK. |
| `passlib` | bcrypt is already working directly in the codebase. passlib adds unnecessary abstraction. |
| `python-jose` | Codebase uses PyJWT directly (`import jwt`). Both work. Do not switch. |
| `slowapi` | Rate limiting is already MySQL-based via api_usage table. Works fine. |
| `@tanstack/react-query` | SWR is already in the stack for data fetching. Do not add a competing library. |
| `Jinja2` (for emails) | Two email types do not justify a template engine. f-strings or string.Template suffice. |

---

## New Environment Variables

```env
# SMTP (Password Reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASS=app-password-here
SMTP_FROM="Clip-Flow <noreply@yourdomain.com>"

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=xxx

# Stripe Billing
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx

# URLs (for OAuth callbacks, email links, Stripe redirects)
FRONTEND_URL=http://localhost:3000
API_URL=http://127.0.0.1:8000
```

---

## Database Schema Additions (Preview)

### Modified: `users` table (new columns)

| Column | Type | Purpose |
|--------|------|---------|
| `totp_secret` | VARCHAR(64) nullable | Fernet-encrypted TOTP secret |
| `totp_enabled` | BOOLEAN default false | Whether 2FA is active |
| `oauth_provider` | VARCHAR(20) nullable | "google" or null |
| `oauth_id` | VARCHAR(255) nullable | Provider unique user ID |
| `stripe_customer_id` | VARCHAR(255) nullable | Stripe customer reference |
| `password_hash` | Make nullable | OAuth-only users have no password |
| `instagram_access_token` | TEXT nullable | Fernet-encrypted, per-user (multi-tenant) |
| `instagram_business_id` | VARCHAR(100) nullable | Per-user IG business account |

### New tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `password_reset_tokens` | Single-use reset links | token_hash, user_id, expires_at, used_at |
| `backup_codes` | 2FA recovery codes | user_id, code_hash, used_at |
| `subscriptions` | Stripe subscription state | stripe_subscription_id, user_id, plan, status, current_period_end |

---

## Phase Ordering Implications (from stack perspective)

1. **Pipeline refactor** -- Zero new deps. Pure code restructuring. Do first because it simplifies everything downstream.
2. **Multi-character pipeline** -- Zero new deps. Uses existing Pillow + themes + SQLAlchemy queries filtered by character_id.
3. **Auth v2 (SMTP + TOTP + OAuth)** -- 3 small new Python libs (aiosmtplib, pyotp+qrcode, authlib). Builds on existing auth module.
4. **Dashboard v2** -- 1 new frontend lib (recharts). Independent of auth changes. Backend uses existing SQLAlchemy for aggregation queries.
5. **Auto-publishing Instagram** -- Zero new deps. Wires existing InstagramClient into PublishingService. Needs per-user token storage from auth v2.
6. **Multi-tenant + Stripe** -- 1 new Python lib (stripe). Most complex phase. Needs auth v2 (user isolation) + dashboard v2 (billing UI) as prerequisites.

---

## Sources

- `src/services/instagram_client.py` -- direct code review (HIGH confidence)
- `src/services/publisher.py` -- direct code review, confirmed placeholder at line 146 (HIGH confidence)
- `src/services/scheduler_worker.py` -- direct code review (HIGH confidence)
- `src/auth/jwt.py` -- direct code review, confirmed PyJWT usage (HIGH confidence)
- `requirements.txt` -- direct file read, confirmed PyJWT missing (HIGH confidence)
- `memelab/package.json` -- direct file read, confirmed current frontend deps (HIGH confidence)
- `.planning/PROJECT.md` -- project constraints and decisions (HIGH confidence)
- Library recommendations (pyotp, aiosmtplib, authlib, stripe, recharts) -- training data up to May 2025 (MEDIUM confidence on exact latest versions; `>=` pins ensure pip resolves latest compatible)
