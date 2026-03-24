# Phase 10: Static Fallback - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 10-static-fallback
**Areas discussed:** Exhaustion detection, Fallback integration point, Static background selection, Logging & observability

---

## Exhaustion Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-check in KeySelector | KeySelector.resolve() checks BOTH free and paid limits. Returns tier='exhausted' when both spent. No wasted API calls. | ✓ |
| Let Gemini fail, catch error | Keep KeySelector as-is. Gemini returns 429, ImageWorker catches and falls through to static. Wastes one API call. | |
| Boolean flag on KeyResolution | Add exhausted: bool field to KeyResolution. resolve() still returns paid key but flags exhausted=True. | |

**User's choice:** Pre-check in KeySelector
**Notes:** None

### Follow-up: Free-only mode behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Exhaust immediately | In free-only mode, free limit hit → tier='exhausted' right away. | ✓ |
| Try anyway | Still return free key even at limit. Let API error be signal. | |

**User's choice:** Exhaust immediately
**Notes:** Consistent behavior — pre-check always prevents wasted calls.

### Follow-up: 0 = unlimited semantics

| Option | Description | Selected |
|--------|-------------|----------|
| 0 = unlimited, never exhausted | Consistent with Phase 8 D-07. Free tier never hits 'exhausted' when limit is 0. | ✓ |
| 0 = disabled, always exhausted | Treat 0 as 'tier disabled'. Skip to next tier or static. | |

**User's choice:** 0 = unlimited, never exhausted
**Notes:** Consistent with Phase 8 D-07.

---

## Fallback Integration Point

| Option | Description | Selected |
|--------|-------------|----------|
| Inside ImageWorker.compose() | Before Gemini/ComfyUI priority chain, call KeySelector.resolve(). If 'exhausted', skip _try_gemini() and go static. | ✓ |
| Inside _try_gemini() | Move usage check into _try_gemini(). Returns (None, 'static', {}) when exhausted. | |
| In GeminiImageClient | Push check deeper — agenerate_image() checks quota before API call. | |

**User's choice:** Inside ImageWorker.compose()
**Notes:** Minimal changes — one check at the top of the existing flow.

### Follow-up: Passing user_id/session to compose()

| Option | Description | Selected |
|--------|-------------|----------|
| Add params to compose() | Add user_id and session as optional params. When None, skip check. Backward compatible. | ✓ |
| Inject selector at __init__ | Pass pre-configured KeySelector + user_id + session_factory into constructor. | |
| You decide | Claude picks the approach. | |

**User's choice:** Add params to compose()
**Notes:** Backward compatible for CLI/script usage without auth.

---

## Static Background Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Random is fine | Keep random.choice(). All backgrounds work for any situation. | ✓ |
| Theme-aware selection | Tag backgrounds with situacao keys. Match first, random fallback. | |
| Weighted random | Track recently used, prefer less-used. Adds state tracking. | |

**User's choice:** Random is fine
**Notes:** Per-character reference dirs already handle multi-character.

---

## Logging & Observability

| Option | Description | Selected |
|--------|-------------|----------|
| Log + metadata | WARNING log + background_source='static' in ContentPackage. No new infrastructure. | ✓ |
| Log + metadata + counter | Same plus increment 'static_fallback' counter in api_usage. | |
| Log only | Just log. Metadata already tracks background_source. | |

**User's choice:** Log + metadata
**Notes:** None

### Follow-up: Distinguishing fallback reasons

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add fallback_reason | Add 'fallback_reason' to metadata: 'quota_exhausted', 'generation_failed', 'mode_static'. | ✓ |
| No, just 'static' | background_source='static' is enough. | |

**User's choice:** Yes, add fallback_reason
**Notes:** Helps debugging and Phase 11 dashboard.

---

## Claude's Discretion

- Internal implementation of paid-tier limit check in resolve()
- Whether fallback_reason goes in metadata dict or as new dataclass field
- Test strategy for exhaustion flow
- Error handling if DB session unavailable during pre-check

## Deferred Ideas

- Usage dashboard showing static fallback stats (Phase 11)
- Theme-aware background selection (future)
- Weighted/LRU background selection (future)
- Static fallback counter in api_usage table (future)
