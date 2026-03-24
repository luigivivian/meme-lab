# Phase 1: Pre-Conditions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 1-pre-conditions
**Areas discussed:** CORS origins, Gemini model strategy, Log masking scope, Health endpoint

---

## CORS Origins

| Option | Description | Selected |
|--------|-------------|----------|
| Localhost only (Recommended) | http://localhost:3000 + http://127.0.0.1:3000 — simplest, add more later via env var | ✓ |
| Localhost + env var list | Hardcode localhost, plus CORS_ORIGINS env var for additional origins | |
| Configurable only | All origins from CORS_ORIGINS env var, no hardcoded values | |

**User's choice:** Localhost only
**Notes:** Simplest approach for v1. Production domain can be added later.

---

## Gemini Model Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-discover on startup (Recommended) | Call client.models.list() at API startup, filter image-capable models, use first valid | ✓ |
| Hardcode known-good + fallback | Research correct names now, hardcode them, fall back on 400 | |
| Env var override | GEMINI_IMAGE_MODEL env var, with auto-discover as fallback | |

**User's choice:** Auto-discover on startup
**Notes:** Catches model deprecations automatically. No manual maintenance of model name lists.

---

## Log Masking Scope

| Option | Description | Selected |
|--------|-------------|----------|
| API keys only (Recommended) | Mask GOOGLE_API_KEY, BLUESKY_APP_PASSWORD, INSTAGRAM_ACCESS_TOKEN — show last 4 chars | |
| All secrets + DB URL | API keys + DATABASE_URL password + any token-like values | |
| Full sanitizer middleware | FastAPI middleware that scans all log output for regex patterns matching keys/tokens/passwords | ✓ |

**User's choice:** Full sanitizer middleware
**Notes:** Most defensive approach. Catches unexpected leaks in error tracebacks and future code.

---

## Health Endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Gemini + DB status (Recommended) | Overall status + Gemini model validation + DB connection check | ✓ |
| Full system health | Gemini + DB + ComfyUI + agent count + scheduler status | |
| Minimal + Gemini only | Just {status: 'ok', gemini_model: 'valid/invalid'} | |

**User's choice:** Gemini + DB status
**Notes:** Satisfies Phase 1 success criteria without scope creep into ComfyUI/agent monitoring.

---

## Claude's Discretion

- Log sanitizer middleware implementation details (regex patterns, placement)
- `list_models()` call timing (sync at startup vs lazy)
- Health endpoint response schema structure

## Deferred Ideas

None — discussion stayed within phase scope.
