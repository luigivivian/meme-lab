# Phase 10: Static Fallback - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Automatic fallback to static backgrounds when both Gemini API keys (free and paid) are exhausted. The pipeline must complete a full run end-to-end even with `GEMINI_IMAGE_DAILY_LIMIT_FREE=0` and `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`. Covers QUOT-06. Does NOT include usage dashboard (Phase 11) or any new UI.

</domain>

<decisions>
## Implementation Decisions

### Exhaustion Detection
- **D-01:** `UsageAwareKeySelector.resolve()` checks BOTH free and paid tiers via `UsageRepository.check_limit()`. When both are exhausted, returns `KeyResolution(api_key='', tier='exhausted', mode='auto')`. No wasted API calls.
- **D-02:** In free-only mode (no paid key), if free limit is hit, `resolve()` returns `tier='exhausted'` immediately. Consistent behavior — pre-check always prevents wasted calls.
- **D-03:** `0 = unlimited, never exhausted` — consistent with Phase 8 D-07. A tier with limit=0 is never considered exhausted.

### Fallback Integration Point
- **D-04:** Pre-check happens inside `ImageWorker.compose()`, at the top before the Gemini/ComfyUI priority chain. If `resolution.tier == 'exhausted'`, skip `_try_gemini()` entirely and go straight to static background.
- **D-05:** `compose()` receives `user_id: int | None` and `session: AsyncSession | None` as new optional parameters. When provided, pre-check runs. When `None` (CLI/script usage without auth), skip the check and use existing behavior. Backward compatible.

### Static Background Selection
- **D-06:** Keep `random.choice(self._generator.backgrounds)` for static fallback. The backgrounds are per-character reference images — they all work for any situation. No theme-aware matching needed.

### Logging & Observability
- **D-07:** `WARNING` log when exhaustion detected: "Both tiers exhausted, using static fallback". `background_source='static'` set in `ContentPackage` metadata (field already exists).
- **D-08:** Add `fallback_reason` field to image metadata distinguishing: `'quota_exhausted'` (both keys spent), `'generation_failed'` (Gemini error/timeout), `'mode_static'` (user explicitly set background_mode=static). Helps debugging and Phase 11 dashboard.

### Claude's Discretion
- Internal implementation of the paid-tier limit check in `resolve()` (add second `check_limit()` call)
- Whether `fallback_reason` goes in `ComposeResult.image_metadata` dict or as a new dataclass field
- Test strategy for the exhaustion flow (mock UsageRepository to return exhausted for both tiers)
- Error handling if DB session is unavailable during pre-check (graceful degradation — try Gemini anyway)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 9 (Direct Predecessor)
- `.planning/phases/09-dual-key-management/09-CONTEXT.md` — KeyResolution dataclass, UsageAwareKeySelector.resolve() priority chain, free-only mode detection (D-01, D-02).
- `src/services/key_selector.py` — Current KeySelector implementation. Must be extended with paid-tier check and `tier='exhausted'` return path.

### Phase 8 (Atomic Counter)
- `.planning/phases/08-atomic-counter/08-CONTEXT.md` — UsageRepository.check_limit() API, limit config via env vars, 0=unlimited semantics (D-07).
- `src/database/repositories/usage_repo.py` — UsageRepository with `check_limit(user_id, service, tier)` returning `(allowed, info_dict)`.

### Image Pipeline
- `src/pipeline/workers/image_worker.py` — ImageWorker.compose() is the integration point. Lines 147-211: existing priority chain and static fallback.
- `src/pipeline/processors/generator.py` — ContentGenerator._load_backgrounds() loads static backgrounds from BACKGROUNDS_DIR.
- `src/pipeline/models_v2.py` — ContentPackage with `background_source` field (line 83).

### Requirements
- `.planning/REQUIREMENTS.md` — QUOT-06 (automatic fallback to static backgrounds when limit reached).

### Roadmap Success Criteria
- `.planning/ROADMAP.md` Phase 10 section — 3 success criteria: ImageWorker produces valid image, metadata has `background_source: "static"`, full pipeline run completes with both limits at 0.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ImageWorker.compose()` already has a `bg is None → random.choice(backgrounds)` fallback at line 192 — the static fallback path exists, just needs to be triggered proactively by exhaustion detection.
- `UsageAwareKeySelector` and `KeyResolution` dataclass in `src/services/key_selector.py` — extend with paid-tier check.
- `UsageRepository.check_limit(user_id, service, tier)` — call twice (free + paid) for exhaustion detection.
- `ComposeResult` dataclass with `background_source` and `image_metadata` fields — ready for `fallback_reason`.

### Established Patterns
- Env var config: `GEMINI_IMAGE_DAILY_LIMIT_{TIER}` pattern from Phase 8.
- Optional async params pattern: several methods accept `None` for optional async dependencies.
- `background_source` values: `"gemini"`, `"comfyui"`, `"static"` — well-established in pipeline.

### Integration Points
- `src/services/key_selector.py` — Add paid-tier `check_limit()` call and `tier='exhausted'` return.
- `src/pipeline/workers/image_worker.py` — Add `user_id` and `session` params to `compose()`, pre-check at top.
- `src/api/routes/generation.py` — Callers of `compose()` need to pass user_id/session through.
- Pipeline orchestrator callers — need to propagate user context to ImageWorker.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: the system must remain backward compatible for CLI/script usage without auth (compose() works without user_id/session).

</specifics>

<deferred>
## Deferred Ideas

- **Usage dashboard showing static fallback stats** — Phase 11 (DASH-01, DASH-02, DASH-03)
- **Theme-aware background selection for static fallback** — future enhancement, not needed for v1
- **Weighted/LRU background selection to avoid repeats** — nice-to-have, not in scope
- **Static fallback counter in api_usage table** — could help Phase 11 but adds schema change, defer

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-static-fallback*
*Context gathered: 2026-03-24*
