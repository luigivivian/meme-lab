# Phase 12: Pipeline Simplification - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Manual pipeline mode that composes memes using pre-existing static backgrounds (solid colors + uploaded images) and Pillow text composition, with zero Gemini Image API calls. Users trigger runs from the Pipeline page, preview results inline, and approve/reject each meme. Trend agents are fully decoupled — the manual pipeline never calls L1/L2/L3.

</domain>

<decisions>
## Implementation Decisions

### Background Selection
- **D-01:** Both solid colors and image library available as background sources
- **D-02:** Per-theme color palettes — each theme in themes.yaml gets 3-5 curated solid colors matching its mood (e.g., sabedoria = deep blues, cafe = warm browns)
- **D-03:** Solid colors only — no gradients in this phase
- **D-04:** Background images are per-character (assets/backgrounds/{character}/ structure, matching existing mago/ pattern)
- **D-05:** Users can upload new background images via the frontend UI, stored per-character

### Pipeline Trigger Flow
- **D-06:** Two input modes: "Generate from topic" (Gemini generates phrase from user's topic) and "Use my phrase" (user writes exact text, no Gemini text call)
- **D-07:** Manual run form lives on the existing Pipeline page (memelab/src/app/(app)/pipeline/page.tsx)
- **D-08:** User chooses meme count (1-10), default 3
- **D-09:** L5 post-production (captions, hashtags, quality) is an optional toggle in the form, default on
- **D-10:** Character comes from the sidebar selector — no redundant character dropdown in the form
- **D-11:** "Use my phrase" mode supports multiple phrases (one per line), each becoming one meme

### Preview & Approval
- **D-12:** Inline results on the Pipeline page — grid of thumbnails with approve/reject buttons per meme after run completes
- **D-13:** Bulk actions: "Approve All" and "Reject All" buttons
- **D-14:** Rejected memes are soft-deleted — marked as 'rejected' status in DB, still visible in gallery with filter. Can be un-rejected.
- **D-15:** Approved memes just get 'approved' status. No download button or next action — publishing comes in Phase 15.

### Trend Decoupling
- **D-16:** Manual pipeline never calls L1/L2/L3 trend agents. Trends remain a standalone tool on the Trends page.
- **D-17:** Only the manual/simplified flow is exposed in the UI for Phase 12. Full 5-layer pipeline code stays in codebase but is not accessible from the frontend.

### Claude's Discretion
- Implementation details for the upload endpoint (storage location, file validation, max size)
- Default meme count value and form layout specifics
- How the Pipeline page UI splits between the run form and the results grid

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Architecture
- `.planning/codebase/ARCHITECTURE.md` — Full 5-layer pipeline architecture, data flow, and entry points
- `.planning/codebase/STRUCTURE.md` — File locations and where to add new code

### Existing Pipeline Code
- `src/pipeline/async_orchestrator.py` — AsyncPipelineOrchestrator with background_mode parameter
- `src/pipeline/workers/image_worker.py` — ImageWorker with background_mode="static" path
- `src/image_maker.py` — Pillow composition engine (text overlay, watermark, vignette)
- `src/pipeline/workers/generation_layer.py` — L4 GenerationLayer (phrase + image coordination)
- `src/pipeline/workers/post_production.py` — L5 PostProductionLayer (caption/hashtag/quality)

### Configuration
- `config/themes.yaml` — Theme definitions (will need per-theme color palettes added)
- `config.py` — IMAGE_WIDTH/HEIGHT, PIPELINE_IMAGES_PER_RUN, layout templates

### API
- `src/api/routes/pipeline.py` — Existing pipeline run endpoint (POST /pipeline/run)
- `src/api/models.py` — PipelineRunRequest model (background_mode field exists)

### Frontend
- `memelab/src/app/(app)/pipeline/page.tsx` — Pipeline page (manual run form goes here)
- `memelab/src/app/(app)/gallery/page.tsx` — Gallery page (reference for image display patterns)

### Database
- `src/database/models.py` — GeneratedImage, ContentPackage, PipelineRun models
- `src/database/repositories/content_repo.py` — Content query patterns
- `src/database/repositories/pipeline_repo.py` — Pipeline run CRUD

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/image_maker.py`: Full Pillow composition engine — text wrapping, stroke, shadow, vignette, watermark, 4 layout templates (bottom, top, center, split_top)
- `src/pipeline/workers/image_worker.py`: Already supports `background_mode="static"` which skips Gemini/ComfyUI entirely
- `src/pipeline/async_orchestrator.py`: Shortcut mode bypasses L1/L2/L3 — can be adapted for manual topics
- `config/themes.yaml`: 13+ themes with mood_keywords — natural place to add color palettes
- Gallery page component patterns for displaying image grids

### Established Patterns
- Shortcut mode (bypass L1/L2/L3 for manual topics) — direct jump to L4
- PipelineRunRequest already accepts background_mode, cost_mode, character_slug
- ContentPackage carries phrase + image_path + background_source + approval status
- Sidebar character selector pattern (Sprint 1 of multi-character)

### Integration Points
- `POST /pipeline/run` — extend with new fields (input_mode, custom_phrases, enrich toggle)
- `GeneratedImage` model — needs approval_status column (or use existing status field)
- Pipeline page — add manual run form above/alongside the 5-layer diagram
- themes.yaml — add `colors` array per theme entry

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-pipeline-simplification*
*Context gathered: 2026-03-24*
