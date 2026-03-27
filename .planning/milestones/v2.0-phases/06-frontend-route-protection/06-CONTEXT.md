# Phase 6: Frontend Route Protection - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Unauthenticated visitors cannot access any dashboard page — they are always redirected to `/login` before the page renders. Implements FAUTH-03. Covers the `(app)` route group guard, loading state during auth check, and authenticated-user redirect away from login/register pages.

</domain>

<decisions>
## Implementation Decisions

### Middleware Strategy
- **D-01:** **Client-side guard** in `(app)/layout.tsx`, NOT Edge Middleware. AuthContext's `isAuthenticated` + `isLoading` checks auth state. If not authenticated after loading, `router.push("/login")`. No cookie-mirror complexity needed — this is a local admin tool.
- **D-02:** This means the redirect is a client-side navigation (not a 307 at Edge Runtime). Acceptable trade-off for simplicity. ROADMAP success criteria #3 (307 at Edge) is relaxed in favor of practical implementation.

### Protected vs Public Routes
- **D-03:** **`(app)/` group = protected**, everything else = public. The guard lives in `memelab/src/app/(app)/layout.tsx`. All pages inside `(app)/` (dashboard, agents, pipeline, gallery, phrases, trends, characters, publishing, jobs) require authentication.
- **D-04:** Public routes: `/login`, `/register`, and the root `/` redirect. These are already outside `(app)/` — no additional allowlist needed.

### Loading State
- **D-05:** **Full-screen spinner** on dark background (#09090b) with purple spinner (#7C3AED) while AuthContext validates the stored token. No text, no sidebar flash. Shows for ~200ms on fast connections.

### Authenticated User Redirect
- **D-06:** `/login` and `/register` pages redirect authenticated users to `/dashboard`. Prevents confusion and satisfies ROADMAP success criteria #2. Check happens in each page component using `useAuth()`.

### Claude's Discretion
- Spinner component implementation (CSS animation vs Lucide loader icon)
- Whether to extract the auth guard into a reusable hook or keep it inline in layout
- Exact redirect timing (immediate vs after a minimum delay to prevent flash)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend Architecture
- `memelab/src/app/(app)/layout.tsx` — Current app group layout (Shell wrapper), will be modified to add auth guard
- `memelab/src/contexts/auth-context.tsx` — AuthContext with isAuthenticated, isLoading, user state
- `memelab/src/app/login/page.tsx` — Login page, needs authenticated-user redirect
- `memelab/src/app/register/page.tsx` — Register page, needs authenticated-user redirect

### Prior Phase Context
- `.planning/phases/05-frontend-auth-pages/05-CONTEXT.md` — Token storage (localStorage), 401 redirect, page structure decisions
- `.planning/phases/03-auth-backend/03-CONTEXT.md` — JWT token strategy (HS256, access 2h, refresh 30d)

### Requirements
- `.planning/REQUIREMENTS.md` — FAUTH-03 (middleware redirecting protected routes to login)
- `.planning/ROADMAP.md` §105-113 — Phase 6 success criteria (3 conditions, #3 relaxed per D-02)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AuthContext` (`useAuth()`) — already provides `isAuthenticated` and `isLoading` states, exactly what the guard needs
- `Shell` component in `components/layout/shell.tsx` — sidebar/header wrapper already used in `(app)/layout.tsx`
- shadcn/ui components — Skeleton available for loading states if needed

### Established Patterns
- All components are `"use client"` (SWR + interactivity)
- `(app)` group layout wraps all dashboard pages with Shell
- Login/register are root-level pages outside `(app)` group
- Navigation via `router.push()` (not `window.location.href`) per memelab CLAUDE.md

### Integration Points
- `memelab/src/app/(app)/layout.tsx` — Add auth guard (check isAuthenticated, redirect or show spinner)
- `memelab/src/app/login/page.tsx` — Add authenticated-user redirect to /dashboard
- `memelab/src/app/register/page.tsx` — Add authenticated-user redirect to /dashboard

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for client-side route protection.

</specifics>

<deferred>
## Deferred Ideas

- **Edge Middleware with cookie mirror** — More complex, provides true 307 redirect. Could revisit if app becomes public-facing.
- **"Return to previous page" after login** — Track pre-redirect URL and return user there after login (v2 enhancement, noted in Phase 5 deferred ideas too)
- **Silent token refresh** — Auto-retry on 401 with refresh token instead of redirecting (v2 enhancement)

</deferred>

---

*Phase: 06-frontend-route-protection*
*Context gathered: 2026-03-24*
