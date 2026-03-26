# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**LLM & Content Generation:**
- **Google Gemini API** - Text phrase generation, trend analysis, image generation
  - SDK/Client: `google-genai` via `src/llm_client.py`
  - Auth: `GOOGLE_API_KEY` (required, from .env)
  - Models: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`
  - Features:
    - Text generation with system prompts (frases, captions, analysis)
    - JSON mode for structured output (analyzer)
    - Google Search grounding via `types.Tool(google_search=...)` (GeminiWebTrendsAgent)
    - Image generation with visual references (Nano Banana pipeline)

**Trend Sources (Public APIs - No Auth):**
- **Google Trends RSS** - Brazilian trending keywords
  - Agent: `src/pipeline/agents/google_trends.py` (GoogleTrendsAgent)
  - SDK: `trendspyg` library (RSS feed parser)
  - Endpoint: `trends.google.com` RSS by geo
  - Config: `PIPELINE_GOOGLE_TRENDS_GEO="BR"`

- **BlueSky Public API** - Viral Brazilian posts
  - Agent: `src/pipeline/agents/bluesky_trends.py` (BlueSkyTrendsAgent)
  - Endpoint: `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`
  - Auth: Public/no auth required
  - SDK: `urllib` (stdlib) + `httpx`
  - Keywords: Brazilian meme/humor keywords (pt-BR)
  - Optional Credentials (for authenticated access, unused):
    - `BLUESKY_HANDLE` - BlueSky username
    - `BLUESKY_APP_PASSWORD` - App password from bsky.app/settings/app-passwords

- **HackerNews Public API** - Trending tech stories
  - Agent: `src/pipeline/agents/hackernews.py` (HackerNewsAgent)
  - Endpoint: `https://hacker-news.firebaseio.com/v0/` (Firebase public)
  - Auth: None required
  - SDK: `urllib` + `httpx`

- **Lemmy Public API** - Community discussions (Brazilian communities)
  - Agent: `src/pipeline/agents/lemmy_communities.py` (LemmyCommunitiesAgent)
  - Endpoint: `https://lemmy.world/api/v3/` (v3 JSON API)
  - Auth: None required
  - SDK: `httpx`

**RSS Feed Sources (Public):**
- **Reddit RSS** - Hot posts from 8 Brazilian subreddits
  - Agents: `src/pipeline/agents/reddit_memes.py`, `src/pipeline/agents/rss_feeds.py`
  - Feeds: Reddit RSS endpoints (reddit.com/r/*/hot/.rss)
  - Subreddits: brasil, eu_nvr, DiretoDoZapZap, memes, dankmemes, meirl
  - Auth: None required
  - SDK: `feedparser`

- **Sensacionalista Feed** - Brazilian humor portal
  - Agent: `src/pipeline/agents/rss_feeds.py`
  - Endpoint: `https://www.sensacionalista.com.br/feed/`
  - Auth: None required
  - SDK: `feedparser`

- **YouTube Channels RSS** - Brazilian content creators
  - Agent: `src/pipeline/agents/youtube_rss.py` (YouTubeRSSAgent)
  - Endpoints: YouTube channel RSS feeds via `youtube.com/feeds/videos.xml?channel_id=`
  - Verified Channel IDs: Porta dos Fundos, Manual do Mundo, KondZilla, BRKsEDU
  - Auth: None required
  - SDK: `feedparser`
  - Note: YouTube trending RSS (mostpopular) disabled in 2025, uses specific channel RSS

- **Brazil Viral Portals** - Meme aggregators
  - Agent: `src/pipeline/agents/brazil_viral_rss.py` (BrazilViralRSSAgent)
  - Sources: Hypeness, Metropoles, meme subreddits
  - Auth: None required
  - SDK: `feedparser`

**Stub Agents (Require API Keys, Not Implemented):**
- TikTok Trends - `src/pipeline/agents/tiktok_trends.py` (stub)
- Instagram Explore - `src/pipeline/agents/instagram_explore.py` (stub)
- Twitter/X Trends - `src/pipeline/agents/twitter_x.py` (stub)
- YouTube Shorts - `src/pipeline/agents/youtube_shorts.py` (stub)
- Facebook Viral - `src/pipeline/agents/facebook_viral.py` (stub)

## Data Storage

**Databases:**
- **MySQL** (primary on branch estrutura-agents)
  - Connection: `DATABASE_URL` env var (e.g., `mysql+aiomysql://user:pass@localhost/memelab`)
  - Client: SQLAlchemy 2.0 async ORM + aiomysql driver
  - Tables: 10 models in `src/database/models.py`
    - `characters` - Multi-character personas (DNA, rules, rendering)
    - `character_refs` - Visual references for each character
    - `themes` - Visual themes (situacao_key, acao, cenario)
    - `pipeline_runs` - Execution history
    - `trend_events` - Collected trends from agents
    - `work_orders` - Curator output (topic + theme assignment)
    - `content_packages` - Generated content (phrase + background + metadata)
    - `generated_images` - Final composed images with metadata
    - `batch_jobs` - Bulk processing jobs
    - `scheduled_posts` - Posts queued for Instagram publishing
    - `agent_stats` - Per-agent performance tracking

- **SQLite** (development/testing)
  - Connection: `sqlite+aiosqlite:///data/clipflow.db` (default)
  - Client: SQLAlchemy 2.0 async ORM + aiosqlite driver
  - Fully compatible with MySQL schema for testing

**File Storage:**
- **Local filesystem only** - No cloud storage integration
  - Generated backgrounds: `output/backgrounds_generated/`
  - Composed images (final): `output/`
  - Character references: `assets/backgrounds/mago/`
  - ComfyUI LoRA: `assets/backgrounds/mago/lora/` (trigger: `ohwx_mago`)
  - Fonts: `assets/fonts/`

**Caching:**
- None detected - All processing is stateless (session-based for ORM)

## Authentication & Identity

**Auth Providers:**
- **Google Gemini API** - API key authentication (no OAuth)
  - Header: `Authorization: Bearer {GOOGLE_API_KEY}`
  - Scopes: Text generation, image generation, web search
  - Cost: Pay-as-you-go (pricing depends on model and tokens)

- **Meta Graph API** (Instagram Publishing) - Access token
  - Token type: Long-lived user access token (generated via Facebook Developer Portal)
  - Required configs: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`
  - Permissions: `instagram_business_content_publish`, `instagram_business_manage_messages`
  - Endpoints: `https://graph.facebook.com/v21.0/`

- **BlueSky AT Protocol** (optional, for authenticated feed)
  - Auth: App password (generated in bsky.app/settings/app-passwords)
  - Unused in current implementation (public API used instead)

**No Built-in Auth:** API endpoints have no authentication layer (open to network)

## Monitoring & Observability

**Error Tracking:**
- None detected - Errors logged to stdout/console

**Logs:**
- `logging` (Python stdlib)
  - Levels: DEBUG, INFO, WARNING, ERROR
  - Format: `[timestamp] [module] [level]: message`
  - Loggers: `clip-flow.llm`, `clip-flow.agent.*`, `clip-flow.comfyui`, etc.
  - Output: console (stderr)

**Database Monitoring:**
- SQLAlchemy echo mode available (disabled by default in `src/database/session.py`)
- Agent stats tracked in `agent_stats` table (performance metrics per agent run)

## CI/CD & Deployment

**Hosting:**
- Local machine (Windows 11) for development
- Production: Requires Python 3.14+, MySQL, internet access (Gemini API calls)
- Optional: Docker container with Alembic migrations

**CI Pipeline:**
- None detected (no GitHub Actions, GitLab CI, etc.)
- Manual testing via pytest

**Deployment Entry Points:**
- `python -m src.api [--port 8000]` - FastAPI + Uvicorn
- `python -m src.pipeline_cli --mode agents` - CLI for pipeline execution
- `python -m src.database.seed` - Database seeding (idempotent)

## Environment Configuration

**Required Environment Variables:**
- `GOOGLE_API_KEY` - Google Gemini API key (must be set)
- `DATABASE_URL` - MySQL or SQLite connection string

**Optional Environment Variables:**
- `LLM_BACKEND` - "gemini" or "ollama" (default: "gemini")
- `COST_MODE` - "normal", "eco", "ultra-eco" (default: "normal")
- `IMAGE_BACKEND_PRIORITY` - "comfyui" or "gemini" (default: "comfyui")
- `OLLAMA_HOST` - Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Ollama model name (default: `gemma3:4b`)
- `BLUESKY_HANDLE` - BlueSky username (empty string = skip auth)
- `BLUESKY_APP_PASSWORD` - BlueSky app password (empty string = skip auth)
- `INSTAGRAM_ACCESS_TOKEN` - Meta Graph API token (empty string = skip publishing)
- `INSTAGRAM_BUSINESS_ID` - Instagram Business Account ID (empty string = skip publishing)

**Secrets Location:**
- `.env` file (Windows: `C:\Users\VIP\testeDev\clip-flow\.env`)
- Not committed to git (listed in `.gitignore`)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- **Instagram Publishing** - `POST https://graph.facebook.com/v21.0/{ig_user_id}/media`
  - Triggered by: `/publishing/schedule` endpoint or scheduler
  - Publishes: Image, carousel, or reel to Instagram feed
  - Response: Media ID for tracking

- **Pipeline Events** (future)
  - Database updates to `pipeline_runs`, `content_packages`, `scheduled_posts`
  - Frontend polls `/pipeline/status`, `/publishing/queue` for updates

## Rate Limiting & Quotas

**Google Gemini API:**
- Semaphore: `GEMINI_MAX_CONCURRENT=5` (limit simultaneous requests)
- Rate limit handling: Exponential backoff with `GEMINI_IMAGE_MAX_RETRIES=2`, `GEMINI_IMAGE_WAIT_BASE=60`
- Cost tiers: `gemini-2.5-flash-lite` (lite/$0.40/1M) vs `gemini-2.5-flash` (normal/$2.50/1M)

**ComfyUI (GPU):**
- Semaphore: `COMFYUI_MAX_CONCURRENT=1` (single GPU, max 1 concurrent generation)
- Timeout: 300 seconds per generation
- Hardware: RTX 4060 Ti 8GB VRAM

**Instagram Graph API:**
- Limits: `INSTAGRAM_MAX_HASHTAGS=30`, `INSTAGRAM_MAX_CAPTION_LENGTH=2200`
- Rate limiting: Handled by Meta (tier-based on app tier)

**Agent Timeouts:**
- `AGENT_FETCH_TIMEOUT=30` seconds per agent fetch
- Broker queue size: `BROKER_MAX_QUEUE_SIZE=100` events

---

*Integration audit: 2026-03-23*
