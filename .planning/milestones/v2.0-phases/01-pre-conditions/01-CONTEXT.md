# Phase 1: Pre-Conditions - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three blocking pre-conditions so that credentialed requests work (CORS), Gemini Image generation succeeds (model names), and sensitive data never leaks in logs (masking). This phase touches `src/api/app.py`, `src/image_gen/gemini_client.py`, and logging infrastructure. No new features — only fixes to unblock Phases 2+.

</domain>

<decisions>
## Implementation Decisions

### CORS Configuration
- **D-01:** Replace `allow_origins=["*"]` with explicit localhost origins: `["http://localhost:3000", "http://127.0.0.1:3000"]`. Keep `allow_credentials=True`.
- **D-02:** No env var for additional origins in v1 — add later when production domain is known. Hardcoded localhost is sufficient.

### Gemini Image Model Resolution
- **D-03:** Auto-discover valid image-capable models on API startup via `client.models.list()`. Filter for image generation capability.
- **D-04:** Replace hardcoded `MODELOS_IMAGEM` list with dynamically discovered models. Log available image models at startup for debugging.
- **D-05:** If no image-capable models found at startup, log a WARNING but don't crash — the fallback chain (ComfyUI → static) handles this at generation time.

### Log Masking
- **D-06:** Implement a full log sanitizer as FastAPI middleware. Regex-based scanner that catches API keys, tokens, passwords, and DATABASE_URL credentials in all log output.
- **D-07:** Pattern targets: `GOOGLE_API_KEY`, `BLUESKY_APP_PASSWORD`, `INSTAGRAM_ACCESS_TOKEN`, `DATABASE_URL` password component, and any string matching common key patterns (sk-*, ghp_*, Bearer tokens).
- **D-08:** Masking format: show last 4 chars only (e.g., `***abcd`). For DATABASE_URL, mask password portion only.

### Health Endpoint
- **D-09:** `GET /health` returns: overall status, Gemini model validation result (valid model name or error), and DB connection check (ping).
- **D-10:** Health endpoint remains unauthenticated (exempt from future JWT protection in Phase 4).

### Claude's Discretion
- Implementation details of the log sanitizer middleware (regex patterns, middleware placement)
- How to structure the `list_models()` call (sync at startup vs lazy on first request)
- Health endpoint response schema

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CORS Fix
- `src/api/app.py` §67-73 — Current broken CORS middleware config (allow_origins=["*"] + allow_credentials=True)

### Gemini Image Model Fix
- `src/image_gen/gemini_client.py` §42-47 — Current `MODELOS_IMAGEM` list with likely invalid model names
- `src/image_gen/gemini_client.py` — Full GeminiImageClient class, understand generate_image() flow and where model name is used

### Log Masking
- `src/pipeline/async_orchestrator.py` §209-229 — `_log_config_summary()` that logs pipeline config
- `src/api/app.py` §42 — DATABASE_URL logging at startup (already partially masked with split('@'))
- `.planning/codebase/CONCERNS.md` §47-51 — Security concern: API key exposure in logs

### Health Endpoint
- `src/api/app.py` §88-103 — Existing `/llm/status` endpoint (pattern reference for health check)

### Requirements
- `.planning/REQUIREMENTS.md` — PRE-01 (CORS), PRE-02 (Gemini models), PRE-03 (log masking)
- `.planning/ROADMAP.md` §29-38 — Phase 1 success criteria (4 conditions that must be TRUE)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/llm_client.py:_get_client()` — Existing Gemini client singleton, use for `list_models()` call
- `src/api/app.py:llm_status()` endpoint — Pattern for system status endpoints
- `src/api/app.py:lifespan()` — Startup hook where model validation should run

### Established Patterns
- FastAPI middleware pattern already used for CORSMiddleware — add log sanitizer as another middleware
- Logger naming: `clip-flow.{module}` convention
- Config values centralized in `config.py` — Gemini model names should follow this pattern

### Integration Points
- `CORSMiddleware` in `src/api/app.py` — direct replacement of origins parameter
- `MODELOS_IMAGEM` in `src/image_gen/gemini_client.py` — replace with validated list from startup
- `lifespan()` in `src/api/app.py` — add model validation step
- New `/health` route in `src/api/app.py` — alongside existing `/llm/status`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for all three fixes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-pre-conditions*
*Context gathered: 2026-03-23*
