# Phase 3: Auth Backend - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can register, log in, receive JWT tokens, and refresh or invalidate their session. Implements AUTH-01 through AUTH-04 and AUTH-06. This phase adds auth routes (`/auth/*`), JWT generation/validation, bcrypt password hashing, a refresh token table, and a `UserRepository`. The seed admin from Phase 2 becomes functional (can log in). Route protection (Phase 4) and frontend auth (Phase 5) are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Token Strategy
- **D-01:** Refresh tokens are DB-backed. A `refresh_tokens` table stores `(id, user_id, token_hash, expires_at, created_at)`. Logout/revocation deletes the row. Leverages existing `db_session()` dependency in `deps.py`.
- **D-02:** Access token lifetime: **2 hours**. Refresh token lifetime: **30 days**. Appropriate for a local admin tool (not public SaaS) — fewer refresh calls, acceptable exposure window.
- **D-03:** Refresh tokens **rotate on each use**. Each `/auth/refresh` call issues a new refresh token and invalidates the old one. Detects token theft via reuse detection.
- **D-04:** Access tokens are stateless JWTs (HS256, signed with `SECRET_KEY` env var). Payload: `sub` (user_id), `email`, `role`, `exp`, `iat`.

### Registration & Login (carried forward + Claude's discretion)
- **D-05:** Open registration (no invite code). Email validated via Pydantic `EmailStr`. Email stored lowercase (Phase 2 D-08).
- **D-06:** Password hashing with bcrypt (per PROJECT.md constraint). Seed admin in `seed.py` already needs bcrypt — Phase 3 formalizes the utility.

### Roles
- **D-07:** Roles `admin` and `user` (Phase 2 D-10). Seed admin is `admin`. New registrations default to `user`. No role-changing endpoint in this phase.

### Auth Endpoints
- **D-08:** New route module `src/api/routes/auth.py` with prefix `/auth`. Endpoints:
  - `POST /auth/register` — 201 + user info (no password in response)
  - `POST /auth/login` — 200 + access_token + refresh_token
  - `POST /auth/refresh` — 200 + new access_token + new refresh_token
  - `POST /auth/logout` — 200 + invalidates refresh token
  - `GET /auth/me` — 200 + current user profile (requires valid access token)

### Claude's Discretion
- JWT signing algorithm details (HS256 vs RS256 — HS256 is standard for single-service)
- Exact bcrypt rounds (12 is standard default)
- Pydantic request/response schemas structure
- Whether to add `last_login_at` update on login (Phase 2 deferred this here)
- Error response format for auth failures (401/403/409)
- Refresh token table migration number and naming
- Whether `GET /auth/me` returns API key info or just profile

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### User Model & Database
- `src/database/models.py` §504-527 — User model with hashed_password, role, is_active, API keys
- `src/database/base.py` — `Base` and `TimestampMixin` classes
- `src/database/session.py` — Async session factory and `get_session()` generator
- `src/database/seed.py` — Seed script where admin user is created (needs bcrypt)

### API Patterns
- `src/api/deps.py` — `db_session()` dependency, add `get_current_user()` here
- `src/api/app.py` §1-50 — FastAPI app setup, route registration, lifespan
- `src/api/routes/characters.py` — Example route module with `Depends(db_session)` pattern
- `src/api/routes/__init__.py` — Route barrel file (register new auth module here)

### Migration Examples
- `src/database/migrations/versions/006_add_users_table.py` — Most recent migration (refresh_tokens table chains from this)

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — AUTH-01 through AUTH-06
- `.planning/ROADMAP.md` §58-68 — Phase 3 success criteria (5 conditions that must be TRUE)

### Prior Phase Context
- `.planning/phases/02-users-table/02-CONTEXT.md` — User table decisions (API key storage, seed admin, email normalization, roles)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db_session()` in `src/api/deps.py` — FastAPI dependency for async DB sessions, reuse for auth routes
- `User` model in `src/database/models.py` — Already has all needed columns (email, hashed_password, role, is_active)
- `src/database/repositories/` — Repository pattern exists, add `UserRepository` here
- `TimestampMixin` — Reuse for `refresh_tokens` table

### Established Patterns
- Route modules: `APIRouter` with prefix, registered in `app.py` via `app.include_router()`
- Dependencies: `Depends(db_session)` injected per-route for DB access
- Pydantic models in `src/api/models.py` or inline — request/response validation
- Error handling: `HTTPException` with status code and detail string
- MySQL compatibility: `server_default=` for simple types, ORM `default=` for complex types

### Integration Points
- `src/api/app.py` — Register `auth` router alongside existing 9 route modules
- `src/api/deps.py` — Add `get_current_user()` dependency (used by Phase 4, but defined here)
- `src/database/seed.py` — Update to use bcrypt for admin password hashing
- `alembic` — New migration for `refresh_tokens` table

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for JWT implementation and auth endpoint design.

</specifics>

<deferred>
## Deferred Ideas

- **Route protection for all 50+ endpoints** — Phase 4 scope, not Phase 3
- **Frontend login/register pages** — Phase 5 scope
- **Password reset by email** — v2 requirement (AUTH-V2-01), requires SMTP
- **API key encryption (Fernet)** — Carried from Phase 2 deferred, revisit at production deploy
- **Rate limiting on registration** — Not needed for local single-user tool in v1

</deferred>

---

*Phase: 03-auth-backend*
*Context gathered: 2026-03-23*
