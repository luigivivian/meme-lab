# Phase 8: Atomic Counter - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 08-atomic-counter
**Areas discussed:** Rejection behavior, Usage endpoint, Limit configuration, Concurrency strategy

---

## Rejection Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| 429 Too Many Requests (Recommended) | Standard HTTP code for rate limiting. Clients and monitoring tools recognize it automatically. Can include Retry-After header. | |
| 403 Forbidden | Simpler -- "you can't do this right now". Less specific about WHY. | |
| You decide | Claude picks the best approach | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** User deferred HTTP status code choice to Claude.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include usage info (Recommended) | Response body includes {used, limit, remaining: 0, resets_at}. Helps frontend. | ✓ |
| Minimal error only | Just {error: "daily limit reached"}. | |
| You decide | Claude picks | |

**User's choice:** Yes, include usage info
**Notes:** Rejection response must include usage details for frontend feedback.

---

## Usage Endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Per-service breakdown (Recommended) | Returns usage for each service separately. Phase 9/11 needs this granularity. | ✓ |
| Aggregate only | Single total. Simpler but Phase 11 needs per-service badges. | |
| You decide | Claude picks | |

**User's choice:** Per-service breakdown
**Notes:** None.

| Option | Description | Selected |
|--------|-------------|----------|
| JWT required (Recommended) | GET /auth/me/usage needs valid token. System usage tracked separately. | ✓ |
| Both authenticated and system | User + admin system endpoint. More work now. | |
| You decide | Claude picks | |

**User's choice:** JWT required
**Notes:** No system usage endpoint in this phase.

---

## Limit Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Per-service (Recommended) | Separate env var per service. Matches Google's per-model limits. | ✓ |
| Single global limit | One number for all services combined. | |
| You decide | Claude picks | |

**User's choice:** Per-service
**Notes:** None.

| Option | Description | Selected |
|--------|-------------|----------|
| Missing = sensible default, 0 = unlimited (Recommended) | No env var = hardcoded default. 0 = no limit. | ✓ |
| Missing = unlimited, 0 = blocked | No env var = no limit. 0 = reject all. | |
| You decide | Claude picks | |

**User's choice:** Missing = sensible default, 0 = unlimited
**Notes:** None.

---

## Concurrency Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| INSERT ON DUPLICATE KEY UPDATE (Recommended) | Single SQL statement, MySQL handles atomicity. Designed for via UniqueConstraint. | ✓ |
| SELECT FOR UPDATE + UPDATE | Two-step with explicit locking. Slower under contention. | |
| You decide | Claude picks | |

**User's choice:** INSERT ON DUPLICATE KEY UPDATE
**Notes:** Confirmed Phase 7 D-08 hint.

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-check then increment (Recommended) | Check limit BEFORE calling API. Reject immediately if at limit. Increment after success. | ✓ |
| Increment first, rollback if over | Increment atomically, check, decrement if over. Wastes one API call at boundary. | |
| You decide | Claude picks | |

**User's choice:** Pre-check then increment
**Notes:** No wasted API calls at the limit boundary.

---

## Claude's Discretion

- HTTP status code for rejection (429 recommended by Claude)
- UsageRepository class structure
- Default limit values per service
- Error response schema details
- Test concurrency strategy

## Deferred Ideas

- UsageAwareKeySelector (Phase 9)
- Static fallback (Phase 10)
- System usage admin endpoint (future)
- Usage history 30 days (Phase 11/v2)
