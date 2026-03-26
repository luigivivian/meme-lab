---
phase: 7
slug: usage-tracking-table
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `tests/` directory (existing) |
| **Quick run command** | `python -m pytest tests/test_api_usage.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_api_usage.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | QUOT-01 | unit | `python -m pytest tests/test_api_usage.py::test_model_columns -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | QUOT-01 | unit | `python -m pytest tests/test_api_usage.py::test_unique_constraint -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | QUOT-07 | unit | `python -m pytest tests/test_api_usage.py::test_pt_timezone_bucketing -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | QUOT-01 | integration | `alembic upgrade head && alembic downgrade -1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_usage.py` — stubs for QUOT-01, QUOT-07
- [ ] Existing `tests/conftest.py` — shared fixtures (already exists)

*Existing pytest infrastructure covers framework needs. Only test file stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration rollback leaves no artifacts | QUOT-01 | Requires DB state inspection | Run `alembic downgrade -1`, verify `api_usage` table absent |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
