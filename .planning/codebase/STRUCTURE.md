# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
meme-lab/                        # Monorepo root
├── config.py                    # Global config (paths, API keys, model IDs, flags)
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Python project metadata
├── alembic.ini                  # Alembic migrations config
├── .env                         # Secrets (not committed)
├── .env.example                 # Required env var template
│
├── src/                         # Python backend source
│   ├── api/                     # FastAPI app, routes, models, deps
│   │   ├── app.py               # FastAPI app factory + lifespan
│   │   ├── deps.py              # Shared FastAPI Depends (session, auth, helpers)
│   │   ├── models.py            # All Pydantic request/response models
│   │   ├── serializers.py       # ORM → dict serialization helpers
│   │   ├── registry.py          # Agent/worker registry
│   │   ├── log_sanitizer.py     # Strips API keys from logs
│   │   └── routes/              # One file per domain (16 modules)
│   │       ├── auth.py          # /auth/* (login, register, logout, me)
│   │       ├── generation.py    # /generate/* (single, batch, refine, compose)
│   │       ├── video.py         # /generate/video/* (Kie.ai jobs, legend)
│   │       ├── pipeline.py      # /pipeline/* (run, status, manual)
│   │       ├── reels.py         # /reels/* (create, step execution, config)
│   │       ├── ads.py           # /ads/* (create, step execution, file upload)
│   │       ├── characters.py    # /characters/* (CRUD + refs)
│   │       ├── content.py       # /content, /images, /phrases
│   │       ├── jobs.py          # /jobs/* (status, list, sync)
│   │       ├── themes.py        # /themes/* (CRUD + AI generate)
│   │       ├── publishing.py    # /publishing/* (schedule, calendar)
│   │       ├── dashboard.py     # /dashboard/* (metrics, stats)
│   │       ├── billing.py       # /billing/* (Stripe, plans)
│   │       ├── agents.py        # /agents, /trends
│   │       ├── drive.py         # /drive/*, /status (file serving)
│   │       └── instagram.py     # /instagram/* (OAuth callback)
│   │
│   ├── database/                # ORM models, session, migrations, repositories
│   │   ├── base.py              # DeclarativeBase + TimestampMixin
│   │   ├── models.py            # All SQLAlchemy ORM models (16 tables)
│   │   ├── session.py           # Async engine + session factory + init_db()
│   │   ├── seed.py              # Dev seed data
│   │   ├── converters.py        # ORM <-> dict conversion helpers
│   │   ├── migrations/          # Alembic migration scripts
│   │   │   └── versions/        # 020 numbered migrations (001-020)
│   │   └── repositories/        # Per-entity repository classes
│   │       ├── character_repo.py
│   │       ├── content_repo.py
│   │       ├── job_repo.py
│   │       ├── pipeline_repo.py
│   │       ├── schedule_repo.py
│   │       ├── theme_repo.py
│   │       ├── usage_repo.py
│   │       └── user_repo.py
│   │
│   ├── auth/                    # JWT auth: tokens, user service, schemas
│   │   ├── jwt.py               # create_access_token, verify_access_token
│   │   ├── service.py           # register/login/logout business logic
│   │   └── schemas.py           # Auth Pydantic schemas
│   │
│   ├── billing/                 # Stripe billing integration
│   │   ├── stripe_service.py
│   │   ├── plans.py
│   │   └── schemas.py
│   │
│   ├── pipeline/                # Meme content multi-agent pipeline
│   │   ├── orchestrator.py      # Sync orchestrator (legacy)
│   │   ├── async_orchestrator.py # Async orchestrator (current)
│   │   ├── broker.py            # Ingest queue + dedup
│   │   ├── curator.py           # Topic selection
│   │   ├── scheduler.py         # Run scheduling
│   │   ├── monitoring.py        # Pipeline metrics
│   │   ├── models.py            # PipelineResult, AnalyzedTopic, TrendItem
│   │   ├── models_v2.py         # WorkOrder, ContentPackage (v2 data models)
│   │   ├── agents/              # Trend-fetching source agents
│   │   │   ├── base.py          # BaseAgent abstract class
│   │   │   ├── async_base.py    # AsyncBaseAgent
│   │   │   ├── google_trends.py
│   │   │   ├── reddit_memes.py
│   │   │   ├── rss_feeds.py
│   │   │   ├── youtube_rss.py
│   │   │   ├── youtube_shorts.py
│   │   │   ├── bluesky_trends.py
│   │   │   ├── brazil_viral_rss.py
│   │   │   ├── gemini_web_trends.py
│   │   │   └── ...              # tiktok, twitter, instagram, facebook stubs
│   │   ├── processors/          # Aggregation, analysis, generation
│   │   │   ├── aggregator.py    # TrendAggregator (dedup + rank)
│   │   │   ├── analyzer.py      # ClaudeAnalyzer (Gemini topic analysis)
│   │   │   └── generator.py     # ContentGenerator (wraps workers)
│   │   └── workers/             # Per-content-type generators
│   │       ├── phrase_worker.py # Gemini text phrase generation
│   │       ├── image_worker.py  # Gemini/ComfyUI image + Pillow compose
│   │       ├── caption_worker.py
│   │       ├── hashtag_worker.py
│   │       ├── quality_worker.py
│   │       ├── legend_worker.py
│   │       ├── generation_layer.py  # Coordinates phrase + image workers
│   │       └── post_production.py
│   │
│   ├── image_gen/               # Image generation clients
│   │   ├── gemini_client.py     # Gemini image API client + SITUACOES dict
│   │   ├── comfyui_client.py    # ComfyUI local API client
│   │   ├── prompt_builder.py    # Image prompt construction
│   │   └── workflows/           # ComfyUI workflow JSON files
│   │
│   ├── video_gen/               # Kie.ai video generation
│   │   ├── kie_client.py        # KieSora2Client (async, exponential backoff)
│   │   ├── gcs_uploader.py      # Google Cloud Storage uploader
│   │   ├── legend_renderer.py   # FFmpeg text overlay
│   │   ├── video_prompt_builder.py
│   │   └── stale_job_scanner.py # Background scanner for stuck jobs
│   │
│   ├── reels_pipeline/          # Instagram Reels end-to-end pipeline
│   │   ├── main.py              # ReelsPipeline orchestrator
│   │   ├── image_gen.py         # Gemini scene image generation
│   │   ├── script_gen.py        # Gemini multimodal script generation
│   │   ├── tts.py               # Gemini Flash TTS narration
│   │   ├── transcriber.py       # Gemini audio transcription → SRT
│   │   ├── video_builder.py     # FFmpeg xfade assembly
│   │   ├── config.py            # Reels-specific config
│   │   └── models.py            # Pydantic models for reels API
│   │
│   ├── product_studio/          # Product Ad 8-step pipeline
│   │   ├── pipeline.py          # ProductAdPipeline orchestrator
│   │   ├── bg_remover.py        # rembg background removal
│   │   ├── scene_composer.py    # Gemini scene composition
│   │   ├── prompt_builder.py    # Cinematic video prompt generation
│   │   ├── copy_generator.py    # Headline + CTA + hashtag generation
│   │   ├── music_client.py      # Suno music API client
│   │   ├── format_exporter.py   # FFmpeg multi-format export
│   │   ├── config.py            # Ad pipeline config + step order
│   │   └── models.py            # Pydantic models for ads API
│   │
│   ├── services/                # Background services + integrations
│   │   ├── publisher.py         # PublishingService (Instagram Graph API)
│   │   ├── scheduler_worker.py  # Scheduled post processor (60s interval)
│   │   ├── instagram_oauth.py   # OAuth token exchange
│   │   ├── instagram_client.py  # Instagram Graph API client
│   │   ├── insights_collector.py
│   │   ├── key_selector.py      # Gemini API key rotation selector
│   │   └── stripe_billing.py    # Stripe webhook handler
│   │
│   ├── llm_client.py            # Unified LLM interface (Gemini/Ollama)
│   ├── image_maker.py           # Pillow image composition (text overlay)
│   ├── characters.py            # Character config helpers (legacy)
│   ├── phrases.py               # Phrase generation helpers (legacy)
│   ├── pipeline_cli.py          # CLI entry point for pipeline
│   └── cli.py                   # General CLI helpers
│
├── memelab/                     # Next.js 15 frontend dashboard
│   ├── next.config.ts           # Proxy rewrites: /api/* → localhost:8000
│   ├── package.json
│   └── src/
│       ├── app/                 # Next.js App Router
│       │   ├── layout.tsx       # Root layout (AuthProvider wrap)
│       │   ├── page.tsx         # / → redirect to /dashboard
│       │   ├── globals.css      # Tailwind 4 @theme design tokens
│       │   ├── login/page.tsx
│       │   ├── register/page.tsx
│       │   ├── landing/page.tsx
│       │   └── (app)/           # Auth-protected route group
│       │       ├── layout.tsx   # Auth guard + Shell wrapper
│       │       ├── dashboard/page.tsx
│       │       ├── gallery/page.tsx
│       │       ├── pipeline/page.tsx
│       │       ├── agents/page.tsx
│       │       ├── trends/page.tsx
│       │       ├── phrases/page.tsx
│       │       ├── characters/
│       │       │   ├── page.tsx
│       │       │   ├── new/page.tsx
│       │       │   └── [slug]/page.tsx + refs/page.tsx
│       │       ├── jobs/page.tsx
│       │       ├── videos/page.tsx
│       │       ├── reels/
│       │       │   ├── page.tsx
│       │       │   └── [jobId]/page.tsx
│       │       ├── ads/
│       │       │   ├── page.tsx
│       │       │   ├── new/page.tsx
│       │       │   └── [jobId]/page.tsx
│       │       ├── publishing/page.tsx
│       │       ├── billing/page.tsx
│       │       ├── settings/page.tsx + instagram/callback/page.tsx
│       │       └── themes/page.tsx
│       ├── components/
│       │   ├── layout/          # Shell, Sidebar, Header, VideoProgress
│       │   ├── ads/             # 8 step components + stepper + wizard
│       │   ├── reels/           # 6 step components + stepper + SRT editor
│       │   ├── agents/          # Agent config + modal
│       │   ├── panels/          # PipelineDiagram (SVG), StatsCard
│       │   └── ui/              # shadcn/ui primitives (button, card, dialog, etc.)
│       ├── contexts/
│       │   ├── auth-context.tsx # JWT auth state, login/logout/register
│       │   └── character-context.tsx
│       ├── hooks/
│       │   ├── use-api.ts       # SWR hooks for status, images, pipeline
│       │   ├── use-pipeline.ts  # Pipeline execution + polling
│       │   ├── use-ads.ts       # Ad job polling hooks
│       │   └── use-reels.ts     # Reels job polling hooks
│       └── lib/
│           ├── api.ts           # HTTP client + all API function calls + TypeScript types
│           ├── constants.ts     # NAV_ITEMS, color maps
│           ├── utils.ts         # cn() (clsx + tailwind-merge)
│           └── animations.ts    # Framer Motion presets
│
├── assets/                      # Static assets
│   ├── backgrounds/             # Character background images (organized by character)
│   └── fonts/                   # Pillow font files (.ttf)
│
├── characters/                  # Per-character reference image directories
│   ├── mago-mestre/refs/approved/
│   └── mario-sincero/refs/approved/
│
├── output/                      # Generated output (not committed)
│   ├── ads/                     # Product ad job directories
│   ├── reels/                   # Reels job directories
│   ├── videos/                  # Generated MP4 files
│   └── backgrounds_generated/   # Gemini-generated backgrounds
│
├── tests/                       # Python test suite
├── scripts/                     # One-off utility scripts
├── config/                      # YAML config files (themes.yaml)
├── data/                        # SQLite DB file (dev)
├── docs/                        # Additional documentation
└── .planning/                   # GSD planning docs (not committed)
```

## Directory Purposes

**`src/api/routes/`:**
- Purpose: One module per feature domain; each defines a FastAPI `APIRouter` with a `prefix`
- Contains: Route handlers, inline `BackgroundTask` calls, validation, ORM queries via repositories
- Key files: `ads.py` (product ad wizard), `reels.py` (reels wizard), `video.py` (Kie.ai video), `generation.py` (meme images)

**`src/database/repositories/`:**
- Purpose: Encapsulate all SQLAlchemy queries; enforce user ownership for multi-tenant isolation
- Contains: One class per entity (e.g., `CharacterRepository`, `UserRepository`)
- Key files: `character_repo.py` (most complex — ownership check on every query), `user_repo.py`

**`src/pipeline/agents/`:**
- Purpose: Pluggable trend-data fetchers, each wrapping one external source
- Contains: Classes extending `BaseAgent` or `AsyncBaseAgent`
- Key files: `google_trends.py`, `reddit_memes.py`, `rss_feeds.py` (active); TikTok/Instagram/Twitter are stubs

**`memelab/src/app/(app)/`:**
- Purpose: All auth-protected pages; the route group's `layout.tsx` enforces auth redirect
- Contains: Page components, mostly `"use client"` with SWR hooks
- Key files: `ads/[jobId]/page.tsx` (stepper UI), `reels/[jobId]/page.tsx` (reels stepper)

**`memelab/src/components/ads/`:**
- Purpose: 8-step product ad pipeline wizard UI
- Contains: `wizard.tsx` (job creation form), `stepper.tsx` (step orchestration), `step-*.tsx` (one per step)
- Key files: `stepper.tsx` (polls step state, renders per-step component), `wizard.tsx` (initial job creation)

**`memelab/src/lib/api.ts`:**
- Purpose: Single file for all backend communication — HTTP client, TypeScript types, and every API function
- CRITICAL: TypeScript types here must match FastAPI response shapes exactly

## Key File Locations

**Entry Points:**
- `src/api/app.py`: FastAPI app — start with `python -m src.api --port 8000`
- `memelab/next.config.ts`: Next.js config + `/api/*` proxy rewrite
- `memelab/src/app/layout.tsx`: Root Next.js layout (AuthProvider)
- `memelab/src/app/(app)/layout.tsx`: Auth guard for all protected routes

**Configuration:**
- `config.py`: All Python config (DATABASE_URL, API keys, model IDs, cost limits)
- `.env`: Runtime secrets (never committed)
- `.env.example`: Documents required variables
- `memelab/src/app/globals.css`: Tailwind 4 design tokens (`@theme`)

**Core Logic:**
- `src/api/deps.py`: Shared FastAPI dependencies (`get_current_user`, `db_session`)
- `src/api/models.py`: All Pydantic schemas for the API
- `src/database/models.py`: All SQLAlchemy ORM models (16 tables)
- `src/database/session.py`: Async session factory
- `src/llm_client.py`: Unified LLM interface
- `memelab/src/lib/api.ts`: All frontend API calls and TypeScript types

**Pipeline Orchestrators:**
- `src/pipeline/async_orchestrator.py`: Meme content pipeline (async)
- `src/reels_pipeline/main.py`: Reels pipeline
- `src/product_studio/pipeline.py`: Product ad pipeline

**Testing:**
- `tests/`: Python tests
- `memelab/src/__tests__/`: TypeScript/React tests

## Naming Conventions

**Python Files:**
- snake_case for all modules: `kie_client.py`, `character_repo.py`, `image_worker.py`
- `_client.py` suffix for external API clients
- `_repo.py` suffix for repository classes
- `_worker.py` suffix for pipeline workers
- Route files named after domain: `ads.py`, `reels.py`, `video.py`

**Python Classes:**
- PascalCase: `ProductAdPipeline`, `KieSora2Client`, `CharacterRepository`
- Pydantic models end with `Request` or `Response`: `AdCreateRequest`, `AdJobResponse`

**TypeScript Files:**
- kebab-case for all files: `auth-context.tsx`, `step-analysis.tsx`, `use-ads.ts`
- `step-*.tsx` for pipeline step components
- `use-*.ts` for SWR hooks

**Routes/Directories:**
- kebab-case for Next.js routes: `[jobId]`, `mago-mestre`
- Snake_case for Python packages: `reels_pipeline`, `product_studio`, `video_gen`

## Where to Add New Code

**New API Route Domain:**
- Create `src/api/routes/{domain}.py` with `router = APIRouter(prefix="/{domain}", tags=[...])`
- Register in `src/api/app.py`: `app.include_router({domain}.router)`
- Add Pydantic models to `src/api/models.py` (or a domain-specific `src/{domain}/models.py`)

**New Pipeline Step (Reels or Ads):**
- Add step logic to `src/reels_pipeline/` or `src/product_studio/`
- Add step name to `ADS_STEP_ORDER` in `src/product_studio/config.py` (or reels equivalent)
- Add `run_step_{name}()` method to the pipeline class
- Add route handler in the relevant routes file
- Add frontend step component in `memelab/src/components/ads/step-{name}.tsx` or `reels/`
- Wire step into `stepper.tsx`

**New Frontend Page:**
- Create `memelab/src/app/(app)/{slug}/page.tsx` for authenticated pages
- Add to `NAV_ITEMS` in `memelab/src/lib/constants.ts` for sidebar navigation
- If data fetching needed, add a hook in `memelab/src/hooks/use-{domain}.ts`
- Add API functions and types to `memelab/src/lib/api.ts`

**New Database Table:**
- Add ORM model class to `src/database/models.py`
- Create Alembic migration: `alembic revision --autogenerate -m "description"`
- Add repository class in `src/database/repositories/{entity}_repo.py`

**New Trend Agent:**
- Create `src/pipeline/agents/{source}.py` extending `AsyncBaseAgent`
- Implement `is_available()` and `fetch()` methods
- Register in `src/api/registry.py`

**Shared UI Components:**
- Add to `memelab/src/components/ui/` following shadcn/ui pattern (Radix UI + CVA + Tailwind)

## Special Directories

**`output/`:**
- Purpose: All generated files (images, videos, ad job directories)
- Generated: Yes
- Committed: No (in `.gitignore`)

**`data/`:**
- Purpose: SQLite database file for local development
- Generated: Yes (on first run)
- Committed: No

**`.planning/`:**
- Purpose: GSD planning docs, phase plans, debug notes
- Generated: By GSD tooling
- Committed: Selectively (phases and docs yes, debug notes no)

**`src/database/migrations/versions/`:**
- Purpose: Alembic migration history (20 migrations covering all schema changes)
- Generated: Via `alembic revision`
- Committed: Yes — required for schema reproducibility

**`src/image_gen/workflows/`:**
- Purpose: ComfyUI workflow JSON files for local GPU image generation
- Generated: No (authored manually)
- Committed: Yes

---

*Structure analysis: 2026-03-30*
