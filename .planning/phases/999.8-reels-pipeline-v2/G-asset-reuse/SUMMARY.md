---
phase: "999.8"
plan: "G"
subsystem: reels-pipeline
tags: [asset-registry, semantic-reuse, embeddings, cosine-similarity]
dependency_graph:
  requires: [Phase 999.6 per-cena images, Phase 999.5 interactive pipeline]
  provides: [scene asset registry, semantic asset reuse, per-image regeneration]
  affects: [src/reels_pipeline/main.py, src/api/routes/reels.py, memelab/src/lib/api.ts]
tech_stack:
  added: [Gemini text-embedding-004, cosine similarity]
  patterns: [asset registry, semantic search, pure Python vector math]
key_files:
  created:
    - src/reels_pipeline/asset_registry.py
    - src/database/migrations/versions/025_scene_asset_registry.py
  modified:
    - src/database/models.py
    - src/reels_pipeline/main.py
    - src/api/routes/reels.py
    - memelab/src/lib/api.ts
    - memelab/src/components/reels/step-images.tsx
    - memelab/src/components/reels/step-video.tsx
decisions:
  - Pure Python cosine similarity (no numpy dependency) — sufficient for <1000 assets per user
  - Gemini text-embedding-004 for 768-dim embeddings — same API key as existing pipeline
  - Threshold 0.85 for similarity match — conservative to avoid wrong reuse
  - metadata_json column name (not metadata) to avoid SQLAlchemy reserved attribute
  - find_similar_asset returns embedding alongside match to avoid double API call
metrics:
  duration: 10min
  completed: 2026-03-31
  tasks: 5
  files: 8
---

# Phase 999.8 Plan G: Scene Asset Registry with Semantic Reuse Summary

Asset registry that tracks all generated images and videos with semantic embeddings. Before generating new content, checks for similar existing assets via cosine similarity. Reuses automatically with UI badge and per-scene regeneration override.

## Tasks Completed

### Task 1: DB Model + Migration (55e6711)
- Added `SceneAsset` model to `models.py` with 13 columns: id, user_id, character_id, asset_type, scene_description, embedding (JSON 768-float list), file_path, file_hash, kie_task_id, model_used, generation_prompt, metadata_json, usage_count
- TimestampMixin for created_at/updated_at
- Migration 025 chains from 024, creates table + 3 indexes including composite (user_id, asset_type, character_id)
- No JSON server_default (MySQL compatible)

### Task 2: Asset Registry Service (5ce38cd)
- `cosine_similarity(a, b)` — pure Python dot product, no numpy
- `generate_embedding(text)` — Gemini text-embedding-004 via asyncio.to_thread
- `find_similar_asset(user_id, character_id, asset_type, description, threshold=0.85)` — queries all matching assets, computes cosine sim, returns best match + computed embedding
- `register_asset(...)` — saves to DB with SHA-256 file hash, returns asset.id
- `compute_file_hash(file_path)` — SHA-256
- `increment_usage(asset_id)` — bumps usage_count
- All DB calls use `get_session_factory()` internally

### Task 3: Pipeline Integration (91316de)
- `run_step_images_per_cena`: added user_id, force_regenerate_indices params; checks registry before each cena, copies via shutil.copy2 on match, registers new assets after generation; returns (paths, reuse_info) tuple
- `run_step_video_kie`: added user_id, character_id, force_regenerate_indices params; checks registry before Kie.ai call per scene, registers new video clips after successful download
- All new params optional with defaults — backward compatible

### Task 4: API Integration (3423412)
- `_execute_step_task`: passes user_id and character_id to pipeline methods, stores reuse_info in step_state
- `POST /reels/{jobId}/regenerate-image/{sceneIndex}` — force-regenerate single image, registers as new asset
- `POST /reels/{jobId}/regenerate-scene-video/{sceneIndex}` — regenerate any scene video (no status restriction, works on reused scenes)

### Task 5: Frontend (75cb939)
- `api.ts`: ImageReuseInfo type, reuse_info on StepState.images, reused/source_asset_id on SceneStatus, regenerateSingleImage + regenerateSceneVideo functions
- `step-images.tsx`: per-image card grid with amber "Reaproveitado" badge for reused images, per-card "Gerar Nova" button (RefreshCw icon) on hover with loading state
- `step-video.tsx`: amber "Reaproveitado" badge on reused scene cards, "Gerar Novo Video" button for reused scenes (expands isRetryable to include reused)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All data paths are wired end-to-end.

## Self-Check: PASSED
