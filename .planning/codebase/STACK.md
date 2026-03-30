# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python 3.12+ - Backend API, image/video pipeline, ML orchestration (`src/`)
- TypeScript 5.8 - Frontend Next.js app (`memelab/src/`)

**Secondary:**
- SQL - Database schema via SQLAlchemy ORM + Alembic migrations

## Runtime

**Backend Environment:**
- Python (CPython) — no explicit version pin in pyproject.toml; SQLAlchemy 2.0+ union types require 3.10+
- Async throughout: `asyncio`, `async/await` on all FastAPI routes, SQLAlchemy async engine

**Frontend Environment:**
- Node.js (managed via npm)
- Lockfile: `memelab/package-lock.json` present

**Package Manager:**
- Python: pip (requirements.txt at root — `requirements.txt`)
- Node: npm (`memelab/package.json`, `memelab/package-lock.json`)

## Frameworks

**Backend:**
- FastAPI `>=0.115.0` — REST API server, 14 route modules, CORS middleware, lifespan events
- SQLAlchemy `>=2.0` — async ORM with `mapped_column` declarative style, 16 DB tables
- Alembic `>=1.13` — DB migration tooling (`src/database/migrations/`)
- Uvicorn `>=0.34.0` — ASGI server (run via `python -m src.api --port 8000`)
- APScheduler `>=3.10.0` — in-process job scheduler for publish queue (60s interval)

**Frontend:**
- Next.js `^15.3.3` — App Router, all routes in `memelab/src/app/(app)/`
- React `^19.1.0` + React DOM `^19.1.0`
- No server-side API routes — Next.js rewrites all `/api/*` → `http://127.0.0.1:8000/*`

**Testing:**
- Vitest `^4.1.1` — frontend test runner (`memelab/vitest.config.ts`)
- pytest — backend test runner (`tests/`, config in `pyproject.toml`)
- @testing-library/react `^16.3.2` — React component testing
- jsdom `^29.0.1` — DOM environment for Vitest

**Build/Dev:**
- Tailwind CSS `^4.1.8` via `@tailwindcss/postcss` — no `tailwind.config.js`; design tokens in `memelab/src/app/globals.css` using `@theme`
- ESLint `^9.27.0` + `eslint-config-next`
- TypeScript strict compilation (`memelab/tsconfig.json`)

## Key Dependencies

**Backend Critical:**
- `google-genai>=1.0.0` — primary LLM and image gen SDK (Gemini 2.5 Flash, TTS, image models)
- `google-cloud-storage>=2.14.0` — GCS for Kie.ai public image URL uploads
- `httpx>=0.27.0` — async HTTP client for Kie.ai, Ollama, external APIs
- `Pillow>=10.0.0` — image compositing (text overlay, watermark, vignette, meme assembly)
- `rembg[cpu]>=2.0.0` — background removal for product studio (`src/product_studio/bg_remover.py`)
- `sqlalchemy>=2.0` + `aiosqlite>=0.20` + `aiomysql>=0.2.0` — async DB, supports both SQLite (dev) and MySQL (prod)
- `bcrypt>=5.0.0` — password hashing for custom auth
- `cryptography>=42.0` — JWT signing (`src/auth/jwt.py`)

**Backend Infrastructure:**
- `playwright>=1.40.0` — headless browser scraping (asset collection in `src/scrape_assets.py`)
- `feedparser>=6.0.0` — RSS feed parsing (trends agents)
- `trendspyg>=0.3.0` — Google Trends wrapper (`src/pipeline/agents/google_trends.py`)
- `beautifulsoup4>=4.12.0` — HTML parsing for scraping
- `pyngrok>=7.0.0` — ngrok tunnel for Colab/public API exposure
- `pyyaml>=6.0` — config file parsing
- `APScheduler>=3.10.0` — publish scheduler

**Frontend Critical:**
- `swr ^2.3.3` — data fetching with auto-revalidation; all hooks in `memelab/src/hooks/use-api.ts`
- `@radix-ui/*` — 9 primitive packages (Dialog, DropdownMenu, Progress, ScrollArea, Select, Separator, Slot, Switch, Tabs, Tooltip)
- `framer-motion ^12.35.2` — animation in step components and UI transitions
- `lucide-react ^0.513.0` — icon set
- `class-variance-authority ^0.7.1` + `tailwind-merge ^3.3.0` + `clsx ^2.1.1` — shadcn/ui component pattern
- `@xyflow/react ^12.10.1` — React Flow (imported but pipeline diagram uses custom SVG)
- `recharts ^3.8.1` — charts in dashboard
- `mermaid ^11.6.0` — imported but replaced by custom SVG diagram

## Configuration

**Environment:**
- Backend: `.env` at project root, loaded via `python-dotenv` in `config.py` and `src/llm_client.py`
- Required: `GOOGLE_API_KEY`
- Optional: `DATABASE_URL`, `KIE_API_KEY`, `STRIPE_SECRET_KEY`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID`, `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`, `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `LLM_BACKEND`, `OLLAMA_MODEL`
- `.env.example` at project root documents all vars

**Database:**
- Default dev: `sqlite+aiosqlite:///data/clipflow.db`
- Default prod: `mysql+aiomysql://root:masterkey@localhost/memelab`
- Controlled by `DATABASE_URL` env var in `config.py`

**Build:**
- Frontend: `memelab/next.config.ts` — configures API proxy rewrite and image remote patterns
- Backend: `alembic.ini` — migration scripts in `src/database/migrations/`

## Platform Requirements

**Development:**
- FFmpeg installed system-wide (video assembly in `src/reels_pipeline/video_builder.py`, `src/product_studio/pipeline.py`, `src/video_gen/legend_renderer.py`)
- ComfyUI server at `127.0.0.1:8188` (optional — feature-flagged via `COMFYUI_ENABLED`)
- Ollama at `http://localhost:11434` (optional — feature-flagged via `LLM_BACKEND=ollama`)

**Production:**
- MySQL database (aiomysql driver)
- GCS bucket for video pipeline image hosting (`GCS_BUCKET_NAME`)
- Google service account credentials (`GOOGLE_APPLICATION_CREDENTIALS`) for GCS
- FastAPI on port 8000, Next.js on port 3000

---

*Stack analysis: 2026-03-30*
