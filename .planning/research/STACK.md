# Technology Stack — Auth, Rate Limiting & API Usage Control

**Project:** Clip-Flow Auth Milestone
**Researched:** 2026-03-23
**Scope:** Libraries to add on top of existing FastAPI + SQLAlchemy 2.0 async + MySQL + Next.js 15

---

## Context

This milestone adds auth, rate limiting, and Gemini API usage control to an existing system.
The constraint is "maintain stack" — no new frameworks, no Redis, no external auth services.
Everything must work with what's already present: FastAPI, SQLAlchemy 2.0 async, aiomysql, MySQL.

The existing `cryptography>=42.0` is already installed as a transitive dependency.

---

## Recommended Additions

### 1. Password Hashing

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `passlib[bcrypt]` | `>=1.7.4` | Hash + verify passwords | Industry standard for FastAPI auth. bcrypt extra pulls `bcrypt>=4.0` which is actively maintained. `passlib` provides a stable API over the underlying bcrypt implementation and handles salting automatically. |

**Confidence:** HIGH — passlib[bcrypt] is the explicit recommendation in FastAPI's official security documentation.

**What NOT to use:**
- `argon2-cffi` directly: stronger algorithm but passlib's argon2 support is less ergonomic. For v1 with a single admin, bcrypt is sufficient and has better FastAPI ecosystem support.
- Rolling your own with `hashlib`: never do this. bcrypt is designed for passwords (slow by design); SHA-256/SHA-512 are not.

```bash
pip install "passlib[bcrypt]>=1.7.4"
```

---

### 2. JWT Token Generation & Validation

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `python-jose[cryptography]` | `>=3.3.0` | Create and validate JWT tokens | Most widely used JWT library in the FastAPI ecosystem. The `[cryptography]` extra uses the already-installed `cryptography` package for HS256/RS256. Minimal dependency footprint. |

**Confidence:** HIGH — python-jose[cryptography] is used in FastAPI's official JWT tutorial and all major FastAPI boilerplates as of 2025.

**What NOT to use:**
- `PyJWT`: also valid, roughly equivalent. python-jose has a slightly simpler API for the specific FastAPI `Depends()` pattern and is what official docs show. Either works; pick one and stay consistent. Recommendation: python-jose to match official docs.
- `authlib`: excellent library but designed for full OAuth2 flows. Overkill for email+password JWT in an internal tool.

```bash
pip install "python-jose[cryptography]>=3.3.0"
```

---

### 3. FastAPI OAuth2 Password Flow (built-in, zero install)

FastAPI includes `fastapi.security.OAuth2PasswordBearer` and `fastapi.security.OAuth2PasswordRequestForm` in its standard library. These integrate directly with FastAPI's `Depends()` and appear in Swagger UI as a proper "Authorize" button.

**Confidence:** HIGH — part of FastAPI stdlib since v0.63.

**Pattern:**
```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    ...
```

This is the correct approach for stateless JWT auth in FastAPI. No additional library needed.

---

### 4. Rate Limiting — MySQL-Backed (no Redis required)

**Decision: Custom sliding-window counter in MySQL via SQLAlchemy, not slowapi.**

Rationale:
- `slowapi` (the standard FastAPI rate limiter) wraps `limits` library, which defaults to in-memory or Redis backends. The in-memory backend is per-process and doesn't persist across restarts. Redis would be a new infrastructure dependency.
- The project already has MySQL + SQLAlchemy 2.0 async. A `api_usage` table (see Database section) stores requests per user per day and serves double duty as rate limiting state AND usage dashboard data. No new dependency, no new infrastructure.
- For this workload (single-user or small team using a meme generator), MySQL-based rate limiting is completely adequate. A Redis Semaphore adds complexity with no benefit.

**What NOT to use:**
- `slowapi` with in-memory backend: resets on every server restart, doesn't work across multiple processes.
- `slowapi` with Redis: valid architecture but adds Redis as a new infrastructure dependency, violating the "maintain stack" constraint.
- `starlette-exceptionhandlers` + custom middleware: unnecessarily complex.

**Implementation pattern (no extra pip install):**
```python
# In deps.py — check usage before each protected endpoint
async def check_rate_limit(user_id: int, api_key_tier: str, session: AsyncSession):
    today_count = await usage_repo.count_today(user_id, "gemini_image")
    limit = FREE_TIER_LIMIT if api_key_tier == "free" else PAID_TIER_LIMIT
    if today_count >= limit:
        raise HTTPException(429, detail="Daily limit reached")
```

---

### 5. Frontend Auth — Next.js 15 (existing stack)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| No new library — use built-in `fetch` + React state | — | HTTP calls to `/auth/token` and `/auth/me` | The existing memeLab frontend already uses direct `fetch` calls via `src/lib/api.ts`. Adding a full auth library (NextAuth, Auth.js) would be overkill for a simple JWT login form. |
| `js-cookie` | `>=3.0.5` | Store JWT token in httpOnly-compatible cookie | Thin (800 bytes), widely used. Needed for persistent login across page refreshes. Alternative: `localStorage` — simpler but less secure. For a single-user internal tool, localStorage is acceptable; js-cookie is slightly better practice. |

**Confidence:** MEDIUM — based on codebase analysis of existing `api.ts` pattern. Verified that Next.js 15 App Router works fine with a simple custom auth context + fetch approach.

**What NOT to use:**
- `NextAuth` / `Auth.js`: excellent for production multi-tenant SaaS, but adds significant complexity (database adapter, session management, callback URLs). The milestone explicitly rules out OAuth and keeps auth simple.
- `@tanstack/react-query` for auth state: the existing code uses plain hooks (`use-api.ts`). Consistent to keep that pattern.

```bash
cd memelab && npm install js-cookie@>=3.0.5 @types/js-cookie
```

---

## Database Schema (New Tables)

Two new tables via Alembic migration. No new ORM library — uses existing SQLAlchemy 2.0 patterns.

### Table: `users`

```python
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")  # admin | user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    # API key tiers
    gemini_free_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gemini_paid_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    active_key_tier: Mapped[str] = mapped_column(String(10), default="free", server_default="free")

    # Multi-tenant prep: will FK to characters eventually
    usage_logs: Mapped[list["ApiUsageLog"]] = relationship(back_populates="user")
```

**Note on API key storage:** Store encrypted at rest using `cryptography.fernet.Fernet` (already available via `cryptography>=42.0`). Never store plaintext API keys in the database.

### Table: `api_usage_logs`

```python
class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    api_service: Mapped[str] = mapped_column(String(50), nullable=False)  # gemini_image | gemini_text | pipeline_run
    key_tier: Mapped[str] = mapped_column(String(10), nullable=False)  # free | paid
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | rate_limited | error | fallback_static
    endpoint: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "used_at"),
        Index("idx_usage_service", "api_service"),
    )
```

This single table serves three purposes:
1. Rate limiting: `COUNT(*) WHERE user_id=X AND api_service='gemini_image' AND DATE(used_at)=TODAY`
2. Usage dashboard: daily/weekly aggregates
3. Fallback tracking: how often did we fall back to static backgrounds

---

## Gemini API Key Management

**Decision: Dual-key in database, per-user, encrypted with Fernet.**

| Component | Approach | Why |
|-----------|----------|-----|
| Key storage | `cryptography.fernet.Fernet` symmetric encryption, keys stored encrypted in `users.gemini_free_key` | Already have `cryptography>=42.0`. AES-128-CBC + HMAC-SHA256. Single encryption key via `FERNET_KEY` env var. |
| Key selection | Service layer checks `api_usage_logs` count → use free key → if limit approaching, switch to paid key | Simple state machine. No external service. |
| Limit tracking | MySQL `api_usage_logs` with `DATE(used_at) = CURDATE()` | Exact counts per day. Resets at midnight naturally. |
| Fallback | `gemini_image → static backgrounds` | Existing `GeminiImageClient` fallback path is already implemented — just needs a signal to skip Gemini. |

**Free tier limits to enforce (from PROJECT.md context, needs validation at runtime):**
- Imagen 3: ~50 RPM, target daily limit configurable per user
- Gemini 2.0 Flash (text): 15 RPM, 1500 RPD — track separately
- Configurable thresholds in `config.py`: `GEMINI_IMAGE_DAILY_LIMIT_FREE=450` (conservative, under the ~500/day estimate)

**What NOT to do:**
- Do not call the Google AI Studio API to check quota programmatically. There is no stable programmatic quota API; track usage locally.
- Do not use environment variables for the second API key. The per-user dual-key model requires database storage.

---

## Route Protection Pattern

Use FastAPI's existing `Depends()` pattern, consistent with how `db_session` works in `deps.py`:

```python
# src/api/deps.py additions
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(db_session),
) -> User:
    """Validates JWT and returns current user. Raises 401 if invalid."""
    ...

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(403, "Admin only")
    return current_user
```

Apply to routers via `dependencies=[Depends(get_current_user)]` at the router level, not per-route — cleaner for protecting entire modules.

**CORS update required:** Current `allow_origins=["*"]` must change to specific origin list when credentials are involved. `allow_credentials=True` with wildcard origins is rejected by browsers (CORS spec). Update to `allow_origins=["http://localhost:3000"]` (dev) with a configurable `ALLOWED_ORIGINS` env var.

---

## Full Installation Summary

**New Python packages:**
```bash
pip install "passlib[bcrypt]>=1.7.4" "python-jose[cryptography]>=3.3.0"
```

**New Node packages:**
```bash
cd memelab && npm install js-cookie@^3.0.5 @types/js-cookie
```

**New environment variables (.env):**
```
JWT_SECRET_KEY=<random 32+ byte hex string>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
FERNET_KEY=<base64-encoded 32-byte key, generated via Fernet.generate_key()>
GEMINI_IMAGE_DAILY_LIMIT_FREE=450
ALLOWED_ORIGINS=http://localhost:3000
```

**New Alembic migration:**
- `006_add_users_and_usage_logs.py` — creates `users` and `api_usage_logs` tables

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Password hashing | `passlib[bcrypt]` | `argon2-cffi` | argon2 is stronger but passlib's argon2 support is less ergonomic; bcrypt is perfectly adequate for v1 |
| JWT | `python-jose[cryptography]` | `PyJWT` | Both valid; python-jose matches FastAPI official docs, less friction |
| Rate limiting | Custom MySQL counter | `slowapi` + Redis | Redis is a new infrastructure dependency; MySQL already available |
| Rate limiting | Custom MySQL counter | `slowapi` in-memory | Resets on restart; per-process only; not persistent |
| Auth service | Custom JWT | Auth0 / Supabase | External dependency, cost, overkill for single-user tool |
| Frontend auth | Custom fetch + `js-cookie` | NextAuth / Auth.js | Heavy framework; OAuth setup required; PROJECT.md rules out OAuth for v1 |
| Key encryption | `cryptography.fernet` | Store as plaintext | Never store API keys plaintext — security baseline requirement |

---

## Sources

- FastAPI Security documentation (official): https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
  Confidence: HIGH — official source, documents python-jose[cryptography] + passlib[bcrypt] as the recommended approach
- SQLAlchemy 2.0 async ORM: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  Confidence: HIGH — existing codebase already uses this correctly
- PROJECT.md constraints: "Manter Python + FastAPI + MySQL + Next.js (não introduzir novos frameworks)"
  Confidence: HIGH — explicit project constraint
- Codebase analysis (`src/api/deps.py`, `src/database/models.py`, `requirements.txt`): existing patterns verified by direct file read
  Confidence: HIGH — first-party source
- Google AI Studio free tier limits: mentioned in PROJECT.md as "needs confirmation at runtime" — the values in this document are estimates from PROJECT.md context, not verified against current Google docs
  Confidence: LOW — treat as configurable defaults, not hardcoded limits. Validate against https://ai.google.dev/pricing at implementation time.
