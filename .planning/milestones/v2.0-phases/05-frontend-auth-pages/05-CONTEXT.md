# Phase 5: Frontend Auth Pages - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can log in and register through the memeLab UI, and all API calls carry the JWT automatically. Implements FAUTH-01 (login page), FAUTH-02 (register page), FAUTH-04 (AuthContext), FAUTH-05 (API header injection). Frontend route protection (Phase 6) is out of scope — this phase creates the pages and wiring, Phase 6 adds the middleware redirect.

</domain>

<decisions>
## Implementation Decisions

### Token Storage & Session
- **D-01:** JWT tokens stored in **localStorage** (`access_token` and `refresh_token` keys). Matches existing CharacterContext localStorage pattern. Acceptable for local admin tool.
- **D-02:** On 401 response, **redirect to /login** (not silent refresh). Simple approach — user re-authenticates when access token expires (2h). Refresh token (30d) is available for future enhancement but not auto-used in v1.

### Login/Register Page Design
- **D-03:** Pages live at **root level** — `memelab/src/app/login/page.tsx` and `memelab/src/app/register/page.tsx`. Outside the `(app)` group, no sidebar/shell wrapper.
- **D-04:** **Centered card on dark background** — matching existing theme (#09090b bg, #1c1c22 card, #7C3AED purple accent). Logo/title at top, form fields, submit button with loading/error states.
- **D-05:** Register form fields: **email + password + confirm password**. Matches AUTH-01 backend contract.
- **D-06:** UI in Portuguese (consistent with existing memeLab convention). Labels: "Email", "Senha", "Confirmar senha", "Entrar", "Criar conta".

### AuthContext & API Injection
- **D-07:** AuthContext Provider wraps at **root layout** (`memelab/src/app/layout.tsx`). Auth state available everywhere — login pages can check if already logged in, (app) pages access user info.
- **D-08:** `api.ts` `request()` reads token **directly from localStorage** on each call. No dependency on React context for API calls. Works in SWR fetchers and outside components.

### Post-Login Redirect Flow
- **D-09:** After successful login → **redirect to /dashboard**. Simple, consistent with current behavior (/ already redirects to /dashboard).
- **D-10:** After successful registration → **auto-login + redirect to /dashboard**. Register calls backend, then immediately calls /auth/login, stores tokens, redirects. No extra login step.
- **D-11:** Logout → call `/auth/logout` (invalidate refresh token server-side), clear localStorage tokens, **redirect to /login**.

### Claude's Discretion
- Form validation approach (inline errors vs toast)
- Loading spinner vs disabled button during submit
- Whether to show/hide password toggle on password fields
- Error message wording for 401/409/500
- Whether AuthContext exposes user profile data from /auth/me or just auth state
- Link between login ↔ register pages ("Nao tem conta? Registrar" / "Ja tem conta? Entrar")

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend Architecture
- `memelab/src/lib/api.ts` — HTTP client, `request()` helper that needs Authorization header injection
- `memelab/src/app/layout.tsx` — Root layout where AuthContext Provider will be added
- `memelab/src/app/(app)/layout.tsx` — App group layout with Shell (sidebar/header)
- `memelab/src/contexts/character-context.tsx` — Reference pattern for context + localStorage + Provider

### UI Components
- `memelab/src/components/ui/input.tsx` — shadcn Input component
- `memelab/src/components/ui/button.tsx` — shadcn Button component
- `memelab/src/components/ui/card.tsx` — shadcn Card component
- `memelab/src/app/globals.css` — Design tokens (#7C3AED primary, #09090b bg, #1c1c22 cards)

### Backend Auth Endpoints (Phase 3)
- `src/api/routes/auth.py` — Auth routes: register, login, refresh, logout, me
- `src/auth/jwt.py` — JWT verification utilities
- `src/api/deps.py` — `get_current_user()` dependency

### Prior Phase Context
- `.planning/phases/03-auth-backend/03-CONTEXT.md` — Token strategy (HS256, access 2h, refresh 30d, rotation)
- `.planning/phases/04-route-protection/04-CONTEXT.md` — Skipped (MVP), routes remain public

### Requirements
- `.planning/REQUIREMENTS.md` — FAUTH-01 through FAUTH-05
- `.planning/ROADMAP.md` §88-102 — Phase 5 success criteria (5 conditions)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CharacterContext` in `src/contexts/character-context.tsx` — Pattern template for AuthContext (createContext + Provider + localStorage + useCallback)
- shadcn/ui components: Button, Card, Input, Skeleton, Badge — ready for auth forms
- `cn()` helper in `src/lib/utils.ts` — clsx + tailwind-merge for conditional classes
- SWR hooks in `src/hooks/use-api.ts` — pattern for API data fetching

### Established Patterns
- All components are `"use client"` (SWR + interactivity)
- Next.js rewrites `/api/*` → `http://127.0.0.1:8000/*` (no CORS issues)
- Dark theme only (html className="dark")
- UI in Portuguese Brazilian

### Integration Points
- `memelab/src/app/layout.tsx` — Add AuthContext Provider (wrapping body children)
- `memelab/src/lib/api.ts` — Modify `request()` to inject Authorization header from localStorage
- `memelab/next.config.ts` — May need to exclude /login and /register from rewrites (probably not needed since they're not /api/* paths)
- `memelab/src/components/layout/sidebar.tsx` — Add logout button/link

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for auth page implementation.

</specifics>

<deferred>
## Deferred Ideas

- **Frontend route protection (Next.js middleware)** — Phase 6 scope
- **Silent token refresh (auto-retry on 401)** — v2 enhancement, current approach is redirect to /login
- **"Return to previous page" after login** — Nice-to-have, redirect always goes to /dashboard for now
- **Password reset by email** — v2 requirement (AUTH-V2-01), requires SMTP
- **Display name field on registration** — Would need User model migration, not in scope

</deferred>

---

*Phase: 05-frontend-auth-pages*
*Context gathered: 2026-03-24*
