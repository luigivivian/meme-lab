# Phase 16: Dashboard v2 - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous --auto, infrastructure phase)

<domain>
## Phase Boundary

Enhance the existing dashboard with usage charts (30-day history), cost breakdown per service, pipeline activity timeline, alert system for quota limits, and publishing stats. All data comes from existing DB tables (api_usage, pipeline_runs, scheduled_posts, content_packages).

</domain>

<decisions>
## Implementation Decisions

### Charts & Visualization
- **D-01:** Use **recharts** library (lightweight, React-native, already common in Next.js projects) for line/bar/area charts.
- **D-02:** 30-day usage history chart: daily API calls by service (gemini_text, gemini_image, kie_video) as stacked area chart.
- **D-03:** Cost breakdown: pie/donut chart showing spend per service this month.
- **D-04:** Pipeline activity: bar chart of memes generated per day (last 30 days).

### API Endpoints
- **D-05:** `GET /dashboard/usage-history?days=30` — daily usage aggregated by service.
- **D-06:** `GET /dashboard/cost-breakdown?days=30` — cost per service aggregated.
- **D-07:** `GET /dashboard/pipeline-activity?days=30` — daily pipeline runs + packages produced.
- **D-08:** `GET /dashboard/publishing-stats` — published/queued/failed counts.

### Alerts
- **D-09:** Alert banner when any service is >80% of daily quota — yellow warning.
- **D-10:** Alert banner when any service is >95% — red critical.
- **D-11:** Alerts derived from existing `/auth/me/usage` data — no new DB tables needed.

### Frontend
- **D-12:** Enhance existing `/dashboard` page — add chart cards below stats grid.
- **D-13:** New chart cards: "Uso 30 dias", "Custos por Servico", "Atividade do Pipeline", "Publicacao".

### Claude's Discretion
- Chart colors and styling
- Responsive breakpoints for chart layout
- Exact recharts component types (Area, Bar, Pie)
- Alert threshold text formatting
- Date formatting in tooltips

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Dashboard page exists at `memelab/src/app/(app)/dashboard/page.tsx` with stats grid, content cards, usage bars
- `useUsage()` hook already fetches per-service usage
- `api_usage` table has daily aggregated data (service, tier, date, usage_count, cost_usd)
- `pipeline_runs` table has timestamps + packages_produced
- `scheduled_posts` table has status + published_at

### Integration Points
- `src/api/routes/` — new `dashboard.py` route module
- `src/api/app.py` — register dashboard router
- `memelab/src/app/(app)/dashboard/page.tsx` — extend with chart sections

</code_context>

<specifics>
## Specific Ideas

- Keep existing dashboard cards (stats, content, agents, runs, queue) — add charts section below
- recharts auto-sizes to container width — responsive by default

</specifics>

<deferred>
## Deferred Ideas

- Real-time WebSocket updates (polling is fine for now)
- Export dashboard as PDF report
- Custom date range picker (30-day default is fine)

</deferred>

---

*Phase: 16-dashboard-v2*
*Context gathered: 2026-03-26 via autonomous mode*
