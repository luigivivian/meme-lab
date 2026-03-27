# Phase 21: Dashboard Business Metrics - Research

**Researched:** 2026-03-27
**Domain:** Frontend dashboard UI + FastAPI backend endpoint for business metrics with BRL currency conversion
**Confidence:** HIGH

## Summary

Phase 21 replaces the 4 existing developer-oriented StatsCards (Imagens, Agentes, Runs, Backgrounds) with business-relevant metrics and converts all cost displays from USD to BRL. A new backend endpoint `GET /dashboard/business-metrics` must aggregate data from multiple tables (api_usage, content_packages, trend_events, pipeline_runs) and return current + previous period values for trend indicators. The frontend StatsCard component already supports `trend` props with percentage change display, which aligns well with the requirements.

The existing codebase provides strong foundations: `formatBRL()` helper, `VIDEO_USD_TO_BRL = 5.75` constant in config.py, `UsageRepository.get_credits_summary()` for video cost data, and the StatsCard component with built-in trend indicator support. The cost charts (PieChart, tooltip formatters) currently display USD ("$") and need conversion to BRL ("R$").

**Primary recommendation:** Build a single `GET /dashboard/business-metrics` endpoint that computes all 4 card metrics + previous period deltas in one DB round-trip, reuse the existing StatsCard component (it already supports trend indicators), and convert all cost chart displays to BRL using the existing `VIDEO_USD_TO_BRL` constant.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Replace all 4 existing StatsCards (Imagens, Agentes, Runs, Backgrounds) with business metrics
- New cards: Videos Gerados, Custo Medio/Video, Creditos Restantes, Trends Coletados
- Keep same grid layout: `grid-cols-2 lg:grid-cols-4`
- Convert cost chart Y-axis to BRL: multiply `cost_usd` by `VIDEO_USD_TO_BRL` (5.75) at display time. Chart tooltip shows "R$" prefix
- Use same 5.75 constant as Phase 20's `VIDEO_USD_TO_BRL` in config.py. Frontend uses a matching constant
- BRL formatting everywhere via `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})` -- proper "R$ 12,50" format
- Comparison period: current 7 days vs previous 7 days -- computed from new backend endpoint
- New backend endpoint: `GET /dashboard/business-metrics` -- returns all 4 card metrics + their previous period values in one call
- Arrow style: green TrendingUp icon for increase, red TrendingDown for decrease, gray Minus for no change. Show percentage change (e.g., "+12%") next to arrow
- Icon improvements: add colored circular backgrounds behind each icon -- `bg-{color}/10` (Video=violet, Cost=green, Budget=amber, Trends=blue)

### Claude's Discretion
- Exact response schema for business-metrics endpoint
- StatsCard component refactor approach (extend existing or create new BusinessMetricCard)
- Chart color adjustments for BRL context
- Empty/zero state handling for new metrics

### Deferred Ideas (OUT OF SCOPE)
- Sparkline mini-charts inside cards -- future enhancement
- Real-time exchange rate lookup -- fixed rate is sufficient
- Historical trend comparison beyond 7 days
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-05 | All spending/cost values on the dashboard display in BRL (not USD) | Cost chart PieChart uses `cost_usd` dataKey (line 671) and formats with "$" prefix (lines 679, 688, 704). Convert all using `VIDEO_USD_TO_BRL * cost_usd` and `formatBRL()`. Existing `formatBRL()` helper at line 963. |
| DASH-06 | Dashboard cards show: total videos generated, average cost per video, remaining Kie.ai budget, total trends collected, active content packages | New `/dashboard/business-metrics` endpoint queries: api_usage (kie_video), content_packages (video_status=success), trend_events (count), api_usage (budget remaining). StatsCard component already supports trend indicator props. |
| DASH-07 | Cards are visually improved with icons, trend indicators (up/down arrows), and comparative data (vs previous period) | StatsCard already has `trend` prop with `{value: number, label: string}` that renders green/red badge with +/-%. Add colored icon backgrounds via className on the icon wrapper div. Backend returns `previous_period` values for delta computation. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend REST endpoint | Already used for all dashboard routes |
| SQLAlchemy 2.0 | existing | Async DB queries for metrics | Already used in usage_repo.py and dashboard.py |
| React/Next.js | existing | Frontend dashboard | Already the app framework |
| SWR | ^2.3.3 | Data fetching hook for new endpoint | Already used by all dashboard hooks |
| Recharts | ^3.8.1 | Charts with BRL conversion | Already used for cost/usage charts |
| lucide-react | ^0.513.0 | Icons (TrendingUp, TrendingDown, Minus, Video, etc.) | Already used throughout dashboard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Intl.NumberFormat | Built-in | BRL currency formatting | All monetary displays via existing `formatBRL()` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single business-metrics endpoint | Multiple smaller endpoints | Single call is fewer round-trips, simpler SWR key management, one loading state |
| Extending StatsCard | New BusinessMetricCard component | StatsCard already has `trend` prop and icon support -- extending is simpler, fewer moving parts |

**Installation:** No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/api/routes/dashboard.py          # Add business-metrics endpoint
src/database/repositories/usage_repo.py  # Add get_business_metrics() method
memelab/src/lib/api.ts               # Add interface + function
memelab/src/hooks/use-api.ts         # Add useBusinessMetrics() hook
memelab/src/app/(app)/dashboard/page.tsx  # Replace StatsCards, convert charts
memelab/src/components/panels/stats-card.tsx  # Add iconClassName prop for colored backgrounds
```

### Pattern 1: Backend Business Metrics Endpoint
**What:** Single endpoint that queries multiple tables and returns current + previous period values
**When to use:** When the frontend needs multiple aggregated metrics displayed together
**Example:**
```python
# In dashboard.py — follows existing endpoint pattern
@router.get("/business-metrics", summary="Metricas de negocio consolidadas")
async def business_metrics(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    repo = UsageRepository(session)
    metrics = await repo.get_business_metrics(current_user.id)
    return metrics
```

### Pattern 2: Period Comparison Query
**What:** Query current 7 days and previous 7 days in a single DB call using conditional aggregation
**When to use:** When computing trend deltas between two time periods
**Example:**
```python
# In usage_repo.py — efficient period comparison
from datetime import datetime, timedelta
from sqlalchemy import case

now = datetime.utcnow()
current_start = now - timedelta(days=7)
previous_start = now - timedelta(days=14)

# Single query with CASE-based period bucketing
stmt = select(
    func.sum(case(
        (ApiUsage.date >= current_start, ApiUsage.usage_count),
        else_=0
    )).label("current_count"),
    func.sum(case(
        (ApiUsage.date < current_start, ApiUsage.usage_count),
        else_=0
    )).label("previous_count"),
).where(
    ApiUsage.date >= previous_start,
    ApiUsage.user_id == user_id,
    ApiUsage.service == "kie_video",
    ApiUsage.status == "success",
)
```

### Pattern 3: Frontend Constant Matching Backend
**What:** Frontend mirrors the backend BRL conversion constant
**When to use:** When displaying converted values that the backend did not pre-convert
**Example:**
```typescript
// In dashboard/page.tsx — matches config.py VIDEO_USD_TO_BRL
const VIDEO_USD_TO_BRL = 5.75;

// Cost chart conversion
const costDataBRL = costBreakdown?.services.map(s => ({
  ...s,
  cost_brl: s.cost_usd * VIDEO_USD_TO_BRL,
}));
```

### Pattern 4: StatsCard Icon Background Extension
**What:** Add `iconClassName` prop for per-card colored icon backgrounds
**When to use:** When cards need distinct color identities
**Example:**
```typescript
// Current StatsCard icon wrapper (line 46-50):
<div className={cn(
  "flex h-11 w-11 items-center justify-center rounded-xl",
  "bg-primary/[0.08]...",
  iconClassName  // NEW: allows "bg-violet-500/10" override
)}>
```

### Anti-Patterns to Avoid
- **Separate API call per card:** 4 separate endpoints means 4 round-trips, 4 loading states. Use single consolidated endpoint.
- **BRL conversion in backend for chart data:** The cost-breakdown endpoint is used elsewhere. Convert at display time in frontend only.
- **Creating a completely new card component:** StatsCard already has trend support. Extending it is simpler.
- **Hardcoding exchange rate in multiple places:** Use a single frontend constant that mirrors `config.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Currency formatting | Custom string manipulation | `Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'})` via existing `formatBRL()` | Handles thousands separators, decimal commas, R$ prefix correctly |
| Percentage change | Manual calculation in frontend | Backend returns both `current` and `previous` values, frontend computes `Math.round(((current - previous) / previous) * 100)` | Avoids division-by-zero when previous is 0 (show raw delta instead) |
| Trend icon selection | Custom logic | Ternary: `delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus` | Clean, standard pattern with lucide-react icons |
| Period-over-period SQL | Multiple queries | SQLAlchemy `case()` expressions for conditional aggregation | Single query is faster and atomic |

**Key insight:** The StatsCard component already supports trend indicators (`trend` prop with `value` and `label`). The main work is data plumbing: backend aggregation and frontend wiring.

## Common Pitfalls

### Pitfall 1: Division by Zero in Percentage Change
**What goes wrong:** Previous period has zero videos/trends, division yields Infinity or NaN
**Why it happens:** New users or first week of usage
**How to avoid:** When `previous === 0`, show raw current value as "new" indicator (e.g., "+5" instead of "+Inf%"). Special case in frontend: `if (previous === 0) return current > 0 ? 100 : 0;`
**Warning signs:** NaN or Infinity displayed in cards

### Pitfall 2: Cost Chart USD Tooltip Still Shows "$"
**What goes wrong:** Converting the chart data key but forgetting to update the tooltip formatter
**Why it happens:** PieChart has `formatter` prop and `label` function (lines 678-679, 688) that both format with "$"
**How to avoid:** Update all 3 locations: (1) Pie data uses `cost_brl` not `cost_usd`, (2) label function uses `formatBRL()`, (3) Tooltip formatter uses `formatBRL()`, (4) total text at line 704
**Warning signs:** Mixed "R$" and "$" symbols on same page

### Pitfall 3: StatsCard Total Lines Below Charts
**What goes wrong:** Missing the "Total 30 dias" text below the cost pie chart (line 704) which shows `$`
**Why it happens:** It's separated from the chart code and easy to miss
**How to avoid:** Search for ALL occurrences of "$" and "cost_usd" in dashboard/page.tsx
**Warning signs:** Running `grep '\$' dashboard/page.tsx` still finds dollar signs

### Pitfall 4: Backend Query Performance
**What goes wrong:** N+1 queries or slow aggregation across multiple tables
**Why it happens:** Querying trend_events, content_packages, api_usage separately
**How to avoid:** Use 4 independent SELECT statements in one async method (not N+1). Each is a simple COUNT/SUM with index support. All tables have relevant indexes (idx_runs_started_at, etc.)
**Warning signs:** Endpoint takes >500ms

### Pitfall 5: Existing StatsCard Consumers Breaking
**What goes wrong:** Modifying StatsCard props breaks other pages that use it
**Why it happens:** StatsCard is a shared component in `components/panels/`
**How to avoid:** Make `iconClassName` prop optional with default undefined (no-op). Existing callers unaffected.
**Warning signs:** TypeScript errors in other files importing StatsCard

### Pitfall 6: Video Dialog Budget Display Still in USD
**What goes wrong:** The video generation dialog (lines 821-828) shows `$` for budget remaining
**Why it happens:** Focus on cards and charts, missing the dialog
**How to avoid:** Search for ALL "$" and "usd" references in the entire file, convert each to BRL
**Warning signs:** User sees "$2.50 restante" instead of "R$ 14,38 restante"

## Code Examples

### Backend: Business Metrics Response Schema
```python
# Recommended response schema for GET /dashboard/business-metrics
{
    "videos_generated": {
        "current": 12,         # last 7 days
        "previous": 8,         # previous 7 days
        "total": 45,           # all-time
    },
    "avg_cost_per_video_brl": {
        "current": 1.25,       # last 7 days average
        "previous": 1.40,      # previous 7 days average
    },
    "budget_remaining_brl": {
        "daily_remaining": 14.38,
        "daily_budget": 17.25,
        "daily_spent": 2.87,
    },
    "trends_collected": {
        "current": 156,        # last 7 days
        "previous": 132,       # previous 7 days
        "total": 1200,         # all-time
    },
    "active_packages": {
        "current": 8,          # content packages with video_status IS NOT NULL in last 7 days
        "total": 45,           # all-time approved packages
    },
}
```

### Backend: Efficient Period Comparison Query
```python
# Source: Existing pattern from usage_repo.py extended with CASE
async def get_business_metrics(self, user_id: int) -> dict:
    from datetime import timedelta
    from config import VIDEO_USD_TO_BRL, VIDEO_DAILY_BUDGET_USD

    now = datetime.utcnow()
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    # Videos generated (kie_video service, success status)
    video_stmt = select(
        func.sum(case(
            (ApiUsage.date >= current_start, ApiUsage.usage_count), else_=0
        )).label("current"),
        func.sum(case(
            ((ApiUsage.date >= previous_start) & (ApiUsage.date < current_start), ApiUsage.usage_count), else_=0
        )).label("previous"),
        func.sum(ApiUsage.usage_count).label("total"),
        func.sum(case(
            (ApiUsage.date >= current_start, ApiUsage.cost_brl), else_=0
        )).label("current_cost_brl"),
        func.sum(case(
            (ApiUsage.date >= current_start, ApiUsage.cost_usd), else_=0
        )).label("current_cost_usd"),
        func.sum(case(
            ((ApiUsage.date >= previous_start) & (ApiUsage.date < current_start), ApiUsage.cost_brl), else_=0
        )).label("previous_cost_brl"),
        func.sum(case(
            ((ApiUsage.date >= previous_start) & (ApiUsage.date < current_start), ApiUsage.cost_usd), else_=0
        )).label("previous_cost_usd"),
    ).where(
        ApiUsage.user_id == user_id,
        ApiUsage.service == "kie_video",
        ApiUsage.status == "success",
    )
    # ... execute and build response
```

### Frontend: StatsCard with Icon Background
```typescript
// Extended StatsCard usage
<StatsCard
  title="Videos Gerados"
  value={metrics.videos_generated.current}
  icon={Video}
  iconClassName="bg-violet-500/10 group-hover:bg-violet-500/15"
  trend={{
    value: computePercentChange(
      metrics.videos_generated.current,
      metrics.videos_generated.previous
    ),
    label: "vs 7d anteriores",
  }}
/>
```

### Frontend: Percentage Change Helper
```typescript
function computePercentChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return Math.round(((current - previous) / previous) * 100);
}
```

### Frontend: Cost Chart BRL Conversion
```typescript
// Existing (lines 669-689 of dashboard/page.tsx):
<Pie data={costBreakdown.services} dataKey="cost_usd" ...>

// Replace with:
const costDataBRL = costBreakdown.services.map(s => ({
  ...s,
  cost_brl: s.cost_usd * VIDEO_USD_TO_BRL,
}));
<Pie data={costDataBRL} dataKey="cost_brl" ...>

// Update label:
label={({ name, value }) => `${(name ?? "").replace("_", " ")} ${formatBRL(value ?? 0)}`}

// Update tooltip:
formatter={(v) => [formatBRL(Number(v)), "Custo"]}

// Update total:
<span>Total 30 dias: <span className="font-medium text-foreground">{formatBRL(costBreakdown.total_cost_usd * VIDEO_USD_TO_BRL)}</span></span>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| StatsCards with dev metrics (Imagens, Agentes, Runs, Backgrounds) | Business metrics (Videos, Cost, Budget, Trends) | Phase 21 | Cards directly show ROI-relevant data |
| All costs in USD | All costs in BRL | Phase 21 | Matches user's local currency (Brazil) |
| No trend indicators on top cards | 7d vs 7d comparison arrows | Phase 21 | Users see directional momentum |

**Deprecated/outdated:**
- The 4 existing StatsCards displaying Imagens/Agentes/Runs/Backgrounds will be REPLACED (not removed as a component, just different data fed to them)

## Open Questions

1. **"Active content packages" as 5th metric**
   - What we know: CONTEXT.md mentions it could be "a 5th metric or subtitle" at Claude's discretion
   - What's unclear: Whether to add a 5th card (breaking the 2x2 grid at mobile) or embed as subtitle
   - Recommendation: Show as a subtitle/description on the "Videos Gerados" card (e.g., "8 pacotes ativos") to keep the clean 4-card grid

2. **Legacy api_usage rows with cost_brl=0**
   - What we know: Phase 20 added cost_brl column. Older rows have cost_brl=0 but cost_usd>0
   - What's unclear: How many legacy rows exist
   - Recommendation: Backend applies same USD*BRL fallback as get_credits_summary() does (already established pattern in lines 446-447 of usage_repo.py)

3. **Trend_events query for total trends**
   - What we know: TrendEvent table has pipeline_run_id FK scoped via Character.user_id join
   - What's unclear: Whether to count deduplicated trends or raw events
   - Recommendation: Count raw trend_events (simpler, already indexed). Dedup is a future refinement.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (testpaths = ["tests"]) |
| Quick run command | `python -m pytest tests/test_dashboard_metrics.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-05 | Cost values display in BRL | manual (UI) + unit (backend) | `python -m pytest tests/test_dashboard_metrics.py::test_cost_breakdown_brl -x` | Wave 0 |
| DASH-06 | Business metrics endpoint returns all 4 cards | unit | `python -m pytest tests/test_dashboard_metrics.py::test_business_metrics_endpoint -x` | Wave 0 |
| DASH-07 | Trend indicators with period comparison | unit | `python -m pytest tests/test_dashboard_metrics.py::test_business_metrics_trend_values -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_dashboard_metrics.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard_metrics.py` -- covers DASH-05, DASH-06, DASH-07 (backend endpoint tests)
- [ ] Frontend validation is manual-only (no Jest/Vitest configured for memelab)

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of:
  - `memelab/src/components/panels/stats-card.tsx` -- StatsCard props interface
  - `memelab/src/app/(app)/dashboard/page.tsx` -- Current dashboard implementation (750+ lines)
  - `src/api/routes/dashboard.py` -- Existing dashboard endpoints (4 routes)
  - `src/database/repositories/usage_repo.py` -- UsageRepository with get_credits_summary()
  - `src/database/models.py` -- TrendEvent, ContentPackage, ApiUsage, PipelineRun models
  - `memelab/src/lib/api.ts` -- API client interfaces and functions
  - `memelab/src/hooks/use-api.ts` -- SWR hook patterns
  - `config.py` -- VIDEO_USD_TO_BRL = 5.75, VIDEO_DAILY_BUDGET_USD = 3.0
  - `memelab/package.json` -- lucide-react ^0.513.0, recharts ^3.8.1, swr ^2.3.3

### Secondary (MEDIUM confidence)
- SQLAlchemy `case()` expression for conditional aggregation -- standard SQLAlchemy 2.0 pattern

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and in use, no new dependencies
- Architecture: HIGH - follows exact patterns from Phase 16 (dashboard endpoints) and Phase 20 (BRL formatting, credits)
- Pitfalls: HIGH - identified from direct code inspection of existing dashboard implementation

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable -- no external dependencies changing)
