---
phase: 13
slug: tenant-isolation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `tests/` directory, imports from `src.api.app` |
| **Quick run command** | `python -m pytest tests/test_tenant.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_tenant.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | TENANT-01 | integration | `python -m pytest tests/test_tenant.py::test_user_isolation -x` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | TENANT-02 | integration | `python -m pytest tests/test_tenant.py::test_repo_filtering -x` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | TENANT-03 | integration | `python -m pytest tests/test_tenant.py::test_admin_bypass -x` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | TENANT-04 | integration | `python -m pytest tests/test_tenant.py::test_403_forbidden -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tenant.py` — integration tests for TENANT-01 through TENANT-04
- [ ] Test fixtures: two users (admin + regular), two characters (one per user), seed child data per character
- [ ] Framework already installed (pytest, pytest-asyncio, httpx) — no new dependencies

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frontend shows only user's own data | TENANT-01 | Browser rendering validation | Login as user A, verify no user B data visible in any page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
