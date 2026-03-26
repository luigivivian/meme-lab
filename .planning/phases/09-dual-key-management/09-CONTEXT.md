# Phase 9: Dual Key Management - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

UsageAwareKeySelector that resolves which Gemini API key (free vs paid) to use based on daily usage from Phase 8's UsageRepository. Covers QUOT-04 and QUOT-05. Does NOT include fallback to static backgrounds (Phase 10) or usage dashboard (Phase 11).

</domain>

<decisions>
## Implementation Decisions

### Missing Paid Key Behavior
- **D-01:** If `GOOGLE_API_KEY_PAID` is not set, system operates in **free-only mode**. Warning log at startup ("Paid key not configured — free-only mode"). When free limit is hit, falls through to Phase 10 fallback chain (no error).
- **D-02:** If `GOOGLE_API_KEY_PAID` equals `GOOGLE_API_KEY` (identical keys), detect at startup, log WARNING ("Paid key identical to free key — treating as free-only"), and operate in free-only mode. Prevents wasted retry on an exhausted key.

### Key Switch Trigger & Flow
- **D-03:** `resolve()` checks `UsageRepository.check_limit()` on **every call**. No caching. Given low volume (~15 images/day on free tier), the extra DB query is negligible.
- **D-04:** No active reset listener at midnight. Since resolve() checks every call, the first image generation after midnight PT naturally sees usage=0 and returns the free key.

### Integration with GeminiImageClient
- **D-05:** `UsageAwareKeySelector` lives in a **new module** (`src/services/key_selector.py`). GeminiImageClient receives it as a dependency. Clean separation of concerns: key management vs image generation.
- **D-06:** `resolve()` returns enough info for the caller to log the correct tier to `api_usage`. The caller (GeminiImageClient) uses the returned key to create/select the appropriate genai Client.

### Manual Override / Force Tier
- **D-07:** `GEMINI_FORCE_TIER` env var (`free` | `paid`). When set, `resolve()` always returns that tier's key, skipping usage checks. Useful for testing and debugging.
- **D-08:** Per-request API parameter (`?force_tier=paid`) available on generation endpoints. **Admin-only** — requires `role=admin` check. Regular users always get automatic selection.
- **D-09:** Priority order: per-request param (if admin) > env var > automatic usage-based selection.

### Claude's Discretion
- Return type of `resolve()` — key string, tuple, or dataclass (as long as tier info is available for logging)
- Internal class structure and method signatures for UsageAwareKeySelector
- How GeminiImageClient creates/switches genai Client instances (new client per call vs cached per tier)
- Test strategy for the selector (mock UsageRepository, test all branches)
- Whether to add a `src/services/__init__.py` or keep flat

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 8 (Direct Predecessor)
- `.planning/phases/08-atomic-counter/08-CONTEXT.md` — UsageRepository API: `check_limit()`, `increment()`, `get_user_usage()`. Critical: pre-check flow (D-09), limit config via env vars (D-06/D-07).

### Phase 7 (Usage Table)
- `.planning/phases/07-usage-tracking-table/07-CONTEXT.md` — api_usage table schema, tier values (`gemini_free`, `gemini_paid`), status values.

### Database & Repository Pattern
- `src/database/repositories/usage_repo.py` — UsageRepository with `check_limit(user_id, service, tier)` returning `(allowed, info_dict)`. Key integration point.
- `src/database/repositories/user_repo.py` — Existing repository pattern to follow.

### Image Generation
- `src/image_gen/gemini_client.py` — GeminiImageClient, currently uses `_get_client()` from llm_client.py. This is where the selector gets injected.
- `src/llm_client.py` — `_get_client()` creates genai.Client with single GOOGLE_API_KEY.

### Auth & Roles
- `src/auth/` — JWT utils, get_current_user dependency, role checking for admin-only param.
- `src/api/routes/auth.py` — Existing auth routes.

### Requirements
- `.planning/REQUIREMENTS.md` — QUOT-04 (dual key management), QUOT-05 (UsageAwareKeySelector).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UsageRepository.check_limit(user_id, service, tier)` — returns `(allowed, info_dict)` with used/limit/remaining/resets_at. Direct input to resolve().
- `get_current_user` dependency — for JWT auth on endpoints.
- `get_daily_limit(service, tier)` — reads env vars with hardcoded defaults. Pattern for GEMINI_FORCE_TIER.
- Repository pattern in `src/database/repositories/` — 8 existing repos.

### Established Patterns
- Env var configuration: `{SERVICE}_DAILY_LIMIT_{TIER}` pattern (usage_repo.py).
- Async SQLAlchemy sessions via `session.py`.
- `_get_client()` in llm_client.py creates `genai.Client(api_key=...)` — pattern for creating tier-specific clients.
- Admin role check exists in user model (`role` column).

### Integration Points
- `src/image_gen/gemini_client.py` — Inject UsageAwareKeySelector, replace direct `_get_client()` usage for image generation.
- `src/services/` — New directory for key_selector.py (services layer).
- `src/api/routes/generation.py` — Add `force_tier` param with admin check.
- Pipeline workers (`src/pipeline/workers/image_worker.py`) — Future callers that use the selector.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for selector implementation. Key constraint: the system must work seamlessly with just the free key (no paid key required).

</specifics>

<deferred>
## Deferred Ideas

- **Static fallback when both keys exhausted** — Phase 10 (QUOT-06)
- **Usage dashboard widget** — Phase 11 (DASH-01, DASH-02, DASH-03)
- **Per-user API keys (BYOK)** — v2 multi-tenant feature (MT-V2-02)

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-dual-key-management*
*Context gathered: 2026-03-24*
