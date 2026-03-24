# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.14 - Backend pipeline, CLI, API, agents, image composition
- TypeScript / Next.js 15 - Frontend (memeLab dashboard in `memelab/`)
- YAML - Configuration (`config/themes.yaml`)

**Secondary:**
- JSON - Workflow definitions for ComfyUI (`src/image_gen/workflows/`)

## Runtime

**Environment:**
- Python 3.14 with pip package manager
- Node.js / npm - Frontend build and development

**Package Manager:**
- `pip` (Python) - Lockfile: `requirements.txt`
- `npm` / `pnpm` - Frontend dependencies

## Frameworks

**Core:**
- FastAPI 0.115.0+ - REST API and route handlers (`src/api/`)
- Uvicorn 0.34.0+ - ASGI server for FastAPI
- Next.js 15 - Frontend dashboard (`memelab/`)

**LLM & Image Generation:**
- google-genai >=1.0.0 - Google Gemini API (text generation, image generation, analysis)
- Pillow >=10.0.0 - Image composition and manipulation (1080x1350 Instagram posts)
- ComfyUI (local) - Flux Dev GGUF image generation fallback (`localhost:8188`)

**Scheduling & Async:**
- APScheduler >=3.10.0 - Task scheduling and automation
- asyncio (stdlib) - Async orchestration and concurrency
- SQLAlchemy >=2.0 - Async ORM (SQLAlchemy 2.0 with async support)

**Testing:**
- pytest - Test framework (configured with `.pytest_cache/`)
- aiosqlite >=0.20 - SQLite async driver for testing

**Build/Dev:**
- Alembic >=1.13 - Database migrations (`alembic.ini`)
- pyngrok >=7.0.0 - Public tunnel for API (optional local testing)

## Key Dependencies

**Critical:**
- google-genai - Gemini API for phrase generation, trend analysis, image generation with visual references
- Pillow - Image composition: overlay, vignette, glow, text stroke, watermark on 1080x1350 canvas
- trendspyg >=0.3.0 - Google Trends RSS feed parser (replaces pytrends, archived 2025)
- feedparser >=6.0.0 - RSS feed parsing (Reddit, Sensacionalista, YouTube channels, etc.)
- sqlalchemy >=2.0 - Async ORM with 10 database tables (MySQL + SQLite compatible)

**Web & HTTP:**
- fastapi >=0.115.0 - REST API framework with automatic Swagger docs
- uvicorn >=0.34.0 - ASGI server (host: 127.0.0.1 on Windows, port: 8000)
- httpx >=0.27.0 - Async HTTP client (Ollama, BlueSky API, HackerNews, Instagram Graph API)
- requests >=2.31.0 - Sync HTTP client (ComfyUI REST calls)
- websocket-client >=1.6.0 - WebSocket for ComfyUI progress tracking

**Infrastructure & Utilities:**
- aiomysql >=0.2.0 - Async MySQL driver (primary DB on branch estrutura-agents)
- aiosqlite >=0.20 - Async SQLite driver (development/testing)
- python-dotenv >=1.0.0 - Environment variable loading (.env)
- beautifulsoup4 >=4.12.0 - HTML parsing (unused, available for future scraping)
- playwright >=1.40.0 - Browser automation (unused, available for dynamic scraping)
- pyyaml >=6.0 - YAML parsing (`config/themes.yaml` for theme definitions)
- cryptography >=42.0 - Password hashing and encryption (dependency for other packages)

## Configuration

**Environment Variables (.env):**
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

**Build Configuration:**
- `alembic.ini` - Database migration configuration
- `config.py` - Centralized settings: IMAGE_WIDTH=1080, IMAGE_HEIGHT=1350, WATERMARK_TEXT="@magomestre420", font, colors, pipeline intervals
- `config/themes.yaml` - 13+ visual themes (sabedoria, cafe, tecnologia, etc.) with situacao/acao/cenario
- `tsconfig.json` - TypeScript configuration (frontend)
- `.env.example` - Template for required environment variables

## Platform Requirements

**Development:**
- Windows 11 Pro (primary), Linux compatible
- Python 3.14+
- Node.js 18+
- MySQL server (or SQLite for dev)
- ComfyUI server (optional, localhost:8188) with:
  - Flux Dev GGUF Q4_K_S model
  - LoRA trained on Mago Mestre references
  - RTX 4060 Ti 8GB VRAM (with --lowvram flag)

**Production:**
- Python 3.14+
- MySQL database (aiomysql async driver)
- Google Gemini API key (quota based on usage)
- Optional: ComfyUI local instance or Gemini Image API calls
- Optional: Instagram Business Account for publishing (Meta Graph API)
- Optional: Ollama server for cost-free local text generation

**Hosting Target:**
- Linux (Ubuntu 22.04+) for deployment
- Docker-compatible (can containerize FastAPI + Alembic)
- API: runs on port 8000, CORS enabled

---

*Stack analysis: 2026-03-23*
