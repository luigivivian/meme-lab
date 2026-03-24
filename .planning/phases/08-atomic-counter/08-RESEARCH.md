# Phase 8: Atomic Counter - Research

**Researched:** 2026-03-24
**Domain:** Atomic database counters, SQLAlchemy upsert, FastAPI usage endpoints
**Confidence:** HIGH

## Summary

Phase 8 adds three capabilities on top of the Phase 7 `api_usage` table: (1) an atomic increment operation that is safe under concurrent access, (2) configurable daily limits read from environment variables, and (3) a `GET /auth/me/usage` endpoint returning per-service consumption. The core technical challenge is implementing `INSERT ... ON DUPLICATE KEY UPDATE` via SQLAlchemy in a way that works with MySQL in production and SQLite in tests, with a critical pitfall around NULL `user_id` values in the unique constraint.

The project uses SQLAlchemy 2.0.47 (async, aiomysql for MySQL, aiosqlite for SQLite tests), FastAPI with Pydantic schemas, and the repository pattern established across 7 existing repositories. The atomic increment can be fully achieved using dialect-specific `insert()` functions from `sqlalchemy.dialects.mysql` and `sqlalchemy.dialects.sqlite`, both of which support upsert semantics. Tests use SQLite in-memory with session singleton reset.

**Primary recommendation:** Build a `UsageRepository` with a dialect-aware `increment()` method that detects the database backend and dispatches to the correct upsert syntax. For the NULL user_id edge case, use a sentinel value (e.g., `user_id=0`) for system/shared usage, or use a SELECT-then-UPDATE/INSERT pattern within a transaction for NULL user_id rows.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Claude's discretion on HTTP status code (429 recommended as standard rate-limiting code)
- D-02: Rejection response MUST include usage details: {used, limit, remaining: 0, resets_at: "<PT midnight ISO>"}
- D-03: A `rejected` status row is written to `api_usage` when a call is blocked (per Phase 7 D-05)
- D-04: GET /auth/me/usage returns per-service breakdown: {services: [{service: "gemini_image", tier: "free", used: N, limit: M, remaining: M-N}, ...], resets_at: "..."}. Supports Phase 11 dashboard needs
- D-05: Endpoint requires JWT authentication (uses `get_current_user` dependency). No system/shared usage endpoint in this phase
- D-06: Per-service env vars: `GEMINI_IMAGE_DAILY_LIMIT_FREE`, `GEMINI_TEXT_DAILY_LIMIT_FREE`, etc. Matches Google's per-model limits
- D-07: Missing env var = sensible hardcoded default (e.g., 15 for gemini_image free). Setting to 0 = unlimited (no limit enforced). Useful for paid tier or testing
- D-08: `INSERT ... ON DUPLICATE KEY UPDATE usage_count = usage_count + 1` for atomic increments. Leverages Phase 7's UniqueConstraint on (user_id, service, tier, date). No explicit row locking needed
- D-09: Pre-check flow: check current count < limit BEFORE calling external API. If at limit, reject immediately (no wasted API call). Increment usage_count only after successful API response

### Claude's Discretion
- HTTP status code for rejection (429 recommended)
- UsageRepository class structure and method signatures
- Default limit values per service
- Error response schema details beyond the required fields
- Test strategy for concurrency (e.g., asyncio.gather with N tasks)

### Deferred Ideas (OUT OF SCOPE)
- UsageAwareKeySelector -- Phase 9 (QUOT-04, QUOT-05)
- Static fallback when both keys exhausted -- Phase 10 (QUOT-06)
- GET /usage/system for shared key stats (admin) -- Future
- Usage history (last 30 days) -- Phase 11 / v2 dashboard feature
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUOT-02 | Tracking atomico de uso por usuario por dia (SELECT FOR UPDATE) | Dialect-specific upsert via `sqlalchemy.dialects.mysql.insert` / `sqlalchemy.dialects.sqlite.insert` with `on_duplicate_key_update` / `on_conflict_do_update`. Verified working on SQLAlchemy 2.0.47 |
| QUOT-03 | Limites diarios configuraveis via env vars (GEMINI_IMAGE_DAILY_LIMIT_FREE) | Config pattern using `os.getenv()` with hardcoded defaults per service/tier, 0 = unlimited convention |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.47 | ORM, async session, dialect-specific insert | Already installed, project standard |
| FastAPI | (installed) | API endpoint for usage | Already installed, project standard |
| Pydantic | (installed) | Response schemas | Already installed, project standard |
| zoneinfo | stdlib | PT timezone conversion | Project pattern from Phase 7 D-04 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy.dialects.mysql | (bundled) | `insert().on_duplicate_key_update()` | Production MySQL upsert |
| sqlalchemy.dialects.sqlite | (bundled) | `insert().on_conflict_do_update()` | Test SQLite upsert |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dialect-specific upsert | SELECT FOR UPDATE + manual INSERT/UPDATE | More code, explicit locking, but backend-agnostic. Decision D-08 locks us to upsert approach |
| Dialect-specific upsert | Raw SQL text() | Simpler but loses ORM type safety and SQLite test compat |

**Installation:** No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/database/repositories/
    usage_repo.py          # NEW: UsageRepository (increment, check_limit, get_usage)
src/api/routes/
    auth.py                # MODIFY: Add GET /auth/me/usage endpoint
src/auth/
    schemas.py             # MODIFY: Add UsageResponse, ServiceUsage schemas
config.py                  # MODIFY: Add usage limit env vars
tests/
    test_atomic_counter.py # NEW: Concurrency + limit + endpoint tests
```

### Pattern 1: Dialect-Aware Upsert
**What:** Detect database backend at runtime and use the correct dialect-specific insert for atomic increment.
**When to use:** Every usage increment call.
**Example:**
```python
# Source: Verified with SQLAlchemy 2.0.47 on this project
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

class UsageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _is_sqlite(self) -> bool:
        return "sqlite" in str(self.session.bind.url)

    async def increment(
        self, user_id: int, service: str, tier: str, status: str = "success"
    ) -> int:
        """Atomically increment usage_count for today. Returns new count."""
        today_utc = self._get_pt_today_as_utc()

        if self._is_sqlite():
            stmt = sqlite_insert(ApiUsage).values(
                user_id=user_id, service=service, tier=tier,
                date=today_utc, usage_count=1, status=status,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "service", "tier", "date"],
                set_={"usage_count": ApiUsage.usage_count + 1},
            )
        else:
            stmt = mysql_insert(ApiUsage).values(
                user_id=user_id, service=service, tier=tier,
                date=today_utc, usage_count=1, status=status,
            )
            stmt = stmt.on_duplicate_key_update(
                usage_count=ApiUsage.usage_count + 1,
            )

        await self.session.execute(stmt)
        await self.session.flush()

        # Read back current count
        result = await self.session.execute(
            select(ApiUsage.usage_count).where(
                ApiUsage.user_id == user_id,
                ApiUsage.service == service,
                ApiUsage.tier == tier,
                ApiUsage.date == today_utc,
            )
        )
        return result.scalar_one()
```

### Pattern 2: Pre-Check + Increment Flow (D-09)
**What:** Two-step flow: check limit before API call, then increment after success.
**When to use:** Any code path that calls an external API.
**Example:**
```python
async def check_and_increment(
    self, user_id: int, service: str, tier: str
) -> tuple[bool, dict]:
    """Check if under limit. Returns (allowed, usage_info).

    Does NOT increment -- caller must call increment() after successful API call.
    """
    today_utc = self._get_pt_today_as_utc()
    current = await self._get_current_count(user_id, service, tier, today_utc)
    limit = get_daily_limit(service, tier)

    if limit > 0 and current >= limit:
        # Write rejected row (D-03)
        await self._write_rejected(user_id, service, tier, today_utc)
        return False, {
            "used": current, "limit": limit, "remaining": 0,
            "resets_at": self._next_pt_midnight_iso(),
        }

    return True, {
        "used": current, "limit": limit, "remaining": limit - current,
        "resets_at": self._next_pt_midnight_iso(),
    }
```

### Pattern 3: Limit Configuration via Env Vars (D-06, D-07)
**What:** Read daily limits from environment with sensible defaults.
**When to use:** At limit-check time, not at import time (allows runtime changes).
**Example:**
```python
import os

# Sensible defaults matching Google AI Studio free tier
_DEFAULT_LIMITS = {
    ("gemini_image", "free"): 15,
    ("gemini_text", "free"): 500,
    ("gemini_web", "free"): 500,
    ("comfyui", "free"): 0,     # 0 = unlimited (local)
    ("gemini_image", "paid"): 0, # 0 = unlimited
    ("gemini_text", "paid"): 0,
}

def get_daily_limit(service: str, tier: str) -> int:
    """Read limit from env var, fallback to hardcoded default.
    Returns 0 for unlimited."""
    env_key = f"{service.upper()}_DAILY_LIMIT_{tier.upper()}"
    env_val = os.getenv(env_key)
    if env_val is not None:
        return int(env_val)
    return _DEFAULT_LIMITS.get((service, tier), 50)
```

### Anti-Patterns to Avoid
- **Application-level locking (asyncio.Lock):** Does NOT protect against multi-process or multi-worker scenarios. The database upsert IS the lock mechanism.
- **SELECT count then INSERT separately without transaction:** Classic TOCTOU race condition. The upsert atomic operation avoids this.
- **Hardcoding limits in source code without env override:** Violates D-06. Always check env vars first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic increment | Manual SELECT + UPDATE with locking | `INSERT ... ON DUPLICATE KEY UPDATE` via SQLAlchemy dialect | Database handles atomicity, no explicit locks needed |
| Timezone conversion | MySQL CONVERT_TZ() | `zoneinfo.ZoneInfo("America/Los_Angeles")` in Python | Phase 7 D-04: keeps SQLite test compatibility |
| Rate limit response | Custom error format | FastAPI `HTTPException(status_code=429)` with detail dict | Standard HTTP semantics, D-01 recommendation |

**Key insight:** The database engine's upsert mechanism IS the concurrency solution. No application-level locks, mutexes, or distributed coordination needed for this use case.

## Common Pitfalls

### Pitfall 1: NULL user_id Breaks Upsert
**What goes wrong:** SQLite (and SQL standard) treats NULL != NULL in unique constraints. Two inserts with `user_id=None` create TWO rows instead of incrementing one.
**Why it happens:** The UniqueConstraint `(user_id, service, tier, date)` does not fire ON CONFLICT when user_id is NULL because NULL is not equal to NULL.
**How to avoid:** For this phase, all usage is per-authenticated-user (D-05 requires JWT). The `user_id` will always be non-NULL. System/shared usage (user_id=NULL) is deferred. If ever needed, use a sentinel user_id (e.g., 0) or a separate query path with explicit SELECT-for-UPDATE.
**Warning signs:** Verified experimentally on this project -- two upserts with user_id=None produce usage_count=[1, 1] instead of [2].
**Confidence:** HIGH -- tested directly on the project codebase.

### Pitfall 2: PT Timezone Date Boundary
**What goes wrong:** Usage counted against wrong day when crossing midnight PT boundary.
**Why it happens:** Google resets quotas at midnight Pacific Time (America/Los_Angeles), not UTC. A request at 2026-03-25 01:00 UTC is still 2026-03-24 in PT.
**How to avoid:** Convert current UTC time to PT, extract the date, then convert BACK to UTC midnight of that PT date for storage. This matches Phase 7 D-03/D-04 pattern.
**Warning signs:** Usage appears to reset at wrong time, or usage counts are split between two date rows near PT midnight.
**Confidence:** HIGH -- documented in STATE.md blockers and Phase 7 context.

### Pitfall 3: Dialect Detection in Async Session
**What goes wrong:** `session.bind` may be None for async sessions obtained via dependency injection.
**Why it happens:** Async sessions created by `async_sessionmaker` may not have `bind` set directly accessible in the same way sync sessions do.
**How to avoid:** Use the `DATABASE_URL` string from config.py directly to detect dialect, not the session object. `"sqlite" in DATABASE_URL` is the established project pattern (see `session.py:_is_sqlite()`).
**Warning signs:** AttributeError on session.bind or NoneType errors.
**Confidence:** HIGH -- verified by reading `src/database/session.py` line 12.

### Pitfall 4: Race Between Check and Increment (D-09 Gap)
**What goes wrong:** Two concurrent requests both pass the pre-check (count < limit), both call the API, both increment -- resulting in count exceeding limit by 1.
**Why it happens:** D-09 specifies check BEFORE API call, increment AFTER. There is an inherent race window between check and increment.
**How to avoid:** Accept this as acceptable behavior -- the limit is soft, not a billing boundary. The count can exceed the limit by at most (N_concurrent - 1). For hard limits, the increment itself should be the gate (increment first, rollback if API fails). Phase 8 success criteria says "10 concurrent calls do not result in count ABOVE 10" -- this tests the increment atomicity, not the check+increment flow.
**Warning signs:** Usage slightly exceeding configured limit under concurrent load.
**Confidence:** HIGH -- this is a well-known TOCTOU pattern.

### Pitfall 5: SQLite ON CONFLICT Requires Matching Index Elements
**What goes wrong:** `on_conflict_do_update(index_elements=[...])` must exactly match the columns in a unique constraint or unique index. Mismatches silently fail or error.
**Why it happens:** SQLite requires specifying which unique constraint to target via column names.
**How to avoid:** Use exactly `["user_id", "service", "tier", "date"]` matching the UniqueConstraint definition.
**Confidence:** HIGH -- verified experimentally.

## Code Examples

### Usage Response Schema (for GET /auth/me/usage)
```python
# Source: Follows existing auth/schemas.py pattern
from pydantic import BaseModel

class ServiceUsage(BaseModel):
    service: str
    tier: str
    used: int
    limit: int
    remaining: int

class UsageResponse(BaseModel):
    services: list[ServiceUsage]
    resets_at: str  # ISO 8601 datetime of next PT midnight
```

### Usage Endpoint in auth.py
```python
# Source: Follows existing /auth/me pattern
@router.get("/me/usage", response_model=UsageResponse)
async def me_usage(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return current user's API usage for today (QUOT-02, QUOT-03)."""
    repo = UsageRepository(session)
    return await repo.get_user_usage(current_user.id)
```

### PT Timezone Helper
```python
# Source: Phase 7 D-04, using stdlib zoneinfo
from datetime import datetime, time
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")

def get_pt_today_start_utc() -> datetime:
    """Get start of 'today' in PT as a UTC datetime."""
    now_pt = datetime.now(PT)
    start_of_day_pt = datetime.combine(now_pt.date(), time.min, tzinfo=PT)
    return start_of_day_pt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

def next_pt_midnight_iso() -> str:
    """ISO 8601 string of next PT midnight (for resets_at field)."""
    from datetime import timedelta
    now_pt = datetime.now(PT)
    tomorrow_pt = datetime.combine(
        now_pt.date() + timedelta(days=1), time.min, tzinfo=PT
    )
    return tomorrow_pt.isoformat()
```

### Concurrency Test Pattern
```python
# Source: Project test pattern (test_auth.py) + asyncio.gather for concurrency
@pytest.mark.asyncio
async def test_concurrent_increments_atomic(client):
    """10 concurrent calls must result in usage_count=10, not more."""
    # Register + login to get token
    token = await _get_auth_token(client)

    # Simulate 10 concurrent image generation success increments
    async def increment_once():
        # Direct repository call via test session, or via a thin endpoint
        ...

    results = await asyncio.gather(*[increment_once() for _ in range(10)])

    # Verify final count
    resp = await client.get("/auth/me/usage", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    gemini_image = next(s for s in data["services"] if s["service"] == "gemini_image")
    assert gemini_image["used"] == 10
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SELECT FOR UPDATE + manual increment | INSERT ON DUPLICATE KEY UPDATE | MySQL 5.7+ / SQLAlchemy 1.4+ | Simpler, fewer round-trips, inherently atomic |
| Redis for rate limiting | MySQL counter with upsert | Project decision (REQUIREMENTS.md) | No new infrastructure needed |
| Global rate limiter (slowapi) | Per-user per-service quota tracking | Project decision | Fine-grained control per user and API service |

**Deprecated/outdated:**
- `SELECT FOR UPDATE` is still valid but unnecessary when upsert is available. D-08 explicitly chose upsert.

## Open Questions

1. **Rejected row semantics with upsert**
   - What we know: D-03 says write a `rejected` status row when a call is blocked. The upsert targets (user_id, service, tier, date) composite key.
   - What's unclear: A rejected row and a success row for the same user/service/tier/date would need different handling since they share the same unique key. The rejected row should NOT increment usage_count.
   - Recommendation: Use a plain INSERT (not upsert) for rejected rows with a different `date` timestamp (include time component to avoid unique constraint collision), OR track rejected counts in a separate column, OR simply log rejections without a database row. The simplest approach: insert a rejected row with the exact current UTC timestamp (not just date bucket) so the unique constraint does not collide. This works because the `date` column is DateTime, not Date.

2. **Env var naming for paid tier**
   - What we know: D-06 says `GEMINI_IMAGE_DAILY_LIMIT_FREE` pattern.
   - What's unclear: Are paid tier limits also configurable? D-07 says "setting to 0 = unlimited" which implies paid tier defaults to 0.
   - Recommendation: Support `GEMINI_IMAGE_DAILY_LIMIT_PAID` but default to 0 (unlimited). Consistent naming.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | None explicit (uses defaults) |
| Quick run command | `python -m pytest tests/test_atomic_counter.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUOT-02 | 10 concurrent increments result in count=10 | integration | `python -m pytest tests/test_atomic_counter.py::test_concurrent_increments -x` | Wave 0 |
| QUOT-02 | Single increment creates/updates row correctly | unit | `python -m pytest tests/test_atomic_counter.py::test_single_increment -x` | Wave 0 |
| QUOT-03 | Env var limit=5 causes 6th call to be rejected | integration | `python -m pytest tests/test_atomic_counter.py::test_limit_enforcement -x` | Wave 0 |
| QUOT-03 | Limit=0 means unlimited | unit | `python -m pytest tests/test_atomic_counter.py::test_unlimited_when_zero -x` | Wave 0 |
| D-04 | GET /auth/me/usage returns per-service breakdown | integration | `python -m pytest tests/test_atomic_counter.py::test_usage_endpoint -x` | Wave 0 |
| D-02 | Rejection response includes usage details | integration | `python -m pytest tests/test_atomic_counter.py::test_rejection_response_format -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_atomic_counter.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_atomic_counter.py` -- covers QUOT-02, QUOT-03, D-02, D-04
- [ ] Test fixtures for authenticated client + database session (can reuse pattern from test_auth.py)

## Sources

### Primary (HIGH confidence)
- `src/database/models.py` lines 555-576 -- ApiUsage model with UniqueConstraint verified
- `src/database/session.py` -- _is_sqlite() pattern for dialect detection
- `src/database/repositories/user_repo.py` -- Repository class pattern
- `src/api/routes/auth.py` -- Existing auth routes pattern
- `src/api/deps.py` -- get_current_user dependency
- `tests/test_auth.py` -- Test infrastructure pattern (SQLite in-memory, httpx AsyncClient)
- Experimental verification: MySQL and SQLite upsert SQL generation confirmed working with SQLAlchemy 2.0.47 on this project
- Experimental verification: NULL user_id breaks SQLite ON CONFLICT (2 rows created instead of 1 incremented)

### Secondary (MEDIUM confidence)
- [SQLAlchemy 2.0 ORM DML docs](https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html) -- ORM-compatible INSERT variants
- [SQLAlchemy SQLite dialect docs](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) -- on_conflict_do_update
- [SQLite UPSERT docs](https://sqlite.org/lang_upsert.html) -- ON CONFLICT behavior with NULL

### Tertiary (LOW confidence)
- Google AI Studio free tier limits (15 images/day cited in CLAUDE.md, 500/day in PROJECT.md) -- treat as configurable defaults, verify at runtime

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and verified
- Architecture: HIGH - follows established project patterns, dialect upsert verified experimentally
- Pitfalls: HIGH - NULL user_id issue verified experimentally, timezone issue documented in STATE.md

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable domain, no fast-moving dependencies)
