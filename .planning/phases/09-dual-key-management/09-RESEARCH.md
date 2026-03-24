# Phase 9: Dual Key Management - Research

**Researched:** 2026-03-24
**Domain:** Gemini API key selection, strategy pattern, async Python
**Confidence:** HIGH

## Summary

Phase 9 implements a `UsageAwareKeySelector` that resolves which Gemini API key (free vs paid) to use for image generation, based on daily usage tracked by Phase 8's `UsageRepository`. The selector is a pure logic component: it reads the current usage count via `check_limit()`, compares against the daily limit, and returns the appropriate key and tier metadata.

The existing codebase already has all the building blocks. `UsageRepository.check_limit(user_id, service, tier)` returns `(allowed, info_dict)` with used/limit/remaining/resets_at. The `_get_client()` function in `llm_client.py` creates `genai.Client(api_key=...)` instances. `GeminiImageClient` currently imports `_get_client` directly (line 18) and calls it in `_tentar_gerar()` (line 760) and `is_available()` (line 750). The integration requires replacing those direct `_get_client()` calls with a selector-resolved client.

**Primary recommendation:** Implement `UsageAwareKeySelector` as a standalone dataclass/class in `src/services/key_selector.py` with an async `resolve()` method. Inject it into `GeminiImageClient` as an optional dependency (defaulting to free-only behavior when not provided), keeping backward compatibility for notebook/CLI usage.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** If `GOOGLE_API_KEY_PAID` is not set, system operates in free-only mode. Warning log at startup. When free limit is hit, falls through to Phase 10 fallback chain (no error).
- **D-02:** If `GOOGLE_API_KEY_PAID` equals `GOOGLE_API_KEY` (identical keys), detect at startup, log WARNING, and operate in free-only mode.
- **D-03:** `resolve()` checks `UsageRepository.check_limit()` on every call. No caching.
- **D-04:** No active reset listener at midnight. First call after midnight naturally sees usage=0.
- **D-05:** `UsageAwareKeySelector` lives in a new module (`src/services/key_selector.py`). GeminiImageClient receives it as a dependency.
- **D-06:** `resolve()` returns enough info for the caller to log the correct tier to `api_usage`.
- **D-07:** `GEMINI_FORCE_TIER` env var (`free` | `paid`). When set, always returns that tier's key.
- **D-08:** Per-request API parameter (`?force_tier=paid`) on generation endpoints. Admin-only (requires `role=admin` check).
- **D-09:** Priority order: per-request param (if admin) > env var > automatic usage-based selection.

### Claude's Discretion
- Return type of `resolve()` -- key string, tuple, or dataclass (as long as tier info is available for logging)
- Internal class structure and method signatures for UsageAwareKeySelector
- How GeminiImageClient creates/switches genai Client instances (new client per call vs cached per tier)
- Test strategy for the selector (mock UsageRepository, test all branches)
- Whether to add a `src/services/__init__.py` or keep flat

### Deferred Ideas (OUT OF SCOPE)
- **Static fallback when both keys exhausted** -- Phase 10 (QUOT-06)
- **Usage dashboard widget** -- Phase 11 (DASH-01, DASH-02, DASH-03)
- **Per-user API keys (BYOK)** -- v2 multi-tenant feature (MT-V2-02)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUOT-04 | Dual key management: key free as default, key paid as fallback | UsageAwareKeySelector.resolve() checks UsageRepository.check_limit() and returns free key when under limit, paid key when over. Free-only mode when paid key absent (D-01/D-02). |
| QUOT-05 | UsageAwareKeySelector that resolves which key to use based on usage | New class in src/services/key_selector.py. Async resolve() method with force_tier override support. Returns dataclass with api_key + tier string for logging. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Stack: `google-genai` SDK, Python, Pillow
- Client creation pattern: `genai.Client(api_key=GOOGLE_API_KEY)`
- Free tier quota: ~15 images/day (Google AI Studio)
- API key env var: `GOOGLE_API_KEY` (free), `GOOGLE_API_KEY_PAID` (paid -- new)
- Force tier env var: `GEMINI_FORCE_TIER` (new)

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| google-genai | (existing) | Gemini API client creation | Already in project, `genai.Client(api_key=...)` |
| SQLAlchemy 2.0 | (existing) | Async DB sessions for UsageRepository | Already in project |
| FastAPI | (existing) | API route params, Depends injection | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | KeyResolution return type | For resolve() result |
| os / dotenv | stdlib + existing | Env var reading | For GOOGLE_API_KEY_PAID, GEMINI_FORCE_TIER |
| logging | stdlib | Startup warnings, tier switch logging | Always |

No new dependencies needed. This phase uses only existing libraries.

## Architecture Patterns

### Recommended Project Structure
```
src/services/
    __init__.py          # Already exists ("Servicos externos")
    key_selector.py      # NEW - UsageAwareKeySelector
    instagram_client.py  # Existing
    publisher.py         # Existing
    ...
```

### Pattern 1: Strategy / Resolver Pattern
**What:** `UsageAwareKeySelector` encapsulates the key selection logic. It receives `UsageRepository` (or session) as a dependency and returns a resolution result.
**When to use:** When the caller (GeminiImageClient) should not know about usage tracking logic.
**Example:**
```python
# src/services/key_selector.py
from dataclasses import dataclass

@dataclass
class KeyResolution:
    """Result of key selection -- carries key + tier for logging."""
    api_key: str
    tier: str  # "gemini_free" or "gemini_paid"
    mode: str  # "auto", "forced_env", "forced_request", "free_only"


class UsageAwareKeySelector:
    def __init__(self, free_key: str, paid_key: str | None = None):
        self._free_key = free_key
        self._paid_key = paid_key
        self._free_only = not paid_key or paid_key == free_key

    async def resolve(
        self,
        user_id: int,
        session: AsyncSession,
        force_tier: str | None = None,
    ) -> KeyResolution:
        # D-09: priority order
        # 1. force_tier param (from API admin or env var)
        # 2. automatic usage-based selection
        ...
```

### Pattern 2: Optional Dependency Injection in GeminiImageClient
**What:** `GeminiImageClient` accepts an optional `key_selector` parameter. When provided, it uses the selector to get the API key. When None (notebook/CLI usage), it falls back to the existing `_get_client()` singleton.
**When to use:** To maintain backward compatibility with notebook and pipeline CLI usage.
**Example:**
```python
# In GeminiImageClient.__init__
class GeminiImageClient:
    def __init__(self, ..., key_selector=None):
        self._key_selector = key_selector
        ...

    def _get_image_client(self, api_key: str | None = None) -> genai.Client:
        """Get genai Client for image generation.
        If api_key provided (from selector), create/cache per-tier client.
        Otherwise fall back to default _get_client().
        """
        if api_key:
            return genai.Client(api_key=api_key)
        return _get_client()  # existing singleton
```

### Pattern 3: Startup Validation
**What:** At application startup (in `app.py` or lifespan), validate key configuration and log warnings.
**When to use:** Always -- per D-01 and D-02.
**Example:**
```python
# At startup
free_key = os.getenv("GOOGLE_API_KEY", "")
paid_key = os.getenv("GOOGLE_API_KEY_PAID", "")

if not paid_key:
    logger.warning("GOOGLE_API_KEY_PAID not configured -- free-only mode")
elif paid_key == free_key:
    logger.warning("GOOGLE_API_KEY_PAID identical to GOOGLE_API_KEY -- treating as free-only")
    paid_key = ""  # normalize to free-only
```

### Anti-Patterns to Avoid
- **Global mutable client switching:** Do NOT modify the global `_client` singleton in `llm_client.py`. Create separate client instances per tier in the selector or GeminiImageClient.
- **Caching check_limit results:** D-03 explicitly says no caching. The volume is ~15 calls/day, so the DB query cost is negligible.
- **Raising errors when paid key is missing:** D-01 says fall through to Phase 10 fallback chain, not raise exceptions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timezone-aware daily bucketing | Custom UTC/PT logic | `UsageRepository._get_pt_today_start_utc()` | Already implemented correctly in Phase 8 |
| Atomic usage counting | Custom counter logic | `UsageRepository.check_limit()` / `increment()` | Already implemented with dialect-aware upsert |
| JWT auth + role checking | Custom auth middleware | `get_current_user` from `src/api/deps.py` + `user.role` check | Already implemented in Phase 3 |
| genai Client creation | Custom wrapper | `genai.Client(api_key=key)` | SDK handles connection pooling internally |

## Common Pitfalls

### Pitfall 1: Modifying the Global _client Singleton
**What goes wrong:** Changing `_client` in `llm_client.py` to point to a different key breaks all concurrent text-generation calls that also use that singleton.
**Why it happens:** The temptation to reuse the existing global client pattern.
**How to avoid:** Create separate `genai.Client` instances for image generation. The text LLM client (`llm_client._get_client()`) stays on the free key. Only image generation uses the selector.
**Warning signs:** Tests passing individually but failing when run together.

### Pitfall 2: Sync resolve() in Async Context
**What goes wrong:** `UsageRepository.check_limit()` is async (uses `await session.execute()`). Calling it from the sync `_tentar_gerar()` method in `GeminiImageClient` would fail.
**Why it happens:** `GeminiImageClient.generate_image()` and `_tentar_gerar()` are sync methods.
**How to avoid:** Resolve the key BEFORE entering the sync generation methods. The API route handler (which is async) calls `selector.resolve()` first, then passes the resolved key to `GeminiImageClient`. Alternatively, create an `asyncio.run()` wrapper if called from sync context (pipeline CLI).
**Warning signs:** "cannot call await in sync function" errors.

### Pitfall 3: Force Tier Without Admin Check
**What goes wrong:** Any user can force the paid tier via API parameter, consuming paid quota.
**Why it happens:** Forgetting to add role validation on the `force_tier` query param.
**How to avoid:** Check `user.role == "admin"` when `force_tier` is provided in the request. If non-admin sends force_tier, ignore it (or return 403).
**Warning signs:** Non-admin users able to set force_tier in API calls.

### Pitfall 4: Not Handling Missing Free Key
**What goes wrong:** If `GOOGLE_API_KEY` is empty, the selector should still fail gracefully.
**Why it happens:** Only checking for paid key absence, not free key.
**How to avoid:** If free key is empty, raise ValueError at startup (existing behavior from `_get_client()`).
**Warning signs:** Cryptic errors from genai.Client with empty API key.

### Pitfall 5: Creating Too Many genai.Client Instances
**What goes wrong:** Creating a new `genai.Client` on every image generation call wastes resources.
**Why it happens:** Naive implementation of "use resolved key each time."
**How to avoid:** Cache two client instances (one per tier) in `GeminiImageClient` or in the selector. Since there are only 2 possible keys, a dict cache is trivial.
**Warning signs:** Slow performance, high memory usage.

## Code Examples

### Key Selector Module
```python
# src/services/key_selector.py
import logging
import os
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.usage_repo import UsageRepository

logger = logging.getLogger("clip-flow.key_selector")


@dataclass(frozen=True)
class KeyResolution:
    """Immutable result of key resolution."""
    api_key: str
    tier: str       # "gemini_free" or "gemini_paid"
    mode: str       # "auto", "forced_env", "forced_request", "free_only"


class UsageAwareKeySelector:
    """Selects Gemini API key based on daily usage limits.

    Priority (D-09): force_tier param > GEMINI_FORCE_TIER env > auto usage-based.
    """

    def __init__(self):
        self._free_key = os.getenv("GOOGLE_API_KEY", "")
        self._paid_key = os.getenv("GOOGLE_API_KEY_PAID", "")
        self._force_tier_env = os.getenv("GEMINI_FORCE_TIER", "").lower()

        # D-01, D-02: detect free-only mode
        if not self._paid_key:
            self._free_only = True
            logger.warning("GOOGLE_API_KEY_PAID not configured -- free-only mode")
        elif self._paid_key == self._free_key:
            self._free_only = True
            self._paid_key = ""
            logger.warning("GOOGLE_API_KEY_PAID identical to free key -- free-only mode")
        else:
            self._free_only = False

    async def resolve(
        self,
        user_id: int,
        session: AsyncSession,
        force_tier: str | None = None,
    ) -> KeyResolution:
        """Resolve which API key to use.

        Args:
            user_id: Current user ID for usage lookup.
            session: DB session for UsageRepository.
            force_tier: Per-request override ("free"/"paid"), admin-only.

        Returns:
            KeyResolution with api_key, tier, and mode.
        """
        # D-09 priority 1: per-request force (already admin-validated by caller)
        if force_tier:
            return self._forced_resolution(force_tier, mode="forced_request")

        # D-09 priority 2: env var force
        if self._force_tier_env in ("free", "paid"):
            return self._forced_resolution(self._force_tier_env, mode="forced_env")

        # D-09 priority 3: automatic usage-based
        if self._free_only:
            return KeyResolution(
                api_key=self._free_key,
                tier="gemini_free",
                mode="free_only",
            )

        # D-03: check usage on every call
        repo = UsageRepository(session)
        allowed, info = await repo.check_limit(user_id, "gemini_image", "free")

        if allowed:
            return KeyResolution(
                api_key=self._free_key,
                tier="gemini_free",
                mode="auto",
            )
        else:
            logger.info(
                "Free tier limit reached (used=%d/%d), switching to paid key",
                info["used"], info["limit"],
            )
            return KeyResolution(
                api_key=self._paid_key,
                tier="gemini_paid",
                mode="auto",
            )

    def _forced_resolution(self, tier: str, mode: str) -> KeyResolution:
        if tier == "paid" and self._free_only:
            logger.warning("Force paid requested but no paid key -- using free")
            return KeyResolution(api_key=self._free_key, tier="gemini_free", mode=mode)
        if tier == "paid":
            return KeyResolution(api_key=self._paid_key, tier="gemini_paid", mode=mode)
        return KeyResolution(api_key=self._free_key, tier="gemini_free", mode=mode)
```

### GeminiImageClient Integration Point
```python
# In _tentar_gerar() -- accept api_key parameter
def _tentar_gerar(self, modelo: str, partes: list, temperatura: float,
                  api_key: str | None = None) -> PIL.Image.Image | None:
    from google.genai import types
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = _get_client()  # fallback to existing singleton
    response = client.models.generate_content(...)
```

### Admin Check in Generation Route
```python
# In src/api/routes/generation.py
from src.api.deps import get_current_user, db_session

@router.post("/single")
async def generate_single(
    req: SingleRequest,
    force_tier: str | None = Query(None, regex="^(free|paid)$"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    # D-08: admin-only force_tier
    effective_force = None
    if force_tier and current_user.role == "admin":
        effective_force = force_tier
    elif force_tier:
        # Non-admin tried to force tier -- ignore silently
        pass

    selector = UsageAwareKeySelector()
    resolution = await selector.resolve(
        user_id=current_user.id,
        session=session,
        force_tier=effective_force,
    )
    # Use resolution.api_key for image generation
    # Log resolution.tier to api_usage after success
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single global API key | Per-call key resolution | This phase | Enables cost optimization via free-first strategy |
| `_get_client()` singleton | Tier-aware client creation | This phase | Image gen can use different keys without affecting text gen |

**No deprecated patterns** -- google-genai SDK `Client(api_key=...)` is the current standard.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_key_selector.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUOT-04 | Free key used when under limit | unit | `python -m pytest tests/test_key_selector.py::test_resolve_returns_free_when_under_limit -x` | Wave 0 |
| QUOT-04 | Paid key used when over limit | unit | `python -m pytest tests/test_key_selector.py::test_resolve_returns_paid_when_over_limit -x` | Wave 0 |
| QUOT-04 | Free-only mode when paid key missing | unit | `python -m pytest tests/test_key_selector.py::test_free_only_mode_no_paid_key -x` | Wave 0 |
| QUOT-04 | Free-only mode when keys identical | unit | `python -m pytest tests/test_key_selector.py::test_free_only_mode_identical_keys -x` | Wave 0 |
| QUOT-05 | Force tier via env var | unit | `python -m pytest tests/test_key_selector.py::test_force_tier_env -x` | Wave 0 |
| QUOT-05 | Force tier via request param (admin) | unit | `python -m pytest tests/test_key_selector.py::test_force_tier_request_admin -x` | Wave 0 |
| QUOT-05 | Force tier ignored for non-admin | integration | `python -m pytest tests/test_key_selector.py::test_force_tier_ignored_non_admin -x` | Wave 0 |
| QUOT-05 | Tier logged correctly | unit | `python -m pytest tests/test_key_selector.py::test_resolution_tier_value -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_key_selector.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_key_selector.py` -- covers QUOT-04, QUOT-05 (all branches)
- [ ] Mock `UsageRepository` to avoid real DB in unit tests (follow test_atomic_counter.py pattern with SQLite in-memory)

## Open Questions

1. **Client caching strategy in GeminiImageClient**
   - What we know: Only 2 possible keys (free, paid). Creating a `genai.Client` is lightweight.
   - What's unclear: Whether genai.Client has internal connection pooling that benefits from reuse.
   - Recommendation: Cache two clients in a dict keyed by api_key. Simple, safe, and avoids repeated instantiation. This is Claude's discretion per CONTEXT.md.

2. **Pipeline CLI (sync) usage of selector**
   - What we know: `pipeline_cli.py` runs sync. Selector.resolve() is async.
   - What's unclear: Whether pipeline CLI will use the selector in this phase.
   - Recommendation: For this phase, only wire the selector into API routes (which are async). Pipeline integration deferred to a future sprint (per CONTEXT.md code_context noting "Future callers").

## Sources

### Primary (HIGH confidence)
- `src/database/repositories/usage_repo.py` -- UsageRepository API (check_limit, increment, get_daily_limit)
- `src/image_gen/gemini_client.py` -- GeminiImageClient class, _get_client() usage points (lines 18, 49, 750, 760)
- `src/llm_client.py` -- _get_client() singleton pattern, genai.Client creation
- `src/api/deps.py` -- get_current_user dependency, db_session dependency
- `src/database/models.py` -- User.role field (line 512), User.gemini_free_key/gemini_paid_key fields
- `.planning/phases/08-atomic-counter/08-CONTEXT.md` -- Phase 8 decisions on check_limit flow
- `.planning/phases/09-dual-key-management/09-CONTEXT.md` -- All D-01 through D-09 decisions

### Secondary (MEDIUM confidence)
- `tests/test_atomic_counter.py` -- Test pattern (SQLite in-memory, register_and_login helper)
- `src/services/__init__.py` -- Existing services module structure

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new deps
- Architecture: HIGH -- patterns derived from existing codebase, decisions locked in CONTEXT.md
- Pitfalls: HIGH -- identified from direct code reading (sync/async mismatch, global singleton)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain, no external API changes expected)
