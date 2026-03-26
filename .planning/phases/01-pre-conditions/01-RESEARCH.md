# Phase 1: Pre-Conditions - Research

**Researched:** 2026-03-23
**Domain:** FastAPI CORS, Google Gemini model discovery, Python log sanitization
**Confidence:** HIGH

## Summary

Phase 1 fixes three blocking pre-conditions: (1) CORS misconfiguration that prevents credentialed requests from the Next.js frontend, (2) hardcoded Gemini image model names that may be invalid/deprecated, and (3) API key exposure in logs. All three are well-understood problems with standard solutions.

The CORS fix is a one-line change (replace wildcard with explicit origins). The Gemini model fix requires using `client.models.list()` from the `google-genai` SDK to auto-discover valid image-capable models at startup. The log masking requires a custom `logging.Filter` subclass that intercepts all log records and redacts secrets via regex. A `/health` endpoint ties the model validation into observable status.

**Primary recommendation:** Implement all three fixes in `src/api/app.py` (CORS + health + lifespan model validation) and `src/image_gen/gemini_client.py` (dynamic model list), plus a new log sanitizer module. No new dependencies required -- all solutions use stdlib `logging` and existing `google-genai` SDK.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Replace `allow_origins=["*"]` with explicit localhost origins: `["http://localhost:3000", "http://127.0.0.1:3000"]`. Keep `allow_credentials=True`.
- **D-02:** No env var for additional origins in v1 -- hardcoded localhost is sufficient.
- **D-03:** Auto-discover valid image-capable models on API startup via `client.models.list()`. Filter for image generation capability.
- **D-04:** Replace hardcoded `MODELOS_IMAGEM` list with dynamically discovered models. Log available image models at startup for debugging.
- **D-05:** If no image-capable models found at startup, log a WARNING but don't crash -- the fallback chain (ComfyUI -> static) handles this at generation time.
- **D-06:** Implement a full log sanitizer as FastAPI middleware. Regex-based scanner that catches API keys, tokens, passwords, and DATABASE_URL credentials in all log output.
- **D-07:** Pattern targets: `GOOGLE_API_KEY`, `BLUESKY_APP_PASSWORD`, `INSTAGRAM_ACCESS_TOKEN`, `DATABASE_URL` password component, and any string matching common key patterns (sk-*, ghp_*, Bearer tokens).
- **D-08:** Masking format: show last 4 chars only (e.g., `***abcd`). For DATABASE_URL, mask password portion only.
- **D-09:** `GET /health` returns: overall status, Gemini model validation result (valid model name or error), and DB connection check (ping).
- **D-10:** Health endpoint remains unauthenticated (exempt from future JWT protection in Phase 4).

### Claude's Discretion
- Implementation details of the log sanitizer middleware (regex patterns, middleware placement)
- How to structure the `list_models()` call (sync at startup vs lazy on first request)
- Health endpoint response schema

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRE-01 | CORS configurado com origins especificos (nao wildcard) para suportar credentials | CORS section: exact code pattern for FastAPI CORSMiddleware with explicit origins |
| PRE-02 | Gemini Image model names validados via list_models() e corrigidos (fix 400) | Gemini Model Discovery section: `client.models.list()` API, filtering by supported_actions |
| PRE-03 | API keys mascaradas em todos os logs (fix exposicao existente) | Log Masking section: custom logging.Filter with regex patterns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | >=1.0.0 | Gemini client + `client.models.list()` for model discovery | Already in project; provides `models.list()` API |
| fastapi | >=0.115.0 | CORSMiddleware config, health endpoint, lifespan hook | Already in project |
| logging (stdlib) | Python 3.14 | Custom `logging.Filter` for log sanitization | Standard approach; no external deps needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | Python 3.14 | Regex patterns for secret masking | Inside the log filter |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom logging.Filter | logredactor PyPI package | Extra dependency for simple task; custom filter is ~30 lines |
| Custom logging.Filter | Pydantic SecretStr | Only works for Pydantic models, not arbitrary log messages |

**Installation:** No new packages needed. All solutions use existing dependencies.

## Architecture Patterns

### Recommended Changes Structure
```
src/
  api/
    app.py                # CORS fix (line 69), lifespan model validation, /health endpoint
    log_sanitizer.py      # NEW: SensitiveDataFilter class + setup function
  image_gen/
    gemini_client.py      # Replace hardcoded MODELOS_IMAGEM with dynamic discovery
```

### Pattern 1: CORS with Explicit Origins
**What:** Replace wildcard `allow_origins=["*"]` with specific localhost origins when `allow_credentials=True`.
**When to use:** Always when cookies or Authorization headers cross origins.
**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/cors/
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why the current code breaks:** The CORS spec forbids `Access-Control-Allow-Origin: *` when `Access-Control-Allow-Credentials: true` is set. Browsers reject the response entirely. FastAPI's Starlette CORSMiddleware silently allows this misconfiguration on the server side but the browser enforces the restriction.

### Pattern 2: Gemini Model Discovery at Startup
**What:** Use `client.models.list()` in the FastAPI lifespan to discover valid image models.
**When to use:** At API startup, inside the existing `lifespan()` async context manager.
**Example:**
```python
# Source: https://googleapis.github.io/python-genai/
from src.llm_client import _get_client

def discover_image_models() -> list[str]:
    """Descobre modelos com capacidade de geracao de imagem."""
    client = _get_client()
    image_models = []
    for model in client.models.list():
        # model.supported_actions ou model.supported_generation_methods
        # contém "generateContent" para modelos de imagem nativa
        if hasattr(model, 'supported_actions'):
            if 'generateImage' in model.supported_actions or 'generateContent' in model.supported_actions:
                # Filtrar por nomes que contenham "image" no ID
                if 'image' in model.name.lower():
                    image_models.append(model.name)
    return image_models
```

**Key insight:** The `client.models.list()` call is synchronous in the google-genai SDK. Inside the async `lifespan()`, wrap with `asyncio.to_thread()` to avoid blocking the event loop, consistent with the project's existing pattern (SyncAgentAdapter).

### Pattern 3: Log Sanitizer as logging.Filter
**What:** Custom `logging.Filter` that redacts secrets from log messages before they reach any handler.
**When to use:** Attached to the root logger at application startup (before any other logging occurs).
**Example:**
```python
# Source: https://dev.to/camillehe1992/mask-sensitive-data-using-python-built-in-logging-module-45fa
import re
import logging
import os

class SensitiveDataFilter(logging.Filter):
    """Filtra dados sensiveis de todas as mensagens de log."""

    def __init__(self):
        super().__init__()
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Constroi patterns de regex para dados sensiveis."""
        patterns = []
        # Valores de env vars conhecidas
        for key in ["GOOGLE_API_KEY", "BLUESKY_APP_PASSWORD", "INSTAGRAM_ACCESS_TOKEN"]:
            value = os.getenv(key, "")
            if value and len(value) > 4:
                escaped = re.escape(value)
                patterns.append((re.compile(escaped), f"***{value[-4:]}"))

        # DATABASE_URL password: mysql+aiomysql://user:PASSWORD@host/db
        db_url = os.getenv("DATABASE_URL", "")
        if ":" in db_url and "@" in db_url:
            import urllib.parse
            # Extrair password do URL
            try:
                parsed = urllib.parse.urlparse(db_url.replace("+aiomysql", "").replace("+aiosqlite", ""))
                if parsed.password:
                    escaped_pw = re.escape(parsed.password)
                    patterns.append((re.compile(escaped_pw), f"***{parsed.password[-4:]}"))
            except Exception:
                pass

        # Padroes genericos
        patterns.append((re.compile(r'sk-[A-Za-z0-9]{20,}'), '***'))
        patterns.append((re.compile(r'ghp_[A-Za-z0-9]{36,}'), '***'))
        patterns.append((re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}'), 'Bearer ***'))

        return patterns

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self._patterns:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            # Tambem sanitizar args (usados em % formatting)
            if isinstance(record.args, dict):
                record.args = {k: self._sanitize(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize(a) for a in record.args)
        return True

    def _sanitize(self, value):
        if isinstance(value, str):
            for pattern, replacement in self._patterns:
                value = pattern.sub(replacement, value)
        return value
```

### Pattern 4: Health Endpoint with Model Validation
**What:** `GET /health` returning system status including Gemini model validation and DB connectivity.
**When to use:** Unauthenticated endpoint for monitoring.
**Example:**
```python
@app.get("/health", tags=["System"])
async def health():
    """Health check: DB + Gemini model validation."""
    db_ok = False
    try:
        from src.database.session import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        db_error = str(e)

    return {
        "status": "healthy" if db_ok and app.state.gemini_image_models else "degraded",
        "database": {"connected": db_ok},
        "gemini_image": {
            "models_available": len(app.state.gemini_image_models),
            "models": app.state.gemini_image_models,
            "validation": "ok" if app.state.gemini_image_models else "no image models found",
        },
    }
```

### Anti-Patterns to Avoid
- **Wildcard CORS with credentials:** Never combine `allow_origins=["*"]` with `allow_credentials=True`. Browsers block this per the CORS spec.
- **Hardcoded model names:** Gemini model names change frequently (gemini-2.0-flash already deprecated for new users). Always validate at runtime.
- **Logging secrets then trying to scrub output:** The filter must be attached BEFORE any logging occurs. Add it in the `logging.basicConfig()` call or immediately after.
- **Blocking async event loop with models.list():** The google-genai `models.list()` is sync. Use `asyncio.to_thread()` inside the async lifespan.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CORS handling | Custom middleware | FastAPI's built-in CORSMiddleware | Handles preflight OPTIONS, Vary headers, all edge cases |
| Model enumeration | Scraping docs for model names | `client.models.list()` API | Always current, handles deprecations automatically |
| Log formatting | Custom print statements | Python `logging.Filter` | Catches ALL log output from all loggers, not just yours |

## Common Pitfalls

### Pitfall 1: CORS Preflight Failures
**What goes wrong:** Even with correct origins, `OPTIONS` preflight requests fail silently.
**Why it happens:** Forgetting `allow_methods=["*"]` or `allow_headers=["*"]`, or the middleware is added after routes are registered.
**How to avoid:** Add CORSMiddleware immediately after creating the FastAPI app, before `include_router()`. Keep `allow_methods=["*"]` and `allow_headers=["*"]`.
**Warning signs:** `fetch()` from frontend gets a network error (no CORS headers in response).

### Pitfall 2: models.list() Returns Models Without Image Capability
**What goes wrong:** Iterating all models includes text-only models, causing confusion.
**Why it happens:** The `models.list()` API returns ALL available models. Need to filter for image generation capability.
**How to avoid:** Filter by model name containing "image" in the ID, and/or check `supported_generation_methods` or `supported_actions` attributes. The current valid image model names (as of March 2026) are: `gemini-2.5-flash-image`, `gemini-3.1-flash-image-preview`, `gemini-3-pro-image-preview`.
**Warning signs:** `MODELOS_IMAGEM` list has 50+ entries after discovery.

### Pitfall 3: Log Filter Not Applied to All Handlers
**What goes wrong:** Secrets still appear in some log outputs.
**Why it happens:** Filter attached to a specific logger, not the root logger. Or attached to handler, not logger.
**How to avoid:** Attach the filter to the root logger (`logging.getLogger().addFilter(filter)`) so ALL loggers inherit it. Apply BEFORE any `logger.info()` calls in module-level code.
**Warning signs:** Secrets visible in uvicorn access logs but not in application logs.

### Pitfall 4: record.args Not Sanitized
**What goes wrong:** Secrets passed as `logger.info("Key: %s", api_key)` bypass `record.msg` sanitization.
**Why it happens:** Python logging uses `msg % args` lazy formatting. The args aren't in `msg` yet when the filter runs.
**How to avoid:** Sanitize both `record.msg` AND `record.args` in the filter (see code example above). Also consider overriding `getMessage()` but filter approach is simpler.
**Warning signs:** Secrets appear when using `%s` formatting but not f-strings.

### Pitfall 5: Gemini Model Name Format Variations
**What goes wrong:** `models.list()` returns names like `models/gemini-2.5-flash-image` but code expects `gemini-2.5-flash-image`.
**Why it happens:** The API returns full resource paths with `models/` prefix.
**How to avoid:** Strip the `models/` prefix when storing discovered names, or be consistent about using full paths.
**Warning signs:** Model name comparison fails; generate call returns 404.

## Code Examples

### Current CORS Config (BROKEN - line 67-73 of app.py)
```python
# BROKEN: wildcard + credentials = browser rejection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # <-- THIS IS THE PROBLEM
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Current MODELOS_IMAGEM (POSSIBLY STALE - line 42-47 of gemini_client.py)
```python
# Some of these may be invalid/deprecated
MODELOS_IMAGEM = [
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-exp-image-generation",    # likely deprecated
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
]
```

### Current lifespan() Hook (line 34-52 of app.py)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.database.session import init_db
    from config import DATABASE_URL
    from src.services.scheduler_worker import start_scheduler, stop_scheduler
    await init_db()
    logger.info(f"Banco de dados inicializado: {DATABASE_URL.split('@')[-1]}")
    start_scheduler(interval_seconds=60)
    yield
    stop_scheduler()
```

### Existing Client Singleton (llm_client.py)
```python
from google import genai
_client: genai.Client | None = None

def _get_client() -> genai.Client:
    global _client
    if not _api_key:
        raise ValueError("GOOGLE_API_KEY nao configurada.")
    if _client is None:
        _client = genai.Client(api_key=_api_key)
    return _client
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-generativeai (deprecated) | google-genai >= 1.0.0 | 2025 | New SDK, different API surface (`genai.Client` vs `genai.configure()`) |
| gemini-2.0-flash for image | gemini-2.5-flash-image, gemini-3.1-flash-image-preview | 2025-2026 | Old model deprecated June 2026, must use new names |
| Hardcoded model lists | `client.models.list()` discovery | Always available | Models change frequently; dynamic discovery is resilient |

**Deprecated/outdated:**
- `gemini-2.0-flash-exp-image-generation`: Likely deprecated for new users as of March 2026. Retirement June 2026.
- `google-generativeai` package: Fully deprecated, replaced by `google-genai`.

## Open Questions

1. **Exact model attribute for image generation capability**
   - What we know: `models.list()` returns model objects with `name` and `supported_actions`/`supported_generation_methods` fields
   - What's unclear: The exact attribute name to filter for image generation (varies between SDK versions)
   - Recommendation: At implementation time, inspect one model object (`print(dir(model))`) to confirm attribute names. Fall back to name-based filtering (`"image" in model.name.lower()`) as reliable heuristic.

2. **models.list() pagination**
   - What we know: The API may return paginated results
   - What's unclear: Whether the SDK handles pagination automatically or requires manual iteration
   - Recommendation: The SDK's `list()` returns an iterator that handles pagination. Just iterate fully.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (no config file, runs via `python -m pytest`) |
| Config file | none -- see Wave 0 |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRE-01 | CORS returns correct headers for credentialed request from localhost:3000 | unit | `python -m pytest tests/test_preconditions.py::test_cors_credentials -x` | Wave 0 |
| PRE-02 | Gemini model discovery returns at least one image model (or graceful empty list) | unit | `python -m pytest tests/test_preconditions.py::test_model_discovery -x` | Wave 0 |
| PRE-03 | Log output does not contain raw API key values | unit | `python -m pytest tests/test_preconditions.py::test_log_sanitizer -x` | Wave 0 |
| PRE-01/09 | /health endpoint returns 200 with expected schema | unit | `python -m pytest tests/test_preconditions.py::test_health_endpoint -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_preconditions.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_preconditions.py` -- covers PRE-01, PRE-02, PRE-03
- [ ] `pytest.ini` or `pyproject.toml` [tool.pytest.ini_options] -- configure test discovery
- [ ] Framework install verification: `python -m pytest --version`

## Project Constraints (from CLAUDE.md)

- **Language:** Python 3.14, portugues brasileiro for comments/logs/prompts
- **Stack:** FastAPI + uvicorn, google-genai SDK, no new frameworks
- **Logger naming:** `clip-flow.{module}` convention
- **Config:** Centralized in `config.py`
- **Host:** 127.0.0.1 (Windows does not resolve 0.0.0.0)
- **Image fallback chain:** Gemini -> ComfyUI -> static (never crash on missing backend)
- **No text in backgrounds:** Gemini prompt must prohibit text rendering
- **GSD Workflow:** All changes through GSD commands

## Sources

### Primary (HIGH confidence)
- [FastAPI CORS docs](https://fastapi.tiangolo.com/tutorial/cors/) -- CORS with credentials behavior, explicit origins requirement
- [Google Gen AI SDK docs](https://googleapis.github.io/python-genai/) -- `client.models.list()` API
- [Gemini API models page](https://ai.google.dev/gemini-api/docs/models) -- Current model names and deprecation schedule
- [Gemini Image Generation docs](https://ai.google.dev/gemini-api/docs/image-generation) -- Valid image model names: gemini-2.5-flash-image, gemini-3.1-flash-image-preview, gemini-3-pro-image-preview

### Secondary (MEDIUM confidence)
- [DEV.to logging filter article](https://dev.to/camillehe1992/mask-sensitive-data-using-python-built-in-logging-module-45fa) -- SensitiveDataFilter pattern verified against Python logging docs
- [Google Developers Blog - Gemini 2.5 Flash Image](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/) -- "Nano Banana" model details

### Tertiary (LOW confidence)
- models.list() attribute names for filtering image capability -- needs runtime verification at implementation time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, no new deps
- Architecture: HIGH - CORS fix is documented behavior, log filter is stdlib pattern
- Pitfalls: HIGH - CORS+credentials is well-documented browser behavior; model name format is verified from docs
- Gemini model filtering: MEDIUM - exact attribute names need runtime verification

**Research date:** 2026-03-23
**Valid until:** 2026-04-07 (Gemini model names may change; CORS/logging patterns are stable)
