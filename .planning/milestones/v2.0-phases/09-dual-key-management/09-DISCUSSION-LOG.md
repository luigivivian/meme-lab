# Phase 9: Dual Key Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 09-dual-key-management
**Areas discussed:** Missing paid key behavior, Key switch trigger & flow, Integration with GeminiImageClient, Manual override / force tier

---

## Missing Paid Key Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Free-only mode | System works with just the free key. When free limit is hit, falls through to Phase 10 fallback. Warning log at startup. | ✓ |
| Require both keys | App refuses to start or disables image generation if paid key is missing. | |
| Warn and prompt | Log WARNING at startup, ERROR at runtime when free limit hit and no paid key. | |

**User's choice:** Free-only mode (Recommended)
**Notes:** No error, graceful degradation.

### Follow-up: Identical Keys

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and treat as free-only | Detect identical keys at startup, log WARNING, operate as free-only. | ✓ |
| Use it anyway | Don't check, just try the "paid" key even if same. | |
| You decide | Claude picks. | |

**User's choice:** Warn and treat as free-only
**Notes:** Prevents wasted attempts on exhausted key.

---

## Key Switch Trigger & Flow

### Check Frequency

| Option | Description | Selected |
|--------|-------------|----------|
| Check every call | Always query UsageRepository.check_limit() before resolving. Simple, always accurate. | ✓ |
| Cache with TTL | Cache decision for N minutes. Reduces DB queries but could overshoot limit. | |
| You decide | Claude picks. | |

**User's choice:** Check every call (Recommended)
**Notes:** Low volume (~15/day) makes extra DB query negligible.

### Midnight Reset

| Option | Description | Selected |
|--------|-------------|----------|
| Natural check | Next resolve() after midnight sees usage=0 and returns free key. No special logic. | ✓ |
| Active reset listener | Scheduled task flips back to free at midnight. More complex, no benefit. | |

**User's choice:** Natural check (Recommended)
**Notes:** Pairs naturally with check-every-call strategy.

---

## Integration with GeminiImageClient

### Module Location

| Option | Description | Selected |
|--------|-------------|----------|
| New module, injected | UsageAwareKeySelector in src/services/key_selector.py. Injected into GeminiImageClient. | ✓ |
| Inside gemini_client.py | Add selector logic directly into GeminiImageClient. Mixes concerns. | |
| Wrap _get_client() | Modify llm_client.py to be tier-aware. Broader impact on all Gemini calls. | |

**User's choice:** New module, injected (Recommended)
**Notes:** Clean separation of concerns.

### Return Type of resolve()

| Option | Description | Selected |
|--------|-------------|----------|
| Key + tier tuple | Returns (api_key, tier) for logging. | |
| Just the key string | Selector handles logging internally. | |
| You decide | Claude picks based on success criteria. | ✓ |

**User's choice:** You decide
**Notes:** Claude's discretion — as long as tier info is available for api_usage logging.

---

## Manual Override / Force Tier

### Override Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Env var override | GEMINI_FORCE_TIER=free|paid. Skips usage checks. | |
| No override | Always automatic. Set free limit to 0 to test paid key. | |
| Both env + API param | Env var for global + query param for per-request (admin-only). | ✓ |

**User's choice:** Both env + API param
**Notes:** Maximum flexibility for testing and debugging.

### API Param Access

| Option | Description | Selected |
|--------|-------------|----------|
| Admin-only | Only role=admin can pass ?force_tier=paid. Prevents abuse. | ✓ |
| All authenticated users | Any logged-in user can force tier. | |
| You decide | Claude picks. | |

**User's choice:** Admin-only (Recommended)
**Notes:** Priority order: per-request param (admin) > env var > automatic.

---

## Claude's Discretion

- Return type of `resolve()` (key + tier tuple, dataclass, or similar)
- Internal class structure of UsageAwareKeySelector
- How GeminiImageClient creates/switches genai Client instances
- Test strategy for the selector

## Deferred Ideas

- Static fallback when both keys exhausted (Phase 10)
- Usage dashboard widget (Phase 11)
- Per-user API keys / BYOK (v2)
