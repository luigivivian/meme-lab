# Codebase Concerns

**Analysis Date:** 2026-03-23

## Tech Debt

**Placeholder/Stub Agents (Unimplemented APIs):**
- Issue: 4 agent stubs exist but provide no real functionality — TikTok, Instagram, Twitter/X, Facebook API integrations are marked as requiring API keys but not implemented
- Files: `src/pipeline/agents/tiktok_trends.py`, `src/pipeline/agents/instagram_explore.py`, `src/pipeline/agents/twitter_x.py`, `src/pipeline/agents/facebook.py` (if exists)
- Impact: Pipeline shows 9 agents in `/agents` endpoint but only 6 are truly active (~227 events). Users cannot fetch TikTok/Instagram/Twitter trends, limiting data sources
- Fix approach: Either fully implement stub agents with real API integration, or remove them from the agent registry to avoid confusion. Prioritize based on usage patterns

**Incomplete Publishing Platform Integration:**
- Issue: Instagram and TikTok publishing endpoints are marked as TODO in source code, no actual API integration exists
- Files: `src/services/publisher.py:149, 167` (TODO comments), `src/api/routes/publishing.py:177` (TODO comment)
- Impact: Users cannot auto-publish to Instagram or TikTok. Schedule queue exists but publishing is not functional beyond database storage
- Fix approach: Implement Instagram Graph API client (requires app approval), defer TikTok integration pending API availability

**Gemini Web Grounding Incompatibility:**
- Issue: Gemini's Google Search grounding tool (`types.Tool(google_search=...)`) is incompatible with `response_mime_type="application/json"`, forcing regex-based JSON parsing from text
- Files: `src/pipeline/agents/gemini_web_trends.py` (GeminiWebTrendsAgent)
- Impact: JSON parsing fragile — if Gemini text format changes, parsing breaks. No structured validation of trend data quality
- Fix approach: Implement custom JSON parser with fallback, add validation schema, consider using Claude API as alternative (supports tool_choice + JSON mode)

## Known Bugs

**Missing `get_queue()` Method Reference:**
- Symptoms: `src/api/routes/publishing.py:69` calls `service.get_queue()` but method may not exist or be incomplete
- Files: `src/api/routes/publishing.py`, `src/services/publisher.py`
- Trigger: `GET /publishing/queue/summary` endpoint
- Workaround: Check if method exists; if missing, implement platform/status grouping in route directly

**Potential Image Generation Result Loss:**
- Issue: `GeminiImageClient.generate_image()` returns `None` on failure but doesn't persist error state to database
- Files: `src/image_gen/gemini_client.py:843-845` (returns None silently)
- Impact: Failed image generations are logged but not tracked in `GeneratedImages` table. No audit trail of failures
- Fix approach: Log failures with full error context to database, update `ImageWorker` to record failed attempts

**Database Migration Column Type Mismatch (MySQL):**
- Issue: `Text` and `JSON` columns in SQLAlchemy models don't have `server_default` (MySQL requirement for NOT NULL without default). Fallback to ORM defaults works but creates inconsistency
- Files: `src/database/models.py:39, 42, 47-48, 57-58` (Character table fields), migration files
- Impact: Schema inconsistency between SQLite dev and MySQL prod. New code adding fields with JSON without ORM defaults can break migrations
- Fix approach: Standardize on ORM-level defaults for all TEXT/JSON, document pattern, add migration validation test

## Security Considerations

**API Key Exposure in Logs:**
- Risk: GOOGLE_API_KEY, OLLAMA_HOST, DATABASE_URL printed in debug logs during orchestrator startup
- Files: `src/pipeline/async_orchestrator.py:217-228` (_log_config_summary), `src/llm_client.py` (logging on errors)
- Current mitigation: `.env` is gitignored, but logs may be captured in production. Secrets never appear in response bodies
- Recommendations: (1) Mask API keys in logs (show only last 4 chars), (2) Move detailed config logging to DEBUG level only, (3) Add log sanitizer middleware to FastAPI

**No Input Validation on Dynamic Prompt Injection:**
- Risk: Character DNA, custom poses, and phrase context are injected directly into Gemini prompts without sanitization
- Files: `src/image_gen/gemini_client.py:816-823` (build_character_image_prompt), `src/pipeline/workers/image_worker.py` (phrase context)
- Current mitigation: Gemini API is read-only (generates images, not stored), but malicious prompts could corrupt training data or trigger rate limits
- Recommendations: (1) Add length caps on user-provided text fields, (2) Escape special characters, (3) Validate phrase_context max length (currently no cap)

**Database Session Lifecycle Issues:**
- Risk: AsyncSession instances created inline in routes without proper cleanup on exception
- Files: `src/api/routes/publishing.py:25` (PublishingService(session) inside route without context manager)
- Current mitigation: FastAPI's dependency injection should handle cleanup, but implicit reliance on framework
- Recommendations: (1) Use explicit async context managers, (2) Test session cleanup under error conditions, (3) Document session lifecycle in deps.py

## Performance Bottlenecks

**Large File Read in Image Generation:**
- Problem: GeminiImageClient._load_referencias() reads all reference images into RAM on each generate_image() call
- Files: `src/image_gen/gemini_client.py:650-683` (_load_referencias method)
- Cause: No caching of loaded PIL.Image objects. For 15+ reference images at 2-5MB each, this is 30-75MB per request
- Improvement path: (1) Implement LRU cache in GeminiImageClient for reference image objects, (2) Pre-load refs on __init__, (3) Use file paths instead of loaded images for Gemini API calls (send bytes, not objects)

**Semaphore-Serialized GPU Access:**
- Problem: ComfyUI has Semaphore(1) for GPU, meaning parallel image generation requests serialize completely
- Files: `src/pipeline/workers/image_worker.py:34` (_gpu_semaphore), `src/image_gen/comfyui_client.py`
- Cause: Single RTX 4060 Ti cannot handle concurrent requests; correct design but bottleneck for scaled production
- Improvement path: (1) Implement GPU queue with priority (e.g., prioritize real-time API requests over batch), (2) Monitor GPU utilization to confirm Semaphore(1) is optimal, (3) Consider secondary GPU or offload to cloud on demand

**Trend Aggregation Quadratic Complexity:**
- Problem: TrendAggregator.aggregate() does title/source matching in O(n²) with string comparisons on every event
- Files: `src/pipeline/processors/aggregator.py` (TrendAggregator class)
- Cause: No indexing by title hash; aggregator re-scans list for duplicates
- Improvement path: (1) Use dict with normalized title keys for O(1) lookup, (2) Pre-sort by score, (3) Benchmark with 1000+ trends

**Regex-Based JSON Parsing in GeminiWebTrendsAgent:**
- Problem: Extracting JSON from Gemini text output via regex is slow and fragile
- Files: `src/pipeline/agents/gemini_web_trends.py` (regex pattern matching)
- Cause: Workaround for tool_choice incompatibility; no structured output guarantee
- Improvement path: (1) Switch to Claude API (native JSON mode), (2) Add retry logic with structured prompting, (3) Cache parsed results keyed by query

## Fragile Areas

**Multi-Character Rendering Config Fallback Chain:**
- Files: `src/image_gen/prompt_builder.py:367-432` (build_rendering_prompt)
- Why fragile: 4-level fallback chain (user custom → preset dict → default preset → hardcoded) means missing dict keys silently fall back without warning. Easy to break with schema changes
- Safe modification: (1) Add validation schema (Pydantic), (2) Use TypedDict for rendering config, (3) Add unit tests for each fallback case
- Test coverage: No tests for rendering config building; add parametrized tests for all presets + custom combinations

**Async Agent Availability Check:**
- Files: `src/pipeline/monitoring.py:28-42` (availability checks), `src/pipeline/agents/async_base.py` (is_available pattern)
- Why fragile: is_available() is async but called without await in some contexts. Mixed sync/async wrapping via SyncAgentAdapter can mask failures
- Safe modification: (1) Add iscoroutine() assertions in MonitoringLayer, (2) Consolidate on pure async agents, (3) Add timeout to availability checks (default 5s)
- Test coverage: test_agents_quick.py tests basic is_available() but not timeout/failure cases

**Character DNA Generation via Gemini (No Schema Validation):**
- Files: `src/api/routes/characters.py:324-331` (generate_profile endpoint)
- Why fragile: Gemini generates JSON but no validation schema; parser expects specific field names without error handling for missing fields
- Safe modification: (1) Define Pydantic schema for expected DNA fields, (2) Add required fields check post-parse, (3) Implement fallback defaults
- Test coverage: test_character_visual in characters.py route tests but no unit tests for DNA schema

**Work Order Creation from Manual Topics (Hidden Assumptions):**
- Files: `src/pipeline/async_orchestrator.py:231-290` (_build_manual_work_orders)
- Why fragile: Keyword matching from KEYWORD_MAP is substring-based with no prioritization. Overlapping keywords can match wrong situacao_key (e.g., "tech" matches both "technology" and "technical")
- Safe modification: (1) Use longest-match-first ordering, (2) Add priority weights to KEYWORD_MAP, (3) Fall back to Gemini analyzer for ambiguous matches
- Test coverage: No unit tests for manual topic to situacao_key mapping

**Database Migrations on MySQL Incompatible Column Types:**
- Files: `src/database/models.py`, `src/database/migrations/versions/*.py`
- Why fragile: TEXT/JSON fields with default=list/dict in SQLAlchemy don't translate to MySQL server_default (MySQL requires literal strings, not Python objects). Alembic migrations may silently skip defaults
- Safe modification: (1) Add pre-migration validation to check all nullable columns have defaults, (2) Document migration pattern in CONTRIBUTING.md, (3) Add fixture to test SQLite→MySQL migration
- Test coverage: No integration tests for MySQL migrations; SQLite-only CI

## Scaling Limits

**Gemini API Rate Limits:**
- Current capacity: 5 concurrent requests (GEMINI_MAX_CONCURRENT=5), 15 requests per minute (hardcoded)
- Limit: ~450 requests/hour with backoff. At 1 image/minute, scales to ~7 images/day without hitting 429 errors
- Scaling path: (1) Implement token bucket rate limiter instead of fixed Semaphore, (2) Monitor actual Gemini quota via API, (3) Add queue with exponential backoff (currently fixed 2^n backoff)

**ComfyUI GPU Memory:**
- Current capacity: RTX 4060 Ti 8GB, --lowvram mode, Flux Dev GGUF Q4_K_S
- Limit: Single Semaphore(1) means 1 image at a time; VRAM exhaustion on concurrent requests even with serialization
- Scaling path: (1) Profile VRAM usage, consider lower quantization (Q3_K), (2) Add GPU memory monitoring, (3) Implement CPU offload for intermediate layers

**Trend Event Queue Size:**
- Current capacity: BROKER_MAX_QUEUE_SIZE (likely 100-200), L3 curator selects top 5-10
- Limit: With 6 agents fetching ~227 events per run, queue is ~50% saturated. No backpressure handling if agents slow down
- Scaling path: (1) Increase queue size, (2) Add LRU eviction for old events, (3) Implement producer slowdown if queue > 80%

**Database Connection Pool:**
- Current capacity: SQLAlchemy default (5-10 connections), MySQL aiomysql
- Limit: API with 10+ concurrent requests can exhaust pool, leading to "queue full" errors on slow queries
- Scaling path: (1) Tune pool_size in engine creation (`pool_size=20, max_overflow=40`), (2) Add connection monitoring, (3) Implement query timeout

## Dependencies at Risk

**trendspyg RSS Feed Deprecation:**
- Risk: trendspyg is archived (June 2025), no longer maintained. Google Trends RSS format may change without warning
- Impact: GoogleTrendsAgent relies on trendspyg; if RSS breaks, data collection fails silently (agent returns [])
- Migration plan: (1) Evaluate trendshell or ts (pytrends forks), (2) Implement fallback to direct Google Search scraping, (3) Add monitoring alert if GoogleTrendsAgent returns 0 events

**google-genai SDK Version Lock:**
- Risk: google-genai SDK is fast-moving; v0.x breaking changes likely. Current code uses specific model names that may deprecate
- Impact: Gemini API calls fail if SDK major version changes or models are deprecated (e.g., gemini-2.0-flash no longer available)
- Migration plan: (1) Pin google-genai version in requirements.txt (currently likely unpinned), (2) Add model availability check on startup, (3) Implement model fallback list in LLM client

**Pillow Image Format Support:**
- Risk: Pillow behavior varies with libjpeg/libpng system libraries. PNG save may fail on systems without libpng
- Impact: Image composition silently fails if output format not supported
- Migration plan: (1) Add format support check on startup, (2) Implement fallback to JPEG for unsupported PNG, (3) Log format negotiation

## Missing Critical Features

**No Circuit Breaker for External APIs:**
- Problem: Repeated failures to Gemini, ComfyUI, or external agents don't trigger fallback. Pipeline retries indefinitely
- Blocks: Graceful degradation during API outages (e.g., Gemini 503 → should switch to ComfyUI automatically)
- Recommended solution: Implement circuit breaker pattern in image_worker.py (open after 5 failures, half-open after 60s)

**No Webhook for Publishing Completion:**
- Problem: Scheduled posts complete but no notification to external systems
- Blocks: Integration with Instagram analytics, Discord notifications, or external dashboards
- Recommended solution: Add webhook registry in database, call webhooks from PostProductionLayer

**No A/B Testing Tracking Database:**
- Problem: PHRASE_AB_ENABLED generates multiple phrase variants but no A/B test tracking in database
- Blocks: Analytics on which phrases perform better; user manual analysis only
- Recommended solution: Create ab_test_run table, log variant generation, track engagement metrics (future feature)

## Test Coverage Gaps

**No Integration Tests for Async Pipeline:**
- What's not tested: Full L1→L2→L3→L4→L5 pipeline execution with real database, mocked Gemini/ComfyUI
- Files: `tests/` directory (test_agents_quick.py exists but limited scope)
- Risk: E2E failures not caught until production. L2 Broker queue bugs, L3 Curator selection bugs undetected
- Priority: **High** — Add pytest fixtures for AsyncPipelineOrchestrator integration tests

**No Error Recovery Tests:**
- What's not tested: Pipeline behavior when Gemini API returns 429, ComfyUI crashes, database connection fails
- Files: Tests should exist in `tests/test_pipeline_errors.py` (missing)
- Risk: Silent failures, orphaned database records, incomplete image generation
- Priority: **High** — Add parametrized tests for common failure modes (API timeouts, SQL errors, file I/O)

**No Character Multi-Rendering Config Tests:**
- What's not tested: All combinations of rendering presets (art_style, lighting, camera) generate valid prompts
- Files: `src/image_gen/prompt_builder.py` (no unit tests for build_rendering_prompt)
- Risk: Broken rendering configs silently fall back to defaults, users unaware
- Priority: **Medium** — Add parametrized tests for all preset combinations

**No Database Migration Validation Tests:**
- What's not tested: MySQL migrations actually create correct schema, column types, constraints
- Files: Alembic migration files in `src/database/migrations/versions/`
- Risk: Migrations succeed locally (SQLite) but fail in production (MySQL)
- Priority: **High** — Add MySQL container test fixture, run migrations, validate schema introspection

**No Publisher Platform Mock Tests:**
- What's not tested: Publishing service queue logic, retry handling, platform-specific validation
- Files: `src/services/publisher.py`, `src/api/routes/publishing.py` (no unit tests for queue operations)
- Risk: Publishing features untested, schedule queue bugs not caught
- Priority: **Medium** — Add unit tests for schedule_post, cancel_scheduled, retry_post methods

---

*Concerns audit: 2026-03-23*
