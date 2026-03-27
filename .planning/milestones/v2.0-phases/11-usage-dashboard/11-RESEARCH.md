# Phase 11: Usage Dashboard - Research

**Researched:** 2026-03-24
**Domain:** Frontend dashboard widget (React/Next.js + SWR) + badge refinement
**Confidence:** HIGH

## Summary

Phase 11 is a frontend-only phase. The backend endpoint (`GET /auth/me/usage`) already exists and returns the `UsageResponse` schema (`{services: [{service, tier, used, limit, remaining}], resets_at}`). The source badges already display `background_source` values but need refinement to distinguish `gemini_free` vs `gemini_paid` vs `static`.

The work involves: (1) adding a `useUsage()` SWR hook with 30s polling, (2) adding TypeScript interfaces matching the existing Pydantic schemas, (3) creating a Usage Card in the dashboard right sidebar between Status and Agents, (4) extending `SOURCE_COLORS` with tier-specific entries, and (5) updating badge rendering to use tier-aware source labels.

**Primary recommendation:** Follow the established SWR hook + Card sidebar pattern exactly. No new libraries needed. All components (Progress, Card, Badge, SkeletonList) already exist.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Usage widget is a new Card in the dashboard right sidebar, placed between the Status card and the Agents card. Consistent with existing sidebar layout pattern.
- **D-02:** Fill indicator uses the existing `Progress` component (Radix-based, `ui/progress.tsx`) with "N / M hoje" text above and percentage. Color shifts from emerald to amber to rose as usage percentage increases (matches quality score bar pattern already in content cards).
- **D-03:** Card shows: tier label ("Free tier"), reset time ("Reseta 00:00 PT"), and per-service breakdown from the existing `UsageResponse` schema.
- **D-04:** 3 distinct source badges: "gemini free", "gemini paid", "static". Users can see which images consumed free quota vs paid key.
- **D-05:** Badge data comes from existing `ContentPackage.background_source` + tier metadata stored by Phase 9/10 in `image_metadata`.
- **D-07:** SWR polling with `refreshInterval: 30000` (30 seconds). Standard pattern matching other SWR hooks in the codebase. No explicit mutate after pipeline runs.

### Claude's Discretion
- Badge color choices (D-06) -- pick colors that fit the design system
- SWR hook name and file organization (new `useUsage()` hook in `use-api.ts`)
- Whether to show all services or just `gemini_image` in the widget
- Loading/error states for the usage card (follow existing SkeletonList pattern)
- Exact text labels (PT-BR) for the widget

### Deferred Ideas (OUT OF SCOPE)
- Usage history graph (last 30 days) -- DASH-V2-01
- Alerts at 80%/95% usage -- DASH-V2-02
- Estimated cost report -- DASH-V2-03
- Static fallback counter in api_usage table
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Widget no dashboard mostrando consumo diario vs limite | Usage Card using existing Progress component + `useUsage()` SWR hook consuming `GET /auth/me/usage` |
| DASH-02 | Indicador visual de source usado (gemini/comfyui/static) por imagem | Extend `SOURCE_COLORS` with `gemini_free`, `gemini_paid` entries; update badge rendering in content cards |
| DASH-03 | Endpoint API retornando estatisticas de uso do usuario | Already implemented at `GET /auth/me/usage` in `src/api/routes/auth.py` line 81. Returns `UsageResponse` schema. No backend work needed. |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| swr | 2.3.3 | Data fetching + polling | Already used for all dashboard hooks |
| @radix-ui/react-progress | 1.1.4 | Fill indicator bar | Already wrapped in `ui/progress.tsx` |
| framer-motion | 12.35.2 | Stagger animations on card content | Already used throughout dashboard |
| lucide-react | 0.513.0 | Icons | Already used; `Gauge` or `BarChart3` for usage card icon |

### Supporting (already installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| next | 15.3.3 | Framework | App router, page.tsx |
| react | 19.1.0 | UI | Components |
| tailwind-merge | 3.3.0 | Class merging | cn() utility |

### Alternatives Considered
None. All required components and libraries are already in the project.

**Installation:**
```bash
# No installation needed -- all dependencies already present
```

## Architecture Patterns

### Recommended File Changes
```
memelab/src/
  hooks/use-api.ts              # ADD: useUsage() hook
  lib/api.ts                    # ADD: UsageResponse/ServiceUsage interfaces + getUsage() function
  lib/constants.ts              # MODIFY: extend SOURCE_COLORS with tier-specific entries
  app/(app)/dashboard/page.tsx  # MODIFY: import useUsage, add UsageCard between Status and Agents
```

### Pattern 1: SWR Hook (follow existing pattern exactly)
**What:** Add `useUsage()` to `use-api.ts` following the identical pattern of other hooks.
**When to use:** For the usage widget data fetching.
**Example:**
```typescript
// In use-api.ts — follows exact pattern of useStatus(), useAgents(), etc.
export function useUsage() {
  return useSWR("usage", () => api.getUsage(), {
    refreshInterval: 30000,  // D-07: 30 second polling
  });
}
```

### Pattern 2: TypeScript Interfaces (match Pydantic schemas)
**What:** Add interfaces in `api.ts` that mirror the backend `UsageResponse` and `ServiceUsage` schemas from `src/auth/schemas.py`.
**Example:**
```typescript
// In api.ts — mirrors src/auth/schemas.py exactly
export interface ServiceUsage {
  service: string;
  tier: string;
  used: number;
  limit: number;
  remaining: number;
}

export interface UsageResponse {
  services: ServiceUsage[];
  resets_at: string;
}

export const getUsage = () => request<UsageResponse>("/auth/me/usage");
```

### Pattern 3: Sidebar Card (follow Status card pattern)
**What:** Add a Card component in the right sidebar section of `dashboard/page.tsx`, positioned between the Status card (line 321) and the Agents card (line 355).
**Example structure:**
```typescript
// Follows exact Card/CardHeader/CardTitle/CardContent pattern from Status card
<Card>
  <CardHeader className="pb-3">
    <CardTitle className="flex items-center gap-2 text-base">
      <Gauge className="h-4 w-4 text-primary" />
      Uso da API
    </CardTitle>
  </CardHeader>
  <CardContent>
    {/* Per-service rows with Progress bars */}
  </CardContent>
</Card>
```

### Pattern 4: Progress Bar Color Shift (matches quality score pattern)
**What:** Use the existing `Progress` component with dynamic `indicatorClassName` for color shifting based on usage percentage.
**Color thresholds:** emerald (0-59%) -> amber (60-84%) -> rose (85-100%). These match the quality score bar pattern already used in content cards (line 214 of dashboard).
**Example:**
```typescript
const pct = limit > 0 ? Math.round((used / limit) * 100) : 0;
const barColor =
  pct < 60 ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]"
  : pct < 85 ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]"
  : "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.3)]";

<Progress value={pct} indicatorClassName={barColor} />
```

### Pattern 5: Badge Color Extension
**What:** Extend `SOURCE_COLORS` in `constants.ts` with tier-specific entries while preserving backward compatibility.
**Example:**
```typescript
export const SOURCE_COLORS: Record<string, string> = {
  gemini: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  gemini_free: "bg-sky-500/20 text-sky-400 border-sky-500/30",
  gemini_paid: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  comfyui: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  static: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};
```

### Anti-Patterns to Avoid
- **Creating a separate component file for the usage card:** The dashboard uses inline JSX for all sidebar cards. Follow the same pattern to maintain consistency. Only extract to a component if it exceeds ~60 lines.
- **Adding mutate() after pipeline runs:** D-07 explicitly says no mutate. SWR polling at 30s handles refresh.
- **Fetching usage without auth token:** The `/auth/me/usage` endpoint requires JWT. The existing `request()` function in `api.ts` already injects the Authorization header from localStorage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bar | Custom div-based bar | `Progress` component from `ui/progress.tsx` | Already has Radix accessibility, animation, and `indicatorClassName` prop |
| Data polling | setInterval + fetch | SWR `refreshInterval` | Already used everywhere, handles stale-while-revalidate, error retry |
| Loading states | Custom skeleton | `SkeletonList` from `ui/skeleton` | Consistent with all other sidebar cards |
| Badge styling | Inline ad-hoc classes | `SOURCE_COLORS` map lookup | Centralized, consistent, already used in content cards |

## Common Pitfalls

### Pitfall 1: Badge Source Value Mismatch
**What goes wrong:** The `background_source` field in `ContentPackageDB` stores values like `"gemini"`, not `"gemini_free"`. The tier distinction needs to come from `image_metadata`.
**Why it happens:** Phase 9/10 store tier info in `image_metadata` dict, not in `background_source` directly.
**How to avoid:** When rendering badges, check `image_metadata` for tier info. If `background_source === "gemini"`, look for a tier field in metadata to determine `gemini_free` vs `gemini_paid`. If no metadata tier, default to `gemini` (backward compat).
**Warning signs:** All images showing just "gemini" badge instead of tier-specific ones.

### Pitfall 2: Unlimited Service Display
**What goes wrong:** Services with `limit: 0` (unlimited) return `remaining: -1` sentinel. Displaying "-1 remaining" to the user.
**Why it happens:** The backend uses 0=unlimited with remaining=-1 sentinel (Phase 8 decision).
**How to avoid:** Check for `limit === 0` and display "Ilimitado" instead of a progress bar. Do not show percentage for unlimited services.
**Warning signs:** Negative numbers or NaN in the UI.

### Pitfall 3: Usage Card Shows When Not Authenticated
**What goes wrong:** The `useUsage()` hook fires on unauthenticated page load, gets 401, triggers redirect loop.
**Why it happens:** Dashboard page might render briefly before auth redirect.
**How to avoid:** The SWR hook will fail gracefully since `api.ts` request() already handles 401 with redirect. But conditionally call `useUsage()` only when user is authenticated (check localStorage token or use auth context). Alternatively, rely on the existing auth middleware redirect.
**Warning signs:** Flash of error state before redirect to login.

### Pitfall 4: Progress Component Percentage > 100
**What goes wrong:** If `used > limit` (edge case where concurrent requests exceed limit), percentage exceeds 100%.
**Why it happens:** Race condition or rejected requests that were already in-flight.
**How to avoid:** Clamp percentage: `Math.min(100, Math.round((used / limit) * 100))`.
**Warning signs:** Progress bar overflow or visual glitch.

### Pitfall 5: Sidebar Order Insertion
**What goes wrong:** New card placed in wrong position breaking visual hierarchy.
**Why it happens:** The right sidebar section starts at line 319 of `dashboard/page.tsx`. Current order: Status (321) -> Agents (355) -> Fila de Publicacao (390) -> Ultimas Execucoes (428) -> Storage+Jobs (479).
**How to avoid:** Insert the Usage Card JSX between the closing `</Card>` of the Status card (line 353) and the opening `<Card>` of the Agents card (line 356).
**Warning signs:** Usage card at bottom instead of between Status and Agents.

## Code Examples

### Complete Usage API Function
```typescript
// In api.ts
export interface ServiceUsage {
  service: string;
  tier: string;
  used: number;
  limit: number;
  remaining: number;
}

export interface UsageResponse {
  services: ServiceUsage[];
  resets_at: string;
}

export const getUsage = () => request<UsageResponse>("/auth/me/usage");
```

### Complete SWR Hook
```typescript
// In use-api.ts
export function useUsage() {
  return useSWR("usage", () => api.getUsage(), {
    refreshInterval: 30000,
  });
}
```

### Badge Source Resolution Helper
```typescript
// Helper to determine tier-aware source label from content package
// NOTE: undefined/missing tier MUST fall back to "gemini", not "gemini_free"
// — backward compatibility with legacy images that have no tier metadata.
function getSourceLabel(pkg: ContentPackageDB): string {
  if (pkg.background_source === "gemini") {
    const tier = (pkg.image_metadata as Record<string, unknown>)?.tier;
    if (tier === "paid") return "gemini_paid";
    if (tier === "free") return "gemini_free";
    return "gemini"; // legacy entries without tier metadata — backward compatible
  }
  return pkg.background_source || "static";
}
```

### Extended SOURCE_COLORS
```typescript
// In constants.ts
export const SOURCE_COLORS: Record<string, string> = {
  gemini: "bg-blue-500/20 text-blue-400 border-blue-500/30",        // backward compat
  gemini_free: "bg-sky-500/20 text-sky-400 border-sky-500/30",      // free tier
  gemini_paid: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30", // paid tier
  comfyui: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  static: "bg-zinc-500/20 text-zinc-400 border-zinc-500/30",
};
```

### Color Shift Logic for Progress
```typescript
function usageBarColor(pct: number): string {
  if (pct < 60) return "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]";
  if (pct < 85) return "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]";
  return "bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.3)]";
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single "gemini" badge | Tier-specific badges (free/paid) | Phase 11 | Users see quota impact per image |
| No usage visibility | Dashboard widget with polling | Phase 11 | Users track daily consumption |

**Backend already done:**
- `GET /auth/me/usage` endpoint (Phase 8, line 81 of auth.py)
- `UsageResponse` / `ServiceUsage` Pydantic schemas (Phase 8, schemas.py)
- `UsageRepository.get_user_usage()` with PT timezone bucketing (Phase 8)
- Atomic counter with dialect-aware upsert (Phase 8)

## Open Questions

1. **Tier metadata field name in image_metadata**
   - What we know: Phase 9/10 store tier info in `image_metadata` dict when generating images
   - What's unclear: Exact key name -- could be `tier`, `key_tier`, or nested in `fallback_reason`
   - Recommendation: Check `image_metadata` structure in actual DB records or Phase 10 code. If no tier key found, fall back to showing "gemini" generic badge. Plan should include a verification step.

2. **Show all services or just gemini_image?**
   - What we know: Backend returns `gemini_image/free`, `gemini_text/free` as known services
   - What's unclear: Whether showing gemini_text usage is useful (it doesn't affect image generation)
   - Recommendation: Show `gemini_image` prominently (with Progress bar), list other services as compact rows below if they have usage > 0. This is Claude's discretion per CONTEXT.md.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (backend) |
| Config file | None in project root (uses defaults) |
| Quick run command | `python -m pytest tests/test_api_usage.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Usage widget renders with progress bar and data | manual-only | Visual inspection in browser | N/A |
| DASH-02 | Source badges show tier-specific labels/colors | manual-only | Visual inspection in browser | N/A |
| DASH-03 | GET /auth/me/usage returns correct data | unit | `python -m pytest tests/test_api_usage.py -x` | Partial (schema tests exist) |

**Justification for manual-only:** This project has no frontend test framework (no jest/vitest config, no testing-library). All frontend validation is done via browser inspection. Backend endpoint already has schema validation tests.

### Sampling Rate
- **Per task commit:** Visual browser check on `http://localhost:3000/dashboard`
- **Per wave merge:** Full backend test suite `python -m pytest tests/ -x`
- **Phase gate:** Dashboard widget visible with real data, badges showing tier-specific colors

### Wave 0 Gaps
None -- no new test infrastructure needed. Frontend is manual-only, backend endpoint already tested.

## Sources

### Primary (HIGH confidence)
- `src/api/routes/auth.py` lines 81-91 -- existing `/auth/me/usage` endpoint
- `src/auth/schemas.py` lines 41-52 -- `ServiceUsage` and `UsageResponse` schemas
- `src/database/repositories/usage_repo.py` -- full usage repo implementation
- `memelab/src/hooks/use-api.ts` -- all SWR hook patterns
- `memelab/src/lib/api.ts` -- all TypeScript interfaces and request patterns
- `memelab/src/lib/constants.ts` -- `SOURCE_COLORS` map
- `memelab/src/app/(app)/dashboard/page.tsx` -- full dashboard layout
- `memelab/src/components/ui/progress.tsx` -- Progress component API

### Secondary (MEDIUM confidence)
- `.planning/phases/11-usage-dashboard/11-CONTEXT.md` -- all locked decisions and discretion areas

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used throughout project
- Architecture: HIGH - following exact existing patterns, no new patterns introduced
- Pitfalls: HIGH - derived from direct code inspection of existing components and backend schemas

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies, all internal code)
