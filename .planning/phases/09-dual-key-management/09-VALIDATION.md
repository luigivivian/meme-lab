---
phase: 9
slug: dual-key-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_key_selector.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_key_selector.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | QUOT-04, QUOT-05 | unit | `python -m pytest tests/test_key_selector.py -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | QUOT-05 | unit | `python -m pytest tests/test_key_selector.py -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | QUOT-04 | unit | `python -c "from src.image_gen.gemini_client import GeminiImageClient"` | ✅ | ⬜ pending |
| 09-01-04 | 01 | 2 | QUOT-04, QUOT-05 | integration | `python -m pytest tests/test_key_selector.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_key_selector.py` — stubs for QUOT-04, QUOT-05 (all selector branches)
- [ ] Mock `UsageRepository` to avoid real DB in unit tests (follow test_atomic_counter.py pattern with SQLite in-memory)

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
