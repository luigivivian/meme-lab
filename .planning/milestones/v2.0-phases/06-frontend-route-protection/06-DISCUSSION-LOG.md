# Phase 6: Frontend Route Protection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 06-frontend-route-protection
**Areas discussed:** Middleware strategy, Protected vs public routes

---

## Middleware Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side guard | useAuth() check in (app)/layout.tsx — simpler, no cookie complexity. Brief loading state instead of 307. | ✓ |
| Cookie mirror + Edge Middleware | Set has_session cookie on login, Edge middleware checks it for 307 redirect. True server-side redirect. | |

**User's choice:** Client-side guard (Recommended)
**Notes:** Local admin tool doesn't need Edge-level protection. localStorage tokens incompatible with Edge Runtime without cookie mirror complexity.

---

## Protected vs Public Routes — Loading State

| Option | Description | Selected |
|--------|-------------|----------|
| Full-screen spinner | Centered spinner on dark background (#09090b), purple (#7C3AED). No text, no sidebar flash. | ✓ |
| Skeleton sidebar + content | Show sidebar skeleton and content placeholders. Feels faster but shows app shell to unauthenticated users. | |
| Blank dark screen | Just dark background, no spinner. Imperceptible on fast connections. | |

**User's choice:** Full-screen spinner (Recommended)
**Notes:** None

---

## Protected vs Public Routes — Auth Redirect

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, redirect | If user visits /login with valid token, redirect to /dashboard. ROADMAP criteria #2. | ✓ |
| No, show login anyway | Let authenticated users see login page for re-login. | |

**User's choice:** Yes, redirect (Recommended)
**Notes:** Required by ROADMAP success criteria #2.

---

## Claude's Discretion

- Spinner component implementation details
- Whether to extract auth guard into reusable hook
- Redirect timing nuances

## Deferred Ideas

- Edge Middleware with cookie mirror — revisit if app becomes public-facing
- "Return to previous page" after login — v2 enhancement
- Silent token refresh — v2 enhancement
