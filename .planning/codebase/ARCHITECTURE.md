# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Event-driven, multi-layer async pipeline orchestration with pluggable agents

**Key Characteristics:**
- Five-layer asynchronous pipeline (Monitoring → Broker → Curator → Generation → Post-Production)
- Agent-based trend collection with parallel execution via asyncio
- Adapter pattern for sync→async bridging (SyncAgentAdapter)
- Semaphore-based resource locking for GPU and API concurrency
- Database-backed state persistence (MySQL with SQLAlchemy 2.0 async)
- REST API gateway for pipeline triggering and monitoring

## Layers

**Layer 1: Monitoring (L1) — Trend Collection**
- Purpose: Fetch trends in parallel from multiple independent sources
- Location: `src/pipeline/monitoring.py`
- Contains: MonitoringLayer orchestrates all agents (6 sync + 3+ async native agents)
- Depends on: Agent implementations in `src/pipeline/agents/`
- Used by: Layer 2 (Broker)
- Key files:
  - `src/pipeline/agents/async_base.py` — AsyncSourceAgent ABC + SyncAgentAdapter wrapper
  - `src/pipeline/agents/google_trends.py` — GoogleTrendsAgent (sync via trendspyg RSS)
  - `src/pipeline/agents/reddit_memes.py` — RedditMemesAgent (sync via RSS)
  - `src/pipeline/agents/rss_feeds.py` — RSSFeedAgent (sync via feedparser)
  - `src/pipeline/agents/youtube_rss.py` — YouTubeRSSAgent (async native)
  - `src/pipeline/agents/gemini_web_trends.py` — GeminiWebTrendsAgent (async native)
  - `src/pipeline/agents/brazil_viral_rss.py` — BrazilViralRSSAgent (async native)
  - `src/pipeline/agents/bluesky_trends.py` — BlueSkyTrendsAgent (async native)
  - `src/pipeline/agents/hackernews.py` — HackerNewsAgent (async native)
  - `src/pipeline/agents/lemmy_communities.py` — LemmyCommunitiesAgent (async native)
- Output: ~227 TrendEvent objects per run

**Layer 2: Broker (L2) — Deduplication & Ranking**
- Purpose: Ingest trends, deduplicate via TrendAggregator, rank by score
- Location: `src/pipeline/broker.py`
- Contains: TrendBroker maintains asyncio.Queue with aggregation logic
- Depends on: TrendAggregator from `src/pipeline/processors/aggregator.py`
- Used by: Layer 3 (Curator)
- Key behavior: Converts TrendEvent ↔ TrendItem to reuse existing aggregator logic
- Output: Ranked, deduplicated event queue

**Layer 3: Curator (L3) — Topic Selection & WorkOrder Generation**
- Purpose: Analyze trending events via LLM, select best themes, emit WorkOrders with visual mappings
- Location: `src/pipeline/curator.py`
- Contains: CuratorAgent wraps ClaudeAnalyzer, applies KEYWORD_MAP → situacao_key mapping
- Depends on: ClaudeAnalyzer in `src/pipeline/processors/analyzer.py`
- Used by: Layer 4 (Generation)
- Key logic:
  - Calls ClaudeAnalyzer.analyze(events) → JSON with best topics + humor angles
  - Maps topic keywords to visual situations (KEYWORD_MAP in `src/image_gen/prompt_builder.py`)
  - Falls back to random selection from SITUACOES pool if keyword doesn't match
  - Supports theme_tags override and exclude_topics (dedup cross-run)
  - Can operate in shortcut mode (bypass L1/L2/L3 for manual topics)
- Output: List[WorkOrder] with trend_event, gandalf_topic, situacao_key, layout, carousel_count

**Layer 4: Generation (L4) — Phrase + Image Production**
- Purpose: Generate phrases and backgrounds in parallel for each WorkOrder
- Location: `src/pipeline/workers/generation_layer.py`
- Contains: GenerationLayer coordinates PhraseWorker + ImageWorker
- Depends on:
  - `src/pipeline/workers/phrase_worker.py` — generates phrases via Gemini API (with optional A/B scoring)
  - `src/pipeline/workers/image_worker.py` — generates backgrounds (priority: ComfyUI → Gemini Image → static)
  - `src/image_maker.py` — Pillow composition engine
- Used by: Layer 5 (Post-Production)
- Key behavior:
  - Phrase generation respects character_system_prompt, max_chars, humor_angle
  - A/B testing mode: generates N alternatives, scores via Gemini on viralidade/humor/identificacao
  - Image worker chooses backend via IMAGE_BACKEND_PRIORITY (comfyui or gemini first)
  - Carousel mode: generates N slides per phrase if carousel_count > 1
  - Semaphore limits: Gemini API = 5 concurrent, GPU (ComfyUI) = 1 concurrent
- Output: List[ContentPackage] with phrase, image_path, background_source, metadata, carousel_slides

**Layer 5: Post-Production (L5) — Enrichment**
- Purpose: Add captions, hashtags, quality scoring before publication
- Location: `src/pipeline/workers/post_production.py`
- Contains: PostProductionLayer coordinates CaptionWorker + HashtagWorker + QualityWorker
- Depends on:
  - `src/pipeline/workers/caption_worker.py` — generates Instagram captions via Gemini
  - `src/pipeline/workers/hashtag_worker.py` — combines trending + branded hashtags
  - `src/pipeline/workers/quality_worker.py` — scores content quality (0-100)
- Used by: API responses, publishing queue
- Key behavior:
  - Captions include character_name, character_handle, CTA via character_caption_prompt
  - Hashtags merge 3-5 trending + 2-3 branded (character_branded_hashtags)
  - Quality scoring: clarity, readability, visual appeal, on-brand alignment
- Output: Enriched List[ContentPackage] with caption, hashtags, quality_score

## Data Flow

**Full Pipeline (L1 → L5):**

1. **L1 Monitoring fetches trends** → 9 agents run in parallel (asyncio.gather)
   - GoogleTrends RSS, RedditRSS, RSSFeeds, YouTubeRSS, GeminiWebTrends, BrazilViral, BlueSky, HN, Lemmy
   - Collect ~227 TrendEvent objects with title, source, score, metadata
   - Timeout per agent: AGENT_FETCH_TIMEOUT (30s default)
   - Failed agents return empty list; never block pipeline

2. **L2 Broker ingests & deduplicates**
   - Receive 227 events from L1
   - Convert to TrendItem, run TrendAggregator.aggregate()
   - Aggregate removes duplicates, boosts multi-source mentions
   - Enqueue deduplicated events (typically 50-70% unique)
   - Top 10 logged by score

3. **L3 Curator analyzes & curates**
   - Drain max 20 events from broker queue
   - Call ClaudeAnalyzer.analyze() with Gemini API
   - Parse JSON: {topic, humor_angle, category, viability}
   - Select top N topics (images_per_run, typically 5)
   - Apply KEYWORD_MAP → situacao_key (visual situation)
   - Generate WorkOrder per topic with:
     - gandalf_topic (curated title)
     - humor_angle (comedy direction)
     - situacao_key (visual mood: cafe, meditando, confronto, etc.)
     - layout (bottom, top, center, split_top)
     - carousel_count (1 or more slides)

4. **L4 Generation produces content**
   - For each WorkOrder:
     - **PhraseWorker:** Generate phrases using character_system_prompt
       - If A/B enabled: generate N alternatives, score each (0-10 viral/humor/identificacao)
       - Return top 1 (or N for carousel)
     - **ImageWorker:** Generate background
       - Check background_mode (auto/comfyui/gemini/static)
       - Try primary backend (respecting Semaphore limits)
       - Fallback to secondary, then static
       - Use phrase for context if use_phrase_context=True
     - **Compose:** Pillow overlay text, watermark, effects on background
   - Create ContentPackage per phrase with image_path, background_source

5. **L5 Post-Production enriches**
   - For each ContentPackage:
     - **CaptionWorker:** Generate Instagram caption (200-300 chars) with handle, CTA
     - **HashtagWorker:** Append 5-6 hashtags (trending + branded)
     - **QualityWorker:** Score (0-100) clarity, readability, brand alignment
   - Update ContentPackage with caption, hashtags, quality_score

**Shortcut Mode (Manual Topics):**
- Bypass L1/L2/L3: provide list[{topic, humor_angle}]
- Auto-detect situacao_key via KEYWORD_MAP or random fallback
- Jump directly to L4

**State Management:**

- **In-memory during run:** TrendEvents, WorkOrders, ContentPackages flow through layers
- **Persisted to DB:**
  - PipelineRun (run_id, character_id, status, started_at, finished_at, image_count, error_messages)
  - GeneratedImage (image_path, pipeline_run_id, character_id, source, phrase, background_source)
  - ContentPackage (phrase, caption, hashtags, quality_score, image_id, published)
  - TrendEvent (title, source, score, fetched_at) — optional, for analytics
  - ScheduledPost (content_package_id, scheduled_at, status) — for publishing queue

## Key Abstractions

**TrendEvent:**
- Purpose: Unified trend representation across all agent sources
- Examples: `src/pipeline/models_v2.py:TrendEvent`
- Pattern: Dataclass with title, source (enum), score, velocity, category, sentiment, metadata
- Replaces: Old TrendItem for new event-driven architecture

**WorkOrder:**
- Purpose: Specification for generation layer (what to make)
- Examples: `src/pipeline/models_v2.py:WorkOrder`
- Pattern: Dataclass linking TrendEvent to visual situacao_key, layout, carousel config
- Flow: Curator emits → Generation consumes

**ContentPackage:**
- Purpose: Complete content item ready for publication
- Examples: `src/pipeline/models_v2.py:ContentPackage`
- Pattern: Dataclass with phrase, image_path, caption, hashtags, quality_score, background_source
- Flow: Generation creates → PostProduction enriches → Publishing/Gallery displays

**Agent (AsyncSourceAgent/BaseSourceAgent):**
- Purpose: Pluggable trend source implementation
- Pattern: ABC with fetch() → List[TrendEvent/TrendItem]
- Implementations: GoogleTrendsAgent, RedditMemesAgent, YouTubeRSSAgent, etc.
- Adapter: SyncAgentAdapter wraps sync agents in async via asyncio.to_thread()

**Semaphore-Protected Resources:**
- GPU (ComfyUI): asyncio.Semaphore(COMFYUI_MAX_CONCURRENT=1)
- Gemini API: asyncio.Semaphore(GEMINI_MAX_CONCURRENT=5)
- Location: `src/pipeline/workers/image_worker.py`, `src/pipeline/workers/phrase_worker.py`

## Entry Points

**REST API (Main):**
- Location: `src/api/app.py`
- Triggers: `POST /pipeline/run` with optional character_slug, cost_mode, use_phrase_context
- Responsibilities:
  - Initialize FastAPI app with CORS middleware
  - Register 9 route modules (generation, jobs, themes, pipeline, content, agents, drive, characters, publishing)
  - Manage DB session lifecycle
  - Start/stop scheduler for auto-publishing

**API Gateway Routes:**
- `src/api/routes/pipeline.py` — `/pipeline/run`, `/pipeline/status/{run_id}`, `/pipeline/list`
- `src/api/routes/generation.py` — `/generate/compose`, `/generate/batch`, `/generate/refinement`
- `src/api/routes/characters.py` — `/characters`, `/characters/{slug}`, `/characters/{slug}/refs`
- `src/api/routes/agents.py` — `/agents`, `/agents/{name}/status`
- `src/api/routes/publishing.py` — `/publishing/queue`, `/publishing/schedule`

**CLI Entry Points:**
- `src/pipeline_cli.py` — `python -m src.pipeline_cli --mode {once|schedule|agents} --count 5`
- `src/api/__main__.py` — `python -m src.api --port 8000 [--ngrok TOKEN]`

**Orchestrator Entry:**
- `src/pipeline/async_orchestrator.py:AsyncPipelineOrchestrator.run()` — Main pipeline execution
- Instantiated by: API routes and CLI with config overrides

## Error Handling

**Strategy:** Graceful degradation with layer isolation — failure in one agent/worker doesn't cascade

**Patterns:**

- **Agent timeout/failure:** MonitoringLayer._safe_fetch wraps each agent in try-except + asyncio.wait_for(timeout=30s)
  - Failed agents logged, return empty list, pipeline continues
  - Layer 1 success criteria: ≥1 agent succeeds
  - All results: `_pipeline_layers[run_id]` tracks per-agent status

- **Broker dedup failure:** Logged but non-fatal; proceeds with raw events

- **Curator analysis failure:** Caught in async_orchestrator.run(), returns error in AgentPipelineResult.errors[]
  - Layer 3 failure is fatal: returns immediately with error

- **Generation layer failures:** Per-work-order try-except
  - Phrase generation fail → return empty ContentPackage (skipped)
  - Image generation fail → fallback chain (ComfyUI → Gemini → static)
  - Compose fail → logged, skip image
  - Layer 4 success criteria: ≥1 ContentPackage succeeds

- **Post-production failures:** Per-package try-except
  - Caption/hashtag/quality failures logged but don't block
  - Return package with partial enrichment

- **DB transaction failures:** Session rolled back, error propagated to caller

**Error Collection:** AgentPipelineResult.errors[] aggregates all layer errors for caller

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Level: DEBUG via --verbose flag, INFO for normal runs
- Format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- Key loggers:
  - `clip-flow.api` — REST API events
  - `clip-flow.async_orchestrator` — Layer summaries
  - `clip-flow.monitoring` — Agent fetch status
  - `clip-flow.broker` — Dedup statistics
  - `clip-flow.curator` — Topic selection
  - `clip-flow.generation` — Phrase/image progress
  - `clip-flow.worker.*` — Per-worker details

**Configuration:**
- Central: `config.py` (BASE_DIR, IMAGE_*, PIPELINE_*, COMFYUI_*, GEMINI_*, etc.)
- Environment: `.env` with DATABASE_URL, GOOGLE_API_KEY, API keys for stub agents
- Cost modes: normal (full Gemini), eco (Flash Lite + no A/B), ultra-eco (no GeminiWebTrends)
- Runtime overrides: API request can set cost_mode, character_slug, use_phrase_context

**Validation:**
- Pydantic models in `src/api/models.py` for request validation
- Range checks on image dimensions, phrase counts, cost modes
- Character config validation: refs_min/ideal, hashtag limits

**Authentication:**
- API: None (127.0.0.1 only; ngrok optional for Colab)
- DB: MySQL user/pass via DATABASE_URL

**Resource Management:**
- Semaphores: GPU (1 ComfyUI job), Gemini API (5 concurrent)
- Timeouts: Agent fetch (30s), ComfyUI generation (300s), Gemini API (60s)
- Queue sizes: Broker queue (100 events max)

---

*Architecture analysis: 2026-03-23*
