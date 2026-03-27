# Phase 10: Static Fallback - Research

**Researched:** 2026-03-24
**Domain:** Pipeline fallback logic, quota exhaustion detection
**Confidence:** HIGH

## Summary

Phase 10 wires the existing `UsageAwareKeySelector` (Phase 9) and `UsageRepository` (Phase 8) into `ImageWorker.compose()` so the pipeline gracefully degrades to static backgrounds when both free and paid Gemini API quotas are exhausted. The code changes are surgical: extend `resolve()` with a paid-tier check and `tier='exhausted'` return, add a pre-check at the top of `compose()`, and propagate `user_id`/`session` from callers.

All building blocks exist. The static fallback path (`random.choice(self._generator.backgrounds)`) already works at line 192-195 of `image_worker.py`. The `background_source` field already supports `"static"`. The `check_limit()` API is proven. This phase connects them with a new exhaustion detection path.

**Primary recommendation:** Extend `UsageAwareKeySelector.resolve()` to check paid tier when free is exhausted, return `KeyResolution(api_key='', tier='exhausted', mode='auto')`. Add pre-check in `compose()` that skips Gemini entirely when exhausted. Pass `user_id`/`session` as optional params through `GenerationLayer` and `ImageWorker`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `UsageAwareKeySelector.resolve()` checks BOTH free and paid tiers via `UsageRepository.check_limit()`. When both are exhausted, returns `KeyResolution(api_key='', tier='exhausted', mode='auto')`. No wasted API calls.
- **D-02:** In free-only mode (no paid key), if free limit is hit, `resolve()` returns `tier='exhausted'` immediately. Consistent behavior -- pre-check always prevents wasted calls.
- **D-03:** `0 = unlimited, never exhausted` -- consistent with Phase 8 D-07. A tier with limit=0 is never considered exhausted.
- **D-04:** Pre-check happens inside `ImageWorker.compose()`, at the top before the Gemini/ComfyUI priority chain. If `resolution.tier == 'exhausted'`, skip `_try_gemini()` entirely and go straight to static background.
- **D-05:** `compose()` receives `user_id: int | None` and `session: AsyncSession | None` as new optional parameters. When provided, pre-check runs. When `None` (CLI/script usage without auth), skip the check and use existing behavior. Backward compatible.
- **D-06:** Keep `random.choice(self._generator.backgrounds)` for static fallback. No theme-aware matching needed.
- **D-07:** `WARNING` log when exhaustion detected: "Both tiers exhausted, using static fallback". `background_source='static'` set in `ContentPackage` metadata (field already exists).
- **D-08:** Add `fallback_reason` field to image metadata distinguishing: `'quota_exhausted'` (both keys spent), `'generation_failed'` (Gemini error/timeout), `'mode_static'` (user explicitly set background_mode=static). Helps debugging and Phase 11 dashboard.

### Claude's Discretion
- Internal implementation of the paid-tier limit check in `resolve()` (add second `check_limit()` call)
- Whether `fallback_reason` goes in `ComposeResult.image_metadata` dict or as a new dataclass field
- Test strategy for the exhaustion flow (mock UsageRepository to return exhausted for both tiers)
- Error handling if DB session is unavailable during pre-check (graceful degradation -- try Gemini anyway)

### Deferred Ideas (OUT OF SCOPE)
- Usage dashboard showing static fallback stats -- Phase 11 (DASH-01, DASH-02, DASH-03)
- Theme-aware background selection for static fallback -- future enhancement
- Weighted/LRU background selection to avoid repeats -- nice-to-have
- Static fallback counter in api_usage table -- adds schema change, defer
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUOT-06 | Fallback automatico para backgrounds estaticos quando limite free atingido | Key selector exhaustion detection + ImageWorker pre-check + fallback_reason metadata |
</phase_requirements>

## Standard Stack

No new dependencies. This phase uses exclusively existing project code:

### Core (existing)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.0 | (existing) | Async DB sessions for check_limit() | Already in project |
| pytest | 9.0.2 | Testing | Already in project |
| pytest-asyncio | (existing) | Async test support | Already in project |

### No New Packages
This phase modifies only existing Python modules. No `pip install` needed.

## Architecture Patterns

### Recommended Change Structure
```
src/
  services/
    key_selector.py          # MODIFY: add paid-tier check + exhausted return
  pipeline/
    workers/
      image_worker.py        # MODIFY: add user_id/session params, pre-check
      generation_layer.py    # MODIFY: propagate user_id/session to compose()
tests/
  test_static_fallback.py    # NEW: exhaustion flow tests
  test_key_selector.py       # EXTEND: add exhausted-tier tests
```

### Pattern 1: Exhaustion Detection in resolve()
**What:** After free tier check fails, check paid tier before returning paid key. If paid also exhausted, return `tier='exhausted'`.
**When to use:** Always in auto mode when free tier is over limit.
**Implementation approach:**

Current `resolve()` flow (Phase 9):
```
free check -> allowed? return free : return paid
```

New flow:
```
free check -> allowed? return free : paid check -> allowed? return paid : return exhausted
```

Key insight: In free-only mode (D-02), there is no paid key to check. When free limit is hit, return `tier='exhausted'` immediately -- no need for a second `check_limit()` call.

For dual-key mode: after free check fails, call `check_limit(user_id, "gemini_image", "paid")`. If also rejected, return `KeyResolution(api_key='', tier='exhausted', mode='auto')`.

The `0 = unlimited` semantics (D-03) are already handled by `check_limit()` -- it returns `(True, ...)` when limit is 0. So if paid tier has `GEMINI_IMAGE_DAILY_LIMIT_PAID=0` (default), it will never be exhausted. Only when both tiers have non-zero limits that are exceeded does exhaustion trigger.

### Pattern 2: Pre-check in compose()
**What:** At the top of `compose()`, if `user_id` and `session` are provided, call `UsageAwareKeySelector.resolve()`. If `tier == 'exhausted'`, skip to static fallback immediately.
**When to use:** Pipeline runs with authenticated context.

```python
async def compose(
    self, phrase: str, work_order: WorkOrder,
    user_id: int | None = None, session: AsyncSession | None = None,
) -> ComposeResult:
    # Pre-check: quota exhaustion
    if user_id is not None and session is not None:
        try:
            selector = UsageAwareKeySelector()
            resolution = await selector.resolve(user_id=user_id, session=session)
            if resolution.tier == "exhausted":
                logger.warning("Both tiers exhausted, using static fallback")
                bg = random.choice(self._generator.backgrounds)
                return ComposeResult(
                    image_path=...,  # still need to compose
                    background_path=bg,
                    background_source="static",
                    image_metadata={"fallback_reason": "quota_exhausted", ...},
                )
        except Exception as e:
            logger.warning(f"Pre-check failed ({e}), proceeding with normal flow")
    # ... existing priority chain continues
```

Important: The pre-check only determines the background -- the Pillow composition (`create_image`) still runs. The compose must still call `create_image(phrase, bg, ...)` to produce the final image.

### Pattern 3: fallback_reason in image_metadata dict
**Recommendation (Claude's Discretion):** Put `fallback_reason` in the `image_metadata` dict rather than as a new dataclass field. Reasons:
1. `image_metadata` is already a catch-all dict for generation context
2. Avoids changing the `ComposeResult` dataclass signature (less downstream impact)
3. ContentPackage already copies `image_metadata` from ComposeResult
4. Phase 11 dashboard can read `image_metadata.get("fallback_reason")` uniformly

Values:
- `"quota_exhausted"` -- both tiers over limit (this phase)
- `"generation_failed"` -- Gemini/ComfyUI error (existing fallback path)
- `"mode_static"` -- user explicitly set `background_mode=static`
- Not set / absent -- Gemini/ComfyUI succeeded (no fallback)

### Pattern 4: Propagating user_id/session through GenerationLayer
**What:** `GenerationLayer.process()` needs to pass `user_id`/`session` down to `image_worker.compose()`.
**Current call sites in generation_layer.py:**
- Line 105: `await self.image_worker.compose(slide_phrase, wo)`
- Line 109: `await self.image_worker.compose(phrase, wo)`
- Line 130: `await self.image_worker.compose(phrase, wo)`

**Approach:** Add `user_id: int | None = None` and `session: AsyncSession | None = None` to `GenerationLayer.process()` signature. Pass through to each `compose()` call.

The pipeline API route (`src/api/routes/pipeline.py`) creates `GenerationLayer` inside `_run_pipeline_task()`. That function already has access to a DB session factory. It needs to pass `user_id` (from the request/current_user) and an open session to `generation.process()`.

For CLI usage (`python -m src.pipeline_cli`), these params remain `None` and the existing behavior is preserved.

### Anti-Patterns to Avoid
- **Creating UsageAwareKeySelector on every compose() call:** Instantiation reads env vars and logs warnings. Cache the selector instance on ImageWorker at init time, or create once per pre-check. Since compose() may be called many times per pipeline run, avoid repeated construction.
- **Checking quota AFTER trying Gemini:** D-01 explicitly says "no wasted API calls." The pre-check must happen BEFORE any Gemini call.
- **Swallowing pre-check exceptions silently:** Log at WARNING level so issues are visible, but degrade gracefully (try Gemini anyway).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quota checking | Custom counter logic | `UsageRepository.check_limit()` | Already handles 0=unlimited, PT timezone, atomic counting |
| Key selection | Manual env var parsing | `UsageAwareKeySelector.resolve()` | Already handles force_tier, free-only, priority chain |
| Static bg selection | Theme-aware matcher | `random.choice(self._generator.backgrounds)` | D-06 says no matching needed |

## Common Pitfalls

### Pitfall 1: Forgetting to compose the final image on static fallback
**What goes wrong:** Pre-check detects exhaustion and returns a ComposeResult with a background path but no composed image (skips `create_image()`).
**Why it happens:** The compose() method has the Pillow composition at lines 200-203. If you return early from the pre-check, you must still call `create_image()`.
**How to avoid:** After selecting the static background in the pre-check, still fall through to the `create_image()` call, or call it explicitly in the pre-check branch.
**Warning signs:** `ComposeResult.image_path` is empty or is just the background path.

### Pitfall 2: UsageAwareKeySelector constructor failing without API key
**What goes wrong:** `UsageAwareKeySelector()` raises `ValueError` if `GOOGLE_API_KEY` is not set. In CLI mode this would crash compose().
**Why it happens:** The selector is meant for environments with API keys configured.
**How to avoid:** Wrap selector instantiation in try/except. If it fails, skip the pre-check and proceed with existing flow. This is already the graceful degradation pattern.
**Warning signs:** Unhandled ValueError in compose().

### Pitfall 3: Session lifecycle mismatch
**What goes wrong:** The `AsyncSession` passed to compose() may be committed or closed by the time the pre-check runs.
**Why it happens:** In pipeline.py, the session is opened via `factory()` context manager. If compose() is called after the session closes, check_limit() fails.
**How to avoid:** Ensure the session passed to `process()` remains open for the entire generation phase. In `_run_pipeline_task`, open a session that spans the generation layer call.
**Warning signs:** SQLAlchemy "Session is closed" errors during pipeline run.

### Pitfall 4: Repeated selector instantiation in hot loop
**What goes wrong:** `compose()` is called once per work order per phrase. Creating `UsageAwareKeySelector()` on each call logs warnings repeatedly and re-reads env vars.
**How to avoid:** Either cache the selector on ImageWorker (constructed once in `__init__`), or create it once in GenerationLayer.process() and pass it down. Recommendation: create once per `process()` call and pass via parameter or store on the layer.

### Pitfall 5: Paid tier default limit is 0 (unlimited)
**What goes wrong:** With default config `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`, paid tier is NEVER exhausted. So the exhaustion path only triggers if the user explicitly sets a non-zero paid limit.
**Why it matters:** For testing the success criteria ("pipeline completes with both limits at 0"), setting both env vars to 0 means UNLIMITED (never exhausted) -- this is the opposite of what you might expect. The success criteria says `GEMINI_IMAGE_DAILY_LIMIT_FREE=0` and `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`, which under current semantics means "unlimited."
**Resolution:** Re-reading the success criteria: "when `GEMINI_IMAGE_DAILY_LIMIT_FREE=0` and `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`" -- this actually means the limits are set to 0 = unlimited, so Gemini should ALWAYS be available. This tests that the pipeline doesn't break with the default config. The actual exhaustion test needs non-zero limits that are exceeded. The success criteria test should use `GEMINI_IMAGE_DAILY_LIMIT_FREE=1` with usage already at 1+, or mock `check_limit` to return False.

**WAIT -- re-reading the success criteria more carefully:** "The pipeline completes a full run end-to-end even when `GEMINI_IMAGE_DAILY_LIMIT_FREE=0` and `GEMINI_IMAGE_DAILY_LIMIT_PAID=0`." In Phase 8 D-07, 0 = unlimited. So this test verifies the pipeline works normally with unlimited quotas. But the FIRST success criterion says "When both free and paid daily limits are exhausted, ImageWorker produces a valid image using a static background." These are TWO DIFFERENT tests: one for exhaustion (limits hit), one for unlimited mode (limits=0).

## Code Examples

### Example 1: Extended resolve() with exhaustion detection

```python
# In UsageAwareKeySelector.resolve() — after free tier check fails:

# Priority 4: automatic — check DB usage
repo = UsageRepository(session)
allowed_free, info_free = await repo.check_limit(user_id, "gemini_image", "free")

if allowed_free:
    return KeyResolution(api_key=self._free_key, tier="gemini_free", mode="auto")

# Free exhausted — check paid tier
if self._free_only:
    # No paid key available, both tiers exhausted
    logger.warning("Free tier exhausted and no paid key — tier=exhausted")
    return KeyResolution(api_key="", tier="exhausted", mode="auto")

allowed_paid, info_paid = await repo.check_limit(user_id, "gemini_image", "paid")
if allowed_paid:
    logger.info("Free tier limit reached, switching to paid key")
    return KeyResolution(api_key=self._paid_key, tier="gemini_paid", mode="auto")

# Both tiers exhausted
logger.warning("Both free and paid tiers exhausted — tier=exhausted")
return KeyResolution(api_key="", tier="exhausted", mode="auto")
```

### Example 2: Pre-check in compose()

```python
async def compose(
    self, phrase: str, work_order: WorkOrder,
    user_id: int | None = None, session: AsyncSession | None = None,
) -> ComposeResult:
    situacao_key = work_order.situacao_key
    topic = AnalyzedTopic(...)

    bg = None
    bg_source = "static"
    gen_metadata = {}
    fallback_reason = None

    # Pre-check: quota exhaustion (D-04, D-05)
    if user_id is not None and session is not None and self._background_mode not in ("static", "comfyui"):
        try:
            from src.services.key_selector import UsageAwareKeySelector
            selector = UsageAwareKeySelector()
            resolution = await selector.resolve(user_id=user_id, session=session)
            if resolution.tier == "exhausted":
                logger.warning("Both tiers exhausted, using static fallback")
                fallback_reason = "quota_exhausted"
                # Force static — skip the entire priority chain below
                bg = random.choice(self._generator.backgrounds)
                bg_source = "static"
                gen_metadata = {"theme_key": situacao_key, "fallback_reason": fallback_reason}
        except Exception as e:
            logger.warning(f"Quota pre-check failed ({e}), continuing with normal flow")

    # Existing priority chain (only if bg not yet selected)
    if bg is None:
        mode = self._background_mode
        # ... existing mode logic ...

    # Fallback final: background estatico
    if bg is None:
        bg = random.choice(self._generator.backgrounds)
        bg_source = "static"
        if fallback_reason is None:
            fallback_reason = "generation_failed"
        gen_metadata = {"theme_key": situacao_key, "fallback_reason": fallback_reason}

    # Compose final image with Pillow
    layout = getattr(work_order, "layout", "bottom")
    image_path = await asyncio.to_thread(create_image, phrase, bg, None, self._watermark_text, layout)
    gen_metadata["layout"] = layout

    # Add fallback_reason to existing static fallback too
    if bg_source == "static" and "fallback_reason" not in gen_metadata:
        gen_metadata["fallback_reason"] = fallback_reason or "generation_failed"

    # background_mode=static explicit
    if self._background_mode == "static" and "fallback_reason" not in gen_metadata:
        gen_metadata["fallback_reason"] = "mode_static"

    return ComposeResult(
        image_path=image_path,
        background_path=bg,
        background_source=bg_source,
        image_metadata=gen_metadata,
    )
```

### Example 3: Test pattern for exhaustion flow

```python
@pytest.mark.asyncio
async def test_resolve_returns_exhausted_when_both_tiers_over_limit(selector, mock_session):
    """When both free and paid check_limit reject, resolve returns tier=exhausted."""
    mock_check = AsyncMock(side_effect=[
        (False, {"used": 15, "limit": 15, "remaining": 0, "resets_at": "..."}),  # free
        (False, {"used": 50, "limit": 50, "remaining": 0, "resets_at": "..."}),  # paid
    ])
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.api_key == ""
    assert result.tier == "exhausted"
    assert result.mode == "auto"
    assert mock_check.await_count == 2
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No quota check in pipeline | Dual-key with auto-switch | Phase 9 (2026-03) | Pipeline uses free key by default, paid as fallback |
| Pipeline fails on API errors | Try next backend, then static | Pre-existing | Static fallback exists but only for generation errors |
| No pre-check before Gemini calls | Quota pre-check prevents wasted calls | Phase 10 (this phase) | Pipeline never wastes API calls on exhausted quotas |

## Open Questions

1. **UsageAwareKeySelector caching strategy**
   - What we know: Constructor reads env vars, logs warnings. Called per compose() if not cached.
   - What's unclear: Best place to cache — ImageWorker.__init__ or GenerationLayer.process().
   - Recommendation: Create once in GenerationLayer.process() and pass as parameter to compose(). This avoids holding a stale reference across pipeline runs while preventing per-call construction.

2. **Pipeline route user_id propagation**
   - What we know: `_run_pipeline_task` in pipeline.py does not currently receive user_id from the request.
   - What's unclear: Whether pipeline is always authenticated (some runs may be from CLI).
   - Recommendation: Add optional `user_id` to `PipelineRunRequest` model or extract from `current_user` in the route handler and pass through to `_run_pipeline_task`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | (implicit, uses default pytest discovery) |
| Quick run command | `python -m pytest tests/test_static_fallback.py tests/test_key_selector.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUOT-06a | resolve() returns exhausted when both tiers over limit | unit | `python -m pytest tests/test_key_selector.py::test_resolve_returns_exhausted_both_tiers -x` | No -- Wave 0 |
| QUOT-06b | resolve() returns exhausted in free-only mode when free over limit | unit | `python -m pytest tests/test_key_selector.py::test_resolve_exhausted_free_only -x` | No -- Wave 0 |
| QUOT-06c | compose() uses static fallback when tier=exhausted | unit | `python -m pytest tests/test_static_fallback.py::test_compose_static_on_exhaustion -x` | No -- Wave 0 |
| QUOT-06d | ContentPackage metadata has background_source=static and fallback_reason=quota_exhausted | unit | `python -m pytest tests/test_static_fallback.py::test_metadata_on_exhaustion -x` | No -- Wave 0 |
| QUOT-06e | compose() backward compatible without user_id/session | unit | `python -m pytest tests/test_static_fallback.py::test_compose_no_auth_backward_compat -x` | No -- Wave 0 |
| QUOT-06f | fallback_reason distinguishes quota_exhausted vs generation_failed vs mode_static | unit | `python -m pytest tests/test_static_fallback.py::test_fallback_reason_values -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_static_fallback.py tests/test_key_selector.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_static_fallback.py` -- covers QUOT-06c, QUOT-06d, QUOT-06e, QUOT-06f
- [ ] New tests in `tests/test_key_selector.py` -- covers QUOT-06a, QUOT-06b

## Project Constraints (from CLAUDE.md)

- Stack: Python, google-genai SDK, Pillow, SQLAlchemy async
- Models: Gemini models listed in CLAUDE.md (not relevant to this phase -- no model calls)
- 0=unlimited semantics consistent with Phase 8 D-07
- Pipeline integration via `python -m src.pipeline_cli --mode once`
- API key from env: `GOOGLE_API_KEY` (free), `GOOGLE_API_KEY_PAID` (paid)

## Sources

### Primary (HIGH confidence)
- `src/services/key_selector.py` -- current resolve() implementation, KeyResolution dataclass
- `src/pipeline/workers/image_worker.py` -- current compose() with static fallback at line 192
- `src/database/repositories/usage_repo.py` -- check_limit() API with 0=unlimited
- `src/pipeline/workers/generation_layer.py` -- compose() call sites at lines 105, 109, 130
- `src/api/routes/generation.py` -- _resolve_key() and _increment_usage() helpers
- `src/api/routes/pipeline.py` -- _run_pipeline_task() pipeline execution context
- `tests/test_key_selector.py` -- existing test patterns for key selector

### Secondary (MEDIUM confidence)
- `.planning/phases/10-static-fallback/10-CONTEXT.md` -- all locked decisions D-01 through D-08

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing code
- Architecture: HIGH -- all integration points examined, changes are surgical
- Pitfalls: HIGH -- based on direct code reading, known edge cases documented

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies changing)
