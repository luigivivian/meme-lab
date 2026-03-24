# Architecture Patterns: Auth + Rate Limiting Integration

**Domain:** Adding auth, rate limiting, and usage control to an existing FastAPI + Next.js pipeline
**Researched:** 2026-03-23
**Confidence:** HIGH — based on direct codebase analysis + established FastAPI/Next.js patterns

---

## Recommended Architecture

### Component Overview

```
Browser
  └── Next.js 15 (memelab/)
        ├── /login page          ← NEW: form → POST /api/auth/login
        ├── middleware.ts         ← NEW: protects all non-auth routes client-side
        ├── AuthContext           ← NEW: global JWT state (localStorage or httpOnly cookie)
        └── api.ts (existing)    ← MODIFY: inject Authorization header on every request

FastAPI (src/api/)
  ├── app.py                     ← MODIFY: add auth + rate limit middleware, protect routes
  ├── routes/auth.py             ← NEW: /auth/login, /auth/register, /auth/refresh, /auth/me
  ├── deps.py                    ← MODIFY: add get_current_user, get_usage_stats dependencies
  ├── middleware/auth_middleware.py   ← NEW: JWT validation on incoming requests
  ├── middleware/rate_limiter.py      ← NEW: per-user daily limit check
  └── routes/ (all existing)    ← MODIFY: add Depends(get_current_user) to protected routes

MySQL (memelab DB)
  ├── users (NEW table)
  ├── api_usage (NEW table)      ← tracks per-user per-day Gemini API calls
  └── (all 11 existing tables, unchanged schema)

Gemini API Layer (src/image_gen/gemini_client.py)
  └── GeminiImageClient         ← MODIFY: accept api_key param, track usage, fallback logic
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `routes/auth.py` | Register/login/refresh JWT tokens, hash passwords | `users` DB table, `deps.py` |
| `middleware/auth_middleware.py` | Validate JWT on every request except /auth/* and /docs | FastAPI request lifecycle |
| `middleware/rate_limiter.py` | Check and increment daily Gemini Image usage counter | `api_usage` DB table |
| `deps.py` get_current_user | Decode JWT, load User from DB, attach to request | `users` table, all protected routes |
| `deps.py` get_usage_stats | Return today's usage counts for current user | `api_usage` table |
| `GeminiImageClient` | Route image generation to free key → paid key → static fallback | Gemini API, `api_usage` table |
| Next.js `middleware.ts` | Redirect unauthenticated users to /login | Next.js route matcher |
| Next.js `AuthContext` | Store JWT, expose login/logout, auto-refresh | localStorage, api.ts |
| `api.ts` (frontend) | Inject `Authorization: Bearer <token>` header | All fetch calls |

---

## Data Flow

### Authentication Flow (Login)

```
User fills /login form
  → POST /api/auth/login {email, password}
  → Next.js rewrites to FastAPI POST /auth/login
  → FastAPI: hash verify bcrypt, query users table
  → Return {access_token, refresh_token, expires_in}
  → AuthContext stores token in localStorage (or httpOnly cookie)
  → api.ts injects header on all subsequent requests
```

### Per-Request Auth Check

```
Browser request → Next.js rewrite → FastAPI
  → auth_middleware.py intercepts
  → Extract Bearer token from Authorization header
  → Verify JWT signature + expiry (python-jose or PyJWT)
  → Decode user_id from payload
  → Attach user to request.state.user
  → Route handler calls Depends(get_current_user) → loads full User from DB
  → Handler executes normally
```

### Rate Limiting Flow (Gemini Image)

```
POST /pipeline/run or /generate/* arrives
  → rate_limiter.py checks api_usage table:
      SELECT usage_count FROM api_usage
      WHERE user_id = ? AND date = TODAY() AND api_key_tier = 'free'
  → If usage_count < FREE_DAILY_LIMIT (e.g. 500):
      → Increment counter
      → Use free API key
  → Elif paid key configured AND usage_count < PAID_DAILY_LIMIT:
      → Increment paid counter
      → Use paid API key
  → Else:
      → background_mode = "static" (graceful degradation)
  → GeminiImageClient receives (api_key, tier) as parameters
```

### Usage Dashboard Flow

```
GET /auth/me/usage → returns today's counts per tier
  ← {free_used: 127, free_limit: 500, paid_used: 0, paid_limit: 1000}
Next.js dashboard renders progress bars
```

---

## New Database Tables

### `users` table

```python
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: int (PK)
    email: str (unique, indexed)
    hashed_password: str
    role: str  # "admin" | "user"
    is_active: bool
    # Future multi-tenant: owns characters, pipeline runs
```

### `api_usage` table

```python
class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: int (PK)
    user_id: int (FK users.id)
    date: Date (indexed)          # YYYY-MM-DD, resets daily
    api_type: str                 # "gemini_image" | "gemini_text" | "comfyui"
    key_tier: str                 # "free" | "paid"
    usage_count: int              # incremented per call
    # Composite unique: (user_id, date, api_type, key_tier)
```

Key design choice: `date + usage_count` pair (not timestamps per call) — single row per user per day per api_type. Atomic `UPDATE ... SET usage_count = usage_count + 1` avoids race conditions without transactions. No write on every pipeline step, just one increment.

---

## Integration Patterns

### Pattern 1: FastAPI Dependency Injection for Auth (do not use middleware alone)

FastAPI's `Depends()` system is the correct integration point, not a global middleware. Middleware runs on every request (including /docs, /openapi.json, health checks), causes friction in development, and doesn't integrate with Pydantic/response models cleanly.

**Recommended approach:** Global middleware does JWT decode + attach to `request.state`. Route-level `Depends(get_current_user)` does the final DB lookup and returns a typed `User` object. This gives:
- Opt-in auth: some routes (e.g. `/status`, `/drive/health`) can remain unauthenticated
- Typed user in route handlers (no manual request.state access)
- Compatible with FastAPI's OpenAPI docs (shows 401 responses automatically)

```python
# deps.py (new additions)
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(db_session)
) -> User:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(401, "Not authenticated")
    payload = verify_jwt(token)  # raises on invalid/expired
    user = await session.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user

# In any existing route (minimal change required):
@router.post("/pipeline/run")
async def run_pipeline(
    body: PipelineRunRequest,
    current_user: User = Depends(get_current_user),  # ← add this line
    session: AsyncSession = Depends(db_session),
):
    ...
```

### Pattern 2: Dual API Key Rotation (Usage-Aware Fallback)

The existing `GeminiImageClient` in `src/image_gen/gemini_client.py` handles one key from `config.py`. The new pattern adds a selection layer before the client is called.

```
UsageAwareKeySelector (new class in image_gen/)
  → check_and_reserve(user_id, api_type="gemini_image") → KeyResult
  → KeyResult: {api_key, tier, remaining}
  → If remaining == 0: KeyResult: {api_key=None, tier="static"}

GeminiImageClient.generate(situacao_key, ..., api_key=key_result.api_key)
  → If api_key is None: skip generation, return static bg path
```

The existing fallback chain `Gemini → ComfyUI → static` already exists in `image_worker.py`. The new layer sits above it: it decides whether to even attempt Gemini before the worker tries.

```python
# Existing flow in image_worker.py (simplified):
async def _generate_background(...):
    if self.use_gemini:
        result = await gemini_client.generate(...)  # may 400/fail
        if result: return result
    if self.use_comfyui:
        result = await comfyui_client.generate(...)
        if result: return result
    return static_background()

# New flow:
async def _generate_background(..., user_id: int):
    key_result = await usage_selector.check_and_reserve(user_id)
    if key_result.tier == "static":
        return static_background()  # skip API calls entirely
    result = await gemini_client.generate(..., api_key=key_result.api_key)
    if result: return result
    # fallback chain continues as before
```

### Pattern 3: Next.js Middleware for Route Protection

Next.js 15 supports `middleware.ts` at the `memelab/src/` level. It runs on the Edge Runtime before any page renders.

```typescript
// memelab/src/middleware.ts (new file)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/login', '/register']

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value
    || request.headers.get('Authorization')?.replace('Bearer ', '')

  const isPublic = PUBLIC_PATHS.some(p => request.nextUrl.pathname.startsWith(p))

  if (!isPublic && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
```

Token storage recommendation: **httpOnly cookie** (not localStorage) for the main access token. Eliminates XSS risk. Next.js rewrites already proxy to FastAPI, so the `Set-Cookie` header from FastAPI `/auth/login` flows through to the browser naturally.

### Pattern 4: Usage Tracking Without Slowing the Pipeline

The key constraint is that the 5-layer async pipeline (L1→L5) must not slow down due to usage accounting. The correct pattern is async DB writes that don't block the critical path.

**Approach:** Fire-and-forget for non-critical usage increments using `asyncio.create_task()`.

```python
# In rate_limiter or image_worker:
async def record_usage_nonblocking(user_id, api_type, tier, session_factory):
    """Increment usage counter without blocking caller."""
    async def _write():
        async with session_factory() as session:
            await upsert_usage(session, user_id, api_type, tier)
    asyncio.create_task(_write())  # fire and forget

# The pipeline continues immediately after this call
```

For the rate limit check (before making the API call), a single indexed read from `api_usage` by `(user_id, date, api_type)` is O(1) — negligible latency. Composite index on these three columns is required.

---

## Existing Architecture Integration Points

### What Changes in `app.py`

1. Register new `auth` router: `app.include_router(auth.router, prefix="/auth", tags=["Auth"])`
2. CORS `allow_origins=["*"]` must change to `allow_credentials=True` with explicit origins when using cookies

### What Changes in `deps.py`

Add `get_current_user` and `get_usage_stats` dependencies (see Pattern 1 above). Existing `db_session()` dependency is already the right shape — new auth dependencies build on top of it.

### What Changes in Route Files (9 modules)

Add `Depends(get_current_user)` to each protected route. For this v1 milestone (single-user admin), this is safe to add uniformly. Routes that should remain public:
- `GET /status` — health check, used by dashboard on load
- `GET /drive/health` — filesystem health
- `GET /docs`, `GET /openapi.json` — Swagger UI (FastAPI handles these)

### What Changes in `api.ts` (frontend)

```typescript
// Add to the request() function:
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken()  // from cookie or localStorage
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...options?.headers
    },
    credentials: "include",  // for httpOnly cookies
    ...options,
  });
  if (res.status === 401) {
    // redirect to login
    window.location.href = '/login'
  }
  ...
}
```

---

## Suggested Build Order

The components have clear dependencies. Build order must respect them:

```
1. DB layer (users + api_usage tables + Alembic migration)
   └── No other dependencies. Foundation for everything.

2. Auth backend (routes/auth.py + get_current_user dep + JWT utils)
   └── Depends on: users table, bcrypt, python-jose/PyJWT

3. Route protection (add Depends(get_current_user) to all routes)
   └── Depends on: get_current_user working correctly

4. Usage tracking (api_usage table + write logic)
   └── Depends on: users table, DB layer

5. Dual key rotation (UsageAwareKeySelector)
   └── Depends on: usage tracking working, api_usage readable

6. Rate limit check + static fallback trigger
   └── Depends on: dual key rotation, existing fallback chain

7. Frontend auth (login page + AuthContext + middleware.ts)
   └── Depends on: auth backend working (/auth/login returning JWT)

8. Frontend usage dashboard
   └── Depends on: usage tracking, /auth/me/usage endpoint
```

**Critical dependency:** Steps 1-3 must be complete before testing any protected routes. Steps 4-6 can be built in parallel with Steps 7-8 once Step 1 is done.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Global Middleware Instead of Depends()

**What:** Implement auth as pure ASGI middleware (like `app.add_middleware(AuthMiddleware)`)
**Why bad:** Breaks FastAPI's OpenAPI docs (no 401 response schemas), makes route-level opt-out awkward, can't inject typed `User` objects into route handlers
**Instead:** Auth middleware only does token extraction → `request.state`. Route-level `Depends()` does the typed lookup.

### Anti-Pattern 2: Write to `api_usage` on Every Gemini API Call Inline

**What:** `await session.commit()` inside the generation worker before each Gemini call
**Why bad:** Adds DB round-trip latency to already-slow image generation (~3-10s). Also couples pipeline correctness to DB write success.
**Instead:** Fire-and-forget `asyncio.create_task()` for usage writes. Pre-flight read for rate limit check is still synchronous (must happen before the API call).

### Anti-Pattern 3: Storing JWT in localStorage

**What:** `localStorage.setItem('token', jwt)`
**Why bad:** XSS-accessible. The memeLab frontend has dynamic content from user-supplied data (phrases, captions) that could contain injected scripts.
**Instead:** httpOnly cookie. Next.js rewrites proxy the `Set-Cookie` header from FastAPI transparently.

### Anti-Pattern 4: Two Separate Gemini Client Instances for Free/Paid Keys

**What:** Create `GeminiImageClientFree` and `GeminiImageClientPaid` classes
**Why bad:** Code duplication, harder to maintain when upstream Gemini API changes
**Instead:** Single `GeminiImageClient` that accepts `api_key` at call time. Key selection is the responsibility of `UsageAwareKeySelector` (a separate concern, separate class).

### Anti-Pattern 5: Putting User Context in the Pipeline Orchestrator

**What:** Passing `user_id` all the way from API route → AsyncPipelineOrchestrator → L4 → ImageWorker
**Why bad:** Requires modifying every layer's signature. Breaks existing CLI usage where there's no user context.
**Instead:** The API route resolves the `api_key` decision before calling the orchestrator. Pass the resolved `background_mode` (already an existing parameter) as `"static"` when the limit is hit. The orchestrator doesn't need to know about users.

---

## Scalability Considerations

This is a single-user (admin) system today, preparing for multi-tenant structure.

| Concern | Single user now | Multi-tenant later |
|---------|-----------------|-------------------|
| Usage tracking | user_id FK on api_usage (even if only one row) | Already correct schema |
| API key rotation | 2 keys (free + paid) in .env | Per-user key vault (separate milestone) |
| Rate limiting | Check api_usage by user_id | Same query, more rows |
| JWT auth | Single admin account | Add registration flow, roles |
| Session storage | Stateless JWT (no Redis needed) | Add token blacklist if refresh tokens needed |

The `users` table with `role: "admin" | "user"` and `character → user_id` FK prepares the multi-tenant path without implementing isolation now.

---

## Configuration Additions

New entries needed in `.env` / `config.py`:

```bash
# Auth
JWT_SECRET_KEY=<32+ random bytes>
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=30

# Dual API keys
GOOGLE_API_KEY=<free tier key>
GOOGLE_API_KEY_PAID=<pay-as-you-go key>   # empty = no paid fallback

# Usage limits (match Google's actual free tier limits)
GEMINI_IMAGE_FREE_DAILY_LIMIT=500
GEMINI_IMAGE_PAID_DAILY_LIMIT=2000
GEMINI_TEXT_FREE_DAILY_LIMIT=1500        # RPD for flash
```

The `GOOGLE_API_KEY` variable already exists. `GOOGLE_API_KEY_PAID` is additive — if empty, the system operates in free-only mode.

---

## Sources

- Direct codebase analysis: `src/api/app.py`, `src/api/deps.py`, `src/api/routes/`, `src/database/models.py`, `src/database/session.py`, `src/image_gen/gemini_client.py`, `memelab/src/lib/api.ts`, `memelab/next.config.ts`
- FastAPI official patterns: Dependency Injection, Security utilities (OAuth2PasswordBearer), HTTPException
- Next.js 15 docs: middleware.ts, Edge Runtime, rewrites configuration (already in use in this codebase)
- Confidence: HIGH — all patterns derived from direct code inspection of the existing system

---

*Architecture analysis: 2026-03-23*
