---
phase: 12
slug: pipeline-simplification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async with pytest-asyncio) |
| **Config file** | None explicit (uses pytest defaults) |
| **Quick run command** | `python -m pytest tests/test_manual_pipeline.py -x --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_manual_pipeline.py -x --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | PIPE-01 | unit | `python -m pytest tests/test_manual_pipeline.py::test_manual_run_static_only -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | PIPE-02 | unit | `python -m pytest tests/test_manual_pipeline.py::test_solid_color_background -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | PIPE-04 | unit | `python -m pytest tests/test_manual_pipeline.py::test_create_image_hex_color -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | PIPE-03 | unit | `python -m pytest tests/test_manual_pipeline.py::test_approval_status -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_manual_pipeline.py` — stubs for PIPE-01 through PIPE-04
- [ ] `tests/conftest.py` — async DB session fixture if not present

*Wave 0 creates test infrastructure before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pillow-composed image looks correct visually | PIPE-04 | Visual quality cannot be automated | Open generated image, verify text placement, no clipping, correct background color/image |
| Frontend approve/reject buttons work | PIPE-03 | Browser UI interaction | Click approve/reject on meme card, verify status badge updates without page refresh |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
