# Codebase Concerns

**Analysis Date:** 2026-03-30

---

## Security Considerations

**Service account credential file uncommitted but unprotected:**
- Risk: `g-credencial.json` (GCS service account key) exists in repo root and shows as untracked (`??`). The `.gitignore` only excludes `gen-lang-client-*.json` by pattern — `g-credencial.json` does not match that glob and is one `git add .` away from being committed.
- Files: `/Users/luigivivian/meme-lab/g-credencial.json`, `/Users/luigivivian/meme-lab/.gitignore`
- Current mitigation: Not yet tracked by git.
- Recommendations: Add `g-credencial.json` explicitly to `.gitignore`. Move credentials to env var `GOOGLE_APPLICATION_CREDENTIALS` pointing to a path outside the repo.

**JWT secret has insecure default:**
- Risk: `SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")` — if the env var is not set in production, all JWTs are signed with a known public string.
- Files: `src/auth/jwt.py:10`
- Current mitigation: None — the fallback is a predictable string, not a generated secret.
- Recommendations: Raise `RuntimeError` at startup if `SECRET_KEY` env var is absent, rather than silently using the default.

**Unauthenticated image serving endpoint:**
- Risk: `GET /drive/images/{filename}` has no `Depends(get_current_user)` — any caller who knows (or guesses) a filename can retrieve images without authentication.
- Files: `src/api/routes/drive.py:124-147`
- Current mitigation: `validate_filename()` blocks path traversal; filenames follow structured patterns.
- Recommendations: Add auth dependency or document intentionally public. The `/download` variant at line 150 correctly requires auth.

**Internal exception detail leaks to API responses:**
- Risk: Multiple routes expose raw `str(e)` in HTTP 500 responses — stack traces and internal paths reach clients.
- Files: `src/api/routes/billing.py:127,201`, `src/api/routes/publishing.py:271,287,308`, `src/api/routes/agents.py:83,288`, `src/api/routes/pipeline.py:219` (full traceback in response body)
- Current mitigation: Error is also logged server-side.
- Recommendations: Return generic messages for 500 responses; include an opaque error ID for correlation. The pipeline route at lines 211-219 literally returns `"traceback": tb` in the JSON body.

**No MIME type or size validation on `upload_product_image`:**
- Risk: The `POST /ads/upload-image` endpoint reads the entire file into memory without checking content type or enforcing a size limit. An attacker can upload arbitrarily large files or non-image content.
- Files: `src/api/routes/ads.py:354-370`
- Current mitigation: None — the background upload (`/pipeline/backgrounds/upload`) at line 690 does enforce a 5MB limit and extension check; this pattern was not carried to the ads upload.
- Recommendations: Add size cap (e.g., 10MB) before `await file.read()` and validate content type against `image/*`.

**Character ref upload has no size limit:**
- Risk: `POST /characters/{slug}/refs/upload` loops over multiple files and calls `await file.read()` with no size gate.
- Files: `src/api/routes/characters.py:856-865`
- Current mitigation: Content type is checked (`file.content_type.startswith("image/")`), but no byte limit.
- Recommendations: Cap total upload size or per-file size before writing to disk.

**CORS locked to localhost only — no production origin configured:**
- Risk: `allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]` — API will reject cross-origin requests from a production frontend domain.
- Files: `src/api/app.py:89`
- Current mitigation: API appears dev-only currently.
- Recommendations: Read allowed origins from env var (`CORS_ORIGINS`) so production deploy does not require a code change.

**JWT tokens stored in `localStorage`:**
- Risk: `localStorage` is accessible to any JavaScript running on the page, making tokens vulnerable to XSS attacks.
- Files: `memelab/src/lib/api.ts:9`, `memelab/src/contexts/auth-context.tsx:92-95`
- Current mitigation: Tokens are cleared on 401; session-only option uses `sessionStorage`.
- Recommendations: Use `httpOnly` cookies for token storage to prevent XSS access, or implement a secure BFF pattern.

---

## Tech Debt

**Five social-media trend agents are permanent stubs:**
- Issue: `TikTokTrendsAgent`, `InstagramExploreAgent`, `TwitterXAgent`, `FacebookViralAgent`, `YouTubeShortsAgent` all return empty lists and log "é um stub".
- Files: `src/pipeline/agents/tiktok_trends.py`, `src/pipeline/agents/instagram_explore.py`, `src/pipeline/agents/twitter_x.py`, `src/pipeline/agents/facebook_viral.py`, `src/pipeline/agents/youtube_shorts.py`
- Impact: Five out of the trend data sources produce nothing; trend quality degrades silently if the active agents (Google, Reddit, RSS) rate-limit.
- Fix approach: Either implement the APIs or remove the stubs and the corresponding `_load_stub_agents` registration in `src/pipeline/async_orchestrator.py:159-187`.

**Two hardcoded TODO stubs in publishing:**
- Issue: `GET /publishing/best-times` returns static hardcoded time slots with a `TODO: Integrar com Instagram Insights`. `_publish_tiktok` raises `NotImplementedError`.
- Files: `src/api/routes/publishing.py:217-232`, `src/services/publisher.py:282-287`
- Impact: TikTok publishing silently crashes any job routed to it; best-times is permanently generic.
- Fix approach: Guard TikTok routes with a feature-flag check before the `NotImplementedError` can propagate; replace static best-times with real Insights once Instagram connection is stable.

**`local Whisper` transcription deferred with `NotImplementedError`:**
- Issue: `transcribe_to_srt` raises `NotImplementedError("Local Whisper deferred to follow-up")` when provider is `whisper_local`.
- Files: `src/reels_pipeline/transcriber.py:40`
- Impact: Callers specifying `whisper_local` get an unhandled error that surfaces as a reel step failure.
- Fix approach: Either implement local Whisper via `openai-whisper` package or remove the provider option from the interface until implemented.

**`BlockingScheduler` in legacy pipeline scheduler:**
- Issue: `src/pipeline/scheduler.py` uses `BlockingScheduler` which blocks the calling thread entirely. This is a CLI-only tool, but it coexists with the async FastAPI scheduler.
- Files: `src/pipeline/scheduler.py:28,40`
- Impact: Low risk today (not used by API), but creates confusion — there are two scheduler systems (`scheduler.py` vs `services/scheduler_worker.py`).
- Fix approach: Mark `src/pipeline/scheduler.py` as deprecated, direct users to `pipeline_cli.py` + `scheduler_worker`.

**`MOTION_TEMPLATES_V1` kept as dead weight:**
- Issue: `MOTION_TEMPLATES_V1` is defined alongside `MOTION_TEMPLATES_V2` with the comment "Backward compatibility alias". `get_motion_templates()` still conditionally returns V1.
- Files: `src/video_gen/video_prompt_builder.py:19-258`
- Impact: 80+ lines of dead config that will silently drift from V2. Any caller passing version detection logic gets V1 with no warning.
- Fix approach: Delete V1 and the version-select function; update any callers to use `MOTION_TEMPLATES` directly.

**`rembg` creates a new session on every call:**
- Issue: `remove_background()` calls `new_session(model_name=ADS_REMBG_MODEL)` on every invocation. Loading the rembg ONNX model is expensive (~2-3s and 200MB+ RAM).
- Files: `src/product_studio/bg_remover.py:21`
- Impact: Each ad job's scene step pays a full model load penalty; repeated jobs are slow.
- Fix approach: Cache the session at module level (or as a singleton) — `rembg` sessions are thread-safe.

**Ad analysis duplicated in two places:**
- Issue: The product analysis LLM call is implemented twice: once in `pipeline.py:run_step_analysis` (with image) and again inline in `ads.py` background task (text-only fallback at lines 145-163) and again in `ads.py:analyze_product` endpoint (lines 384-402). All three build similar prompts independently.
- Files: `src/api/routes/ads.py:145-163`, `src/api/routes/ads.py:384-410`, `src/product_studio/pipeline.py:66-80`
- Impact: Prompt diverges between paths; bugs fixed in one location are missed in others.
- Fix approach: Centralize in `ProductAdPipeline.run_step_analysis()` with an optional `image_path` parameter; route all three callers through it.

**`datetime.utcnow()` deprecated — used extensively:**
- Issue: Python 3.12 deprecates `datetime.utcnow()` in favor of `datetime.now(timezone.utc)`. The codebase uses `utcnow()` in at least 10 places.
- Files: `src/database/repositories/usage_repo.py:355,390,415,554`, `src/database/repositories/schedule_repo.py:95,126`, `src/api/routes/dashboard.py:76`, `src/services/publisher.py:311`, `src/billing/stripe_service.py:262,282,300`
- Impact: Will emit deprecation warnings now, will break in Python 3.14+.
- Fix approach: Global search-replace `datetime.utcnow()` → `datetime.now(timezone.utc)` with `from datetime import timezone` where missing.

**Relative path used in security boundary check:**
- Issue: In `serve_artifact_file`, the allowed path `output_real = os.path.realpath("output/reels")` resolves relative to the process working directory, not the repo root. If the server is started from a different directory, the realpath check fails silently (resolves to wrong absolute path), allowing arbitrary file access.
- Files: `src/api/routes/reels.py:857-858`
- Impact: Path containment check is environment-dependent — fails when CWD is not repo root.
- Fix approach: Use `Path(__file__).resolve().parents[N] / "output/reels"` or import the absolute output path from `config.py`.

---

## Performance Bottlenecks

**`blocking time.sleep(5)` on event loop thread in `gemini_client.py`:**
- Problem: `iterative_refinement()` calls `time.sleep(5)` (not `await asyncio.sleep(5)`) between refinement passes, blocking the entire asyncio event loop.
- Files: `src/image_gen/gemini_client.py:1135`
- Cause: Sync sleep called from a context that may be invoked on the event loop thread.
- Improvement path: Replace with `await asyncio.sleep(5)` if the function is async, or ensure the call is always wrapped in `asyncio.to_thread`.

**`_list_drive_images` does filesystem stat on every request:**
- Problem: `GET /drive/images` calls `_list_drive_images()` which does a full directory scan + `stat()` on every file every request. No caching.
- Files: `src/api/routes/drive.py:49-78`
- Cause: No TTL cache or DB-backed index for generated images.
- Improvement path: Add a short TTL in-memory cache (e.g., 30s) on the result, or track generated files in the database.

**`images_by_theme` has no pagination limit:**
- Problem: `GET /drive/images/by-theme/{theme_key}` returns all matching images with no `limit`/`offset` parameter.
- Files: `src/api/routes/drive.py:118-121`
- Cause: Pagination not applied to the theme-filtered endpoint.
- Improvement path: Add `limit` and `offset` query params consistent with the main `/drive/images` endpoint.

---

## Fragile Areas

**`traceback` stored in pipeline run DB record:**
- Files: `src/api/routes/pipeline.py:219`
- Why fragile: Full Python traceback (including file paths, variable values) written to `pipeline_runs.results` JSON column and returned in API responses. This leaks internal server structure.
- Safe modification: Replace with `exception_type` + sanitized message only; keep full traceback in server logs.
- Test coverage: No test for the failure path response shape.

**`step_state` JSON column mutated in-place with `flag_modified`:**
- Files: `src/api/routes/ads.py:118-347`, `src/api/routes/reels.py` (similar pattern)
- Why fragile: Both routes load `step_state = dict(job.step_state or {})`, mutate it, then call `flag_modified(job, "step_state")` to signal SQLAlchemy. If two requests race (e.g., rapid retrigger), the second write can clobber the first because there is no row-level lock.
- Safe modification: Use a DB-level `SELECT FOR UPDATE` before mutating step_state, or move step state to dedicated columns with atomic updates.
- Test coverage: No concurrency test exists.

**GCS fallback uploads to `litterbox.catbox.moe` (1-hour expiry):**
- Files: `src/video_gen/gcs_uploader.py:91-107`
- Why fragile: When GCS is unavailable, image URLs sent to Kie.ai expire after 1 hour. If video generation takes longer than 1 hour (it can: `KIE_POLL_TIMEOUT=600`s by default, but external API queues can be longer), the source image URL becomes invalid mid-generation.
- Safe modification: Ensure GCS is always configured in production. Add a warning log when using the temp fallback, and surface it in the job status.
- Test coverage: No test for fallback expiry scenario.

**`analyze_product` endpoint returns a 200 with empty defaults on Gemini failure:**
- Files: `src/api/routes/ads.py:403-410`
- Why fragile: Any Gemini API error silently returns `{"niche": "", "tone": "professional", "audience": "general", "scene_suggestions": []}`. Callers cannot distinguish success from failure.
- Safe modification: Return 502 on Gemini failure, or include an `"error"` flag in the response so the UI can show the user a retry prompt.
- Test coverage: No test for the failure branch.

---

## Test Coverage Gaps

**Product Studio pipeline untested:**
- What's not tested: `src/product_studio/pipeline.py`, `src/product_studio/bg_remover.py`, `src/product_studio/scene_composer.py`, `src/product_studio/copy_generator.py`, `src/product_studio/prompt_builder.py`
- Risk: 8-step ad pipeline has no automated regression coverage. A Gemini API shape change or rembg version bump would be caught only in production.
- Priority: High

**Reels pipeline untested:**
- What's not tested: `src/reels_pipeline/main.py`, `src/reels_pipeline/video_builder.py`, `src/reels_pipeline/transcriber.py`
- Risk: FFmpeg invocation, subtitle generation, and crossfade logic have no unit or integration tests.
- Priority: High

**`src/api/routes/ads.py` and `src/api/routes/reels.py` have no tests:**
- What's not tested: All step execution, step approval, artifact serving, race condition protection
- Files: `src/api/routes/ads.py`, `src/api/routes/reels.py`
- Risk: Step state machine logic is entirely manual-tested; regressions go undetected.
- Priority: High

**Frontend has zero test files:**
- What's not tested: All React components, all API client functions in `memelab/src/lib/api.ts` (1716 lines), auth flow, ad wizard stepper
- Files: `memelab/src/` (entire directory)
- Risk: UI regressions caught only by manual QA.
- Priority: Medium

---

## Missing Critical Features

**No production deployment configuration:**
- Problem: CORS is hardcoded to `localhost:3000`. There is no `Dockerfile`, no `docker-compose.yml`, no environment variable documentation for production. The database defaults to SQLite (`data/clipflow.db`) which is not production-safe.
- Blocks: Deploying the system to any non-local environment.

**No request rate limiting on the API:**
- Problem: FastAPI has no rate-limiting middleware. Any authenticated user can hammer Gemini-backed endpoints (image generation, theme enhancement, ad analysis) at will, burning API quotas.
- Blocks: Multi-tenant SaaS stability once more than one user is active.

---

## Dependencies at Risk

**`litterbox.catbox.moe` as production dependency:**
- Risk: Free third-party file host used as fallback when GCS is unavailable. No SLA, no auth, files expire after 1 hour.
- Impact: Video generation pipeline silently degrades to an unreliable public file host.
- Migration plan: Enforce GCS in production; remove the fallback or replace with a self-hosted MinIO endpoint.

---

*Concerns audit: 2026-03-30*
