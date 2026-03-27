---
phase: 21-dashboard-business-metrics
verified: 2026-03-27T21:57:06Z
status: passed
score: 11/11 must-haves verified
re_verification: true
gaps: []
      - "Convert '15s — $0.23' to BRL equivalent using VIDEO_USD_TO_BRL (e.g. '15s — R$ 1,32') on line 912"
  - truth: "DASH-05, DASH-06, DASH-07 requirements appear in REQUIREMENTS.md traceability"
    status: failed
    reason: "Requirements DASH-05, DASH-06, DASH-07 are referenced extensively in plan frontmatter, RESEARCH.md, and ROADMAP.md but have NO definition entries in REQUIREMENTS.md (Dashboard v2 section ends at DASH-04). The traceability table also has no rows for these IDs."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Dashboard v2 section contains only DASH-01 through DASH-04. DASH-05/06/07 are used in phase plans but undefined in the requirements document."
    missing:
      - "Add DASH-05 definition to REQUIREMENTS.md: '- [x] **DASH-05**: All spending/cost values on the dashboard display in BRL (not USD)'"
      - "Add DASH-06 definition to REQUIREMENTS.md: '- [x] **DASH-06**: Dashboard cards show: total videos generated, average cost per video, remaining Kie.ai budget, total trends collected, active content packages'"
      - "Add DASH-07 definition to REQUIREMENTS.md: '- [x] **DASH-07**: Cards have colored icon backgrounds and trend indicators (up/down arrows) with comparative data vs previous period'"
      - "Add traceability rows: DASH-05, DASH-06, DASH-07 → Phase 21 → Complete"
human_verification:
  - test: "Navigate to dashboard and confirm all 4 StatsCards load with real data"
    expected: "Videos Gerados, Custo Medio/Video, Creditos Restantes, Trends Coletados cards each show numeric values and trend percentages (not 0 for all)"
    why_human: "Cannot verify live API data flow without a running server with DB records"
  - test: "Inspect cost pie chart in dashboard"
    expected: "Pie chart labels and tooltip values show R$ prefix (e.g. 'R$ 1,25'), not dollar signs"
    why_human: "BRL conversion is applied via costDataBRL useMemo at render time — cannot verify visual output without browser"
  - test: "Confirm duration buttons show USD vs BRL"
    expected: "After fix, duration buttons should read '10s — R$ 0,86' and '15s — R$ 1,32' (or similar BRL amounts)"
    why_human: "Current state has USD labels — this is the gap, confirmation needed after fix"
---

# Phase 21: Dashboard Business Metrics Verification Report

**Phase Goal:** Improve dashboard info cards with business-relevant metrics (videos gerados, custo medio por video, creditos restantes, trends coletados) and update all spending values to display in BRL
**Verified:** 2026-03-27T21:57:06Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Plan 01 — Backend)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /dashboard/business-metrics returns videos_generated, avg_cost_per_video_brl, budget_remaining_brl, trends_collected, active_packages | VERIFIED | `dashboard.py` line 156: `@router.get("/business-metrics")`, method returns `repo.get_business_metrics(current_user.id)` — all 5 keys present in return dict (lines 694-718 of usage_repo.py) |
| 2 | Each metric includes current (7d) and previous (7d) period values for trend computation | VERIFIED | SQLAlchemy `case()` expressions bucket results by `date >= current_start` vs `date < current_start` (lines 560-578); TrendEvent uses `created_at >= current_start` (lines 620-625) |
| 3 | Legacy api_usage rows with cost_brl=0 fallback to cost_usd * VIDEO_USD_TO_BRL | VERIFIED | Fallback applied at lines 595-601 (period level) and 688-689 (daily level): `if current_cost_brl == 0 and current_cost_usd > 0: current_cost_brl = round(current_cost_usd * VIDEO_USD_TO_BRL, 2)` |
| 4 | Trends counted via TrendEvent join through PipelineRun.character_id for tenant scoping | VERIFIED | Lines 627-632: `.join(PipelineRun, TrendEvent.pipeline_run_id == PipelineRun.id).outerjoin(Character, ...).where((Character.user_id == user_id) \| (PipelineRun.character_id.is_(None)))` |

### Observable Truths (Plan 02 — Frontend)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5 | All 4 StatsCards show business metrics: Videos Gerados, Custo Medio/Video, Creditos Restantes, Trends Coletados | VERIFIED | `dashboard/page.tsx` lines 199-251: four StatsCard instances with exact titles, each wired to `businessMetrics` data |
| 6 | Each StatsCard has a colored icon background and trend indicator with percentage change | VERIFIED | `iconClassName="bg-violet-500/10"` (line 203), `bg-emerald-500/10` (line 219), `bg-amber-500/10` (line 234), `bg-blue-500/10` (line 243); `computePercentChange()` helper called for trend values |
| 7 | Trend indicators display TrendingUp/TrendingDown/Minus icons rendered inside stats-card.tsx | VERIFIED | `stats-card.tsx` lines 35-41: three-state conditional renders `<TrendingUp>`, `<TrendingDown>`, `<Minus>` based on `trend.value > 0`, `< 0`, `=== 0` |
| 8 | Cost pie chart displays values in BRL with R$ prefix, not USD with $ prefix | VERIFIED | `costDataBRL` useMemo (lines 166-172) converts `cost_usd * VIDEO_USD_TO_BRL`; `dataKey="cost_brl"` (line 732); tooltip uses `formatBRL()` (line 749); label uses `formatBRL()` (line 740) |
| 9 | Video dialog budget shows BRL amount, not USD | VERIFIED | Line 883: `{formatBRL(budgetData.remaining_usd * VIDEO_USD_TO_BRL)} restante` |
| 10 | Total 30 dias text below cost chart shows BRL | VERIFIED | Line 765: `{formatBRL(costBreakdown.total_cost_usd * VIDEO_USD_TO_BRL)}` |
| 11 | No dollar signs ($) remain for cost displays in dashboard | FAILED | Lines 903 and 912 contain hardcoded `10s — $0.15` and `15s — $0.23` in video duration selection buttons inside the video generation dialog. These are spending/cost indicators visible to the user on the dashboard page. |

**Score: 10/11 truths verified**

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/database/repositories/usage_repo.py` | get_business_metrics() method | VERIFIED | 187-line method at line 532, 4 efficient queries, legacy BRL fallback, all 5 metric groups returned |
| `src/api/routes/dashboard.py` | GET /dashboard/business-metrics endpoint | VERIFIED | Lines 154-168: endpoint registered with DASH-05/06/07 comment, calls `repo.get_business_metrics(current_user.id)` |
| `tests/test_dashboard_metrics.py` | Unit tests for business metrics | VERIFIED | 116 lines, 11 tests covering method existence, schema validation, BRL conversion, endpoint registration — all pass |
| `memelab/src/lib/api.ts` | BusinessMetricsResponse interface and getBusinessMetrics function | VERIFIED | Lines 1363-1397: `getBusinessMetrics()` function and 5 interfaces (PeriodMetric, CostPeriodMetric, BudgetMetric, ActivePackagesMetric, BusinessMetricsResponse) |
| `memelab/src/hooks/use-api.ts` | useBusinessMetrics() SWR hook | VERIFIED | Lines 265-270: `useBusinessMetrics()` with 60s refresh interval |
| `memelab/src/components/panels/stats-card.tsx` | Extended StatsCard with iconClassName and trend arrow icons | VERIFIED | 68 lines: `iconClassName?: string` prop, TrendingUp/TrendingDown/Minus imports, three-state trend rendering with icon + color badge |
| `memelab/src/app/(app)/dashboard/page.tsx` | Dashboard with business cards and BRL charts | VERIFIED (partial) | 4 business cards wired to useBusinessMetrics hook, costDataBRL useMemo, BRL conversions applied — except 2 duration button labels remain in USD |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/api/routes/dashboard.py` | `src/database/repositories/usage_repo.py` | `UsageRepository.get_business_metrics()` | VERIFIED | Line 165: `repo = UsageRepository(session)`, line 166: `metrics = await repo.get_business_metrics(current_user.id)` |
| `src/database/repositories/usage_repo.py` | `src/database/models.py` | TrendEvent, ContentPackage, PipelineRun, Character | VERIFIED | Lines 547-552: all 4 models imported; queries join TrendEvent, PipelineRun, Character, ContentPackage |
| `memelab/src/app/(app)/dashboard/page.tsx` | `memelab/src/hooks/use-api.ts` | useBusinessMetrics() hook call | VERIFIED | Line 28: imported, line 107: `const { data: businessMetrics, isLoading: metricsLoading } = useBusinessMetrics()` |
| `memelab/src/hooks/use-api.ts` | `memelab/src/lib/api.ts` | getBusinessMetrics() API function | VERIFIED | Line 266: `() => api.getBusinessMetrics()` calls the exported function |
| `memelab/src/app/(app)/dashboard/page.tsx` | `memelab/src/components/panels/stats-card.tsx` | StatsCard with iconClassName prop | VERIFIED | Lines 203, 219, 234, 243: `iconClassName` prop passed to all 4 StatsCard instances |
| `memelab/src/components/panels/stats-card.tsx` | lucide-react | TrendingUp/TrendingDown/Minus icons | VERIFIED | Line 2: `import { type LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react"` — all 3 rendered conditionally |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `dashboard/page.tsx` StatsCards | `businessMetrics` | `useBusinessMetrics()` SWR → `getBusinessMetrics()` → `GET /dashboard/business-metrics` → `UsageRepository.get_business_metrics()` → 4 SQL queries on api_usage, trend_events, content_packages | Yes — queries use `func.sum`, `func.count` on live DB tables with user_id scoping | FLOWING |
| `dashboard/page.tsx` pie chart | `costDataBRL` | `useMemo` transforms `costBreakdown?.services` (from `useDashboardCostBreakdown` SWR hook) — each service entry gets `cost_brl = cost_usd * VIDEO_USD_TO_BRL` | Yes — derived from real DB-backed cost data | FLOWING |
| `dashboard/page.tsx` video dialog budget | `budgetData.remaining_usd` | `useVideoBudget()` SWR hook → existing endpoint | Yes — existing endpoint | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 11 unit tests pass | `python -m pytest tests/test_dashboard_metrics.py -x -v` | `11 passed in 0.41s` | PASS |
| TypeScript compiles clean | `cd memelab && npx tsc --noEmit` | No output (zero errors) | PASS |
| Endpoint declared in router | `grep "business-metrics" src/api/routes/dashboard.py` | Line 156: `@router.get("/business-metrics", ...)` | PASS |
| Commit hashes exist in git | `git log --oneline \| grep 4ad652c\|1329932\|7166ceb\|444b354` | All 4 hashes found | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DASH-05 | 21-01-PLAN, 21-02-PLAN | All spending/cost values display in BRL | PARTIAL | Cost chart, total text, budget dialog converted. Two duration button labels (`$0.15`, `$0.23`) remain in USD. |
| DASH-06 | 21-01-PLAN, 21-02-PLAN | Dashboard cards show business metrics (videos, cost, budget, trends, packages) | SATISFIED | 4 cards implemented and wired to live endpoint. Active packages shown as description on Videos Gerados card. |
| DASH-07 | 21-01-PLAN, 21-02-PLAN | Cards have colored icon backgrounds, trend indicators with arrows and period comparison | SATISFIED | `iconClassName` prop enables colored backgrounds (violet/green/amber/blue). TrendingUp/TrendingDown/Minus arrows render in StatsCard. computePercentChange provides 7d vs 7d delta. |

### Orphaned Requirements

DASH-05, DASH-06, and DASH-07 are referenced throughout all phase planning documents and the ROADMAP.md, but they have **NO definition entries** in `.planning/REQUIREMENTS.md`. The Dashboard v2 section ends at DASH-04. The traceability table also has no rows for these IDs.

This is a documentation gap only — the implementation clearly delivers the behaviors described in the phase plan. However, the requirements document is inconsistent: these IDs are used as authoritative references without being defined.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `memelab/src/app/(app)/dashboard/page.tsx` | 903 | `10s — $0.15` hardcoded USD price label | Warning | DASH-05 partial gap — cost display in USD on dashboard |
| `memelab/src/app/(app)/dashboard/page.tsx` | 912 | `15s — $0.23` hardcoded USD price label | Warning | DASH-05 partial gap — cost display in USD on dashboard |

Note: These are hardcoded string literals for video generation duration pricing, visible as button labels in the video generation dialog. The plan's Step 7 ("Search and fix any remaining '$' cost displays") should have caught these. The gallery page dollar sign was noted as out of scope, but these dashboard dialog labels were not addressed.

---

## Human Verification Required

### 1. Business metrics cards load with real data

**Test:** With the backend running and at least some api_usage + trend_events records in the DB, navigate to the dashboard page
**Expected:** All 4 StatsCards display non-zero values; trend percentage badges show with color-coded arrows (not all zeros)
**Why human:** Cannot verify live API data flow without a running server with populated DB records

### 2. Cost pie chart BRL rendering

**Test:** Navigate to dashboard, scroll to the "Custos por Servico" pie chart section
**Expected:** Pie chart labels and tooltip values show `R$ X,XX` format (e.g. `R$ 1,25`), not `$0.25` dollar format
**Why human:** BRL conversion applied at render time via costDataBRL useMemo — visual verification needed

### 3. StatsCard trend arrows render correctly

**Test:** When businessMetrics has non-zero period changes, inspect the trend block on each StatsCard
**Expected:** A green TrendingUp arrow for positive change, red TrendingDown for negative, gray Minus for zero — rendered visibly beside the percentage badge
**Why human:** Visual rendering of icon + badge combination requires browser inspection

---

## Gaps Summary

Two gaps found, one substantive and one documentary:

**Gap 1 — DASH-05 partial: Two USD price labels in video dialog duration buttons (lines 903, 912 of `dashboard/page.tsx`).** The plan's Step 7 instructed searching for remaining `$` cost displays and fixing them, but the hardcoded strings `10s — $0.15` and `15s — $0.23` in the video generation dialog's duration selection buttons were not converted. These are user-visible cost indicators on the dashboard. Fix: replace with BRL equivalents using `VIDEO_USD_TO_BRL = 5.75` (10s → R$ 0,86; 15s → R$ 1,32), or compute dynamically from a cost constant.

**Gap 2 — ORPHANED requirements: DASH-05, DASH-06, DASH-07 not defined in REQUIREMENTS.md.** The requirements document only defines DASH-01 through DASH-04 in its Dashboard v2 section. These three IDs are used extensively in plan frontmatter and ROADMAP.md but lack formal definition and traceability rows. This does not block functionality but creates documentation inconsistency. Fix: add definitions to REQUIREMENTS.md and three traceability table rows.

Both gaps are low-severity. The core goal (business-relevant metric cards with BRL values) is substantially achieved.

---

_Verified: 2026-03-27T21:57:06Z_
_Verifier: Claude (gsd-verifier)_
