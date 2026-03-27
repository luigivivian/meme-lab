---
phase: 03-auth-backend
plan: 01
subsystem: auth
tags: [jwt, bcrypt, pydantic, sqlalchemy, refresh-tokens]

# Dependency graph
requires:
  - phase: 02-users-table
    provides: User ORM model and migration 006
provides:
  - RefreshToken ORM model and migration 007
  - UserRepository with CRUD operations
  - JWT creation/verification utilities (HS256, 2h access, 30d refresh)
  - Pydantic auth schemas (register, login, token, user response)
  - AuthService with register/login/refresh/logout business logic
affects: [03-02-auth-routes, api-protection, frontend-login]

# Tech tracking
tech-stack:
  added: [PyJWT, pydantic-email-validator]
  patterns: [repository-pattern, service-layer, refresh-token-rotation]

key-files:
  created:
    - src/auth/__init__.py
    - src/auth/jwt.py
    - src/auth/schemas.py
    - src/auth/service.py
    - src/database/repositories/user_repo.py
    - src/database/migrations/versions/007_add_refresh_tokens.py
  modified:
    - src/database/models.py

key-decisions:
  - "HS256 with SECRET_KEY env var for JWT signing (per D-04)"
  - "bcrypt rounds=12 for password hashing (per D-06)"
  - "SHA-256 hashed refresh tokens stored in DB (per D-01)"
  - "Refresh token rotation on use — old deleted, new issued (per D-03)"

patterns-established:
  - "Repository pattern: async methods on class with session in __init__"
  - "AuthService pattern: business logic class wrapping UserRepository + JWT utils"
  - "Refresh token flow: generate random -> hash -> store in DB -> return raw to client"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-06]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 03 Plan 01: Auth Foundation Summary

**JWT auth service with bcrypt registration, refresh token rotation, and UserRepository over SQLAlchemy async**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T02:48:47Z
- **Completed:** 2026-03-24T02:50:46Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- RefreshToken ORM model with user_id FK, unique token_hash, and expires_at
- Alembic migration 007 chaining from 006 for refresh_tokens table
- UserRepository with get_by_id, get_by_email, create (follows character_repo pattern)
- JWT utilities: HS256 access tokens (2h expiry) with sub/email/role/exp/iat claims
- Pydantic schemas for all auth request/response contracts including EmailStr validation
- AuthService with full register/login/refresh/logout flow, bcrypt hashing, token rotation

## Task Commits

Each task was committed atomically:

1. **Task 1: RefreshToken model, migration, and UserRepository** - `fb3704e` (feat)
2. **Task 2: Auth module — JWT utils, Pydantic schemas, AuthService** - `164287e` (feat)

## Files Created/Modified
- `src/database/models.py` - Added RefreshToken model (section 13)
- `src/database/migrations/versions/007_add_refresh_tokens.py` - Alembic migration for refresh_tokens table
- `src/database/repositories/user_repo.py` - UserRepository with async CRUD
- `src/auth/__init__.py` - Auth module init
- `src/auth/jwt.py` - JWT creation, verification, refresh token hashing
- `src/auth/schemas.py` - Pydantic request/response models (Register, Login, Token, User, Refresh, Message)
- `src/auth/service.py` - AuthService with register, login, refresh, logout

## Decisions Made
- HS256 with SECRET_KEY env var for JWT signing (per D-04)
- bcrypt rounds=12 for password hashing (per D-06)
- SHA-256 hashed refresh tokens stored in DB, never raw (per D-01)
- Refresh token rotation on every use (per D-03)
- Default role "user" for new registrations (per D-07)
- Access tokens expire in 2 hours, refresh tokens in 30 days (per D-02)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auth foundation complete: models, repository, JWT, schemas, service all functional
- Ready for Plan 02: HTTP route endpoints (register, login, refresh, logout, /me)
- SECRET_KEY env var should be set to a strong value in production (.env)

---
*Phase: 03-auth-backend*
*Completed: 2026-03-24*
