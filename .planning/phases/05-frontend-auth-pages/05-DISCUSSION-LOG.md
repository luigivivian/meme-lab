# Phase 5: Frontend Auth Pages - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 05-frontend-auth-pages
**Areas discussed:** Token storage & session, Login/Register page design, AuthContext & API injection, Post-login redirect flow

---

## Token Storage & Session

| Option | Description | Selected |
|--------|-------------|----------|
| localStorage | Simple, persists across tabs/refreshes. Matches CharacterContext pattern. Acceptable for local admin tool. | ✓ |
| Memory only (useState) | Most secure — tokens lost on refresh/tab close. User must re-login each session. | |
| httpOnly cookies | Server-set cookies, invisible to JS. Requires backend changes. Overkill for local tool. | |

**User's choice:** localStorage
**Notes:** Consistent with existing CharacterContext localStorage pattern.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Silent refresh | api.ts catches 401, calls /auth/refresh, retries original request. | |
| Redirect to login | Any 401 sends user back to /login. Simpler implementation. | ✓ |
| Proactive refresh | Timer-based refresh before expiry. More complex. | |

**User's choice:** Redirect to login
**Notes:** Simpler approach — user re-authenticates on token expiry.

---

## Login/Register Page Design

| Option | Description | Selected |
|--------|-------------|----------|
| /login and /register at root | Outside (app) group — no sidebar/shell. Clean standalone pages. | ✓ |
| /(auth) route group | Dedicated (auth) group with its own layout. More organized for future. | |
| Inside (app) group | Inside (app)/ with sidebar visible. Unusual for auth pages. | |

**User's choice:** /login and /register at root
**Notes:** None.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Centered card, dark bg | Matching existing dark theme. Simple card with form fields. | ✓ |
| Split layout | Left branding, right form. Requires design assets. | |
| Full-page form | No card — ultra-minimal. | |

**User's choice:** Centered card, dark bg
**Notes:** Consistent with memeLab design tokens.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Email + password + confirm | Standard registration form. Matches AUTH-01 backend. | ✓ |
| Email + password only | Simpler but risk of typos. | |
| Email + password + name | Needs User model migration. | |

**User's choice:** Email + password + confirm password
**Notes:** None.

---

## AuthContext & API Injection

| Option | Description | Selected |
|--------|-------------|----------|
| Root layout | Wrap in root layout.tsx. Auth state available everywhere. | ✓ |
| (app) layout only | Login/register pages won't have auth context. | |

**User's choice:** Root layout
**Notes:** Matches how CharacterProvider would work.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Read from localStorage directly | api.ts request() reads localStorage on each call. Works outside components. | ✓ |
| Module-level setter | AuthContext calls api.setToken(). Token can go stale on tab resume. | |
| Pass token per-call | Each API function accepts optional token param. Threading overhead. | |

**User's choice:** Read from localStorage directly
**Notes:** Simple, no React dependency in api.ts.

---

## Post-Login Redirect Flow

| Option | Description | Selected |
|--------|-------------|----------|
| /dashboard | Consistent with current behavior. Simple, predictable. | ✓ |
| Return to previous page | Store URL before redirect. Better UX but more complex. | |

**User's choice:** /dashboard
**Notes:** None.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-login + redirect to dashboard | Register → login → store tokens → /dashboard. No extra step. | ✓ |
| Redirect to /login with success message | User logs in manually after register. More friction. | |

**User's choice:** Auto-login + redirect to dashboard
**Notes:** None.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Clear tokens + redirect to /login | Call /auth/logout, clear localStorage, go to /login. | ✓ |
| Clear tokens + redirect to landing | Same but to landing page instead. | |

**User's choice:** Clear tokens + redirect to /login
**Notes:** Standard approach.

---

## Claude's Discretion

- Form validation approach (inline errors vs toast)
- Loading spinner vs disabled button during submit
- Show/hide password toggle
- Error message wording
- AuthContext user profile exposure
- Login ↔ register page cross-links

## Deferred Ideas

- Silent token refresh (auto-retry on 401) — v2 enhancement
- "Return to previous page" after login — nice-to-have
- Password reset by email — v2
- Display name on registration — needs migration
