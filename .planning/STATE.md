---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Pipeline Simplification, Auto-Publicacao & Multi-Tenant
status: Phase complete — ready for verification
stopped_at: Completed 999.8-G-asset-reuse plan
last_updated: "2026-03-31T06:59:03.547Z"
last_activity: "2026-03-31 - Completed quick task 260330-tgu: Enhance theme button for reels"
progress:
  total_phases: 17
  completed_phases: 8
  total_plans: 27
  completed_plans: 28
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** Pipeline compoe e publica memes automaticamente — simples, rapido, sem depender de APIs caras de geracao de imagem
**Current focus:** Phase 421 — product-studio-ai-video-ads-generator

## Current Position

Phase: 421 (product-studio-ai-video-ads-generator) — EXECUTING
Plan: 7 of 7

## Performance Metrics

**Velocity:**

- Total plans completed: 0 (v2.0)
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 12 P01 | 9min | 2 tasks | 9 files |
| Phase 12 P02 | 8min | 2 tasks | 4 files |
| Phase 13 P01 | 3min | 2 tasks | 5 files |
| Phase 13 P02 | 3min | 2 tasks | 5 files |
| Quick 260325-qhl | 6min | 3 tasks | 7 files |
| Phase 999.1 P01 | 2min | 2 tasks | 6 files |
| Phase 999.1 P02 | 3min | 2 tasks | 3 files |
| Phase 999.1 P03 | 3min | 2 tasks | 4 files |
| Phase 15 P01 | 4min | 2 tasks | 4 files |
| Phase 15 P02 | 4min | 2 tasks | 3 files |
| Phase 16 P02 | 4min | 2 tasks | 4 files |
| Phase 999.2 P01 | 6min | 2 tasks | 6 files |
| Phase 999.2 P02 | 5min | 3 tasks | 5 files |
| Phase 999.3 P01 | 4min | 1 tasks | 3 files |
| Phase 999.3 P02 | 4min | 1 tasks | 3 files |
| Phase 18 P01 | 3min | 2 tasks | 5 files |
| Phase 18 P02 | 5min | 2 tasks | 3 files |
| Phase 19 P01 | 5min | 2 tasks | 4 files |
| Phase 19 P02 | 3min | 2 tasks | 2 files |
| Phase 19 P02 | 4min | 2 tasks | 2 files |
| Phase 20 P01 | 4min | 2 tasks | 7 files |
| Phase 20 P02 | 2min | 2 tasks | 3 files |
| Phase 21 P01 | 2min | 1 tasks | 3 files |
| Phase 21 P02 | 3min | 2 tasks | 4 files |
| Phase 999.4 P01 | 3min | 2 tasks | 6 files |
| Phase 999.4 P02 | 3min | 2 tasks | 4 files |
| Phase 999.4 P03 | 2min | 2 tasks | 2 files |
| Phase 999.4 P04 | 2min | 2 tasks | 2 files |
| Phase 999.4 P05 | 3min | 2 tasks | 4 files |
| Phase 999.5 P01 | 3min | 3 tasks | 5 files |
| Phase 999.5 P02 | 2min | 1 tasks | 2 files |
| Phase 999.5 P03 | 5min | 2 tasks | 8 files |
| Phase 999.5 P04 | 3min | 2 tasks | 5 files |
| Phase 999.6 P02 | 2min | 1 tasks | 3 files |
| Phase 999.6 P01 | 2min | 2 tasks | 4 files |
| Phase 999.6 P03 | 1min | 2 tasks | 5 files |
| Phase 421 P01 | 3min | 2 tasks | 6 files |
| Phase 421 P02 | 2min | 2 tasks | 4 files |
| Phase 421 P03 | 2min | 2 tasks | 2 files |
| Phase 421 P04 | 2min | 1 tasks | 1 files |
| Phase 421 P05 | 2min | 2 tasks | 2 files |
| Phase 421 P06 | 3min | 2 tasks | 6 files |
| Phase 421 P07 | 5min | 2 tasks | 13 files |
| Phase quick-260330-ie5 P01 | 3min | 2 tasks | 5 files |
| Phase quick-260330-tgu P01 | 5min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Roadmap]: Split Instagram publishing into two phases (14: Connection/CDN, 15: Scheduling/Publishing) for cleaner delivery boundaries
- [v2.0 Roadmap]: Dashboard v2 (Phase 16) depends only on Phase 13 (tenant isolation), not on publishing — can be parallelized
- [v2.0 Roadmap]: Auth v2 (password reset, 2FA, OAuth) deferred to future milestone
- Pipeline nao chama Gemini Image API — apenas compoe backgrounds existentes + frases
- Agentes de trends desacoplados do pipeline (consulta avulsa)
- [Phase 12]: Hex color passed via background_path param — avoids new parameter, detected by startswith('#')
- [Phase 12]: Manual pipeline forces background_mode=static and use_gemini_image=False — zero Gemini Image calls guaranteed
- [Phase 12]: Optimistic UI updates for approve/reject — immediate feedback, revert on API error
- [Phase 13]: Fetch-then-check pattern for 403 vs 404 distinction in CharacterRepository
- [Phase 13]: PermissionError at repo level, HTTPException 403 at deps.py helper level
- [Phase 13]: Transitive ownership via Character join for all child-table repos (consistent pattern)
- [Phase 13]: ThemeRepository hybrid ownership: global themes public, user themes by user_id, character themes by Character.user_id
- [Quick 260325-qhl]: Tile-based token estimation: ceil(w/768)*ceil(h/768)*258 per input image
- [Quick 260325-qhl]: cost_usd accumulated via upsert per day/service/tier bucket in api_usage
- [Phase 999.1]: Migration 012 chains from 011 (sequential pattern); all video columns nullable; GCSUploader lazy client init
- [Phase 999.1]: Config fallback chain (param -> config module -> env var) for video_gen modules
- [Phase 999.1]: 17 motion templates for full theme coverage (15 core + cotidiano + descanso)
- [Phase 999.1]: Background video task uses get_session_factory() for independent DB sessions (request session unavailable in BackgroundTasks)
- [Phase 999.1]: Budget enforcement: pre-check estimated cost before generation, track actual cost after completion via kie_video service
- [Phase 15]: InstagramStatus type includes token_expires_at for future expiry warnings
- [Phase 15]: useInstagramStatus refreshes every 60s with errorRetryCount 1 (non-critical)
- [Phase 15]: Month view uses colored dots (not full cards) for compact calendar cells
- [Phase 15]: Schedule dialog hard-blocks submit when Instagram not connected
- [Phase 16]: QuotaAlerts uses existing useUsage() data (no new endpoint/DB tables needed)
- [Phase 16]: Charts placed below existing dashboard content, not replacing anything
- [Phase 999.2]: Migration 014 chains from 012 (not 013) because 013 migrations exist only in parallel worktrees
- [Phase 999.2]: Textfile approach for FFmpeg drawtext phrase text to avoid Windows escaping issues
- [Phase 999.2]: Typewriter mode uses line-by-line reveal with per-line fade-in (not char-by-char)
- [Phase 999.2]: LegendWorker uses lazy renderer init to avoid importing FFmpeg deps when disabled
- [Phase 999.2]: Legend runs AFTER asyncio.gather in PostProductionLayer (sequential post-step for I/O-heavy FFmpeg)
- [Phase 999.3]: v2 templates use 4 sentences 300-355 chars; camera mapped per theme emotional tone; MOTION_TEMPLATES alias points to V2 for backward compat
- [Phase 999.3]: v2 system prompt uses structured CAMERA/SUBJECT/PHYSICS/ATMOSPHERE sections per OpenAI Cookbook
- [Phase 999.3]: max_tokens 250 for v2 (4-5 sentences, 300-500 chars); _get_system_prompt()/_get_enhance_prompt() version switching
- [Phase 18]: Stale scanner checks Kie.ai task status before marking as failed (avoids false positives)
- [Phase 18]: Progress endpoint queries Kie.ai live for generating jobs, returns from DB for terminal states
- [Phase 18]: Video section always shown (even when empty) with centered empty state
- [Phase 18]: BRL cost in video cards: cost_usd * 5.5 (approximate conversion)
- [Phase 19]: JSON LIKE filtering for video model in MySQL; dict copy for SQLAlchemy JSON change detection; separate useVideoGallery hook from useVideoList
- [Phase 19]: VideoCard inline component in same file (per Phase 18 pattern)
- [Phase 19]: Video Gerado badge uses violet color to distinguish from source badges (gemini=blue, comfyui=purple, static=zinc)
- [Phase 19]: Inline VideoCard component in same file per Phase 18 pattern
- [Phase 19]: Violet badge color for Video Gerado distinguishes from existing source badges
- [Phase 20]: tier=model_id approach: per-model rows via existing unique constraint, no schema change needed
- [Phase 20]: Legacy api_usage rows (cost_brl=0, cost_usd>0) handled by USD*BRL fallback in summary query
- [Phase 20]: compute_video_cost_brl in config.py: prices_brl lookup with closest-duration snap, USD fallback for unknown models
- [Phase 20]: VideoCreditsCard placed below existing dashboard content, before Dialog (per Phase 16 pattern)
- [Phase 20]: No existing cost_usd displays modified (deferred to Phase 21 per user decision)
- [Phase 20]: formatBRL uses Intl.NumberFormat pt-BR for locale-aware BRL formatting
- [Phase 21]: All-time totals use separate unbounded queries (not limited to 14-day comparison window)
- [Phase 21]: Active packages defined as ContentPackage with video_status IS NOT NULL
- [Phase 21]: Legacy cost_brl=0 fallback applied at both period and daily level using VIDEO_USD_TO_BRL
- [Phase 21]: VIDEO_USD_TO_BRL = 5.75 frontend constant matching backend config.py for BRL conversion
- [Phase 21]: Arrow icons (TrendingUp/TrendingDown/Minus) rendered inside StatsCard component for reusability, not in dashboard page
- [Phase 21]: Active packages count shown as description subtitle on Videos Gerados card (clean 4-card grid)
- [Phase 999.4]: TTS/transcription defaults to gemini (not openai) — zero new dependencies for reels pipeline
- [Phase 999.4]: Direct Gemini API for image gen (no wrapper), response_schema for script JSON, PCM-to-WAV for TTS
- [Phase 999.4]: xfade filter for crossfade transitions (not concat demuxer); lazy imports in pipeline orchestrator
- [Phase 999.4]: Models imported from src/reels_pipeline/models.py (no duplication in api/models.py)
- [Phase 999.4]: Native HTML range inputs for config sliders (no Slider component in project)
- [Phase 999.5]: Per-step pipeline methods take explicit I/O for interactive execution (no hidden class state)
- [Phase 999.5]: Video segmentation uses greedy bin-packing at ~30s boundaries; SRT slicing filters and re-indexes entries
- [Phase 999.5]: Prompt step runs sync, heavy steps in background; flag_modified on all step_state mutations; regenerate clears downstream
- [Phase 999.5]: Approve-then-execute pattern: each step component calls approveStep then executeStep for next step
- [Phase 999.5]: StepScript auto-saves dirty edits on approve to prevent data loss
- [Phase 999.5]: Shared handleApprove/handleRegenerate in jobId page centralizes API calls and SWR refresh for all 6 steps
- [Phase 999.5]: StepSubtitles auto-saves dirty SRT edits on approve to prevent data loss (same pattern as StepScript)
- [Phase 999.6]: Hailuo 2.3 Standard model for per-scene image-to-video (R$1.31/6s); static image fallback on failure; FontSize=28 Bold=1 Outline=3 MarginV=80 for mobile subtitles
- [Phase 999.6]: n_imagens defaults to 5 when image_paths=None (text-only script gen mode)
- [Phase 999.6]: Per-cena image gen falls back to generic gen when no script available in step_state
- [Phase 999.6]: Button labels reflect next action (Gerar Roteiro, Gerar Imagens, Aprovar e Gerar Narracao) for clearer UX
- [Phase 421]: Migration 020 chains from 018 (latest numbered); Float for cost columns matching ReelsJob; Config follows reels_pipeline pattern
- [Phase 421]: compose_scene uses gemini-2.5-flash-image for scene composition; analyze_product uses gemini-2.5-flash text model for JSON analysis
- [Phase 421]: prompt_builder appends NEGATIVE_PROMPTS per style after LLM-generated motion prompt; copy_generator uses response_mime_type=application/json
- [Phase 421]: KieMusicClient uses same Bearer token auth and BASE_URL as KieSora2Client (no shared base class)
- [Phase 421]: GCS upload_image before Kie.ai create_task (public URL required); estimate_cost returns BRL breakdown per D-19
- [Phase 421]: Ads router mirrors reels.py pattern exactly (background tasks, flag_modified, get_session_factory)
- [Phase 421]: Manual collapsible sections in wizard (no Accordion component); client-side cost estimate by style; AI analysis via /ads/analyze pre-fill
- [Phase 421]: AdStepper uses horizontal scrollable layout for 8 steps; StepExport has no approve button per D-22 auto-complete; Ad API types created inline due to worktree isolation
- [Phase quick-260330-tgu]: Niche selector replaces plain text input; enhance sends PT-BR niche label to Gemini
- [Phase 999.8-G]: Pure Python cosine similarity (no numpy) for asset reuse; Gemini text-embedding-004 for 768-dim embeddings; threshold 0.85 for conservative match

### Pending Todos

None.

### Blockers/Concerns

- Facebook App Review for `instagram_content_publish` takes 2-6 weeks — must start early (during Phase 13)
- Cloudflare R2 CDN setup required before Phase 14 testing
- `api_usage.date` column DateTime vs Date ambiguity — resolve during Phase 16 planning

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260330-ie5 | Enhance ads wizard scene step with customizable presets for backgrounds cameras lighting organized by product categories editable scene suggestions product description and manual prompt editing | 2026-03-30 | 9e02cdc | [260330-ie5-enhance-ads-wizard-scene-step-with-custo](./quick/260330-ie5-enhance-ads-wizard-scene-step-with-custo/) |
| 260330-tgu | Add Enhance Theme button to reels creation - AI-powered topic suggestions after sub-theme selection | 2026-03-31 | 073c33c | [260330-tgu-add-enhance-theme-button-to-reels-creati](./quick/260330-tgu-add-enhance-theme-button-to-reels-creati/) |

## Session Continuity

Last activity: 2026-03-31 - Completed quick task 260330-tgu: Enhance theme button for reels
Last session: 2026-03-31T06:59:03.538Z
Stopped at: Completed 999.8-G-asset-reuse plan
Resume file: None
