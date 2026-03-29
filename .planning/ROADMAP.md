# Roadmap: Clip-Flow

## Completed Milestones

- [x] **v1.0**: Auth, Rate Limiting & Gemini Image Fix — 11 phases, 25/25 requirements, completed 2026-03-24 — [details](milestones/v1.0-ROADMAP.md)

## Current Milestone: v2.0 Pipeline Simplification, Auto-Publicacao & Multi-Tenant

**Milestone Goal:** Pipeline simplificado que compoe memes (backgrounds existentes + frases) sem chamar Gemini Image API, com publicacao automatica Instagram, isolamento multi-tenant, dashboard de metricas e billing via Stripe.

## Phases

**Phase Numbering:**
- Integer phases (12, 13, ...): Planned milestone work (continuing from v1.0 phase 11)
- Decimal phases (12.1, 12.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 12: Pipeline Simplification** - Manual pipeline mode with static backgrounds and Pillow composition, zero Gemini Image calls (completed 2026-03-26)
- [x] **Phase 13: Tenant Isolation** - Per-user data scoping across all resources with admin bypass (completed 2026-03-25)
- [x] **Phase 14: Instagram Connection & CDN** - Connect Instagram Business Account, CDN image upload, token lifecycle management (completed 2026-03-26)
- [x] **Phase 15: Publishing & Scheduling** - Schedule, publish, manage, and calendar-view Instagram posts (completed 2026-03-26)
- [x] **Phase 16: Dashboard v2** - 30-day usage history, limit alerts, cost reports, and pipeline run history (completed 2026-03-26)
- [x] **Phase 17: Billing & Stripe** - Subscription plans with Stripe Checkout, webhooks, portal, and plan enforcement (completed 2026-03-26)
- [x] **Phase 999.1: Video Generation — Kie.ai Sora 2** - Image-to-video via Kie.ai API, GCS upload, motion prompts, budget cap (completed 2026-03-26)
- [x] **Phase 999.2: Video Legends & Subtitles** - FFmpeg text overlays on videos, 3 animation modes, pipeline integration (completed 2026-03-27)
- [x] **Phase 999.3: Sora 2 Prompt Engineering Research** - V2 motion templates, three-layer framework, version switching (completed 2026-03-27)
- [x] **Phase 18: Job Status Sync & Management** - Fix stale/failed jobs, status sync, improved jobs page UI with progress visualization (completed 2026-03-27)
- [x] **Phase 19: Video Gallery & Management** - Dedicated videos page, inline player, download/approve/delete, filters, video tag on images (completed 2026-03-27)
- [x] **Phase 20: Kie.ai Credits & Cost Tracking** - Credits system per model, only charge on success, BRL cost tracking (completed 2026-03-27)
- [x] **Phase 21: Dashboard Business Metrics** - Spending in BRL, business-relevant cards, improved info density (completed 2026-03-27)
- [x] **Phase 999.4: Instagram Reels Pipeline** - Geracao automatizada de Reels: imagens → roteiro Claude → TTS → legendas → FFmpeg → MP4 (completed 2026-03-28)
- [ ] **Phase 999.5: Interactive Reels Pipeline** - Stepper UI com aprovacao por etapa, regeneracao individual, videos longos via segmentacao (BACKLOG)
- [ ] **Phase 999.6: Reels Pipeline v2 — Hailuo + Scene Context + Interactive Fix** - Fix interactive stepper flow, scene-by-scene image gen following script, Hailuo video generation per scene, mobile-optimized subtitles (BACKLOG)
- [ ] **Phase 421: Product Studio — AI Video Ads Generator** - Wizard progressivo para geracao 100% IA de videos comerciais de produto. 8-step pipeline: analise, cenario, prompt, video (Wan 2.6/Kling 2.5), copy, audio (Suno+TTS), montagem, export multi-formato. 3 estilos: cinematico, narrado, lifestyle. Secao /ads (BACKLOG)

## Phase Details

### Phase 12: Pipeline Simplification
**Goal**: Users can generate composed memes through a manual pipeline using pre-existing backgrounds and Pillow composition, without any Gemini Image API calls
**Depends on**: Nothing (first phase of v2.0; builds on v1.0 infrastructure)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. User can trigger a pipeline run that produces composed meme images using only static backgrounds and Gemini text phrases — no Gemini Image API calls are made
  2. User can select a theme and background style before running the pipeline
  3. User can preview composed memes in a gallery and approve or reject each one before they move downstream
  4. Pipeline output images are visually correct compositions (background + phrase text rendered by Pillow)
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md — Backend: DB migration, image_maker hex colors, themes.yaml palettes, API endpoints
- [x] 12-02-PLAN.md — Frontend: API client, hooks, Pipeline page rewrite per UI-SPEC
- [ ] 12-03-PLAN.md — Integration: migration + servers + human verification checkpoint

### Phase 13: Tenant Isolation
**Goal**: Every user sees only their own data across all resources, with admin users able to bypass isolation
**Depends on**: Phase 12
**Requirements**: TENANT-01, TENANT-02, TENANT-03, TENANT-04
**Success Criteria** (what must be TRUE):
  1. User can only see their own characters, pipeline runs, content packages, images, scheduled posts, and batch jobs — no other user's data appears anywhere
  2. All tenant-scoped tables have a user_id foreign key and all repository queries filter by it
  3. An admin user can access any user's data through admin-flagged requests
  4. A user attempting to access another user's resource receives a 403 Forbidden (not 404 Not Found)
**Plans**: 3 plans

Plans:
- [x] 13-01-PLAN.md — Foundation: migration (backfill + NOT NULL + Theme.user_id), CharacterRepo tenant filtering, deps.py helper, test scaffold
- [x] 13-02-PLAN.md — Remaining repos: pipeline, content, job, theme, schedule repos with tenant filtering
- [ ] 13-03-PLAN.md — Route wiring: all 9 route files pass current_user to repos, catch PermissionError as 403

### Phase 14: Instagram Connection & CDN
**Goal**: Users can connect their Instagram Business Account and have their images uploaded to a CDN with public URLs ready for Instagram publishing
**Depends on**: Phase 13
**Requirements**: PUB-01, PUB-02, PUB-07
**Success Criteria** (what must be TRUE):
  1. User can connect an Instagram Business Account via Facebook OAuth flow and see the connected account in their settings
  2. Composed meme images are automatically uploaded to Cloudflare R2 CDN and assigned public URLs accessible by Instagram's servers
  3. Instagram access tokens auto-refresh before the 60-day expiry — user never has to manually reconnect due to token expiration
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [ ] 14-01: TBD
- [ ] 14-02: TBD

### Phase 15: Publishing & Scheduling
**Goal**: Users can schedule posts to specific times, have them auto-published via Instagram Graph API, manage the queue, and view everything in a content calendar
**Depends on**: Phase 14
**Requirements**: PUB-03, PUB-04, PUB-05, PUB-06
**Success Criteria** (what must be TRUE):
  1. User can schedule an approved meme for a specific date and time
  2. The scheduler automatically publishes posts at the scheduled time via Instagram Graph API (container create, poll, publish)
  3. User can view, cancel, and retry scheduled posts from a management interface
  4. User can view a content calendar (month and week views) showing scheduled and published posts
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD

### Phase 16: Dashboard v2
**Goal**: Users can monitor their usage, costs, and pipeline activity through an enhanced dashboard with charts, alerts, and history
**Depends on**: Phase 13
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. User can view a 30-day usage history chart showing daily consumption trends
  2. User sees alert notifications when approaching 80% and 95% of their plan quota
  3. User can view an estimated cost report broken down by service and tier
  4. User can view pipeline run history with status indicators (success, failed, in-progress)
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [ ] 16-01: TBD
- [ ] 16-02: TBD

### Phase 17: Billing & Stripe
**Goal**: Users can subscribe to plans, have limits enforced, and manage their billing entirely through Stripe integration
**Depends on**: Phase 16
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05
**Success Criteria** (what must be TRUE):
  1. User can subscribe to a plan (Free, Pro, or Enterprise) via Stripe Checkout and see their active plan in the app
  2. Plan limits are enforced — user hitting their quota sees an upgrade prompt instead of being able to exceed limits
  3. Stripe webhooks correctly handle subscription lifecycle events (create, renew, update, cancel) and the app reflects changes within seconds
  4. User can manage billing (update card, change plan, cancel subscription) via Stripe Customer Portal without leaving the flow
  5. Failed payments trigger a grace period and eventual automatic downgrade to Free tier
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 17-01-PLAN.md -- Backend: DB migration (subscriptions table + user billing columns), Stripe service, billing API routes, plan-aware quota enforcement
- [ ] 17-02-PLAN.md -- Frontend: billing page, plan selector, checkout redirect, subscription management UI

## Progress

**Execution Order:**
Phases execute in numeric order: 12 -> 12.1 -> 12.2 -> 13 -> ...

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Pipeline Simplification | 2/3 | Complete    | 2026-03-26 |
| 13. Tenant Isolation | 2/3 | Complete    | 2026-03-25 |
| 14. Instagram Connection & CDN | 0/? | Complete    | 2026-03-26 |
| 15. Publishing & Scheduling | 0/? | Complete    | 2026-03-26 |
| 16. Dashboard v2 | 0/? | Complete    | 2026-03-26 |
| 17. Billing & Stripe | 1/2 | Complete    | 2026-03-26 |
| 999.1. Video Generation — Kie.ai Sora 2 | 3/3 | Complete    | 2026-03-26 |
| 999.2. Video Legends & Subtitles | 2/2 | Complete    | 2026-03-27 |
| 999.3. Sora 2 Prompt Engineering | 2/2 | Complete    | 2026-03-27 |
| 18. Job Status Sync & Management | 1/2 | Complete    | 2026-03-27 |
| 19. Video Gallery & Management | 2/2 | Complete    | 2026-03-27 |
| 20. Kie.ai Credits & Cost Tracking | 2/2 | Complete    | 2026-03-27 |
| 21. Dashboard Business Metrics | 2/2 | Complete    | 2026-03-27 |

### Phase 18: Job Status Sync & Management
**Goal**: Kill stale/failed jobs still showing as running, fix job status synchronization (update to failed on request error or missing job ID), and improve the jobs page UI with better progress visualization and clear status states
**Depends on**: Phase 999.1
**Requirements**: JOB-01, JOB-02, JOB-03, JOB-04
**Success Criteria** (what must be TRUE):
  1. No stale jobs remain — any job that failed or whose Kie.ai task ID is not found is marked as failed in the database
  2. Job status sync validates against Kie.ai API on each poll — request errors and missing IDs trigger automatic failed status
  3. Jobs page shows clear visual distinction between running (spinner), completed (green check), and failed (red X) states
  4. Jobs page has improved progress bars with real-time updates and accurate percentage display
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md -- Backend: stale job scanner, retry endpoint, progress step labels, kie_client transient retry
- [ ] 18-02-PLAN.md -- Frontend: jobs page card grid, progress bars, retry button, expandable detail rows

### Phase 19: Video Gallery & Management
**Goal**: Create a dedicated "Videos Gerados" page with its own sidebar menu entry, supporting inline video playback, download, approve/delete actions, filters, and newest-first ordering. Images with existing videos show a tag but keep all generation actions enabled.
**Depends on**: Phase 18
**Requirements**: VGAL-01, VGAL-02, VGAL-03, VGAL-04, VGAL-05, VGAL-06
**Success Criteria** (what must be TRUE):
  1. A new "Videos" entry exists in the sidebar navigation, leading to a dedicated video gallery page
  2. Videos are displayed ordered from newest to oldest, with inline video player (play in browser without download)
  3. Each video has separate action buttons: download, approve, delete — with confirmation dialog for delete
  4. Filter tabs allow filtering by status (all/completed/failed) and model used
  5. In the image gallery, images that already have generated videos show a "Video Gerado" tag but all actions remain enabled for new video generations
  6. Deleting a video removes the file and clears video columns from the content package
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 19-01-PLAN.md — Backend approve endpoint + model/sort filters on video list, frontend API client + SWR hook + sidebar Videos entry
- [x] 19-02-PLAN.md — Videos gallery page with inline player, actions, filters + gallery video tag badge

### Phase 20: Kie.ai Credits & Cost Tracking
**Goal**: Create a credits tracking system for Kie.ai API that correctly accounts costs per model using configured BRL prices, only deducting credits on successful video generation
**Depends on**: Phase 18
**Requirements**: CRED-01, CRED-02, CRED-03, CRED-04
**Success Criteria** (what must be TRUE):
  1. Credits are only deducted when a video generation succeeds — failed generations cost zero
  2. Each model's cost is tracked using the prices_brl values from VIDEO_MODELS config
  3. A credits summary is available via API showing total spent, per-model breakdown, and remaining budget
  4. Dashboard displays accurate cumulative costs in BRL with per-model granularity
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 20-01-PLAN.md — Backend: migration, cost_brl column, compute helper, UsageRepository extension, credits summary endpoint
- [x] 20-02-PLAN.md — Frontend: API client, SWR hook, VideoCreditsCard dashboard component

### Phase 21: Dashboard Business Metrics
**Goal**: Improve dashboard info cards with business-relevant metrics (videos gerados, custo medio por video, creditos restantes, trends coletados) and update all spending values to display in BRL
**Depends on**: Phase 20
**Requirements**: DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):
  1. All spending/cost values on the dashboard display in BRL (not USD)
  2. Dashboard cards show: total videos generated, average cost per video, remaining Kie.ai budget, total trends collected, active content packages
  3. Cards are visually improved with icons, trend indicators (up/down arrows), and comparative data (vs previous period)
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 21-01-PLAN.md -- Backend: get_business_metrics() repo method + GET /dashboard/business-metrics endpoint
- [x] 21-02-PLAN.md -- Frontend: API types/hook, StatsCard extension, business cards, BRL conversion

## Backlog

### Phase 999.1: Video Generation — Kie.ai Sora 2 (BACKLOG)

**Goal:** Convert generated meme images into 10-15 second portrait videos using Kie.ai Sora 2 image-to-video API, with LLM-generated motion prompts that improve per-theme over time via manual feedback. GCS for public image URLs, daily budget cap, opt-in per content package.

**Scope:**
- New service: `src/video_gen/kie_client.py` — KieSora2Client (httpx async, create task + poll + download)
- New module: `src/video_gen/video_prompt_builder.py` — 15 motion templates per theme + LLM prompt generation + per-theme notes
- New module: `src/video_gen/gcs_uploader.py` — GCS upload for public image URLs (per D-04)
- DB migration: Add `video_path`, `video_source`, `video_prompt_used`, `video_task_id`, `video_metadata`, `video_status` to `content_packages` + `video_prompt_notes` to `themes`
- API: `POST /generate/video`, `POST /generate/video/batch`, `GET /generate/video/status/{id}`, `GET /generate/video/budget`
- Config: `KIE_API_KEY`, `VIDEO_ENABLED=false`, `VIDEO_DURATION=10`, `VIDEO_MODEL`, `VIDEO_DAILY_BUDGET_USD=3.0`, `GCS_BUCKET_NAME`
- Cost tracking: Extend `api_usage` table with `kie_video` service
- Image upload: GCS for public URLs (independent of Phase 14)

**Key integration:** Feature-flagged via `VIDEO_ENABLED`. Opt-in per content package via API.
**Cost:** ~$0.15 per 10s video (standard tier), ~$45/month at 10 videos/day.
**Depends on:** Nothing (uses GCS instead of Phase 14 CDN)
**Research:** `.planning/research/kie-ai-sora2-research.md`
**Requirements:** VID-01, VID-02, VID-03, VID-04, VID-05, VID-06, VID-07, VID-08, VID-09, VID-10
**Plans:** 2/2 plans complete

Plans:
- [x] 999.1-01-PLAN.md — Foundation: DB migration (video columns + video_prompt_notes), config constants, GCS uploader
- [x] 999.1-02-PLAN.md — Core modules: KieSora2Client (async API client) + VideoPromptBuilder (LLM motion prompts)
- [x] 999.1-03-PLAN.md — API routes: video generation endpoints, cost tracking, app wiring

### Phase 999.2: Video Legends & Subtitles (BACKLOG)

**Goal:** Add text overlays (meme phrase + watermark) to generated videos using FFmpeg, matching the existing Pillow text style. Produces ready-to-publish Instagram Reels with burned-in captions.

**Scope:**
- New module: `src/video_gen/legend_renderer.py` — FFmpeg `drawtext` filter chain (white text, black stroke, watermark)
- New worker: `src/pipeline/workers/legend_worker.py` — runs in L5 post-production after video generation
- 3 modes: `static` (default, full duration), `fade` (in/out), `typewriter` (line-by-line reveal)
- API: `POST /generate/video/legend`, `POST /generate/video/legend/batch`
- Config: `VIDEO_LEGEND_ENABLED=false`, `VIDEO_LEGEND_MODE=static`, `VIDEO_LEGEND_FONT_SIZE=48`
- Dep: FFmpeg system binary (subprocess, no pip wrapper)
- Port word-wrap logic from `src/image_maker.py` for video text rendering
- DB: `legend_status`, `legend_path` columns on `content_packages`

**Cost:** Zero (local FFmpeg processing).
**Depends on:** Phase 999.1 (needs videos to overlay)
**Requirements:** LEG-01, LEG-02, LEG-03, LEG-04, LEG-05, LEG-06, LEG-07, LEG-08
**Plans:** 2/2 plans complete

Plans:
- [x] 999.2-01-PLAN.md — Foundation: config constants, DB migration, LegendRenderer module with 3 animation modes
- [ ] 999.2-02-PLAN.md — Pipeline + API: LegendWorker, API endpoints (single + batch), PostProduction integration

### Phase 999.3: Sora 2 Prompt Engineering Research (BACKLOG)

**Goal:** Apply researched Sora 2 prompt engineering patterns (three-layer motion framework, present continuous tense, structured system prompts) to VideoPromptBuilder, with v1/v2 version switching via config.

**Scope:**
- Research: Study https://github.com/ZeroLu/awesome-sora2 techniques, best practices, and community patterns
- Analyze: Map applicable techniques to existing MOTION_TEMPLATES in `src/video_gen/video_prompt_builder.py`
- Implement: Update motion templates with researched patterns (camera movement, scene description, temporal flow)
- Improve: LLM system prompt for Gemini-generated motion prompts — incorporate best-practice structure
- Test: Compare before/after prompt quality with sample generations
- Config: `VIDEO_PROMPT_STYLE` env var for prompt template version (v1=current, v2=researched)

**Cost:** Zero (research + code changes only).
**Depends on:** Phase 999.1 (uses VideoPromptBuilder)
**Requirements:** D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08
**Plans:** 2/2 plans complete

Plans:
- [x] 999.3-01-PLAN.md — v2 motion templates (17 themes, three-layer framework), config constant, version switching, test scaffold
- [ ] 999.3-02-PLAN.md — v2 system prompts (structured CAMERA/SUBJECT/PHYSICS/ATMOSPHERE sections), LLM wiring, additional tests

### Phase 999.4: Instagram Reels Pipeline (BACKLOG)
**Goal**: Pipeline standalone em src/reels_pipeline/ para geracao automatizada de Instagram Reels: imagens Gemini 9:16 → roteiro Gemini multimodal (JSON estruturado) → narracao OpenAI TTS-HD → legendas Whisper SRT → montagem FFmpeg xfade → MP4 pronto para publicar. Config no banco com painel de ajustes e presets.
**Depends on**: Nothing (reuses existing modules: GeminiImageClient, LegendRenderer, GCSUploader, InstagramClient)
**Requirements**: REEL-01, REEL-02, REEL-03, REEL-04, REEL-05, REEL-06, REEL-07, REEL-08, REEL-09
**Success Criteria** (what must be TRUE):
  1. User can trigger reel generation from /reels page with a tema and see real-time progress
  2. Pipeline generates 5 images at 9:16, creates structured roteiro via Gemini, narrates via TTS, transcribes to SRT, assembles MP4 via FFmpeg
  3. User can view job history with status badges and cost tracking in BRL
  4. User can configure pipeline settings (TTS voice, duration, presets) via config panel
  5. All /reels/* API endpoints respond correctly with tenant isolation
**Plans**: 5 plans
**UI hint**: yes

Plans:
- [x] 999.4-01-PLAN.md — Foundation: DB migration (reels_config + reels_jobs), config constants, Pydantic models
- [x] 999.4-02-PLAN.md — Pipeline modules: image_gen, script_gen, tts, transcriber
- [x] 999.4-03-PLAN.md — Video builder (FFmpeg xfade) + pipeline orchestrator (main.py)
- [x] 999.4-04-PLAN.md — API routes (/reels/*) + app wiring
- [x] 999.4-05-PLAN.md — Frontend: reels page, config panel, API client, SWR hooks, sidebar nav

### Phase 999.5: Interactive Reels Pipeline (BACKLOG)
**Goal**: Transformar pipeline de Reels em fluxo interativo com stepper UI: cada etapa (prompt → imagens → roteiro → narracao → legendas → video) requer aprovacao do usuario com opcao de regenerar/editar. Videos longos (>30s) segmentados em blocos consistentes e concatenados.
**Depends on**: Phase 999.4 (existing pipeline modules)
**Requirements**: IREEL-01, IREEL-02, IREEL-03, IREEL-04, IREEL-05
**Success Criteria** (what must be TRUE):
  1. User navigates a visual stepper with 6 steps, each showing preview and approve/regenerate controls
  2. Each step can be regenerated individually without restarting the whole pipeline
  3. User can edit generated text (prompt, roteiro, legendas) inline before approving
  4. Videos >30s are automatically segmented into consistent blocks and concatenated
  5. Final video preview plays in-browser before download
**Plans**: 4 plans

Plans:
- [x] 999.5-01-PLAN.md — Backend: DB migration (step_state), per-step pipeline methods, video segmentation
- [x] 999.5-02-PLAN.md — Step-based API endpoints (approve, regenerate, edit, file serving)
- [x] 999.5-03-PLAN.md — Frontend: API client, hooks, stepper component, first 3 step components
- [ ] 999.5-04-PLAN.md — Frontend: narration, subtitles, video step components, full wiring + checkpoint

### Phase 999.6: Reels Pipeline v2 — Hailuo + Scene Context + Interactive Fix (BACKLOG)
**Goal**: Fix the interactive stepper to actually work step-by-step (not sequential), generate per-scene images following script context, replace FFmpeg slideshow with Hailuo AI video generation per scene, and optimize subtitles for mobile 9:16 format.
**Depends on**: Phase 999.5 (stepper UI), Phase 999.1 (Kie.ai client)
**Requirements**: REELV2-01, REELV2-02, REELV2-03, REELV2-04
**Success Criteria** (what must be TRUE):
  1. User clicks "Criar Reel Interativo" and lands on stepper at step 1, must approve each step before next runs
  2. Images are generated per-scene following the script roteiro — each cena gets its own contextual image matching the story
  3. Video is generated using Hailuo 2.3 Fast via Kie.ai API (image-to-video per scene), not FFmpeg slideshow
  4. Subtitles are sized and styled for mobile 9:16 format, matching the meme visual style
**Plans**: 3 plans

Plans:
- [x] 999.6-01-PLAN.md — Backend: reorder steps, text-only script gen, per-cena image gen
- [x] 999.6-02-PLAN.md — Backend: Hailuo video step (Kie.ai per scene), mobile subtitle fix
- [ ] 999.6-03-PLAN.md — Frontend: reorder stepper, fix step wiring, visual checkpoint

### Phase 421: Product Studio — AI Video Ads Generator (BACKLOG)
**Goal**: Users can generate professional product advertisement videos 100% via AI — from product photo to multi-format video — through a wizard-driven 8-step pipeline with 3 styles (cinematic, narrated, lifestyle)
**Depends on**: Phase 999.1 (Kie.ai client), Phase 999.5 (stepper UI pattern)
**Requirements**: ADS-01, ADS-02, ADS-03, ADS-04, ADS-05, ADS-06, ADS-07, ADS-08, ADS-09, ADS-10, ADS-11, ADS-12, ADS-13, ADS-14, ADS-15, ADS-16, ADS-17, ADS-18, ADS-19
**Success Criteria** (what must be TRUE):
  1. User uploads product photo and wizard suggests defaults (nicho, tom, cenario) via Gemini Vision
  2. Pipeline generates scene image (rembg bg removal + Gemini inpainting) and user approves
  3. Video is generated via configurable model (Wan 2.6 / Kling 2.5 / Hailuo) through Kie.ai
  4. Final video includes text overlay (headline + CTA) and audio (Suno trilha + optional TTS narration)
  5. Export produces multi-format videos (9:16, 16:9, 1:1) via intelligent crop + background blur padding
**Plans**: 7 plans
**UI hint**: yes

Plans:
- [ ] 421-01-PLAN.md — Foundation: rembg install, DB migration (product_ad_jobs), config.py, models.py
- [ ] 421-02-PLAN.md — Scene modules: bg_remover, scene_composer (Gemini Vision + Image), prompt_builder, copy_generator
- [ ] 421-03-PLAN.md — Audio & export modules: KieMusicClient (Suno via Kie.ai), format_exporter (blur pad + drawtext + amix)
- [ ] 421-04-PLAN.md — Pipeline orchestrator: ProductAdPipeline with 8 step methods
- [ ] 421-05-PLAN.md — API routes: ads.py (10 endpoints) + app.py wiring
- [ ] 421-06-PLAN.md — Frontend: API client, SWR hooks, wizard page (/ads/new), jobs listing (/ads)
- [ ] 421-07-PLAN.md — Frontend: stepper UI (8 step components), job detail page (/ads/[jobId]), sidebar nav
