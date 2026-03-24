---
phase: 8
slug: atomic-counter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | None explicit (uses defaults) |
| **Quick run command** | `python -m pytest tests/test_atomic_counter.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_atomic_counter.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | QUOT-02 | integration | `python -m pytest tests/test_atomic_counter.py::test_concurrent_increments -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | QUOT-02 | unit | `python -m pytest tests/test_atomic_counter.py::test_single_increment -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | QUOT-03 | integration | `python -m pytest tests/test_atomic_counter.py::test_limit_enforcement -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | QUOT-03 | unit | `python -m pytest tests/test_atomic_counter.py::test_unlimited_when_zero -x` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | D-04 | integration | `python -m pytest tests/test_atomic_counter.py::test_usage_endpoint -x` | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 1 | D-02 | integration | `python -m pytest tests/test_atomic_counter.py::test_rejection_response_format -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_atomic_counter.py` — stubs for QUOT-02, QUOT-03, D-02, D-04
- [ ] Test fixtures for authenticated client + database session (reuse pattern from test_auth.py)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
