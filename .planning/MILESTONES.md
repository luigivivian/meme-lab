# Milestones

## v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant (Shipped: 2026-04-01)

**Phases completed:** 8 phases, 27 plans, 53 tasks

**Key accomplishments:**

- Stale job scanner with 15-min auto-fail, retry endpoint for failed video jobs, progress API with step labels, and kie_client transient retry logic
- Card grid video jobs UI with progress bars, retry buttons, expandable detail rows, and status filter tabs
- Backend PATCH approve endpoint, model/sort filters on video list, frontend API client with SWR hook, and Videos sidebar navigation entry
- Dedicated /videos page with responsive video card grid, inline HTML5 playback, download/approve/delete actions, filter tabs, and violet Video Gerado badge on gallery images
- BRL-native cost tracking via ApiUsage cost_brl column, per-model tier grouping, and credits summary API endpoint with prices_brl lookup
- VideoCreditsCard component with per-model BRL cost breakdown table, daily budget progress bar, and all-time stats on dashboard
- GET /dashboard/business-metrics endpoint with 5 metric groups (videos, avg cost BRL, budget, trends, packages) using period comparison queries and legacy USD-to-BRL fallback
- 4 business StatsCards with colored icon backgrounds and trend arrow icons, plus full USD-to-BRL conversion for cost pie chart, total text, and video dialog budget
- Four AI modules for product ad pipeline: rembg background removal, Gemini scene composition with product preservation, style-aware cinematic prompt builder, and Portuguese copy generator
- KieMusicClient for Suno music via Kie.ai, FFmpeg format exporter with blur pad, text overlay (drawtext+tempfile), and 4-mode audio mixing
- ProductAdPipeline with 8 step methods chaining all modules -- GCS upload for video gen, Suno music, FFmpeg assembly, and BRL cost estimation before generation
- REST API with 10 endpoints for product ad pipeline following reels.py pattern -- create, execute, approve, regenerate, cost estimate
- API client types, SWR hooks, ads listing page, and 4-section wizard for creating video ads
- 1. [Rule 3 - Blocking] Ad API types and hooks not in worktree
- 4 async modules generating 9:16 images via Gemini, structured JSON roteiro via multimodal, WAV narration via Flash TTS, and SRT subtitles via Gemini audio transcription -- all using same GOOGLE_API_KEY with zero new dependencies
- FFmpeg xfade slideshow assembly (scale+pad, crossfade, SRT subtitles, audio mix) and ReelsPipeline 5-step sequential orchestrator with progress tracking and USD/BRL cost accumulation
- Complete Reels page with generation form (tema + tone/duration/niche/preset), real-time progress polling at 2s, job history card grid with status badges, and collapsible config panel for TTS/video settings
- Per-step pipeline execution with step_state persistence, video segmentation for >30s reels, and backward-compatible run() refactor
- Step-based API surface for interactive pipeline: execute/approve/regenerate/edit per step with tenant isolation and artifact file serving
- Interactive stepper UI with 6-step indicators, AnimatePresence transitions, and first 3 step components (prompt, images, script) with full approve/regenerate/edit controls
- Full 6-step interactive stepper with HTML5 audio preview, inline SRT editing, and video player with download
- Reordered interactive pipeline steps so script generates before images, with per-cena context-aware image generation from approved script cenas
- Per-scene Hailuo image-to-video generation via Kie.ai with parallel polling, static fallback, and mobile-optimized subtitle styling (FontSize=28)
- Reordered frontend stepper to match backend step order and fixed all approve wiring so each step triggers the correct next generation
- script_gen.py

---

## v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant (Shipped: 2026-03-27)

**Phases completed:** 4 phases, 8 plans, 15 tasks

**Key accomplishments:**

- BRL-native cost tracking via ApiUsage cost_brl column, per-model tier grouping, and credits summary API endpoint with prices_brl lookup
- VideoCreditsCard component with per-model BRL cost breakdown table, daily budget progress bar, and all-time stats on dashboard
- GET /dashboard/business-metrics endpoint with 5 metric groups (videos, avg cost BRL, budget, trends, packages) using period comparison queries and legacy USD-to-BRL fallback
- 4 business StatsCards with colored icon backgrounds and trend arrow icons, plus full USD-to-BRL conversion for cost pie chart, total text, and video dialog budget

---

## v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant (Shipped: 2026-03-27)

**Phases completed:** 9 phases, 23 plans, 43 tasks

**Key accomplishments:**

- Manual pipeline backend with hex-color Pillow composition, approval workflow, 27 theme palettes, and 9 API endpoints forcing zero Gemini Image calls
- Pipeline page rewrite with manual run form (input mode tabs, theme/color/image selectors), results grid with optimistic approve/reject per card and bulk actions, matching UI-SPEC design contract
- Alembic migration 010 with backfill/NOT NULL, CharacterRepository tenant filtering with admin bypass, and get_user_character deps helper
- PipelineRunRepository
- Alembic migration 012 with 6 video columns on ContentPackage, video_prompt_notes on Theme, 13 config constants for Kie.ai Sora 2, and GCS uploader service for public image URLs
- 4 video API endpoints (generate, batch, status, budget) with daily budget enforcement, background async processing, and cost tracking via kie_video service

---
