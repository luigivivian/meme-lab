# Phase 19: Video Gallery & Management - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a dedicated "Videos Gerados" page with its own sidebar menu entry. Support inline video playback, download, approve/delete actions, filters, and newest-first ordering. Images with existing videos show a tag but keep all generation actions enabled.

</domain>

<decisions>
## Implementation Decisions

### Video Gallery Layout
- Page layout: Grid of video cards (3 cols desktop, 2 tablet, 1 mobile) — responsive grid consistent with existing gallery
- Video card content: Thumbnail (from source image), play overlay icon, model badge, duration, status badge, BRL cost
- Inline player: Click card to expand inline with native HTML5 video player, autoplay on expand
- Sort default: Newest first (created_at DESC)

### Actions & Filters
- Delete confirmation: Confirmation dialog ("Deletar video X?") before removing video file and clearing DB fields
- Approve action: Toggle "Aprovado" badge on card + update DB field (video_metadata.approved = true)
- Filter types: Status tabs (Todos / Concluidos / Falhados) + dropdown for model selection
- Download button: Separate icon button on card, independent from play action

### Video Tag on Images & Sidebar
- Sidebar menu: "Videos" entry below "Gallery" with Film/Video icon
- Video tag on gallery images: Small "Video" chip/badge on image card (non-blocking, all actions visible)
- Re-generation: Same "Gerar Video" button regardless of existing videos — no blocking, allows multiple generations

### Claude's Discretion
- Animation and transition details for inline player expand/collapse
- Exact responsive breakpoints
- Card hover effects and loading states
- API endpoint for approve/delete video actions (extend existing video routes)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `memelab/src/app/(app)/gallery/page.tsx` — existing image gallery with grid layout, model selector, video generation trigger
- `memelab/src/app/(app)/jobs/page.tsx` — Phase 18 redesigned jobs page with card grid, progress bars
- `memelab/src/hooks/use-api.ts` — useVideoList, useVideoModels hooks
- `memelab/src/lib/api.ts` — getVideoList, deleteVideo, videoFileUrl functions
- `memelab/src/components/layout/shell.tsx` — sidebar navigation

### Established Patterns
- SWR hooks with refreshInterval for data fetching
- Grid layouts with responsive columns (existing gallery pattern)
- Filter tabs using computed variables (Phase 18 pattern)
- API routes in src/api/routes/video.py

### Integration Points
- Sidebar navigation: shell.tsx menuItems array
- Video file serving: GET /generate/video/file/{id}
- Video list: GET /generate/video/list
- Content package: video_status, video_path, video_metadata columns

</code_context>

<specifics>
## Specific Ideas

- Reuse videoFileUrl() for inline player source and download href
- Video list API should support sort=newest and filter params
- Approve could use PATCH on video_metadata JSON field
- Gallery page: add small "Video" chip next to images that have video_status="success"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
