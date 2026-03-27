# Phase 20: Kie.ai Credits & Cost Tracking - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a credits tracking system for Kie.ai API that correctly accounts costs per model using configured BRL prices, only deducting credits on successful video generation. Includes a summary API endpoint and a basic dashboard card showing cumulative BRL costs with per-model granularity.

</domain>

<decisions>
## Implementation Decisions

### Cost Storage & Calculation
- Store costs in BRL natively — add `cost_brl` column to existing `api_usage` table via Alembic migration. VIDEO_MODELS already has `prices_brl` per model per duration; avoids exchange rate drift
- Extend `api_usage` table (not new table) — reuses existing upsert pattern from `usage_repo.py`
- Record cost only after Kie.ai confirms `status=success` — failed/timeout generations cost zero
- Fallback for models not in VIDEO_MODELS config: use `cost_usd * 5.5` (same conversion Phase 18 uses), log warning

### Credits Summary API
- Single endpoint `GET /video/credits/summary` returning total, per-model breakdown, and budget info in one response
- Support `?days=30` query param for time range (default 30 days + all-time totals)
- Include failed generation counters (`failed_count`, `failed_zero_cost`) to show cost discipline
- Daily budget display: `daily_budget_brl`, `daily_spent_brl`, `daily_remaining_brl` based on existing `VIDEO_DAILY_BUDGET_USD` converted to BRL

### Dashboard Display (Phase 20 scope)
- New "Video Credits" card below existing dashboard content (per Phase 16 pattern: add below, don't replace)
- Compact table inside card showing per-model breakdown: model name, count, total BRL. Expandable if >5 models
- Do NOT update existing cost_usd displays — Phase 21 specifically handles "update all spending values to display in BRL"

### Claude's Discretion
- Migration number sequencing (chain from latest existing migration)
- Exact response schema for credits summary endpoint
- Card styling consistent with existing dashboard cards

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/database/models.py:ApiUsage` — existing usage tracking model with cost_usd, service, tier, date columns
- `src/database/repositories/usage_repo.py` — upsert pattern for usage recording
- `config.py:VIDEO_MODELS` — 10 models with `prices_brl` dict keyed by duration
- `config.py:VIDEO_DAILY_BUDGET_USD` — daily budget cap ($3.00 default)
- `src/video_gen/kie_client.py` — `cost_usd` already calculated per generation result
- `src/api/routes/video.py` — existing video route module
- `src/api/routes/dashboard.py` — existing dashboard routes

### Established Patterns
- Upsert per day/service/tier bucket in api_usage (from Quick Win QW3)
- Phase 18: BRL display uses `cost_usd * 5.5` approximation
- Phase 16: Dashboard adds new sections below existing content, never replaces
- Phase 999.1: Budget pre-check before generation, track actual after completion
- Alembic migrations chain sequentially (latest is 014 from Phase 999.2)

### Integration Points
- `kie_client.py` result handler — where cost recording happens after success
- `video.py` routes — add credits summary endpoint
- Dashboard frontend — add Video Credits card
- `usage_repo.py` — extend with BRL cost recording method

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: prices_brl from VIDEO_MODELS is the source of truth for BRL costs, not USD conversion.

</specifics>

<deferred>
## Deferred Ideas

- Converting all existing USD displays to BRL — Phase 21 scope
- Monthly budget tracking — daily budget is sufficient for Phase 20
- Cost forecasting/projections — future enhancement

</deferred>
