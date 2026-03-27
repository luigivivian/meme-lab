---
phase: 21
slug: dashboard-business-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + TypeScript compiler |
| **Config file** | none (uses default discovery) |
| **Quick run command** | `python -m pytest tests/test_dashboard_metrics.py -x` |
| **Full suite command** | `python -m pytest tests/ -x && cd memelab && npx tsc --noEmit` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_dashboard_metrics.py -x`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-T1 | 21-01 | 1 | DASH-05, DASH-06 | unit | `python -m pytest tests/test_dashboard_metrics.py -x` | Wave 0 | pending |
| 21-02-T1 | 21-02 | 2 | DASH-05, DASH-06 | tsc | `cd memelab && npx tsc --noEmit` | exists | pending |
| 21-02-T2 | 21-02 | 2 | DASH-05, DASH-06, DASH-07 | manual | Navigate to dashboard, verify cards and BRL | N/A | pending |

---

## Requirements Coverage

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-05 | All spending/cost values display in BRL | unit + manual | `pytest tests/test_dashboard_metrics.py -x` + visual check | Wave 0 |
| DASH-06 | Business metric cards show correct values | unit + manual | `pytest tests/test_dashboard_metrics.py -x` + visual check | Wave 0 |
| DASH-07 | Cards have icons, trend arrows, comparative data | manual + tsc | `npx tsc --noEmit` + visual check | exists |

---

## Wave 0 Gaps

- [ ] `tests/test_dashboard_metrics.py` — covers DASH-05, DASH-06
- [ ] Business metrics endpoint returns correct schema with BRL values
- [ ] 7d vs 7d comparison logic correctness
