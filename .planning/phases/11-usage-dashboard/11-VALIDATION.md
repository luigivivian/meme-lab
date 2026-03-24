---
phase: 11
slug: usage-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `memelab/vitest.config.ts` |
| **Quick run command** | `cd memelab && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd memelab && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd memelab && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd memelab && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | DASH-01 | unit | `cd memelab && npx vitest run` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | DASH-02 | unit | `cd memelab && npx vitest run` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | DASH-03 | unit | `cd memelab && npx vitest run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `memelab/src/__tests__/usage-widget.test.tsx` — stubs for DASH-01 (usage widget renders)
- [ ] `memelab/src/__tests__/source-badges.test.tsx` — stubs for DASH-02 (source badge rendering)
- [ ] `memelab/src/__tests__/use-usage.test.ts` — stubs for DASH-03 (useUsage hook)

*Existing infrastructure covers framework installation — vitest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual fill indicator color shifts | DASH-01 | CSS color transitions require visual inspection | Open dashboard, verify bar is emerald (<50%), amber (50-80%), rose (>80%) |
| Badge visual distinction | DASH-02 | Color contrast requires visual check | Generate images with each source, verify badges are visually distinct |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
