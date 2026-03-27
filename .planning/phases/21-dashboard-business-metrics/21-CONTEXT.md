# Phase 21: Dashboard Business Metrics - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the dashboard from developer-oriented metrics to business-relevant cards, convert all spending values to BRL, and add trend indicators with period-over-period comparison. New backend endpoint provides consolidated business metrics.

</domain>

<decisions>
## Implementation Decisions

### Card Content & Layout
- Replace all 4 existing StatsCards (Imagens, Agentes, Runs, Backgrounds) with business metrics
- New cards: Videos Gerados, Custo Medio/Video, Creditos Restantes, Trends Coletados
- Keep same grid layout: `grid-cols-2 lg:grid-cols-4`

### USD to BRL Conversion
- Convert cost chart Y-axis to BRL: multiply `cost_usd` by `VIDEO_USD_TO_BRL` (5.75) at display time. Chart tooltip shows "R$" prefix
- Use same 5.75 constant as Phase 20's `VIDEO_USD_TO_BRL` in config.py. Frontend uses a matching constant
- BRL formatting everywhere via `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})` — proper "R$ 12,50" format

### Trend Indicators & Visual Improvements
- Comparison period: current 7 days vs previous 7 days — computed from new backend endpoint
- New backend endpoint: `GET /dashboard/business-metrics` — returns all 4 card metrics + their previous period values in one call
- Arrow style: green TrendingUp icon for increase, red TrendingDown for decrease, gray Minus for no change. Show percentage change (e.g., "+12%") next to arrow
- Icon improvements: add colored circular backgrounds behind each icon — `bg-{color}/10` (Video=violet, Cost=green, Budget=amber, Trends=blue)

### Claude's Discretion
- Exact response schema for business-metrics endpoint
- StatsCard component refactor approach (extend existing or create new BusinessMetricCard)
- Chart color adjustments for BRL context
- Empty/zero state handling for new metrics

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/components/panels/stats-card.tsx` — existing StatsCard (title, value, icon)
- `memelab/src/hooks/use-api.ts` — SWR hook patterns, `useVideoCredits()` from Phase 20
- `memelab/src/lib/api.ts` — API client with typed interfaces
- `src/api/routes/dashboard.py` — existing dashboard routes
- `src/database/repositories/usage_repo.py` — `get_credits_summary()` from Phase 20
- Cost chart at dashboard/page.tsx lines ~660-710 uses `cost_usd` dataKey

### Established Patterns
- StatsCard takes (title, value, icon) — may need extending for trend data
- SWR hooks follow `useFoo()` pattern returning `SWRResponse`
- Dashboard adds new sections below existing content (Phase 16 pattern)
- `formatBRL()` helper already exists in dashboard/page.tsx from Phase 20
- `VIDEO_USD_TO_BRL = 5.75` constant in config.py

### Integration Points
- dashboard/page.tsx StatsCard section (lines 175-192) — replace card content
- Cost chart section (lines ~660-710) — convert USD to BRL
- Total 30 dias text (line ~704) — convert to BRL format
- New backend endpoint in dashboard.py routes

</code_context>

<specifics>
## Specific Ideas

- The 4 business metrics map directly to ROADMAP SC-2: videos gerados, custo medio por video, creditos restantes, trends coletados
- "Active content packages" mentioned in SC-2 could be a 5th metric or subtitle — Claude's discretion

</specifics>

<deferred>
## Deferred Ideas

- Sparkline mini-charts inside cards — future enhancement
- Real-time exchange rate lookup — fixed rate is sufficient
- Historical trend comparison beyond 7 days

</deferred>
