# Phase 3: Auth Backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 03-auth-backend
**Areas discussed:** Token strategy

---

## Token Strategy

### Q1: Refresh token storage

| Option | Description | Selected |
|--------|-------------|----------|
| DB-backed (Recommended) | Store refresh tokens in a table (user_id, token_hash, expires_at). Enables logout/revocation by deleting the row. | ✓ |
| Stateless (JWT-only) | Both access and refresh are pure JWTs. Simpler, but logout = blacklist or wait for expiry. | |
| HTTP-only cookie | Refresh token in httpOnly cookie, access token in memory/header. Better XSS protection but adds CORS complexity. | |

**User's choice:** DB-backed (Recommended)
**Notes:** None — straightforward selection.

### Q2: Token lifetimes

| Option | Description | Selected |
|--------|-------------|----------|
| Short access / long refresh (Recommended) | Access: 15-30 min. Refresh: 7 days. Standard for SPAs. | |
| Medium access / medium refresh | Access: 1-2 hours. Refresh: 30 days. Fewer refresh calls, acceptable for admin tool. | ✓ |
| You decide | Claude picks reasonable defaults. | |

**User's choice:** Medium access / medium refresh
**Notes:** User chose longer lifetimes appropriate for a local admin tool rather than a public SPA.

### Q3: Refresh token rotation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, rotate (Recommended) | Each /auth/refresh returns new token, invalidates old. Detects token theft. | ✓ |
| No, reuse until expiry | Same token works for full 30-day lifetime. Simpler, fewer DB writes. | |
| You decide | Claude picks based on security/simplicity tradeoff. | |

**User's choice:** Yes, rotate (Recommended)
**Notes:** None — followed recommendation.

---

## Areas Not Discussed (Claude's Discretion)

- Registration rules (open registration, validation depth)
- Auth endpoint structure and response shapes
- Password policy (bcrypt rounds, complexity requirements)

## Deferred Ideas

- Route protection for all endpoints — Phase 4
- Frontend auth pages — Phase 5
- Password reset by email — v2
