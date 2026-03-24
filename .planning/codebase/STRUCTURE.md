# Codebase Structure

**Analysis Date:** 2026-03-23

## Directory Layout

```
clip-flow/
├── config.py                          # Central configuration (images, prompts, pipeline, Gemini, ComfyUI)
├── requirements.txt                   # Python dependencies
├── .env                               # Environment vars (GOOGLE_API_KEY, DATABASE_URL)
├── alembic.ini                        # Alembic migration config
│
├── assets/                            # Static assets
│   ├── backgrounds/mago/              # Reference images for Gemini Image generation
│   ├── fonts/                         # Custom fonts (fallback: Windows Impact/Arial)
│   └── character_model.md             # Character DNA template
│
├── config/                            # Configuration files
│   └── themes.yaml                    # Visual situations (13+ themes with mood keywords)
│
├── data/                              # Database storage
│   └── clipflow.db                    # SQLite (dev) or MySQL connection via .env
│
├── output/                            # Generated images (gitignored)
│   └── backgrounds_generated/         # ComfyUI/Gemini output
│
├── src/                               # Main Python package
│   ├── __init__.py
│   ├── cli.py                         # Original CLI (--topic "tema" --count N)
│   ├── pipeline_cli.py                # Main CLI (--mode agents|once|schedule)
│   ├── llm_client.py                  # Unified Gemini API client (wraps google.genai)
│   ├── phrases.py                     # Phrase generation (via llm_client)
│   ├── image_maker.py                 # Pillow composition engine
│   ├── characters.py                  # Character YAML loader
│   ├── scrape_assets.py               # Asset downloading utilities
│   │
│   ├── api/                           # FastAPI REST server
│   │   ├── __init__.py
│   │   ├── __main__.py                # Entry: python -m src.api --port 8000
│   │   ├── app.py                     # FastAPI app definition + lifespan
│   │   ├── deps.py                    # Dependency injection (db_session)
│   │   ├── models.py                  # Pydantic request/response schemas
│   │   ├── registry.py                # Service registry for character/theme loaders
│   │   ├── serializers.py             # ORM → dict conversion functions
│   │   └── routes/                    # Route modules (each is APIRouter with prefix)
│   │       ├── __init__.py
│   │       ├── pipeline.py            # POST /pipeline/run, GET /pipeline/status
│   │       ├── generation.py          # POST /generate/compose, /generate/batch
│   │       ├── characters.py          # /characters CRUD + refs
│   │       ├── themes.py              # /themes CRUD
│   │       ├── agents.py              # /agents status
│   │       ├── content.py             # /images, /phrases, /content list
│   │       ├── jobs.py                # /jobs status/results
│   │       ├── publishing.py          # /publishing queue/schedule
│   │       └── drive.py               # /drive/* image browser + /status
│   │
│   ├── database/                      # SQLAlchemy 2.0 async ORM + migrations
│   │   ├── __init__.py
│   │   ├── base.py                    # Base class + TimestampMixin
│   │   ├── models.py                  # 11 ORM tables: Character, CharacterRef, Theme, GeneratedImage, etc.
│   │   ├── session.py                 # Async session factory + init_db()
│   │   ├── converters.py              # ORM ↔ dataclass conversion
│   │   ├── seed.py                    # Idempotent seed: YAML → MySQL
│   │   ├── repositories/              # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── character_repo.py      # Character CRUD
│   │   │   ├── content_repo.py        # GeneratedImage + ContentPackage queries
│   │   │   ├── pipeline_repo.py       # PipelineRun CRUD
│   │   │   ├── job_repo.py            # BatchJob queries
│   │   │   ├── schedule_repo.py       # ScheduledPost CRUD
│   │   │   └── theme_repo.py          # Theme CRUD
│   │   └── migrations/                # Alembic versioned migrations
│   │       ├── env.py                 # Migration environment (reads DATABASE_URL from .env)
│   │       ├── versions/
│   │       │   ├── 001_initial_schema.py
│   │       │   ├── 002_nullable_work_order_id.py
│   │       │   ├── 003_add_image_metadata.py
│   │       │   ├── 004_add_scheduled_posts.py
│   │       │   ├── 005_add_quick_wins.py
│   │       │   └── ee583b64523f_add_rendering_column_to_characters.py
│   │       └── script.py.mako
│   │
│   ├── image_gen/                     # Image generation backends
│   │   ├── __init__.py
│   │   ├── prompt_builder.py          # KEYWORD_MAP, SCENE_TEMPLATES (theme → situation mapping)
│   │   ├── gemini_client.py           # GeminiImageClient with refs + refinement (Nano Banana)
│   │   ├── comfyui_client.py          # ComfyUIClient REST/WS for local Flux Dev GGUF
│   │   └── workflows/
│   │       └── flux_img2img.json       # ComfyUI Flux img2img workflow
│   │
│   ├── pipeline/                      # Multi-agent orchestration (5 layers)
│   │   ├── __init__.py
│   │   ├── models.py                  # Old TrendItem, AnalyzedTopic (legacy, preserved for compat)
│   │   ├── models_v2.py               # New TrendEvent, WorkOrder, ContentPackage, AgentPipelineResult
│   │   ├── async_orchestrator.py      # AsyncPipelineOrchestrator (L1-L5 coordinator)
│   │   ├── orchestrator.py            # Old orchestrator (legacy)
│   │   ├── monitoring.py              # MonitoringLayer (L1) — parallel agent fetch
│   │   ├── broker.py                  # TrendBroker (L2) — dedup + queue
│   │   ├── curator.py                 # CuratorAgent (L3) — theme selection via LLM
│   │   ├── scheduler.py               # APScheduler wrapper for auto-runs
│   │   │
│   │   ├── agents/                    # Trend source implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # BaseSourceAgent (abstract sync base)
│   │   │   ├── async_base.py          # AsyncSourceAgent (abstract async) + SyncAgentAdapter
│   │   │   ├── google_trends.py       # GoogleTrendsAgent (sync via trendspyg RSS)
│   │   │   ├── reddit_memes.py        # RedditMemesAgent (sync via Reddit RSS)
│   │   │   ├── rss_feeds.py           # RSSFeedAgent (sync via feedparser)
│   │   │   ├── youtube_rss.py         # YouTubeRSSAgent (async native)
│   │   │   ├── gemini_web_trends.py   # GeminiWebTrendsAgent (async native, uses Gemini API)
│   │   │   ├── brazil_viral_rss.py    # BrazilViralRSSAgent (async native)
│   │   │   ├── bluesky_trends.py      # BlueSkyTrendsAgent (async native)
│   │   │   ├── hackernews.py          # HackerNewsAgent (async native)
│   │   │   ├── lemmy_communities.py   # LemmyCommunitiesAgent (async native)
│   │   │   ├── tiktok_trends.py       # Stub (requires API key)
│   │   │   ├── instagram_explore.py   # Stub (requires API key)
│   │   │   ├── twitter_x.py           # Stub (requires API key)
│   │   │   ├── facebook_viral.py      # Stub (requires API key)
│   │   │   └── youtube_shorts.py      # Stub (requires API key)
│   │   │
│   │   ├── processors/                # Data processing (trend aggregation, analysis, generation)
│   │   │   ├── __init__.py
│   │   │   ├── aggregator.py          # TrendAggregator (dedup via title similarity)
│   │   │   ├── analyzer.py            # ClaudeAnalyzer (LLM-based topic selection)
│   │   │   └── generator.py           # ContentGenerator (wraps phrase + image workers)
│   │   │
│   │   └── workers/                   # Generation layer implementations
│   │       ├── __init__.py
│   │       ├── generation_layer.py    # GenerationLayer (L4) — phrase + image parallelization
│   │       ├── phrase_worker.py       # PhraseWorker (Gemini text with A/B scoring)
│   │       ├── image_worker.py        # ImageWorker (ComfyUI/Gemini/static with Semaphore)
│   │       ├── post_production.py     # PostProductionLayer (L5) — caption/hashtag/quality
│   │       ├── caption_worker.py      # CaptionWorker (Instagram caption generation)
│   │       ├── hashtag_worker.py      # HashtagWorker (trending + branded hashtags)
│   │       └── quality_worker.py      # QualityWorker (content scoring 0-100)
│   │
│   └── services/                      # External integrations (publishing, scheduling, analytics)
│       ├── __init__.py
│       ├── __main__.py                # Service worker entry point
│       ├── scheduler_worker.py        # APScheduler for auto-publishing
│       ├── publisher.py               # Instagram publishing client
│       ├── instagram_client.py        # Instagram API wrapper
│       └── insights_collector.py      # Analytics aggregator
│
├── memelab/                           # Next.js 15 frontend dashboard
│   ├── src/
│   │   ├── app/                       # App router pages (Next.js 15)
│   │   │   ├── layout.tsx             # Root layout with Shell
│   │   │   ├── page.tsx               # Home page redirect
│   │   │   ├── dashboard/page.tsx     # Main dashboard (stats + agent modals)
│   │   │   ├── agents/page.tsx        # Agent status / monitoring
│   │   │   ├── pipeline/page.tsx      # Pipeline orchestrator UI
│   │   │   ├── trends/page.tsx        # Trend browser
│   │   │   ├── phrases/page.tsx       # Phrase generator test
│   │   │   ├── characters/            # Character CRUD + management
│   │   │   │   ├── page.tsx
│   │   │   │   ├── [slug]/page.tsx
│   │   │   │   └── [slug]/refs/page.tsx
│   │   │   ├── themes/page.tsx        # Theme/situation editor
│   │   │   ├── gallery/page.tsx       # Generated images browser
│   │   │   ├── jobs/page.tsx          # Batch job history
│   │   │   ├── publishing/page.tsx    # Publication queue + scheduling
│   │   │   ├── globals.css            # Global styles
│   │   │   └── [layout]/page.tsx      # Dynamic layout preview
│   │   │
│   │   ├── components/                # Reusable UI components
│   │   │   ├── layout/
│   │   │   │   ├── shell.tsx          # Main layout wrapper (sidebar + content)
│   │   │   │   ├── sidebar.tsx        # Navigation sidebar
│   │   │   │   └── header.tsx         # Top header bar
│   │   │   ├── ui/                    # Base UI primitives (button, card, input, etc.)
│   │   │   ├── panels/                # Composite panels
│   │   │   │   ├── pipeline-diagram.tsx   # 5-layer visualization
│   │   │   │   └── stats-card.tsx     # Stats display
│   │   │   ├── agents/                # Agent-specific components
│   │   │   │   ├── agent-modal.tsx    # Agent status modal
│   │   │   │   └── agent-config.ts    # Agent metadata
│   │   │   └── ...
│   │   │
│   │   ├── hooks/
│   │   │   └── use-api.ts             # API client hook
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client (fetch wrapper)
│   │   │   └── constants.ts           # UI constants
│   │   │
│   │   └── tsconfig.json
│   │
│   ├── package.json                   # Next.js dependencies
│   ├── next.config.js
│   ├── tsconfig.json
│   └── ...
│
├── tests/                             # Test suite
│   └── test_agents_quick.py           # Quick validation tests for agents
│
├── scripts/                           # Utility scripts
│   ├── setup_comfyui.py               # Install ComfyUI + Flux Dev GGUF
│   ├── start_comfyui.py               # Launch ComfyUI server
│   ├── train_lora.py                  # LoRA fine-tuning
│   └── prepare_lora_dataset.py        # Dataset preparation
│
├── docs/                              # Documentation
│   ├── API_README.md                  # API endpoint reference
│   ├── CLAUDE.md                      # Project instructions
│   └── roadmap-monetizacao.md         # Monetization roadmap
│
└── .planning/
    └── codebase/                      # GSD mapping documents
        ├── ARCHITECTURE.md            # This file
        ├── STRUCTURE.md               # File organization guide
        ├── CONVENTIONS.md             # Code style standards
        ├── TESTING.md                 # Test patterns
        ├── STACK.md                   # Technology stack
        └── CONCERNS.md                # Technical debt + issues
```

## Directory Purposes

**config.py**
- Purpose: Central configuration point for all settings
- Contains: Image dimensions, text styling, prompt templates, pipeline params, Gemini/ComfyUI settings, cost modes
- Key configs: IMAGE_WIDTH/HEIGHT (1080x1350), WATERMARK_TEXT, PIPELINE_IMAGES_PER_RUN, GEMINI_MAX_CONCURRENT (5), COMFYUI_MAX_CONCURRENT (1)

**src/api/**
- Purpose: FastAPI REST gateway for pipeline control and monitoring
- Entry: `python -m src.api --port 8000 [--ngrok TOKEN]`
- Lifespan: Initializes database on startup, starts scheduler
- Dependency injection: db_session, config overrides via request

**src/database/**
- Purpose: SQLAlchemy 2.0 async ORM + migration management
- Models: 11 tables (Character, CharacterRef, Theme, PipelineRun, GeneratedImage, ContentPackage, ScheduledPost, BatchJob, etc.)
- Session: Agnóstic to SQLite (dev) or MySQL (prod) via DATABASE_URL
- Repositories: Data access layer for each domain (character, content, pipeline, job, schedule, theme)
- Migrations: Alembic version control (001-005+)

**src/image_gen/**
- Purpose: Image generation backend abstraction
- Clients: GeminiImageClient (API + visual refs), ComfyUIClient (local GPU via WebSocket)
- Prompt builder: KEYWORD_MAP (theme keyword → visual situation) + SCENE_TEMPLATES
- SITUACOES: 13 pre-defined visual moods (cafe, meditando, confronto, sabedoria, etc.)

**src/pipeline/**
- Purpose: Multi-layer orchestration for trend→content pipeline
- Layers:
  - L1 Monitoring: Parallel agent fetch via asyncio.gather
  - L2 Broker: Event deduplication + queueing
  - L3 Curator: LLM-based topic selection + situation mapping
  - L4 Generation: Phrase + image production in parallel
  - L5 Post-Production: Caption + hashtag + quality enrichment
- Models: TrendEvent, WorkOrder, ContentPackage (v2 event-driven models)
- Agents: 9 active + 5 stub sources (RSS, Gemini Trends, BlueSky, HN, Lemmy)
- Processors: Aggregator (dedup), Analyzer (LLM), Generator (phrase+image)
- Workers: Phrase, Image, Caption, Hashtag, Quality, GenerationLayer, PostProductionLayer

**src/services/**
- Purpose: Background services (scheduling, publishing, analytics)
- Scheduler: APScheduler for auto-pipeline runs (default every 6 hours)
- Publisher: Instagram API client for posting ContentPackages
- Insights: Analytics aggregation from published content

**memelab/**
- Purpose: Next.js 15 dashboard frontend
- App Router: File-based routing (pages = files in src/app/)
- Pages: Dashboard, Pipeline, Trends, Phrases, Characters (CRUD), Themes, Gallery, Jobs, Publishing
- Components: Shell layout, Sidebar nav, Agent modals, Pipeline diagram, Stats cards
- API: use-api.ts hook + lib/api.ts fetch wrapper

## Key File Locations

**Entry Points:**
- `config.py` — Central configuration
- `src/api/__main__.py` — REST API server
- `src/pipeline_cli.py` — CLI orchestrator
- `memelab/src/app/layout.tsx` — Next.js root

**Configuration:**
- `config.py` — Main settings
- `config/themes.yaml` — Visual situation definitions
- `.env` — Environment variables (GOOGLE_API_KEY, DATABASE_URL)
- `alembic.ini` — Migration config

**Core Logic:**
- `src/pipeline/async_orchestrator.py` — Main orchestrator (L1-L5)
- `src/pipeline/monitoring.py` — L1 agent coordination
- `src/pipeline/broker.py` — L2 deduplication
- `src/pipeline/curator.py` — L3 topic selection
- `src/pipeline/workers/generation_layer.py` — L4 content production
- `src/pipeline/workers/post_production.py` — L5 enrichment
- `src/image_maker.py` — Pillow composition

**Testing:**
- `tests/test_agents_quick.py` — Agent validation tests

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (phrase_worker.py, async_orchestrator.py)
- Routes: `routes/{domain}.py` (pipeline.py, characters.py, generation.py)
- Migrations: `NNNNN_description.py` (001_initial_schema.py, 005_add_quick_wins.py)
- Components: `PascalCase.tsx` (Shell.tsx, PipelineModal.tsx)

**Directories:**
- Package modules: `lowercase` (api, database, pipeline, image_gen)
- Domains: `plural` (routes, agents, processors, workers, repositories)
- Frontend: `app` (Next.js), `components` (React), `hooks` (React), `lib` (utilities)

**Classes/Functions:**
- Classes: `PascalCase` (AsyncPipelineOrchestrator, TrendBroker, CuratorAgent)
- Functions: `snake_case` (fetch_all, ingest, curate)
- Private: `_snake_case` (_safe_fetch, _notify, _load_stub_agents)
- Constants: `UPPER_SNAKE_CASE` (PIPELINE_IMAGES_PER_RUN, GEMINI_MAX_CONCURRENT)

**Database:**
- Tables: `snake_case` (characters, character_refs, pipeline_runs)
- Columns: `snake_case` (created_at, updated_at, character_slug)
- Enums: `PascalCase` (TrendSource)

## Where to Add New Code

**New Trend Source (Agent):**
- File: `src/pipeline/agents/{platform_name}.py`
- Inherit: AsyncSourceAgent (native async) or BaseSourceAgent (wrap with SyncAgentAdapter)
- Implement: `async def fetch() -> List[TrendEvent]`, `async def is_available() -> bool`
- Register: Add instance to agents list in `AsyncPipelineOrchestrator.__init__`
- Example: `src/pipeline/agents/bluesky_trends.py`

**New API Route:**
- File: `src/api/routes/{domain}.py`
- Pattern: FastAPI APIRouter with prefix, inject db_session via deps.py
- Register: Include router in `src/api/app.py` (app.include_router)
- Serializers: Add conversion functions in `src/api/serializers.py`
- Example: `src/api/routes/characters.py`

**New Worker (Generation Layer):**
- File: `src/pipeline/workers/{worker_type}_worker.py`
- Pattern: Class with async process(input) -> output
- Semaphore: Use global asyncio.Semaphore for resource limits
- Integration: Add to GenerationLayer or PostProductionLayer
- Example: `src/pipeline/workers/phrase_worker.py`

**New Database Table:**
- File: `src/database/models.py` (append new class)
- Pattern: Inherit Base + TimestampMixin (if needed)
- Migration: `alembic revision --autogenerate -m "add_{table}"`
- Run: `alembic upgrade head`

**New Frontend Page:**
- File: `memelab/src/app/{feature}/page.tsx`
- Pattern: Default export React component (Server Component by default)
- API: Use use-api hook from `src/hooks/use-api.ts`
- Layout: Wrap in Shell from `src/components/layout/shell.tsx`
- Example: `memelab/src/app/characters/page.tsx`

**Utilities/Helpers:**
- Shared: `src/{module}/helpers.py` or `src/utils/` (if creating)
- Frontend: `memelab/src/lib/{utility}.ts`

## Special Directories

**output/**
- Purpose: Generated images output directory
- Generated: Yes (runtime created)
- Committed: No (.gitignore)
- Structure: `output/image_YYYYMMDD_HHMMSS.png` + `output/backgrounds_generated/`

**assets/backgrounds/mago/**
- Purpose: Reference images for Gemini Image generation (visual inspiration)
- Generated: No (manually curated)
- Committed: Yes (tracked in git)
- Usage: Used by GeminiImageClient via visual refs in prompt

**config/themes.yaml**
- Purpose: Visual situation definitions (additional to hardcoded SITUACOES)
- Generated: Can be seeded from DB via `src/database/seed.py`
- Committed: Yes (tracked in git)
- Format: YAML array of {key, name, mood_keywords, description, ...}

**data/**
- Purpose: Database storage (SQLite in dev)
- Generated: Yes (created by init_db())
- Committed: No (.gitignore)
- MySQL: Connection via DATABASE_URL in .env

**src/database/migrations/versions/**
- Purpose: Alembic versioned migrations
- Generated: Yes (via `alembic revision --autogenerate`)
- Committed: Yes (tracked in git for reproducibility)
- Execution: `alembic upgrade head` (idempotent per version)

**.env**
- Purpose: Environment variables (secrets + config)
- Generated: No (user-created from .env.example)
- Committed: No (.gitignore)
- Required: GOOGLE_API_KEY, DATABASE_URL (optional, defaults to SQLite)

---

*Structure analysis: 2026-03-23*
