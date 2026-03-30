# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**AI / LLM:**
- Google Gemini API — primary LLM for text generation, image generation, TTS, audio transcription, web search grounding
  - SDK/Client: `google-genai>=1.0.0`, client at `src/llm_client.py` (singleton `genai.Client`)
  - Auth: `GOOGLE_API_KEY` env var (optional paid key: `GOOGLE_API_KEY_PAID`)
  - Models used: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-flash-preview-tts`, `gemini-2.5-flash-image`
  - Image model discovery runs at API startup (`src/image_gen/gemini_client.py`: `discover_image_models`)
  - Supports Gemini Google Search grounding for trend discovery (`src/pipeline/agents/gemini_web_trends.py`)
- Ollama — optional local LLM fallback for cost-zero text generation
  - SDK/Client: direct HTTP via `httpx`, client at `src/llm_client.py`
  - Auth: none (local)
  - Config: `LLM_BACKEND=ollama`, `OLLAMA_HOST`, `OLLAMA_MODEL` env vars
  - Fallback: auto-reverts to Gemini if Ollama unavailable (`OLLAMA_FALLBACK_TO_GEMINI`)

**Video Generation:**
- Kie.ai API — image-to-video and music generation
  - SDK/Client: custom async httpx client at `src/video_gen/kie_client.py` (video) and `src/product_studio/music_client.py` (Suno music)
  - Auth: `KIE_API_KEY` env var, `Authorization: Bearer` header
  - Base URL: `https://api.kie.ai/api/v1`
  - Video models: Hailuo 2.3, Seedance, Wan 2.6, Kling v2.1/3.0, Grok Imagine (configured in `config.py` `VIDEO_MODELS`)
  - Music: Suno V4 instrumental via `KieMusicClient` (`src/product_studio/music_client.py`)
  - Polling: exponential backoff, 5s initial → 30s max, 600s timeout
  - Budget cap: `VIDEO_DAILY_BUDGET_USD` (default $3.00/day)

**Image Generation (Local):**
- ComfyUI — local Stable Diffusion / Flux image generation
  - SDK/Client: custom WebSocket client at `src/image_gen/comfyui_client.py`
  - Auth: none (local)
  - Config: `COMFYUI_HOST=127.0.0.1`, `COMFYUI_PORT=8188`
  - Feature-flagged: `COMFYUI_ENABLED` (default `True`), used as primary backend when `IMAGE_BACKEND_PRIORITY=comfyui`
  - Workflows in `src/image_gen/workflows/`

**Trend Intelligence:**
- Google Trends — pytrends wrapper via `trendspyg`
  - SDK/Client: `trendspyg>=0.3.0`, used in `src/pipeline/agents/google_trends.py`
  - Auth: none (public)
  - Config: `PIPELINE_GOOGLE_TRENDS_GEO=BR`
- Gemini Web Trends — uses Gemini `google_search` grounding tool to discover BR viral topics
  - SDK/Client: `google-genai` (same as LLM), at `src/pipeline/agents/gemini_web_trends.py`
  - Auth: `GOOGLE_API_KEY`
- Reddit — RSS feeds parsed via `feedparser`
  - SDK/Client: `feedparser>=6.0.0`, no auth
  - Subreddits: `brasil`, `eu_nvr`, `DiretoDoZapZap`, `memes`, `dankmemes`, `meirl` (config in `config.py`)
- BlueSky — public AT Protocol API (no auth required)
  - SDK/Client: `urllib.request`, at `src/pipeline/agents/bluesky_trends.py`
  - Endpoint: `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`
  - Optional authenticated posting: `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` env vars
- YouTube RSS — public YouTube RSS feeds for trending content
  - SDK/Client: `feedparser`, at `src/pipeline/agents/youtube_rss.py`
  - Auth: none (public)

**Web Scraping:**
- Playwright — headless browser for asset collection
  - SDK/Client: `playwright>=1.40.0`, used in `src/scrape_assets.py`
  - Auth: none

## Data Storage

**Databases:**
- SQLite (development)
  - Driver: `aiosqlite>=0.20` (async)
  - Default path: `data/clipflow.db`
  - Connection: `sqlite+aiosqlite:///data/clipflow.db`
- MySQL (production)
  - Driver: `aiomysql>=0.2.0` (async)
  - Connection: `DATABASE_URL` env var (format: `mysql+aiomysql://user:pass@host/db`)
  - Default: `mysql+aiomysql://root:masterkey@localhost/memelab`
  - Pool: size 10, max overflow 20, recycle 3600s
- ORM: SQLAlchemy 2.0 async (`src/database/session.py`, models in `src/database/models.py`)
- Migrations: Alembic (`src/database/migrations/`, config `alembic.ini`)
- Schema: 16 tables including `characters`, `users`, `refresh_tokens`, `content_packages`, `video_jobs`, `product_ad_jobs`, `reels_jobs`, `usage_events`

**File Storage:**
- Local filesystem: generated images to `output/`, memes to `output/memes/`, backgrounds to `output/backgrounds_generated/`, videos to `output/videos/`, ads to `output/ads/`, reels to `output/reels/`
- GCS (Google Cloud Storage) — for Kie.ai video generation (images must be public URLs)
  - SDK/Client: `google-cloud-storage>=2.14.0`, at `src/video_gen/gcs_uploader.py`
  - Auth: `GOOGLE_APPLICATION_CREDENTIALS` (service account JSON path)
  - Config: `GCS_BUCKET_NAME` env var (default: `clipflow-video-uploads`)
  - Signed URL expiry: `GCS_SIGNED_URL_EXPIRY` (default 3600s)
  - Fallback: litterbox.catbox.moe (free temporary hosting, no auth, 1h expiry) if GCS not configured

**Caching:**
- None (no Redis or in-memory cache layer)
- SWR handles frontend client-side cache with auto-revalidation

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based auth (no third-party provider like Supabase or Auth0)
  - Implementation: `src/auth/service.py` — register, login, refresh, logout
  - Password hashing: bcrypt (`bcrypt>=5.0.0`, 12 rounds)
  - Tokens: JWT access token + refresh token rotation (`src/auth/jwt.py`, `cryptography>=42.0`)
  - Storage: `users` and `refresh_tokens` tables in DB
  - FastAPI dependency: `get_current_user` in `src/api/deps.py`
  - Routes: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`
  - Multi-tenant: each `Character`, `ContentPackage`, etc. is scoped to `user_id`

## Billing & Payments

**Payment Provider:**
- Stripe — subscription billing (Phase 17, not yet active by default)
  - SDK/Client: `stripe` Python package (imported lazily in `src/services/stripe_billing.py`)
  - Auth: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` env vars
  - Config: `STRIPE_PRO_PRICE_ID`, `STRIPE_ENTERPRISE_PRICE_ID` env vars
  - Plan tiers: Free / Pro ($19/mo) / Enterprise ($49/mo) — defined in `src/services/stripe_billing.py` `PLAN_TIERS`
  - Endpoints: `/billing/status`, `/billing/create-checkout`, `/billing/webhook`, `/billing/portal`
  - Webhook handler at `POST /billing/webhook` (no JWT, per design doc D-10)
  - Graceful degradation: all billing routes work without Stripe configured (returns Free tier info)

## Social Media Publishing

**Instagram Graph API:**
  - SDK/Client: custom async httpx client at `src/services/instagram_client.py`
  - Auth: OAuth 2.0 flow — `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID` env vars; OAuth redirect at `/instagram/callback`
  - API version: `v21.0` at `https://graph.facebook.com/v21.0`
  - Supports: single image posts, carousel (2–10 images), Reels (video + cover)
  - Insights: media and account insights via Graph API
  - OAuth flow: `/instagram/auth-url` → Facebook popup → `/instagram/callback`

**BlueSky (optional posting):**
  - SDK/Client: direct HTTP via `urllib.request`
  - Auth: `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` env vars (app password, not account password)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry or similar)

**Logs:**
- Python `logging` module, structured via `src/api/log_sanitizer.py` (redacts secrets from log output)
- Log format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s` (set in `src/api/app.py`)
- Logger namespaces: `clip-flow.api`, `clip-flow.llm`, `clip-flow.kie_client`, `clip-flow.instagram`, etc.

## CI/CD & Deployment

**Hosting:**
- Local development: FastAPI at `localhost:8000`, Next.js at `localhost:3000`
- Colab support: `pyngrok` for public URL tunneling (`start_server()` in `src/api/app.py`)
- No Vercel or cloud deployment config detected

**CI Pipeline:**
- None detected (no GitHub Actions, CircleCI, etc.)

## Webhooks & Callbacks

**Incoming:**
- `POST /billing/webhook` — Stripe payment events (no JWT auth, webhook secret validation)
- `GET /instagram/callback` — Facebook OAuth redirect with authorization code

**Outgoing:**
- Kie.ai polling (pull-based, not push) — `src/video_gen/kie_client.py`
- Instagram Graph API publishing calls — `src/services/instagram_client.py`
- Gemini API calls — `src/llm_client.py`, `src/image_gen/gemini_client.py`

## Environment Configuration

**Required env vars:**
- `GOOGLE_API_KEY` — Gemini API (LLM, image gen, TTS, transcription)

**Optional env vars (grouped by feature):**
- Database: `DATABASE_URL`
- Video generation: `KIE_API_KEY`, `VIDEO_ENABLED=true`, `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`
- LLM backend: `LLM_BACKEND`, `OLLAMA_MODEL`, `OLLAMA_HOST`
- Billing: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`, `STRIPE_ENTERPRISE_PRICE_ID`, `STRIPE_PUBLISHABLE_KEY`
- Instagram: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`
- BlueSky: `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`
- Image backend: `IMAGE_BACKEND_PRIORITY` (`comfyui` | `gemini`)
- Cost control: `GEMINI_MODEL_LITE`, `GEMINI_MODEL_NORMAL`, `COST_MODE`, `VIDEO_DAILY_BUDGET_USD`
- Reels: `REELS_ENABLED=true`
- Product Ads: `ADS_ENABLED=true`

**Secrets location:**
- `.env` at project root (gitignored)
- `.env.example` at project root documents all vars with placeholder values

---

*Integration audit: 2026-03-30*
