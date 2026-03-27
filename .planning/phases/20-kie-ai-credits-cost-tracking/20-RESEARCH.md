# Phase 20: Kie.ai Credits & Cost Tracking - Research

**Researched:** 2026-03-27
**Domain:** API cost tracking, database schema extension, REST endpoint design, dashboard UI
**Confidence:** HIGH

## Summary

Phase 20 adds BRL-native cost tracking for Kie.ai video generation. The existing `api_usage` table already tracks `cost_usd` via upsert per day/service/tier bucket. This phase extends it with a `cost_brl` column, computes BRL cost from `VIDEO_MODELS.prices_brl` (source of truth), and only records cost on successful generation. A new `GET /video/credits/summary` endpoint aggregates per-model spending over a configurable time range, and a dashboard card displays the breakdown.

The primary complexity is low: the `UsageRepository.increment()` pattern already handles dialect-aware upsert for MySQL/SQLite. Adding a `cost_brl` float column to `api_usage` is a straightforward Alembic migration (016, chaining from 015). The video generation background task already has a success-only code path where `repo.increment()` is called -- this is the exact place to add BRL cost recording. The credit summary endpoint is a new query method on `UsageRepository` that groups by model (stored in `tier` or extracted from video_metadata).

**Primary recommendation:** Add `cost_brl` column to `api_usage`, compute BRL from `VIDEO_MODELS[model].prices_brl[duration]` at recording time, add `get_credits_summary()` to `UsageRepository`, expose via `GET /video/credits/summary`, and render a "Video Credits" card at the bottom of the dashboard page.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Store costs in BRL natively -- add `cost_brl` column to existing `api_usage` table via Alembic migration. VIDEO_MODELS already has `prices_brl` per model per duration; avoids exchange rate drift
- Extend `api_usage` table (not new table) -- reuses existing upsert pattern from `usage_repo.py`
- Record cost only after Kie.ai confirms `status=success` -- failed/timeout generations cost zero
- Fallback for models not in VIDEO_MODELS config: use `cost_usd * 5.5` (same conversion Phase 18 uses), log warning
- Single endpoint `GET /video/credits/summary` returning total, per-model breakdown, and budget info in one response
- Support `?days=30` query param for time range (default 30 days + all-time totals)
- Include failed generation counters (`failed_count`, `failed_zero_cost`) to show cost discipline
- Daily budget display: `daily_budget_brl`, `daily_spent_brl`, `daily_remaining_brl` based on existing `VIDEO_DAILY_BUDGET_USD` converted to BRL
- New "Video Credits" card below existing dashboard content (per Phase 16 pattern: add below, don't replace)
- Compact table inside card showing per-model breakdown: model name, count, total BRL. Expandable if >5 models
- Do NOT update existing cost_usd displays -- Phase 21 specifically handles "update all spending values to display in BRL"

### Claude's Discretion
- Migration number sequencing (chain from latest existing migration)
- Exact response schema for credits summary endpoint
- Card styling consistent with existing dashboard cards

### Deferred Ideas (OUT OF SCOPE)
- Converting all existing USD displays to BRL -- Phase 21 scope
- Monthly budget tracking -- daily budget is sufficient for Phase 20
- Cost forecasting/projections -- future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CRED-01 | Credits are only deducted when a video generation succeeds -- failed generations cost zero | Verified: `_generate_video_task()` in video.py already has success-only path (line 307-328) where `repo.increment()` is called. Failed path (line 334-338) sets metadata error but never calls increment. Add `cost_brl` to the same success-only block. |
| CRED-02 | Each model's cost is tracked using the prices_brl values from VIDEO_MODELS config | `VIDEO_MODELS` dict in config.py (lines 364-465) has `prices_brl` keyed by duration for all 10 models. At recording time, look up `VIDEO_MODELS[model]["prices_brl"][duration]` to get native BRL cost. Fallback: `cost_usd * 5.5`. |
| CRED-03 | A credits summary is available via API showing total spent, per-model breakdown, and remaining budget | New `get_credits_summary()` method on `UsageRepository` querying `api_usage` grouped by `tier` (or a new `model` column). New `GET /video/credits/summary` endpoint in video routes. |
| CRED-04 | Dashboard displays accurate cumulative costs in BRL with per-model granularity | New "Video Credits" card component added below existing dashboard content (Phase 16 pattern). Uses SWR hook to fetch from credits summary endpoint. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0+ (existing) | ORM, async queries, dialect-aware upsert | Already used throughout; `UsageRepository` pattern established |
| Alembic | existing | Database migrations | Sequential migration chain (latest: 015) |
| FastAPI | existing | REST API endpoints | All routes follow established patterns |
| Pydantic | existing | Response models | `BaseModel` for `VideoCreditsResponse` |

### Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SWR | existing | Data fetching hooks | `useSWR` pattern established in `use-api.ts` |
| Recharts | existing | Charts (optional for pie/bar) | Already imported in dashboard page |
| Lucide React | existing | Icons | Already used for all dashboard cards |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cost_brl` column on api_usage | Separate `video_credits` table | New table adds complexity; extending api_usage reuses upsert pattern and is user's locked decision |
| Storing model in `tier` column | New `model` column on api_usage | `tier` is already `"standard"` for all kie_video entries -- need a way to differentiate models. Options: (a) store model_id in tier, or (b) add new column. Using `tier` for model breaks existing tier semantics. Recommend new nullable `metadata` JSON column or reuse existing approach where model is in video_metadata on ContentPackage. |

## Architecture Patterns

### Key Insight: Model Identification Problem

The current `api_usage` table uses `tier="standard"` for all `kie_video` entries. All 10 Kie.ai models write the same `service="kie_video", tier="standard"` row. To get per-model cost breakdown, we have two options:

**Option A: Store model in api_usage (recommended)**
Add a nullable `model` column (String(100)) to `api_usage`. When recording kie_video cost, pass the model ID. For credits summary, `GROUP BY model`. Clean, queryable, no JSON parsing.

**Option B: Cross-reference ContentPackage.video_metadata**
Join `api_usage` with `content_packages` via date correlation. Fragile (date bucket matching), poor performance, breaks if packages are deleted.

**Recommendation:** Option A. Add `model` column to `api_usage` via migration 016. Backward compatible (nullable, existing rows get NULL). Only populate for kie_video service entries going forward.

### BRL Cost Calculation Flow

```
1. Video generation succeeds in _generate_video_task()
2. Read model and duration from gen_result
3. Look up: VIDEO_MODELS[model]["prices_brl"][duration]
4. If not found: fallback = gen_result.cost_usd * VIDEO_USD_TO_BRL (5.75)
5. Call repo.increment(cost_usd=X, cost_brl=Y, model=model_id)
6. Upsert accumulates both cost_usd and cost_brl in daily bucket
```

### Recommended Changes by File

```
src/database/models.py              # Add cost_brl, model columns to ApiUsage
src/database/migrations/versions/   # 016_add_cost_brl_and_model.py
src/database/repositories/usage_repo.py  # Extend increment() + add get_credits_summary()
src/api/routes/video.py             # Add GET /video/credits/summary endpoint
src/api/models.py                   # Add VideoCreditsResponse schema
config.py                           # (no changes needed, VIDEO_MODELS already has prices_brl)
memelab/src/lib/api.ts              # Add getVideoCredits() API function
memelab/src/hooks/use-api.ts        # Add useVideoCredits() SWR hook
memelab/src/app/(app)/dashboard/page.tsx  # Add VideoCreditsCard component
```

### Pattern: Extending UsageRepository.increment()

Current signature:
```python
async def increment(
    self,
    user_id: int,
    service: str,
    tier: str,
    status: str = "success",
    cost_usd: float = 0.0,
) -> int:
```

Extended signature:
```python
async def increment(
    self,
    user_id: int,
    service: str,
    tier: str,
    status: str = "success",
    cost_usd: float = 0.0,
    cost_brl: float = 0.0,      # NEW
    model: str | None = None,    # NEW
) -> int:
```

The upsert must accumulate `cost_brl` the same way it accumulates `cost_usd`:
```python
# MySQL
stmt = stmt.on_duplicate_key_update(
    usage_count=ApiUsage.usage_count + 1,
    cost_usd=ApiUsage.cost_usd + cost_usd,
    cost_brl=ApiUsage.cost_brl + cost_brl,  # NEW
)
```

**Important:** When adding the `model` column, the unique constraint `uq_api_usage_user_service_tier_date` currently groups all kie_video into one row per day. To track per-model, we need per-model rows. Two approaches:

1. **Change tier to model_id** for kie_video entries (e.g., `tier="hailuo/2-3-image-to-video-standard"` instead of `"standard"`). This fits the existing unique constraint and requires NO schema change to the constraint. The `model` column becomes metadata, grouping uses `tier`.

2. **Add model to unique constraint**. Breaking change -- requires dropping and recreating constraint.

**Recommendation:** Use approach 1. Set `tier=model_id` when calling `increment()` for kie_video. This naturally creates per-model-per-day rows without schema constraint changes. The `_KNOWN_SERVICES` list already handles the display. The only downside: existing rows have `tier="standard"` -- these show as a legacy bucket in summaries (acceptable, will naturally age out in 30 days).

### Credits Summary Response Schema

```python
class VideoCreditsResponse(BaseModel):
    """GET /video/credits/summary response."""
    # Time range
    days: int  # requested range

    # Totals (within range)
    total_spent_brl: float
    total_spent_usd: float
    total_videos: int
    avg_cost_brl: float

    # All-time totals
    alltime_spent_brl: float
    alltime_videos: int

    # Per-model breakdown (within range)
    models: list[ModelCostBreakdown]

    # Failed generations (cost discipline)
    failed_count: int
    failed_zero_cost: bool  # True = all failed have zero cost

    # Daily budget (converted to BRL)
    daily_budget_brl: float
    daily_spent_brl: float
    daily_remaining_brl: float

class ModelCostBreakdown(BaseModel):
    model_id: str
    model_name: str  # Human-readable from VIDEO_MODELS
    count: int
    total_brl: float
    avg_brl: float
```

### Anti-Patterns to Avoid
- **Do NOT query ContentPackage for cost aggregation:** The api_usage table is the authoritative cost ledger. ContentPackage.video_metadata has cost info but is not designed for aggregation queries.
- **Do NOT modify the existing cost_usd columns or displays:** Phase 21 explicitly owns the USD-to-BRL display migration. Phase 20 only ADDS cost_brl alongside existing cost_usd.
- **Do NOT use floating point for currency comparison:** Use `round()` consistently. BRL values from config are already defined to 2 decimal places.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dialect-aware upsert | Custom SQL strings | Existing `UsageRepository.increment()` pattern | MySQL vs SQLite INSERT handling already solved |
| BRL price lookup | Hardcoded price table | `VIDEO_MODELS[model]["prices_brl"][duration]` from config.py | Single source of truth, already maintained |
| Dashboard data fetching | Custom fetch + state | SWR hook pattern from `use-api.ts` | Automatic revalidation, error retry, caching |
| Currency formatting | Manual string format | `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })` in frontend | Handles R$ symbol, thousands separator, decimal correctly |

## Common Pitfalls

### Pitfall 1: Unique Constraint Collision When Switching to Per-Model Tier
**What goes wrong:** If `tier` is changed from `"standard"` to model_id for kie_video entries, and two videos of the same model are generated on the same day, the upsert correctly accumulates. However, if the SAME user generates videos with DIFFERENT models on the same day, they get separate rows (desired). The risk is if code accidentally passes `tier="standard"` somewhere -- it would create a separate bucket from model-specific rows.
**Why it happens:** Multiple call sites (`_generate_video_task`, batch handler) all call `repo.increment()`.
**How to avoid:** Create a helper function `_compute_video_cost_brl(model: str, duration: int) -> tuple[float, str]` that returns `(cost_brl, tier_for_upsert)`. All call sites use this single function. Never hardcode tier for kie_video.
**Warning signs:** Total cost_brl in summary doesn't match expected per-generation costs.

### Pitfall 2: Existing Rows Have tier="standard" and cost_brl=0
**What goes wrong:** The credits summary shows zero BRL for all historical data before this migration.
**Why it happens:** Old rows don't have cost_brl populated.
**How to avoid:** In the summary query, for rows where `cost_brl = 0` but `cost_usd > 0`, apply the fallback conversion `cost_usd * VIDEO_USD_TO_BRL`. Document this in the query. Historical data will show approximate BRL.
**Warning signs:** Summary shows $0 BRL but nonzero USD.

### Pitfall 3: MySQL TEXT/JSON server_default Limitation
**What goes wrong:** Adding a Float column with `server_default="0.0"` works fine on MySQL. But if someone tries to add a JSON column, MySQL will reject it.
**Why it happens:** MySQL doesn't support `server_default` for TEXT/JSON columns (documented in project CLAUDE.md).
**How to avoid:** `cost_brl` is Float with `server_default="0.0"` -- this is safe. `model` is String(100), nullable -- also safe.

### Pitfall 4: Background Task Session Isolation
**What goes wrong:** The `_generate_video_task()` runs in a background task with its own DB session (via `get_session_factory()`). It cannot share the request session.
**Why it happens:** FastAPI BackgroundTasks run after the HTTP response is sent; the request session is already closed.
**How to avoid:** This is already correctly handled -- the background task creates its own session. Just ensure the new `cost_brl` and model parameters flow through the existing session correctly.
**Warning signs:** `DetachedInstanceError` or session-related exceptions in logs.

### Pitfall 5: Model ID in Config vs Model ID from Kie.ai Response
**What goes wrong:** The model_id in `VIDEO_MODELS` config (e.g., `"hailuo/2-3-image-to-video-standard"`) might differ from what Kie.ai returns in `gen_result.model`.
**Why it happens:** Kie.ai API may return a different model string than what was sent.
**How to avoid:** Use the model_id that was REQUESTED (from config/request param), not the one returned by Kie.ai. The config model_id is what maps to `prices_brl`. Fall back to the Kie.ai-returned model only if the requested one is unknown.

## Code Examples

### BRL Cost Lookup Helper

```python
# Source: config.py VIDEO_MODELS structure (verified in codebase)
def compute_video_cost_brl(model_id: str, duration: int) -> float:
    """Look up BRL cost from VIDEO_MODELS config.

    Falls back to cost_usd * VIDEO_USD_TO_BRL if model not found.
    """
    from config import VIDEO_MODELS, VIDEO_USD_TO_BRL, VIDEO_COST_PER_SECOND

    model_info = VIDEO_MODELS.get(model_id)
    if model_info and "prices_brl" in model_info:
        prices = model_info["prices_brl"]
        # Snap to nearest valid duration
        if duration in prices:
            return prices[duration]
        # Find closest duration
        valid = list(prices.keys())
        if valid:
            closest = min(valid, key=lambda d: abs(d - duration))
            return prices[closest]

    # Fallback: USD conversion
    import logging
    logging.getLogger("clip-flow.credits").warning(
        "Model %s not in VIDEO_MODELS, using USD fallback", model_id,
    )
    cost_usd = duration * VIDEO_COST_PER_SECOND
    return round(cost_usd * VIDEO_USD_TO_BRL, 2)
```

### Alembic Migration Pattern (from 015 as template)

```python
# 016_add_cost_brl_and_model.py
revision: str = '016'
down_revision: Union[str, None] = '015'

def upgrade() -> None:
    op.add_column(
        'api_usage',
        sa.Column('cost_brl', sa.Float(), server_default='0.0', nullable=False),
    )
    op.add_column(
        'api_usage',
        sa.Column('model', sa.String(100), nullable=True),
    )

def downgrade() -> None:
    op.drop_column('api_usage', 'model')
    op.drop_column('api_usage', 'cost_brl')
```

### Credits Summary Query Pattern

```python
# In UsageRepository
async def get_credits_summary(
    self, user_id: int, days: int = 30,
) -> dict:
    from datetime import timedelta
    from config import VIDEO_MODELS, VIDEO_DAILY_BUDGET_USD, VIDEO_USD_TO_BRL

    cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    # Per-model breakdown (within range)
    result = await self.session.execute(
        select(
            ApiUsage.tier,
            func.sum(ApiUsage.cost_brl).label("total_brl"),
            func.sum(ApiUsage.cost_usd).label("total_usd"),
            func.sum(ApiUsage.usage_count).label("count"),
        )
        .where(
            ApiUsage.user_id == user_id,
            ApiUsage.service == "kie_video",
            ApiUsage.status == "success",
            ApiUsage.date >= cutoff,
        )
        .group_by(ApiUsage.tier)
    )
    # ... aggregate and return
```

### Frontend BRL Formatting

```typescript
// Source: standard Intl.NumberFormat API
function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}
// formatBRL(2.62) => "R$ 2,62"
```

### Dashboard Card Pattern (from Phase 16)

```tsx
// Follows Phase 16 pattern: add below existing content
<Card>
  <CardHeader className="pb-3">
    <CardTitle className="flex items-center gap-2 text-base">
      <DollarSign className="h-4 w-4 text-primary" />
      Video Credits
    </CardTitle>
  </CardHeader>
  <CardContent>
    {/* Compact table: model | count | total BRL */}
    <table className="w-full text-sm">
      <thead>
        <tr className="text-muted-foreground text-xs">
          <th className="text-left pb-2">Modelo</th>
          <th className="text-right pb-2">Videos</th>
          <th className="text-right pb-2">Total</th>
        </tr>
      </thead>
      <tbody>
        {models.map(m => (
          <tr key={m.model_id}>
            <td>{m.model_name}</td>
            <td className="text-right">{m.count}</td>
            <td className="text-right font-mono">{formatBRL(m.total_brl)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </CardContent>
</Card>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cost_usd * 5.5` hardcoded | `VIDEO_USD_TO_BRL` env var (5.75) | Phase 18 | Configurable conversion rate |
| Single `VIDEO_COST_PER_SECOND` for all models | `VIDEO_MODELS[model].prices_brl` per model/duration | Phase 18 config expansion | Accurate per-model BRL pricing |
| tier="standard" for all kie_video | tier=model_id (Phase 20) | This phase | Enables per-model cost grouping |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (uses default discovery) |
| Quick run command | `python -m pytest tests/test_api_usage.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRED-01 | cost_brl recorded only on success, zero on failure | unit | `python -m pytest tests/test_credits.py::test_cost_brl_only_on_success -x` | Wave 0 |
| CRED-02 | cost_brl matches VIDEO_MODELS prices_brl | unit | `python -m pytest tests/test_credits.py::test_cost_brl_from_config -x` | Wave 0 |
| CRED-03 | credits summary endpoint returns correct schema | unit | `python -m pytest tests/test_credits.py::test_credits_summary_schema -x` | Wave 0 |
| CRED-04 | api_usage model has cost_brl and model columns | unit | `python -m pytest tests/test_credits.py::test_api_usage_cost_brl_column -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_credits.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_credits.py` -- covers CRED-01, CRED-02, CRED-03, CRED-04
- [ ] Schema validation for new cost_brl/model columns on ApiUsage (pattern from test_api_usage.py)
- [ ] compute_video_cost_brl helper unit tests

## Open Questions

1. **Unique constraint for per-model rows**
   - What we know: Current constraint is `uq_api_usage_user_service_tier_date` on (user_id, service, tier, date). If we set `tier=model_id`, each model gets its own row per day. This works without constraint changes.
   - What's unclear: Should the `model` column also be added to the unique constraint for future-proofing? Or is reusing `tier` sufficient?
   - Recommendation: Reuse `tier` for model_id. The `model` column is informational/display only. No constraint change needed. This minimizes migration risk.

2. **Historical data backfill**
   - What we know: Existing rows have `cost_brl=0.0` and `model=NULL` and `tier="standard"`.
   - What's unclear: Should we backfill BRL costs for historical data in the migration?
   - Recommendation: No backfill in migration. The summary query handles legacy rows by converting `cost_usd * VIDEO_USD_TO_BRL` when `cost_brl = 0`. Simple, safe, no data mutation.

## Sources

### Primary (HIGH confidence)
- **Codebase direct inspection** - `src/database/models.py:ApiUsage` (lines 593-615), `src/database/repositories/usage_repo.py` (full file), `src/api/routes/video.py` (lines 176-358), `config.py:VIDEO_MODELS` (lines 364-465)
- **Existing test patterns** - `tests/test_api_usage.py` (schema validation pattern)
- **Migration chain** - `015_add_legend_columns.py` confirms latest revision is 015

### Secondary (MEDIUM confidence)
- **Dashboard UI patterns** - `memelab/src/app/(app)/dashboard/page.tsx`, `memelab/src/hooks/use-api.ts` (SWR hook patterns)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in use, no new dependencies
- Architecture: HIGH - extending established patterns (upsert, SWR hooks, Card components)
- Pitfalls: HIGH - identified from direct code reading, all edge cases are in existing code paths

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain, internal codebase patterns)
