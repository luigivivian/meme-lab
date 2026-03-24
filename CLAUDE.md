# Clip-Flow

Automacao de memes "O Mago Mestre" para Instagram (@magomestre420). Pipeline multi-agente que busca trends virais, gera frases via Gemini API, cria backgrounds com Gemini Image, e compoe imagens formatadas 1080x1350.

## Stack

- **Python 3.14** / Windows 11
- **Pillow** — composicao de imagens 1080x1350 (4:5 Instagram)
- **Google Gemini API** — geracao de frases, analise de trends, e geracao de backgrounds com referencias visuais
- **trendspyg** — Google Trends RSS (substitui pytrends, arquivado em 2025)
- **feedparser** — RSS feeds (Reddit + Sensacionalista)
- **APScheduler** — agendamento automatico do pipeline
- **FastAPI + uvicorn** — API REST para controlar o pipeline
- **pyngrok** — tunel publico para a API (opcional)

## Estrutura do Projeto

```
clip-flow/
  config.py                    # Configuracoes centralizadas (imagem, prompts, pipeline, Gemini, ComfyUI)
  config/themes.yaml           # Situacoes visuais para backgrounds (YAML)
  requirements.txt
  .env                         # GOOGLE_API_KEY (nao committar)
  assets/
    character_model.md         # DNA do personagem + prompts AI
    backgrounds/mago/          # Imagens de referencia do Mago (usadas pelo Gemini Image)
    fonts/                     # Fontes customizadas — fallback: Impact/Arial do Windows
  output/                      # Imagens geradas (gitignored)
  src/
    cli.py                     # CLI original: --topic "tema" --count N / --text "frase"
    llm_client.py              # Client unificado Gemini (google.genai)
    phrases.py                 # generate_phrases(topic, count) via Gemini API
    image_maker.py             # create_image(text, bg_path) — composicao Pillow
    pipeline_cli.py            # CLI: --mode once|schedule|agents --comfyui --phrase-context
    image_gen/
      gemini_client.py         # GeminiImageClient — geracao via Gemini com refs visuais + refinamento
      prompt_builder.py        # KEYWORD_MAP + SCENE_TEMPLATES para mapear temas a situacoes
      comfyui_client.py        # ComfyUIClient REST/WS (fallback local)
    api/
      app.py                   # FastAPI — rotas de pipeline, geracao, themes, agents
      models.py                # Pydantic request/response models
      __main__.py              # python -m src.api [--port] [--ngrok]
    pipeline/
      models.py                # Dataclasses originais: TrendItem, AnalyzedTopic
      models_v2.py             # TrendEvent, WorkOrder, ContentPackage, AgentPipelineResult
      async_orchestrator.py    # AsyncPipelineOrchestrator (L1→L2→L3→L4→L5)
      monitoring.py            # MonitoringLayer — fetch paralelo de agents
      broker.py                # TrendBroker — asyncio.Queue + dedup
      curator.py               # CuratorAgent — ClaudeAnalyzer + KEYWORD_MAP → WorkOrders
      agents/
        async_base.py          # AsyncSourceAgent ABC + SyncAgentAdapter
        google_trends.py       # GoogleTrendsAgent — trendspyg RSS (geo="BR") [sync/SyncAgentAdapter]
        reddit_memes.py        # RedditMemesAgent — 8 subreddits RSS BR [sync/SyncAgentAdapter]
        rss_feeds.py           # RSSFeedAgent — Sensacionalista + Reddit [sync/SyncAgentAdapter]
        youtube_rss.py         # YouTubeRSSAgent — RSS de canais BR verificados [async nativo]
        gemini_web_trends.py   # GeminiWebTrendsAgent — Gemini + Google Search grounding, 15 topics BR [async nativo]
        brazil_viral_rss.py    # BrazilViralRSSAgent — subreddits meme BR + portais (Hypeness, Metropoles) [async nativo]
        tiktok_trends.py       # Stub — requer API key
        instagram_explore.py   # Stub — requer API key
        twitter_x.py           # Stub — requer API key
      processors/
        aggregator.py          # TrendAggregator — merge, dedup, boost multi-fonte
        analyzer.py            # ClaudeAnalyzer — seleciona melhores temas (JSON)
        generator.py           # ContentGenerator — wrapper sync
      workers/
        phrase_worker.py       # PhraseWorker — async wrapper de generate_phrases()
        image_worker.py        # ImageWorker — Gemini/ComfyUI/estatico + Pillow compose
        caption_worker.py      # CaptionWorker — legenda Instagram com CTA
        hashtag_worker.py      # HashtagWorker — hashtags trending + branded
        quality_worker.py      # QualityWorker — score de qualidade
        generation_layer.py    # GenerationLayer — processa WorkOrders em paralelo
        post_production.py     # PostProductionLayer — caption + hashtags + quality
  scripts/
    setup_comfyui.py           # Instalacao ComfyUI + Flux Dev GGUF
```

## Como Executar

```bash
python -m pip install -r requirements.txt

# CLI manual
python -m src.cli --topic "segunda-feira" --count 5

# Pipeline multi-agente
python -m src.pipeline_cli --mode agents --count 5 --verbose

# Pipeline com background contextualizado pela frase
python -m src.pipeline_cli --mode agents --count 5 --phrase-context

# API REST (localhost:8000/docs para Swagger)
python -m src.api --port 8000
```

## Arquitetura Multi-Agente (5 Camadas)

```
L1 Monitoring ── fetch paralelo: GoogleTrends + RedditRSS + RSSFeeds + YouTubeRSS + GeminiWebTrends + BrazilViralRSS + stubs
                 6 agents ativos, ~227 eventos por run
L2 Broker ────── Ingest → Dedup → Rank via TrendAggregator (asyncio.Queue)
L3 Curator ───── Gemini Analyzer → Keyword Map → WorkOrders com situacao_key
L4 Generation ── PhraseWorker + ImageWorker em paralelo por WorkOrder
L5 PostProd ──── CaptionWorker + HashtagWorker + QualityWorker em paralelo
                 → output/*.png + metadados
```

## Geracao de Backgrounds

Fallback: **Gemini Image API → ComfyUI local → backgrounds estaticos**

- **Gemini Image**: 5 refs do mago + prompt fotorrealista com situacao/pose/cenario
- **use_phrase_context**: injeta frase no prompt para adaptar cenario ao conteudo. Prompt proibe renderizar texto na imagem (apenas mood reference).
- **ComfyUI**: Flux Dev GGUF + LoRA. Requer GPU (--lowvram).

13 situacoes em `gemini_client.py` + extras em `config/themes.yaml`.

## API REST

`http://localhost:8000/docs` para Swagger. Principais rotas:
- `POST /pipeline/run` — pipeline completo (`use_phrase_context`, `use_gemini_image`, `count`)
- `POST /generate/compose` — background + frase = imagem final
- `POST /phrases/generate` — gerar frases por tema
- `GET /themes` / `POST /themes/generate` — gerenciar situacoes visuais
- `GET /agents` — listar agents e status

## Estilo Visual

Composicao Pillow: background → overlay (10,10,30,40) → vinheta(80) → glow(255,200,80,15) → texto branco stroke 2px → watermark @magomestre420.

Texto no terco inferior (`TEXT_VERTICAL_POSITION=0.80`), fonte 48px. Backgrounds Gemini: fotorrealista cinematico, `NEGATIVE_TRAITS` proibe texto/letras.

## Configuracoes Chave (config.py)

- `IMAGE_WIDTH=1080, IMAGE_HEIGHT=1350` — Instagram 4:5
- `FONT_SIZE=48`, `TEXT_STROKE_WIDTH=2`, `TEXT_VERTICAL_POSITION=0.80`
- `WATERMARK_TEXT="@magomestre420"`
- `GEMINI_IMAGE_ENABLED=True`, `GEMINI_MAX_CONCURRENT=5`
- `COMFYUI_MAX_CONCURRENT=1` (semaforo GPU)
- `PIPELINE_IMAGES_PER_RUN=5`, `PIPELINE_GOOGLE_TRENDS_GEO="BR"`

## Tom do Conteudo — CRITICO

**VIRAL, ENGRACADO, LEVE, RELATABLE**. Memes brasileiros estilo Twitter/TikTok. Tom de "tio sabio zoeiro".

**NUNCA**: desmotivacional, ofensivo, politica, religiao, conteudo que magoa.

## Decisoes Tecnicas

- **Gemini API** para frases + analise + imagem (substituiu Anthropic SDK)
- **Reddit JSON API bloqueada (403)** — RSS via feedparser
- **asyncio.to_thread()** para wrapping sync existente (SyncAgentAdapter)
- **Semaphore**: GPU=1, Gemini=5
- **NO TEXT em backgrounds**: Gemini proibido de renderizar texto; overlay feito pelo Pillow
- **YouTube trending RSS desativado** (400) — usa RSS por channel_id de canais BR verificados
- **Gemini web grounding**: `types.Tool(google_search=...)` — incompativel com `response_mime_type="application/json"`, usa texto + regex parse
- **gemini-2.5-flash** para GeminiWebTrendsAgent (gemini-2.0-flash descontinuado)

## Requisitos

- `GOOGLE_API_KEY` no `.env`
- Python 3.12+
- `python -m pip install -r requirements.txt`

## Idioma

Projeto, comentarios, prompts e logs em **portugues brasileiro**.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Clip-Flow: Auth, Rate Limiting & Gemini Image Fix**

Evolução do Clip-Flow para suportar autenticação de usuários, controle de uso da Gemini Image API respeitando limites do plano free, e fallback inteligente para backgrounds estáticos quando o limite é atingido. Preparação para multi-tenant futuro onde cada usuário terá seu próprio personagem/marca.

**Core Value:** O pipeline nunca para de gerar conteúdo — quando a Gemini Image API atinge o limite free, o sistema degrada graciosamente usando backgrounds existentes + Pillow, sem interromper a produção de memes.

### Constraints

- **API Limits**: Respeitar limites do plano free do Google como padrão
- **Backward Compatible**: Pipeline existente deve continuar funcionando
- **Stack**: Manter Python + FastAPI + MySQL + Next.js (não introduzir novos frameworks)
- **Security**: Senhas com bcrypt/argon2, JWT com expiração, nunca logar API keys
- **Graceful Degradation**: Pipeline nunca para — fallback para estáticos
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - Backend pipeline, CLI, API, agents, image composition
- TypeScript / Next.js 15 - Frontend (memeLab dashboard in `memelab/`)
- YAML - Configuration (`config/themes.yaml`)
- JSON - Workflow definitions for ComfyUI (`src/image_gen/workflows/`)
## Runtime
- Python 3.14 with pip package manager
- Node.js / npm - Frontend build and development
- `pip` (Python) - Lockfile: `requirements.txt`
- `npm` / `pnpm` - Frontend dependencies
## Frameworks
- FastAPI 0.115.0+ - REST API and route handlers (`src/api/`)
- Uvicorn 0.34.0+ - ASGI server for FastAPI
- Next.js 15 - Frontend dashboard (`memelab/`)
- google-genai >=1.0.0 - Google Gemini API (text generation, image generation, analysis)
- Pillow >=10.0.0 - Image composition and manipulation (1080x1350 Instagram posts)
- ComfyUI (local) - Flux Dev GGUF image generation fallback (`localhost:8188`)
- APScheduler >=3.10.0 - Task scheduling and automation
- asyncio (stdlib) - Async orchestration and concurrency
- SQLAlchemy >=2.0 - Async ORM (SQLAlchemy 2.0 with async support)
- pytest - Test framework (configured with `.pytest_cache/`)
- aiosqlite >=0.20 - SQLite async driver for testing
- Alembic >=1.13 - Database migrations (`alembic.ini`)
- pyngrok >=7.0.0 - Public tunnel for API (optional local testing)
## Key Dependencies
- google-genai - Gemini API for phrase generation, trend analysis, image generation with visual references
- Pillow - Image composition: overlay, vignette, glow, text stroke, watermark on 1080x1350 canvas
- trendspyg >=0.3.0 - Google Trends RSS feed parser (replaces pytrends, archived 2025)
- feedparser >=6.0.0 - RSS feed parsing (Reddit, Sensacionalista, YouTube channels, etc.)
- sqlalchemy >=2.0 - Async ORM with 10 database tables (MySQL + SQLite compatible)
- fastapi >=0.115.0 - REST API framework with automatic Swagger docs
- uvicorn >=0.34.0 - ASGI server (host: 127.0.0.1 on Windows, port: 8000)
- httpx >=0.27.0 - Async HTTP client (Ollama, BlueSky API, HackerNews, Instagram Graph API)
- requests >=2.31.0 - Sync HTTP client (ComfyUI REST calls)
- websocket-client >=1.6.0 - WebSocket for ComfyUI progress tracking
- aiomysql >=0.2.0 - Async MySQL driver (primary DB on branch estrutura-agents)
- aiosqlite >=0.20 - Async SQLite driver (development/testing)
- python-dotenv >=1.0.0 - Environment variable loading (.env)
- beautifulsoup4 >=4.12.0 - HTML parsing (unused, available for future scraping)
- playwright >=1.40.0 - Browser automation (unused, available for dynamic scraping)
- pyyaml >=6.0 - YAML parsing (`config/themes.yaml` for theme definitions)
- cryptography >=42.0 - Password hashing and encryption (dependency for other packages)
## Configuration
- `GOOGLE_API_KEY` - Google Gemini API key (required)
- `DATABASE_URL` - MySQL or SQLite connection string (default: `sqlite:///data/clipflow.db`)
- `LLM_BACKEND` - "gemini" or "ollama" for text generation backend (default: "gemini")
- `COST_MODE` - "normal", "eco", or "ultra-eco" cost optimization (default: "normal")
- `IMAGE_BACKEND_PRIORITY` - "comfyui" or "gemini" for image generation order (default: "comfyui")
- `BLUESKY_HANDLE` - BlueSky username for auth (optional)
- `BLUESKY_APP_PASSWORD` - BlueSky app password (optional)
- `INSTAGRAM_ACCESS_TOKEN` - Meta Graph API token for publishing (optional, long-lived)
- `INSTAGRAM_BUSINESS_ID` - Instagram Business Account ID (optional)
- `OLLAMA_HOST` - Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Ollama model name (default: `gemma3:4b`)
- `alembic.ini` - Database migration configuration
- `config.py` - Centralized settings: IMAGE_WIDTH=1080, IMAGE_HEIGHT=1350, WATERMARK_TEXT="@magomestre420", font, colors, pipeline intervals
- `config/themes.yaml` - 13+ visual themes (sabedoria, cafe, tecnologia, etc.) with situacao/acao/cenario
- `tsconfig.json` - TypeScript configuration (frontend)
- `.env.example` - Template for required environment variables
## Platform Requirements
- Windows 11 Pro (primary), Linux compatible
- Python 3.14+
- Node.js 18+
- MySQL server (or SQLite for dev)
- ComfyUI server (optional, localhost:8188) with:
- Python 3.14+
- MySQL database (aiomysql async driver)
- Google Gemini API key (quota based on usage)
- Optional: ComfyUI local instance or Gemini Image API calls
- Optional: Instagram Business Account for publishing (Meta Graph API)
- Optional: Ollama server for cost-free local text generation
- Linux (Ubuntu 22.04+) for deployment
- Docker-compatible (can containerize FastAPI + Alembic)
- API: runs on port 8000, CORS enabled
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Python: lowercase with underscores (`async_orchestrator.py`, `image_worker.py`, `prompt_builder.py`)
- TypeScript: camelCase (`use-api.ts`, `character-context.tsx`, `agent-modal.tsx`)
- React components: PascalCase (`DashboardPage.tsx`, `AgentModal.tsx`, `StatsCard.tsx`)
- Test files: `test_*.py` or `*.test.ts` (though testing is minimal)
- Python: snake_case (`async def fetch()`, `def _init_gemini_image()`, `def generate_phrases()`)
- Private/internal methods: prefix with `_` (`_get_client()`, `_ollama_available()`, `_try_gemini()`)
- Async functions: use `async def` keyword, prefix with `a` when wrapping sync (e.g., `agenerate_image()`)
- TypeScript: camelCase (`useStatus()`, `getDriveImages()`, `handleQuickRun()`)
- Python: snake_case (`work_order`, `trend_item`, `background_path`, `gemini_client`)
- Semaphores/locks: `_[resource]_semaphore` (e.g., `_gpu_semaphore`, `_gemini_image_semaphore`)
- Global clients: `_[client]` (e.g., `_client`, `_ollama_client`)
- TypeScript: camelCase (`activeCharacter`, `isLoading`, `sourceDistribution`)
- Python: PascalCase (`AsyncSourceAgent`, `GoogleTrendsAgent`, `ContentGenerator`, `TrendBroker`)
- TypeScript interfaces: PascalCase (`StatusResponse`, `AgentInfo`, `ContentPackage`)
- Dataclasses: PascalCase with descriptive name (`TrendEvent`, `WorkOrder`, `ComposeResult`)
- Enums: PascalCase values (`TrendSource.BLUESKY`, `TrendSource.HACKERNEWS`)
- Python: UPPER_SNAKE_CASE in `config.py` (`PIPELINE_IMAGES_PER_RUN`, `GEMINI_MAX_CONCURRENT`, `TEXT_VERTICAL_POSITION`)
- TypeScript: UPPER_SNAKE_CASE for constants, but most use PascalCase dict objects (`NAV_ITEMS`, `STATUS_COLORS`, `AGENT_TYPE_COLORS`)
## Code Style
- No explicit formatter configured (no `.eslintrc`, `.prettierrc`, or `pyproject.toml` with formatting)
- Python follows PEP 8 informally: 4-space indentation, max 88 chars (observed)
- TypeScript uses standard conventions: 2-space indentation, semicolons present
- Python: No linter configuration detected, but code follows standards
- TypeScript: ESLint configured via Next.js default (`eslint: ^9.27.0`, `eslint-config-next: ^15.3.3`)
- Next.js built-in linting via `npm run lint` command
- Python source: typical 80-120 characters
- Comments: 88-100 characters preferred
- TypeScript: 88-100 characters typical
## Import Organization
- TypeScript: `@/` points to `src/` directory (defined in `tsconfig.json`)
- All imports use alias: `@/hooks`, `@/components`, `@/lib`, `@/contexts`
## Error Handling
- Python: Agent methods catch internally and return empty lists, logged as warnings
- Python: Worker methods catch and fallback to next strategy
- TypeScript: API layer throws with HTTP status, caller handles
## Logging
- Python: `logging` module (standard library)
- TypeScript: Console (no structured logging detected)
- No external logging service (Sentry, LogRocket)
- `clip-flow.api`
- `clip-flow.async_orchestrator`
- `clip-flow.worker.image`
- `clip-flow.llm`
- `clip-flow.analyzer`
| Level | When | Example |
|-------|------|---------|
| `INFO` | Start/stop operations, config | `logger.info(f"Background mode: {mode}")` |
| `WARNING` | Recoverable errors, fallbacks | `logger.warning(f"Gemini unavailable: {e}")` |
| `ERROR` | Unrecoverable, request fails | `logger.error(f"Agent {name} failed: {e}")` |
| `DEBUG` | Detailed flow (not seen at INFO) | Would use but not in codebase |
- No `logger.debug()` calls observed in production code
- Focus is INFO for state changes, WARNING for issues
## Comments
- Module docstring: Always (describe purpose, key functions)
- Function docstring: Key functions only (not every method)
- Inline comments: Explain "why" not "what" (code should be self-documenting)
- TODOs: Mark known limitations or deferred work
- "comfyui": ComfyUI local (custo zero) → Gemini API → estatico
- "gemini":  Gemini API → ComfyUI local → estatico
## Function Design
- Python functions: 10-50 lines typical, up to 100 for complex workers
- Async orchestrator methods: up to 150 lines (event-driven pattern)
- Break into `_private_helper()` methods for clarity
- Use positional for first 1-2 required args
- Use keyword-only for optional config (preferred in Python 3.8+)
- Avoid more than 5 positional params (use dataclass if more needed)
- Single return type preferred (not Union unless necessary)
- Optional returns: return `None` explicitly, never silent `None`
- Tuple unpacking: `path, source, metadata = await worker()`
- Dict with consistent keys for structured data
## Module Design
- Python: No `__all__` observed; export public classes/functions at module level
- TypeScript: Named exports preferred over default
- Examples: `export function useStatus()`, `export interface StatusResponse`
- Used in `src/api/routes/__init__.py`: imports all route modules (allows `from src.api.routes import generation`)
- Used in `src/database/repositories/__init__.py`: exports all repo classes
- Minimal re-export, mostly for organizational clarity
- Database: `models.py` (ORM) → `repositories/` (queries) → `session.py` (connection)
- Pipeline: `models_v2.py` (data) → `agents/` (sources) → `processors/` (logic) → `workers/` (workers)
- API: `app.py` (FastAPI) → `routes/` (endpoints) → `models.py` (Pydantic) → `serializers.py` (conversion)
## Language-Specific Notes
- Type hints used throughout (no bare `*args`, `**kwargs`)
- Async/await consistently used for I/O
- Dataclasses preferred for simple data holders
- String formatting: f-strings only
- Strict mode implied (tsconfig.json default)
- Interface over type for contracts
- React hooks: `use*` naming convention
- No `any` types observed (proper typing throughout)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Five-layer asynchronous pipeline (Monitoring → Broker → Curator → Generation → Post-Production)
- Agent-based trend collection with parallel execution via asyncio
- Adapter pattern for sync→async bridging (SyncAgentAdapter)
- Semaphore-based resource locking for GPU and API concurrency
- Database-backed state persistence (MySQL with SQLAlchemy 2.0 async)
- REST API gateway for pipeline triggering and monitoring
## Layers
- Purpose: Fetch trends in parallel from multiple independent sources
- Location: `src/pipeline/monitoring.py`
- Contains: MonitoringLayer orchestrates all agents (6 sync + 3+ async native agents)
- Depends on: Agent implementations in `src/pipeline/agents/`
- Used by: Layer 2 (Broker)
- Key files:
- Output: ~227 TrendEvent objects per run
- Purpose: Ingest trends, deduplicate via TrendAggregator, rank by score
- Location: `src/pipeline/broker.py`
- Contains: TrendBroker maintains asyncio.Queue with aggregation logic
- Depends on: TrendAggregator from `src/pipeline/processors/aggregator.py`
- Used by: Layer 3 (Curator)
- Key behavior: Converts TrendEvent ↔ TrendItem to reuse existing aggregator logic
- Output: Ranked, deduplicated event queue
- Purpose: Analyze trending events via LLM, select best themes, emit WorkOrders with visual mappings
- Location: `src/pipeline/curator.py`
- Contains: CuratorAgent wraps ClaudeAnalyzer, applies KEYWORD_MAP → situacao_key mapping
- Depends on: ClaudeAnalyzer in `src/pipeline/processors/analyzer.py`
- Used by: Layer 4 (Generation)
- Key logic:
- Output: List[WorkOrder] with trend_event, gandalf_topic, situacao_key, layout, carousel_count
- Purpose: Generate phrases and backgrounds in parallel for each WorkOrder
- Location: `src/pipeline/workers/generation_layer.py`
- Contains: GenerationLayer coordinates PhraseWorker + ImageWorker
- Depends on:
- Used by: Layer 5 (Post-Production)
- Key behavior:
- Output: List[ContentPackage] with phrase, image_path, background_source, metadata, carousel_slides
- Purpose: Add captions, hashtags, quality scoring before publication
- Location: `src/pipeline/workers/post_production.py`
- Contains: PostProductionLayer coordinates CaptionWorker + HashtagWorker + QualityWorker
- Depends on:
- Used by: API responses, publishing queue
- Key behavior:
- Output: Enriched List[ContentPackage] with caption, hashtags, quality_score
## Data Flow
- Bypass L1/L2/L3: provide list[{topic, humor_angle}]
- Auto-detect situacao_key via KEYWORD_MAP or random fallback
- Jump directly to L4
- **In-memory during run:** TrendEvents, WorkOrders, ContentPackages flow through layers
- **Persisted to DB:**
## Key Abstractions
- Purpose: Unified trend representation across all agent sources
- Examples: `src/pipeline/models_v2.py:TrendEvent`
- Pattern: Dataclass with title, source (enum), score, velocity, category, sentiment, metadata
- Replaces: Old TrendItem for new event-driven architecture
- Purpose: Specification for generation layer (what to make)
- Examples: `src/pipeline/models_v2.py:WorkOrder`
- Pattern: Dataclass linking TrendEvent to visual situacao_key, layout, carousel config
- Flow: Curator emits → Generation consumes
- Purpose: Complete content item ready for publication
- Examples: `src/pipeline/models_v2.py:ContentPackage`
- Pattern: Dataclass with phrase, image_path, caption, hashtags, quality_score, background_source
- Flow: Generation creates → PostProduction enriches → Publishing/Gallery displays
- Purpose: Pluggable trend source implementation
- Pattern: ABC with fetch() → List[TrendEvent/TrendItem]
- Implementations: GoogleTrendsAgent, RedditMemesAgent, YouTubeRSSAgent, etc.
- Adapter: SyncAgentAdapter wraps sync agents in async via asyncio.to_thread()
- GPU (ComfyUI): asyncio.Semaphore(COMFYUI_MAX_CONCURRENT=1)
- Gemini API: asyncio.Semaphore(GEMINI_MAX_CONCURRENT=5)
- Location: `src/pipeline/workers/image_worker.py`, `src/pipeline/workers/phrase_worker.py`
## Entry Points
- Location: `src/api/app.py`
- Triggers: `POST /pipeline/run` with optional character_slug, cost_mode, use_phrase_context
- Responsibilities:
- `src/api/routes/pipeline.py` — `/pipeline/run`, `/pipeline/status/{run_id}`, `/pipeline/list`
- `src/api/routes/generation.py` — `/generate/compose`, `/generate/batch`, `/generate/refinement`
- `src/api/routes/characters.py` — `/characters`, `/characters/{slug}`, `/characters/{slug}/refs`
- `src/api/routes/agents.py` — `/agents`, `/agents/{name}/status`
- `src/api/routes/publishing.py` — `/publishing/queue`, `/publishing/schedule`
- `src/pipeline_cli.py` — `python -m src.pipeline_cli --mode {once|schedule|agents} --count 5`
- `src/api/__main__.py` — `python -m src.api --port 8000 [--ngrok TOKEN]`
- `src/pipeline/async_orchestrator.py:AsyncPipelineOrchestrator.run()` — Main pipeline execution
- Instantiated by: API routes and CLI with config overrides
## Error Handling
- **Agent timeout/failure:** MonitoringLayer._safe_fetch wraps each agent in try-except + asyncio.wait_for(timeout=30s)
- **Broker dedup failure:** Logged but non-fatal; proceeds with raw events
- **Curator analysis failure:** Caught in async_orchestrator.run(), returns error in AgentPipelineResult.errors[]
- **Generation layer failures:** Per-work-order try-except
- **Post-production failures:** Per-package try-except
- **DB transaction failures:** Session rolled back, error propagated to caller
## Cross-Cutting Concerns
- Framework: Python logging module
- Level: DEBUG via --verbose flag, INFO for normal runs
- Format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- Key loggers:
- Central: `config.py` (BASE_DIR, IMAGE_*, PIPELINE_*, COMFYUI_*, GEMINI_*, etc.)
- Environment: `.env` with DATABASE_URL, GOOGLE_API_KEY, API keys for stub agents
- Cost modes: normal (full Gemini), eco (Flash Lite + no A/B), ultra-eco (no GeminiWebTrends)
- Runtime overrides: API request can set cost_mode, character_slug, use_phrase_context
- Pydantic models in `src/api/models.py` for request validation
- Range checks on image dimensions, phrase counts, cost modes
- Character config validation: refs_min/ideal, hashtag limits
- API: None (127.0.0.1 only; ngrok optional for Colab)
- DB: MySQL user/pass via DATABASE_URL
- Semaphores: GPU (1 ComfyUI job), Gemini API (5 concurrent)
- Timeouts: Agent fetch (30s), ComfyUI generation (300s), Gemini API (60s)
- Queue sizes: Broker queue (100 events max)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
