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
- [ ] **Phase 14: Instagram Connection & CDN** - Connect Instagram Business Account, GCS CDN image upload, token lifecycle management
- [ ] **Phase 15: Publishing & Scheduling** - Schedule, publish, manage, and calendar-view Instagram posts
- [ ] **Phase 16: Dashboard v2** - 30-day usage history, limit alerts, cost reports, and pipeline run history
- [ ] **Phase 17: Billing & Stripe** - Subscription plans with Stripe Checkout, webhooks, portal, and plan enforcement

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

### Phase 12.1: Viral Content Engine — Trend Agents & Content Quality Overhaul (INSERTED)

**Goal:** Overhaul the trend agent layer (L1) and curator layer (L3) to produce content that is consistently relevant, timely, and viral-ready for Brazilian meme audiences
**Depends on:** Phase 12
**Requirements**: VIRAL-01, VIRAL-02, VIRAL-03, VIRAL-04, VIRAL-05, VIRAL-06, VIRAL-07, VIRAL-08, VIRAL-09, VIRAL-10, VIRAL-11, VIRAL-12, VIRAL-13, VIRAL-14, VIRAL-15, VIRAL-16
**Success Criteria** (what must be TRUE):
  1. Pipeline only uses agents that produce BR-relevant meme content (HackerNews and Lemmy removed)
  2. Trend scoring is dynamic — fresh multi-source trends rank higher than stale single-source ones
  3. Curator intelligently maps trending topics to visual themes via LLM instead of rigid keyword matching
  4. Generated phrases pass quality validation (length, language, format) before image composition
  5. Topic-image coherence is verified before generation, with automatic theme remapping on mismatch
**Plans**: 4 plans

Plans:
- [x] 12.1-01-PLAN.md — Agent cleanup: remove HN/Lemmy, simplify RSS, improve Reddit/YouTube/Gemini/BlueSky agents
- [x] 12.1-02-PLAN.md — Scoring engine: fix Google Trends parsing, temporal decay, multi-source boost, engagement scoring
- [ ] 12.1-03-PLAN.md — Curator intelligence: LLM theme mapping, relevance filter, throughput increase
- [x] 12.1-04-PLAN.md — Content guardrails: phrase validation, topic-image coherence check

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
**Goal**: Users can connect their Instagram Business Account and have their images uploaded to GCS CDN with public signed URLs ready for Instagram publishing
**Depends on**: Phase 13
**Requirements**: PUB-01, PUB-02, PUB-07
**Success Criteria** (what must be TRUE):
  1. User can connect an Instagram Business Account via Facebook OAuth flow and see the connected account in their settings
  2. Composed meme images are uploaded to GCS (meme-lab-bucket) and assigned signed public URLs accessible by Instagram's servers
  3. Instagram access tokens auto-refresh before the 60-day expiry — user never has to manually reconnect due to token expiration
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [ ] 14-01-PLAN.md — Backend foundation: DB migration (instagram_connections), ORM model, config, InstagramOAuthService (token exchange, encryption, refresh)
- [ ] 14-02-PLAN.md — API routes: 5 Instagram endpoints (auth-url, callback, status, disconnect, upload-media) + token refresh scheduler job
- [ ] 14-03-PLAN.md — Frontend: Settings page with Instagram connection card, OAuth popup flow, sidebar nav entry

### Phase 15: Publishing & Scheduling
**Goal**: Users can schedule posts to specific times, have them auto-published via Instagram Graph API, manage the queue, and view everything in a content calendar
**Depends on**: Phase 14
**Requirements**: PUB-03, PUB-04, PUB-05, PUB-06
**Success Criteria** (what must be TRUE):
  1. User can schedule an approved meme for a specific date and time
  2. The scheduler automatically publishes posts at the scheduled time via Instagram Graph API (container create, poll, publish)
  3. User can view, cancel, and retry scheduled posts from a management interface
  4. User can view a content calendar (month and week views) showing scheduled and published posts
**Plans**: TBD
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
**Plans**: TBD
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
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 17-01: TBD
- [ ] 17-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 12 -> 12.1 -> 12.2 -> 13 -> ...

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Pipeline Simplification | 2/3 | Complete    | 2026-03-26 |
| 12.1 Viral Content Engine | 3/4 | Complete    | 2026-03-26 |
| 13. Tenant Isolation | 2/3 | Complete    | 2026-03-25 |
| 14. Instagram Connection & CDN | 0/3 | Not started | - |
| 15. Publishing & Scheduling | 0/? | Not started | - |
| 16. Dashboard v2 | 0/? | Not started | - |
| 17. Billing & Stripe | 0/? | Not started | - |

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
**Plans:** 3/3 plans complete

Plans:
- [x] 999.1-01-PLAN.md — Foundation: DB migration (video columns + video_prompt_notes), config constants, GCS uploader
- [x] 999.1-02-PLAN.md — Core modules: KieSora2Client (async API client) + VideoPromptBuilder (LLM motion prompts)
- [x] 999.1-03-PLAN.md — API routes: video generation endpoints, cost tracking, app wiring

### Phase 999.2: Video Legends & Subtitles (BACKLOG)

**Goal:** Add text overlays (meme phrase + watermark) to generated videos using FFmpeg, matching the existing Pillow text style. Produces ready-to-publish Instagram Reels with burned-in captions.

**Scope:**
- New module: `src/video_gen/legend_renderer.py` — FFmpeg `drawtext` filter chain (white text, black stroke, watermark)
- New worker: `src/pipeline/workers/legend_worker.py` — runs in L5 post-production after video generation
- 3 modes: `static` (default, full duration), `fade` (in/out), `typewriter` (char-by-char)
- API: `POST /generate/video/legend`, `POST /generate/video/legend/batch`
- Config: `VIDEO_LEGEND_ENABLED=true`, `VIDEO_LEGEND_MODE=static`, `VIDEO_LEGEND_FONT_SIZE=48`
- Dep: `ffmpeg-python` (pip) + FFmpeg system binary
- Port word-wrap logic from `src/image_maker.py` for video text rendering

**Cost:** Zero (local FFmpeg processing).
**Depends on:** Phase 999.1 (needs videos to overlay)
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
