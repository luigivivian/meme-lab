---
created: 2026-04-01T03:59:42.165Z
title: Per-scene clip generation control and dynamic scene count
area: ui
files:
  - memelab/src/components/reels/step-video.tsx
  - memelab/src/components/reels/step-images.tsx
  - memelab/src/app/(app)/reels/[jobId]/page.tsx
  - src/api/routes/reels.py
  - src/reels_pipeline/main.py
  - src/reels_pipeline/script_gen.py
---

## Problem

Two related UX gaps in the reels wizard:

### 1. No granular clip generation control
Before generating videos, the user has no choice — it's all-or-nothing (all scenes sent to Kie.ai at once). User should be able to:
- Generate clips **one by one**, reviewing each before proceeding
- Use a **"Gerar Todos Clips"** button to batch-generate all at once
- **Skip** specific scenes and keep them as static images if preferred
- Mix animated and static scenes in the final video

### 2. Fixed scene count (always 5)
For complex themes, 5 scenes may not be enough. For simple themes, 5 may be too many. User should be able to:
- See an **auto-suggested scene count** based on theme complexity (longer narration = more scenes)
- **Configure scene count manually** (e.g., 3-10 range slider)
- This affects script generation (n_imagens param) and downstream image/video generation

## Solution

### Clip generation control
1. Add intermediate step between images approval and final video — a "Clips" review screen
2. Each scene card shows the image + "Gerar Clip" button + "Manter Estatica" toggle
3. "Gerar Todos Clips" button at top for batch generation
4. Scene cards update in real-time as clips complete (existing `on_scene_update` callback)
5. "Montar Video Final" button appears once all scenes have either a clip or static designation

### Dynamic scene count
1. Add `n_cenas` field to reels creation form (default auto-suggested)
2. Auto-suggestion: analyze tema/sub_theme complexity (char count, topic depth) to suggest 3-8 scenes
3. Pass to script generation which already uses `n_imagens` param
4. Configurable in ReelsConfig too for saved presets
