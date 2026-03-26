---
phase: 10
slug: static-fallback
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | implicit, uses default pytest discovery |
| **Quick run command** | `python -m pytest tests/test_static_fallback.py tests/test_key_selector.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_static_fallback.py tests/test_key_selector.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | QUOT-06a | unit | `python -m pytest tests/test_key_selector.py::test_resolve_returns_exhausted_both_tiers -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | QUOT-06b | unit | `python -m pytest tests/test_key_selector.py::test_resolve_exhausted_free_only -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | QUOT-06c | unit | `python -m pytest tests/test_static_fallback.py::test_compose_static_on_exhaustion -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | QUOT-06d | unit | `python -m pytest tests/test_static_fallback.py::test_metadata_on_exhaustion -x` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 1 | QUOT-06e | unit | `python -m pytest tests/test_static_fallback.py::test_compose_no_auth_backward_compat -x` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 1 | QUOT-06f | unit | `python -m pytest tests/test_static_fallback.py::test_fallback_reason_values -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_static_fallback.py` — stubs for QUOT-06c, QUOT-06d, QUOT-06e, QUOT-06f
- [ ] New tests in `tests/test_key_selector.py` — stubs for QUOT-06a, QUOT-06b

*Existing infrastructure covers framework — no new installs needed.*

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
