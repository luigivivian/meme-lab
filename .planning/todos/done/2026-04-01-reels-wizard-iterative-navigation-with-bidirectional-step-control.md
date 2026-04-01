---
created: 2026-04-01T03:58:14.112Z
title: Reels wizard iterative navigation with bidirectional step control
area: ui
files:
  - memelab/src/app/(app)/reels/[jobId]/page.tsx
  - memelab/src/components/reels/step-images.tsx
  - memelab/src/components/reels/step-video.tsx
  - memelab/src/components/reels/step-script.tsx
  - memelab/src/components/reels/step-subtitles.tsx
  - src/api/routes/reels.py
---

## Problem

The reels generation wizard currently only allows forward progression. Once a step is completed (e.g., video generation), the user cannot go back to a previous step (e.g., images or script) to make changes and re-run downstream steps. This forces users to start over or live with suboptimal results.

Requirements:
- User can navigate from any step to any previous step (e.g., step 5 back to step 2)
- User CANNOT skip forward past incomplete steps
- All state is saved and preserved when navigating back
- When a previous step is re-done, downstream steps should be invalidated/cleared
- The step indicator/nav should be clickable for completed steps
- Current step state (approved, generating, etc.) must be respected

## Solution

1. **Frontend**: Add a step navigation bar (clickable breadcrumbs/tabs) showing all 5 steps. Completed steps are clickable. Future incomplete steps are disabled. Current step is highlighted.
2. **Backend**: The `regenerateStep` endpoint already clears downstream steps — this can be leveraged when the user navigates back and re-triggers a step.
3. **State management**: `step_state.current_step` already tracks position. Add ability to set `current_step` to any value <= current without clearing data (view mode). Only clear downstream when user explicitly re-runs a step.
4. **UX flow**: Navigating back shows the step's current data (read-only view of previously approved content). User can choose to edit/regenerate from there, which triggers downstream invalidation.
