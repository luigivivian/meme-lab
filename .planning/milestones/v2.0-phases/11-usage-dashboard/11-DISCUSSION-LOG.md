# Phase 11: Usage Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 11-usage-dashboard
**Areas discussed:** Usage widget placement & style, Source badge granularity, Refresh & real-time behavior

---

## Usage Widget Placement & Style

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Right sidebar card | New card in right sidebar alongside Status, Agents, Queue cards. Consistent with existing layout. | ✓ |
| Stats grid row | Add as 5th card in top stats grid. Compact but less room for details. | |
| Banner above content | Horizontal banner between stats and content. High visibility but takes vertical space. | |

**User's choice:** Right sidebar card (recommended)
**Notes:** None — straightforward pick following existing patterns.

### Fill Indicator Style

| Option | Description | Selected |
|--------|-------------|----------|
| Progress bar + text | Horizontal bar using existing Progress component + "N / M" text. Color shifts emerald → amber → rose. | ✓ |
| Radial/circular gauge | Circular SVG arc. Compact but needs new component. | |
| Numbers only | Just "N / M" with color coding. Minimal, no bar. | |

**User's choice:** Progress bar + text (recommended)
**Notes:** Reuses existing Progress component. Color shift matches quality score bar pattern.

---

## Source Badge Granularity

### Tier Distinction

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — 3 distinct badges | Show 'gemini free', 'gemini paid', 'static'. Users see which images consumed free vs paid. | ✓ |
| No — keep current 2-level | Keep 'gemini' and 'static'. Simpler but no tier visibility. | |
| Badge + tooltip detail | Keep 'gemini' badge, tooltip shows tier on hover. Less noise, detail on demand. | |

**User's choice:** Yes — 3 distinct badges (recommended)
**Notes:** Tier data already stored in image metadata from Phase 9/10.

### Badge Colors

| Option | Description | Selected |
|--------|-------------|----------|
| Sky/Amber/Zinc | gemini free = sky-400, gemini paid = amber-400, static = zinc-500. Minimal change. | |
| Emerald/Violet/Zinc | gemini free = emerald-400, gemini paid = violet-400, static = zinc-500. Stronger contrast. | |
| You decide | Claude picks colors fitting the design system. | ✓ |

**User's choice:** You decide
**Notes:** Claude has discretion on colors as long as they fit the dark theme and are visually distinct.

---

## Refresh & Real-time Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| SWR polling every 30s | Standard SWR refreshInterval. Updates within 30s of pipeline run. Consistent with codebase. | ✓ |
| SWR + mutate after pipeline run | Polling + explicit mutate on pipeline completion. Instant update after runs. | |
| On-demand only | No auto-refresh. Updates on page load only. Lowest API overhead. | |

**User's choice:** SWR polling every 30s (recommended)
**Notes:** Matches existing SWR hook patterns in the codebase.

---

## Claude's Discretion

- Badge color selection for gemini free/gemini paid/static
- SWR hook organization (useUsage() in use-api.ts)
- Loading/error states (follow existing skeleton pattern)
- PT-BR text labels for the widget

## Deferred Ideas

- Usage history graph (last 30 days) — DASH-V2-01
- Alerts at 80%/95% — DASH-V2-02
- Estimated cost report — DASH-V2-03
