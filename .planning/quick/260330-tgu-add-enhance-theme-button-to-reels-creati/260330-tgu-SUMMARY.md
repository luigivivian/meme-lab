---
phase: quick-260330-tgu
plan: 01
subsystem: ui, api
tags: [gemini, reels, niche-selector, ai-suggestions, fastapi, react]

requires:
  - phase: 999.4
    provides: reels pipeline API routes and reel-niches data
provides:
  - POST /reels/enhance-theme endpoint for AI topic suggestions
  - Niche/sub-theme selector UI in reels creation page
  - enhanceReelTheme frontend API function
affects: [reels-pipeline, reels-page]

tech-stack:
  added: []
  patterns: [gemini-call-pattern-in-reels-routes]

key-files:
  created:
    - memelab/src/components/reels/reel-niches.ts
  modified:
    - src/api/routes/reels.py
    - memelab/src/lib/api.ts
    - memelab/src/app/(app)/reels/page.tsx

key-decisions:
  - "Niche selector replaces plain text niche input -- uses REEL_NICHES data with 18 niches across 4 tiers"
  - "Enhance sends niche label (PT-BR) + sub-theme text to Gemini for context-aware suggestions"
  - "reel-niches.ts copied to worktree from main repo (file existed in main but not in worktree)"

patterns-established:
  - "Gemini call pattern in reels.py: same asyncio.to_thread + _get_client/_extract_text as ads.py"

requirements-completed: [ENHANCE-THEME-01]

duration: 5min
completed: 2026-03-30
---

# Quick 260330-tgu: Add Enhance Theme Button to Reels Creation Summary

**AI-powered "Sugerir Temas" button with niche/sub-theme selector generating 5-8 viral topic suggestions via Gemini**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T00:17:43Z
- **Completed:** 2026-03-31T00:22:59Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- POST /reels/enhance-theme endpoint calls Gemini 2.5 Flash for viral topic suggestions
- Niche selector with 18 niches grouped by 4 tiers replaces plain text niche input
- Sub-theme pills appear when niche selected; "Sugerir Temas" button appears when sub-theme selected
- Suggestion pills populate tema textarea on click; suggestions clear on niche/sub-theme change

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend endpoint + frontend API function** - `94d6209` (feat)
2. **Task 2: Enhance Theme button + suggestion pills in reels page** - `38a339e` (feat)

## Files Created/Modified
- `src/api/routes/reels.py` - Added /enhance-theme endpoint with Gemini call, added asyncio import
- `memelab/src/lib/api.ts` - Added enhanceReelTheme() API function
- `memelab/src/app/(app)/reels/page.tsx` - Niche selector, sub-theme pills, enhance button, suggestion pills
- `memelab/src/components/reels/reel-niches.ts` - 18 niche definitions with sub-themes, hooks, CTAs (copied from main repo)

## Decisions Made
- Niche selector replaces plain text niche input: the plan assumed selectedNiche/selectedSubTheme state existed, but page only had a simple text input. Adapted by adding proper niche selector using REEL_NICHES data.
- Enhance sends PT-BR niche label (not ID) to Gemini for better context-aware suggestions.
- Removed unused Input component import after replacing text niche field with Select component.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Page structure mismatch -- no niche/sub-theme selection existed**
- **Found during:** Task 2
- **Issue:** Plan referenced selectedNiche/selectedSubTheme state and sub-theme pills that did not exist in the current page. Page had a simple text niche input in collapsible settings.
- **Fix:** Added full niche selector (Select component with REEL_NICHES data grouped by tier) and sub-theme pills UI. Removed the plain text niche input from collapsible settings.
- **Files modified:** memelab/src/app/(app)/reels/page.tsx
- **Committed in:** 38a339e

**2. [Rule 3 - Blocking] reel-niches.ts missing from worktree**
- **Found during:** Task 2
- **Issue:** reel-niches.ts existed in main repo but not in this worktree. Required for niche data.
- **Fix:** Copied file from main repo to worktree.
- **Files modified:** memelab/src/components/reels/reel-niches.ts (created)
- **Committed in:** 38a339e

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary to make the feature work. The niche selector is a UX improvement over what the plan assumed existed.

## Issues Encountered
- Pre-existing TypeScript errors in api.ts (duplicate function declarations) and wizard.tsx (missing Film icon) -- not caused by this plan's changes, out of scope per deviation rules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Feature ready for manual testing: start both servers, select niche, select sub-theme, click "Sugerir Temas"
- Requires Gemini API key in environment for the enhance endpoint to return actual suggestions

## Self-Check: PASSED
- All 4 files verified present
- Both commit hashes (94d6209, 38a339e) verified in git log
