---
phase: 20
slug: kie-ai-credits-cost-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none (uses default discovery) |
| **Quick run command** | `python -m pytest tests/test_credits.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_credits.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-T1 | 20-01 | 1 | CRED-01, CRED-02 | unit | `python -m pytest tests/test_credits.py -x` | Wave 0 | pending |
| 20-01-T2 | 20-01 | 1 | CRED-03 | unit | `python -m pytest tests/test_credits.py::test_credits_summary_schema -x` | Wave 0 | pending |
| 20-02-T1 | 20-02 | 2 | CRED-04 | manual | Navigate to dashboard, verify Video Credits card displays | N/A | pending |
| 20-02-T2 | 20-02 | 2 | CRED-04 | tsc | `cd memelab && npx tsc --noEmit` | exists | pending |

---

## Requirements Coverage

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRED-01 | cost_brl recorded only on success, zero on failure | unit | `python -m pytest tests/test_credits.py::test_cost_brl_only_on_success -x` | Wave 0 |
| CRED-02 | cost_brl matches VIDEO_MODELS prices_brl | unit | `python -m pytest tests/test_credits.py::test_cost_brl_from_config -x` | Wave 0 |
| CRED-03 | credits summary endpoint returns correct schema | unit | `python -m pytest tests/test_credits.py::test_credits_summary_schema -x` | Wave 0 |
| CRED-04 | dashboard displays cumulative BRL costs with per-model granularity | manual + tsc | Navigate to dashboard; `npx tsc --noEmit` | N/A + exists |

---

## Wave 0 Gaps

- [ ] `tests/test_credits.py` — covers CRED-01, CRED-02, CRED-03
- [ ] compute_video_cost_brl helper unit tests
- [ ] Schema validation for new cost_brl/model columns on ApiUsage
