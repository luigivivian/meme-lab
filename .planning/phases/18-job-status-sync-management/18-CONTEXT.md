# Phase 18: Job Status Sync & Management - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix stale/failed jobs still showing as running, implement proper job status synchronization that handles Kie.ai API errors and missing task IDs, and improve the jobs page UI with better progress visualization and clear status states.

</domain>

<decisions>
## Implementation Decisions

### Stale Job Detection
- Stale threshold: 15 minutes — any job with video_status="generating" older than 15 minutes is auto-marked as failed
- Detection timing: Server startup scan + periodic background check every 5 minutes
- Error message for stale jobs: "Timeout: geração excedeu o tempo limite" stored in video_metadata.error

### Failed Job Recovery
- One-click retry button on failed jobs — resubmits same prompt/model/image to Kie.ai
- Auto-retry on transient errors (429, 500): max 2 retries with exponential backoff within kie_client
- Kie.ai task_id shown in expandable detail row for debugging

### Jobs Page UI
- Progress visualization: percentage bar + step label ("Enviando...", "Gerando...", "Baixando...")
- Job card layout: card grid with thumbnail, model name, duration, cost BRL, status badge
- Auto-refresh: 3s while any job is generating, 30s when all idle (adaptive polling already exists)
- Sort order: newest first by creation date

### Claude's Discretion
- Internal implementation details of the stale job scanner (asyncio task vs APScheduler)
- Exact retry logic wiring between kie_client and the background task
- Card grid responsive breakpoints and exact styling

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/video_gen/kie_client.py` — KieSora2Client with poll_until_complete (5-30s backoff, 600s timeout)
- `src/api/routes/video.py` — all video endpoints including _generate_video_task background handler
- `memelab/src/hooks/use-api.ts` — useVideoList (adaptive 3s/10s polling), useVideoProgress
- `memelab/src/app/(app)/jobs/page.tsx` — existing jobs page with batch image + video sections

### Established Patterns
- Background task pattern: FastAPI BackgroundTasks with get_session_factory() for independent DB sessions
- SWR hooks with refreshInterval for polling
- Filter tabs using computed variables (not IIFEs) per previous feedback

### Integration Points
- ContentPackage.video_status column (generating/success/failed)
- ContentPackage.video_task_id for Kie.ai task tracking
- ContentPackage.video_metadata JSON for error storage
- DELETE /generate/video/{id} for cleanup

</code_context>

<specifics>
## Specific Ideas

- Stale job scanner should run as asyncio background task on server startup
- Retry should create a new Kie.ai task (not resume old one) with same parameters
- Progress endpoint already hits Kie.ai live — use task state for step labels
- Failed jobs: red icon (XCircle), red badge, error tooltip on hover (partially exists)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
