# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Full-stack monorepo with a Python FastAPI backend and a Next.js frontend, connected via HTTP proxy. The backend follows a layered pipeline architecture: trend agents feed an orchestrator, which drives workers, which produce content packages stored in a relational database. Multiple specialized sub-pipelines (meme content, Instagram Reels, product ad videos) share the same database and API layer.

**Key Characteristics:**
- Backend is async throughout (FastAPI + SQLAlchemy async + asyncio)
- Frontend proxies all requests through Next.js rewrites — no direct browser-to-backend calls, no API routes in Next.js
- Multi-tenant: all ORM models carry `user_id` foreign key; repository layer enforces ownership
- Job-based pattern for long-running tasks: route creates a DB record and fires a `BackgroundTask`, frontend polls for status
- Three distinct pipeline systems share one FastAPI app: meme content pipeline, Reels pipeline (`src/reels_pipeline/`), Product Ad pipeline (`src/product_studio/`)

## Layers

**Configuration Layer:**
- Purpose: Single source of truth for all runtime config
- Location: `config.py` (root)
- Contains: Directory paths, API keys, model IDs, cost limits, feature flags
- Depends on: `python-dotenv`, `.env`
- Used by: Every Python module imports from `config`

**Database Layer:**
- Purpose: Persistence — ORM models, session management, migrations, repositories
- Location: `src/database/`
- Contains: SQLAlchemy async models (`models.py`), Alembic migrations (`migrations/versions/`), session factory (`session.py`), per-entity repositories (`repositories/`)
- Depends on: SQLAlchemy async, config DATABASE_URL (MySQL or SQLite)
- Used by: API routes (via FastAPI `Depends`), background tasks

**API Layer:**
- Purpose: HTTP interface — routing, request validation, auth enforcement, background task dispatch
- Location: `src/api/`
- Contains: FastAPI app (`app.py`), shared dependencies (`deps.py`), Pydantic request/response models (`models.py`), 16 route modules (`routes/`)
- Depends on: Database layer, service layer, pipeline sub-systems
- Used by: Next.js frontend (via proxy at `/api/*`)

**Service Layer:**
- Purpose: Business logic that is not pipeline-specific
- Location: `src/services/`, `src/auth/`, `src/billing/`
- Contains: Instagram OAuth (`instagram_oauth.py`, `instagram_client.py`), scheduled post publisher (`publisher.py`, `scheduler_worker.py`), Stripe billing (`stripe_billing.py`), JWT auth (`auth/jwt.py`, `auth/service.py`), Gemini API key selector (`key_selector.py`)
- Depends on: Database layer, external APIs
- Used by: API routes

**Pipeline Layer (Meme Content):**
- Purpose: Multi-step agent orchestration for meme generation
- Location: `src/pipeline/`
- Contains: Trend-fetching agents (`agents/`), processors (`processors/`), workers (`workers/`), orchestrators (`orchestrator.py`, `async_orchestrator.py`)
- Depends on: Image gen layer, LLM client, database layer
- Used by: `/pipeline` and `/generate` API routes

**Image Generation Layer:**
- Purpose: Generate and compose meme images
- Location: `src/image_gen/`, `src/image_maker.py`
- Contains: Gemini image client (`gemini_client.py`), ComfyUI client (`comfyui_client.py`), prompt builder (`prompt_builder.py`), Pillow composition (`image_maker.py`)
- Depends on: Google Gemini API, optional local ComfyUI
- Used by: `ImageWorker` in pipeline, `/generate` routes

**LLM Client:**
- Purpose: Unified text generation interface with Gemini/Ollama fallback
- Location: `src/llm_client.py`
- Contains: Single `generate()` function that routes to Gemini or Ollama based on config
- Depends on: `google-genai`, optional Ollama
- Used by: All workers, agents, analyzers

**Video Generation Layer:**
- Purpose: Image-to-video via Kie.ai, legend overlay via FFmpeg
- Location: `src/video_gen/`
- Contains: Kie.ai async client (`kie_client.py`), GCS uploader (`gcs_uploader.py`), legend renderer (`legend_renderer.py`), stale job scanner (`stale_job_scanner.py`)
- Depends on: Kie.ai API, Google Cloud Storage, FFmpeg
- Used by: `/generate/video` routes

**Reels Pipeline:**
- Purpose: End-to-end Instagram Reels video production
- Location: `src/reels_pipeline/`
- Contains: Script gen, TTS, image gen, transcription, FFmpeg video builder — each as a module, orchestrated by `main.py`
- Depends on: Gemini API (images, TTS, transcription), FFmpeg, database
- Used by: `/reels` routes

**Product Ad Pipeline:**
- Purpose: 8-step AI video ad production wizard
- Location: `src/product_studio/`
- Contains: Background remover (`bg_remover.py`), scene composer (`scene_composer.py`), prompt builder (`prompt_builder.py`), copy generator (`copy_generator.py`), music client (`music_client.py`), format exporter (`format_exporter.py`), `ProductAdPipeline` orchestrator (`pipeline.py`)
- Depends on: Gemini API, Kie.ai, rembg, FFmpeg, Suno
- Used by: `/ads` routes

**Frontend Layer:**
- Purpose: Management dashboard and interactive wizards
- Location: `memelab/src/`
- Contains: Next.js App Router pages (`app/`), React components (`components/`), SWR hooks (`hooks/`), API client (`lib/api.ts`), auth context (`contexts/auth-context.tsx`)
- Depends on: Backend via `/api/*` proxy rewrites
- Used by: End users in browser

## Data Flow

**Meme Content Pipeline:**

1. Frontend (`/pipeline/page.tsx`) calls `POST /pipeline/run` or `POST /generate/manual`
2. Route creates a `PipelineRun` record in DB, fires `BackgroundTask`
3. `PipelineOrchestrator` runs trend agents (Google Trends, Reddit, RSS, etc.)
4. `TrendAggregator` deduplicates and ranks; `ClaudeAnalyzer` picks topics
5. `GenerationLayer` spawns `PhraseWorker` (Gemini text) + `ImageWorker` (Gemini image or ComfyUI) in parallel
6. Composed meme images saved to `output/`; `ContentPackage` records written to DB
7. Frontend polls `GET /jobs` → displays results in gallery

**Reels / Ad Job Flow:**

1. Frontend wizard collects config, calls `POST /reels/create-interactive` or `POST /ads/`
2. Route creates `ReelsJob` or `ProductAdJob` in DB with `step_state` JSON column
3. Frontend executes steps individually via `POST /reels/{jobId}/step/{step_name}` or `POST /ads/{jobId}/step/{step_name}`
4. Each step runs in a `BackgroundTask` and updates `step_state` in DB
5. Frontend polls step state at 2s interval (SWR `refreshInterval: 2000`) and shows per-step progress
6. Approval/regeneration: `POST /reels/{jobId}/step/{step}/approve` or `reject`

**Video Generation:**

1. Frontend calls `POST /generate/video` with `content_package_id`
2. Route checks daily budget (`VIDEO_DAILY_BUDGET_USD`) in DB, raises 402 if exceeded
3. `BackgroundTask` calls `KieSora2Client.generate()` — creates Kie.ai task, polls with exponential backoff (up to 10 min)
4. On success, video downloaded locally and GCS URL recorded in `ContentPackage`
5. Frontend polls `GET /generate/video/{id}/status` at 3s interval

**Auth Flow:**

1. `POST /auth/login` validates credentials, returns JWT access + refresh tokens
2. Frontend stores tokens in localStorage (persistent) or sessionStorage (session-only)
3. `lib/api.ts` `request()` attaches `Authorization: Bearer <token>` to every call
4. On 401, tokens cleared and user redirected to `/login`
5. FastAPI `get_current_user` dependency verifies JWT and loads `User` ORM from DB

**State Management:**
- Server state: SWR hooks in `hooks/` with deterministic cache keys (e.g., `"ad-job-{jobId}"`)
- Auth state: React Context in `contexts/auth-context.tsx`, hydrated by `GET /auth/me` on mount
- No global client state store (no Redux/Zustand) — all data fetched on demand

## Key Abstractions

**Repository Pattern:**
- Purpose: Encapsulate all DB queries; enforce tenant isolation
- Examples: `src/database/repositories/character_repo.py`, `user_repo.py`, `job_repo.py`
- Pattern: Class receives `AsyncSession`; methods take optional `user` parameter; raises `PermissionError` on ownership violations

**FastAPI Depends:**
- Purpose: Shared injection of DB session and current user
- Examples: `src/api/deps.py` — `db_session()`, `get_current_user()`, `get_user_character()`
- Pattern: All protected routes declare `current_user = Depends(get_current_user)`, `db: AsyncSession = Depends(db_session)`

**Step State Pattern (Reels + Ads):**
- Purpose: Track per-step status of multi-step pipelines in a single JSON column
- Examples: `ReelsJob.step_state`, `ProductAdJob.step_state` — both are `JSON` columns
- Pattern: `{"step_name": {"status": "pending|generating|approved|error", ...artifacts...}}`. Routes read/write this column; frontend polls and renders per-step UI

**SWR Hooks:**
- Purpose: Typed data fetching with auto-refresh for polling patterns
- Examples: `hooks/use-ads.ts`, `hooks/use-reels.ts`, `hooks/use-pipeline.ts`
- Pattern: One hook per entity/operation; `refreshInterval` set to 2000-5000ms for job polling; cache key is a deterministic string

**Agent Base Pattern:**
- Purpose: Uniform interface for trend-fetching data sources
- Examples: `src/pipeline/agents/base.py`, extended by `google_trends.py`, `reddit_memes.py`, etc.
- Pattern: `is_available()` guard + `fetch()` method returning `list[TrendItem]`

## Entry Points

**FastAPI Backend:**
- Location: `src/api/app.py`
- Triggers: `python -m src.api --port 8000`
- Responsibilities: Registers all routers, starts scheduler worker, starts stale job scanner, discovers Gemini image models on startup

**Next.js Frontend:**
- Location: `memelab/src/app/layout.tsx`, `memelab/next.config.ts`
- Triggers: `cd memelab && npm run dev`
- Responsibilities: Wraps all pages in `AuthProvider`, configures `/api/*` → `http://127.0.0.1:8000/*` rewrite

**CLI Pipeline Runner:**
- Location: `src/pipeline_cli.py`
- Triggers: `python -m src.pipeline_cli --mode once`
- Responsibilities: Runs the meme content pipeline directly without the API server

**Background Services (started in FastAPI lifespan):**
- Scheduler worker (`src/services/scheduler_worker.py`): processes scheduled posts every 60s
- Stale job scanner (`src/video_gen/stale_job_scanner.py`): detects and marks stuck Kie.ai jobs

## Error Handling

**Strategy:** Errors surface at the API boundary; internal pipeline failures are caught, logged, and written back to the job's `step_state` or `status` field. Frontend reads the status and shows error state per step.

**Patterns:**
- Route-level: FastAPI `HTTPException` for 4xx (validation, 401, 403, 404); unhandled exceptions return 500
- Background tasks: `try/except Exception` wraps entire step; `step_state[step]["status"] = "error"` + `"error": str(e)` written back to DB
- LLM/API retries: `gemini_client.py` implements retry with exponential backoff for 429 errors; `kie_client.py` implements transient retry for Kie.ai failures
- Budget enforcement: `VIDEO_DAILY_BUDGET_USD` checked before task creation; returns `HTTP 402`

## Cross-Cutting Concerns

**Logging:** `logging.getLogger("clip-flow.<module>")` pattern throughout; `log_sanitizer.py` strips API keys from log output
**Validation:** Pydantic models on API boundary in `src/api/models.py`; path traversal guard in `deps.validate_filename()`
**Authentication:** JWT Bearer tokens; `get_current_user` Depends used on all non-public routes; `/health` and `/auth/*` exempt
**Multi-tenancy:** `user_id` on every major entity; repository `get_by_slug(slug, user=current_user)` raises 403 on ownership mismatch

---

*Architecture analysis: 2026-03-30*
