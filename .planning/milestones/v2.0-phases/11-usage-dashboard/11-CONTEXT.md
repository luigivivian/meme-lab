# Phase 11: Usage Dashboard - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Widget on the dashboard showing daily Gemini API consumption (used/limit) with a visual fill indicator, and source badges per generated image distinguishing gemini free, gemini paid, and static. Covers DASH-01, DASH-02, DASH-03. Note: DASH-03 (GET /auth/me/usage endpoint) already exists from Phase 8. DASH-02 (source badges) partially exists — current badges show "gemini/comfyui/static" but need to distinguish free vs paid tier.

</domain>

<decisions>
## Implementation Decisions

### Usage Widget Placement & Style
- **D-01:** Usage widget is a new Card in the dashboard **right sidebar**, placed between the Status card and the Agents card. Consistent with existing sidebar layout pattern.
- **D-02:** Fill indicator uses the existing `Progress` component (Radix-based, `ui/progress.tsx`) with "N / M hoje" text above and percentage. Color shifts from emerald → amber → rose as usage percentage increases (matches quality score bar pattern already in content cards).
- **D-03:** Card shows: tier label ("Free tier"), reset time ("Reseta 00:00 PT"), and per-service breakdown from the existing `UsageResponse` schema.

### Source Badge Granularity
- **D-04:** 3 distinct source badges: "gemini free", "gemini paid", "static". Users can see which images consumed free quota vs paid key.
- **D-05:** Badge data comes from existing `ContentPackage.background_source` + tier metadata stored by Phase 9/10 in `image_metadata`.

### Badge Colors
- **D-06:** Claude's discretion on exact badge colors. Must fit existing dark theme and `SOURCE_COLORS` map in `constants.ts`. Constraint: visually distinct from each other, accessible contrast.

### Refresh Behavior
- **D-07:** SWR polling with `refreshInterval: 30000` (30 seconds). Standard pattern matching other SWR hooks in the codebase. No explicit mutate after pipeline runs.

### Claude's Discretion
- Badge color choices (D-06) — pick colors that fit the design system
- SWR hook name and file organization (new `useUsage()` hook in `use-api.ts`)
- Whether to show all services or just `gemini_image` in the widget
- Loading/error states for the usage card (follow existing SkeletonList pattern)
- Exact text labels (PT-BR) for the widget

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 8 (Usage Endpoint — Already Exists)
- `.planning/phases/08-atomic-counter/08-CONTEXT.md` — D-04 defines UsageResponse schema: `{services: [{service, tier, used, limit, remaining}], resets_at}`
- `src/api/routes/auth.py` line 81 — `GET /auth/me/usage` endpoint implementation
- `src/auth/schemas.py` — `UsageResponse` and `ServiceUsage` Pydantic models

### Phase 9/10 (Tier Metadata in Images)
- `.planning/phases/09-dual-key-management/09-CONTEXT.md` — KeyResolution dataclass, tier values
- `.planning/phases/10-static-fallback/10-CONTEXT.md` — D-07/D-08: `background_source` and `fallback_reason` in metadata

### Frontend Dashboard
- `memelab/src/app/(app)/dashboard/page.tsx` — Existing dashboard with sidebar cards, source badges on content cards (lines 245-249), `SOURCE_COLORS` usage
- `memelab/src/components/ui/progress.tsx` — Progress component to reuse for fill indicator
- `memelab/src/components/panels/stats-card.tsx` — StatsCard component
- `memelab/src/hooks/use-api.ts` — SWR hooks pattern for new `useUsage()` hook
- `memelab/src/lib/constants.ts` — `SOURCE_COLORS` map to extend with tier-specific colors
- `memelab/src/lib/api.ts` — API client types to add `UsageResponse` interface

### Requirements
- `.planning/REQUIREMENTS.md` — DASH-01 (usage widget), DASH-02 (source indicator), DASH-03 (usage endpoint)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Progress` component (Radix): horizontal bar with customizable `indicatorClassName` — use for fill indicator with color shifts
- `Card`, `CardHeader`, `CardTitle`, `CardContent`: sidebar card pattern (5 existing cards in right sidebar)
- `Badge` component: used for status/source badges throughout dashboard
- `SOURCE_COLORS` map in `constants.ts`: extend with `gemini_free`, `gemini_paid` entries
- `StatsCard`: compact metric display if needed for summary
- `SkeletonList` / `SkeletonCard`: loading states

### Established Patterns
- SWR hooks with typed responses in `use-api.ts` (e.g., `useStatus()`, `useAgents()`)
- Framer Motion stagger animations on card lists (`fastStaggerContainer`, `fastStaggerItem`)
- Color coding: emerald = good, amber = warning, rose = bad (used in quality scores, run status)
- Content cards already show `background_source` badge with `SOURCE_COLORS` map

### Integration Points
- `dashboard/page.tsx` right sidebar section (after Status card, before Agents card)
- `use-api.ts` — add `useUsage()` SWR hook calling `GET /auth/me/usage`
- `api.ts` — add TypeScript interfaces matching `UsageResponse` / `ServiceUsage` schemas
- `constants.ts` — extend `SOURCE_COLORS` with tier-specific entries

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: reuse existing Progress component and follow sidebar card pattern.

</specifics>

<deferred>
## Deferred Ideas

- **Usage history graph (last 30 days)** — DASH-V2-01, future milestone
- **Alerts at 80%/95% usage** — DASH-V2-02, future milestone
- **Estimated cost report** — DASH-V2-03, future milestone
- **Static fallback counter in api_usage table** — mentioned in Phase 10 deferred

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-usage-dashboard*
*Context gathered: 2026-03-24*
