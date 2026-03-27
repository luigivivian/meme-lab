---
phase: 01
slug: pre-conditions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (no config file, runs via `python -m pytest`) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/test_preconditions.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_preconditions.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | PRE-01 | unit | `python -m pytest tests/test_preconditions.py::test_cors_credentials -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | PRE-02 | unit | `python -m pytest tests/test_preconditions.py::test_model_discovery -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | PRE-03 | unit | `python -m pytest tests/test_preconditions.py::test_log_sanitizer -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | PRE-01/09 | unit | `python -m pytest tests/test_preconditions.py::test_health_endpoint -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preconditions.py` — stubs for PRE-01, PRE-02, PRE-03
- [ ] `pytest.ini` or `pyproject.toml` [tool.pytest.ini_options] — configure test discovery
- [ ] Framework install verification: `python -m pytest --version`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CORS request from browser | PRE-01 | Requires real browser fetch with credentials | Open localhost:3000, open DevTools, run `fetch('http://localhost:8000/health', {credentials:'include'})` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
