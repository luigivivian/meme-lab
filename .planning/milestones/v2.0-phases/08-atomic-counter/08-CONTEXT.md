# Phase 8: Atomic Counter - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Atomic usage increment without race conditions, configurable daily limits via env vars, and a usage read endpoint (GET /auth/me/usage). Builds on the `api_usage` table from Phase 7. No key selection logic (Phase 9) or fallback behavior (Phase 10).

</domain>

<decisions>
## Implementation Decisions

### Rejection Behavior
- **D-01:** Claude's discretion on HTTP status code (429 recommended as standard rate-limiting code).
- **D-02:** Rejection response MUST include usage details: `{used, limit, remaining: 0, resets_at: "<PT midnight ISO>"}` so the frontend can show meaningful feedback.
- **D-03:** A `rejected` status row is written to `api_usage` when a call is blocked (per Phase 7 D-05).

### Usage Endpoint
- **D-04:** GET /auth/me/usage returns per-service breakdown: `{services: [{service: "gemini_image", tier: "free", used: N, limit: M, remaining: M-N}, ...], resets_at: "..."}`. Supports Phase 11 dashboard needs.
- **D-05:** Endpoint requires JWT authentication (uses `get_current_user` dependency). No system/shared usage endpoint in this phase.

### Limit Configuration
- **D-06:** Per-service env vars: `GEMINI_IMAGE_DAILY_LIMIT_FREE`, `GEMINI_TEXT_DAILY_LIMIT_FREE`, etc. Matches Google's per-model limits.
- **D-07:** Missing env var = sensible hardcoded default (e.g., 15 for gemini_image free). Setting to 0 = unlimited (no limit enforced). Useful for paid tier or testing.

### Concurrency Strategy
- **D-08:** `INSERT ... ON DUPLICATE KEY UPDATE usage_count = usage_count + 1` for atomic increments. Leverages Phase 7's UniqueConstraint on (user_id, service, tier, date). No explicit row locking needed.
- **D-09:** Pre-check flow: check current count < limit BEFORE calling external API. If at limit, reject immediately (no wasted API call). Increment usage_count only after successful API response.

### Claude's Discretion
- HTTP status code for rejection (429 recommended)
- UsageRepository class structure and method signatures
- Default limit values per service
- Error response schema details beyond the required fields
- Test strategy for concurrency (e.g., asyncio.gather with N tasks)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 7 Context (Direct Predecessor)
- `.planning/phases/07-usage-tracking-table/07-CONTEXT.md` -- All api_usage table decisions (D-01 to D-08). Critical: UniqueConstraint design, status values, PT timezone logic.

### Database Models & Patterns
- `src/database/models.py` -- ApiUsage model (line ~555), User model (line ~506). Follow existing column/relationship patterns.
- `src/database/base.py` -- Base and TimestampMixin classes.
- `src/database/session.py` -- Async session factory.

### Repository Pattern
- `src/database/repositories/user_repo.py` -- Existing user repository, pattern for new UsageRepository.
- `src/database/repositories/schedule_repo.py` -- Example repository with query patterns.

### Auth Routes
- `src/api/routes/auth.py` -- Existing auth routes (register, login, refresh, logout, /me). Usage endpoint adds to this module.
- `src/auth/` -- JWT utils, AuthService, get_current_user dependency.

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` -- QUOT-02 (atomic tracking), QUOT-03 (configurable daily limits)
- `.planning/ROADMAP.md` section Phase 8 -- Success criteria (3 conditions: concurrent safety, env var limit, usage endpoint)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ApiUsage` model with UniqueConstraint on (user_id, service, tier, date) -- ready for ON DUPLICATE KEY UPDATE
- `get_current_user` dependency in `src/auth/` -- reuse for /auth/me/usage endpoint
- `UserResponse` and other Pydantic models in auth routes -- pattern for UsageResponse schema
- Repository pattern in `src/database/repositories/` -- 7 existing repos to follow

### Established Patterns
- Async SQLAlchemy sessions via `session.py`
- PT timezone conversion in Python layer (zoneinfo), not MySQL (Phase 7 D-04)
- SQLite in-memory for tests with session singleton reset (Phase 3 pattern)
- Auth routes grouped under `/auth` prefix in `src/api/routes/auth.py`

### Integration Points
- `src/api/routes/auth.py` -- Add GET /auth/me/usage endpoint here
- `src/database/repositories/` -- New UsageRepository for atomic increment + read
- `src/image_gen/gemini_client.py` -- Future caller of increment (Phase 9 will wire this)
- Pipeline workers -- Future callers that check limits before API calls (Phase 9/10)

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches for repository implementation and endpoint design.

</specifics>

<deferred>
## Deferred Ideas

- **UsageAwareKeySelector** -- Phase 9 (QUOT-04, QUOT-05), decides free vs paid key based on usage
- **Static fallback when both keys exhausted** -- Phase 10 (QUOT-06)
- **GET /usage/system for shared key stats (admin)** -- Future, not needed for v1
- **Usage history (last 30 days)** -- Phase 11 / v2 dashboard feature

</deferred>

---

*Phase: 08-atomic-counter*
*Context gathered: 2026-03-24*
