# Phase 12: Pipeline Simplification - Research

**Researched:** 2026-03-24
**Domain:** Pipeline orchestration, Pillow image composition, FastAPI endpoints, Next.js frontend
**Confidence:** HIGH

## Summary

Phase 12 transforms the existing 5-layer pipeline into a manual mode where users compose memes using pre-existing backgrounds (solid colors or image files) and Pillow text overlay, with zero Gemini Image API calls. The codebase already has most of the building blocks: `background_mode="static"` in ImageWorker, manual topic shortcut in AsyncPipelineOrchestrator, the Pillow composition engine in `image_maker.py`, and a working Pipeline page with form + results grid.

The main gaps are: (1) no `approval_status` column on ContentPackage or GeneratedImage -- needed for approve/reject flow, (2) no per-theme color palettes in themes.yaml, (3) `create_image()` only accepts image file paths as background -- needs to also handle solid color hex strings or PIL Color objects, (4) no "use my phrase" mode that bypasses PhraseWorker entirely, (5) no background image upload endpoint, and (6) the frontend form needs significant restructuring per the UI-SPEC (input mode tabs, background type selector, color palette picker, image picker, approve/reject per meme).

**Primary recommendation:** Extend the existing pipeline plumbing rather than building new orchestration. Add approval_status to ContentPackage via Alembic migration, extend `create_image()` to accept solid colors, add per-theme color palettes to themes.yaml, create a new "manual run" API endpoint that supports both phrase generation and literal phrases, and rebuild the Pipeline page form per the UI-SPEC.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Both solid colors and image library available as background sources
- **D-02:** Per-theme color palettes -- each theme in themes.yaml gets 3-5 curated solid colors matching its mood
- **D-03:** Solid colors only -- no gradients in this phase
- **D-04:** Background images are per-character (assets/backgrounds/{character}/ structure)
- **D-05:** Users can upload new background images via the frontend UI, stored per-character
- **D-06:** Two input modes: "Generate from topic" (Gemini generates phrase) and "Use my phrase" (user writes exact text)
- **D-07:** Manual run form lives on the existing Pipeline page
- **D-08:** User chooses meme count (1-10), default 3
- **D-09:** L5 post-production is an optional toggle, default on
- **D-10:** Character comes from sidebar selector -- no redundant dropdown
- **D-11:** "Use my phrase" supports multiple phrases (one per line), each becoming one meme
- **D-12:** Inline results on Pipeline page -- grid with approve/reject per meme
- **D-13:** Bulk actions: "Approve All" and "Reject All" buttons
- **D-14:** Rejected memes are soft-deleted -- marked 'rejected' status, still visible, can be un-rejected
- **D-15:** Approved memes get 'approved' status. No download/next action.
- **D-16:** Manual pipeline never calls L1/L2/L3 trend agents
- **D-17:** Only manual/simplified flow exposed in UI. Full 5-layer code stays but not accessible from frontend.

### Claude's Discretion
- Implementation details for the upload endpoint (storage location, file validation, max size)
- Default meme count value and form layout specifics
- How the Pipeline page UI splits between the run form and the results grid

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-01 | User can run pipeline in manual mode with pre-existing backgrounds (zero Gemini Image calls) | Existing `background_mode="static"` path in ImageWorker + manual_topics shortcut in orchestrator. Need to add solid color support to `create_image()` and wire "use my phrase" mode. |
| PIPE-02 | User can select theme/background for pipeline composition | themes.yaml exists with 13+ themes. Need to add `colors` array per theme. Frontend needs theme select + color/image picker. |
| PIPE-03 | User can preview composed memes before publishing (approve/reject) | Need `approval_status` column on ContentPackage (Alembic migration). Frontend results grid needs approve/reject buttons + bulk actions. |
| PIPE-04 | Pipeline composes images via Pillow with static backgrounds + phrases | `create_image()` in image_maker.py handles full Pillow composition. Need to extend it to accept hex color strings as background source. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow (PIL) | Already installed | Image composition, text rendering, solid color backgrounds | Already the project's composition engine in `image_maker.py` |
| FastAPI | Already installed | API endpoints for manual run, approve/reject, upload | Already the project's API framework |
| SQLAlchemy 2.0 | Already installed | ORM with async session, Alembic migrations | Already the project's DB layer |
| Alembic | Already installed | Database schema migrations | Already used for all schema changes |
| Next.js + shadcn/ui | Already installed | Frontend Pipeline page components | Already the project's frontend stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | Already installed | File upload handling in FastAPI | Background image upload endpoint |
| aiofiles | Check if installed | Async file I/O for uploads | Saving uploaded background images |

No new packages required. Everything needed is already in the project stack.

## Architecture Patterns

### Recommended Project Structure (new/modified files)
```
config/
  themes.yaml                      # MODIFY: add colors array per theme
src/
  api/
    models.py                      # MODIFY: add ManualRunRequest, ApprovalRequest models
    routes/
      pipeline.py                  # MODIFY: add manual-run, approve, reject, upload endpoints
  database/
    migrations/versions/
      009_add_approval_status.py   # NEW: add approval_status to content_packages
    models.py                      # MODIFY: add approval_status column to ContentPackage
    repositories/
      content_repo.py              # MODIFY: add approval queries (by status, bulk update)
  image_maker.py                   # MODIFY: support solid color backgrounds
  pipeline/
    async_orchestrator.py          # MINOR: may need custom_phrases bypass mode
    workers/
      generation_layer.py          # MODIFY: support literal phrases (skip PhraseWorker)
memelab/src/
  app/(app)/pipeline/
    page.tsx                       # MAJOR REWRITE: new form per UI-SPEC
  lib/
    api.ts                         # MODIFY: add new API calls (manual-run, approve, upload)
  hooks/
    use-pipeline.ts                # MODIFY: support new manual run flow
```

### Pattern 1: Solid Color Background in create_image()
**What:** Extend `create_image()` to accept hex color string (e.g., "#1A1A3E") instead of only file paths. When a hex string is detected, create a solid color PIL Image instead of loading from disk.
**When to use:** Every time a user selects "Cor solida" as background type.
**Example:**
```python
# In image_maker.py
def create_image(
    text: str,
    background_path: str,  # Can be file path OR hex color like "#1A1A3E"
    output_path: str | None = None,
    watermark_text: str | None = None,
    layout: str | None = None,
) -> str:
    # Detect solid color
    if background_path.startswith("#") and len(background_path) in (4, 7):
        # Parse hex to RGB tuple
        hex_color = background_path.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        bg = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (r, g, b, 255))
    else:
        bg = Image.open(background_path).convert("RGBA")
        bg = _crop_center(bg, IMAGE_WIDTH, IMAGE_HEIGHT)
    # ... rest of composition unchanged
```

### Pattern 2: Literal Phrases (bypass PhraseWorker)
**What:** When user provides exact phrases ("Use my phrase" mode), skip the PhraseWorker entirely and create WorkOrders with pre-filled phrases. The GenerationLayer needs a path where it receives phrases directly rather than generating them.
**When to use:** D-06 "Use my phrase" mode.
**Example:**
```python
# In the manual run endpoint or orchestrator adapter:
# For "use my phrase" mode, each phrase becomes its own WorkOrder
# with a pre-set phrase field. GenerationLayer.process() checks
# if wo has a pre_phrase attribute and skips PhraseWorker.
```

### Pattern 3: Approval Status on ContentPackage
**What:** Add `approval_status` column with values: 'pending' (default), 'approved', 'rejected'. Expose via API endpoints for single and bulk updates.
**When to use:** D-12 through D-15 (approve/reject flow).
**Example:**
```python
# Alembic migration
# In content_packages table:
approval_status: Mapped[str] = mapped_column(
    String(20), default="pending", server_default="pending"
)
# Index for filtering:
Index("idx_pkg_approval_status", "approval_status")
```

### Pattern 4: Background Image Upload
**What:** POST endpoint that accepts multipart file upload, validates type/size, saves to `assets/backgrounds/{character_slug}/` directory.
**When to use:** D-05 (upload new backgrounds).
**Example:**
```python
@router.post("/backgrounds/upload")
async def upload_background(
    file: UploadFile,
    character_slug: str = Query(...),
    current_user=Depends(get_current_user),
):
    # Validate: max 5MB, accept jpg/png/webp
    # Save to assets/backgrounds/{character_slug}/{filename}
    # Return: { filename, path, width, height }
```

### Anti-Patterns to Avoid
- **Creating a new orchestrator class:** Reuse `AsyncPipelineOrchestrator` with its existing `manual_topics` + `background_mode="static"` path. Don't duplicate orchestration logic.
- **Calling Gemini Image API anywhere:** The entire point of Phase 12 is zero Gemini Image calls. Verify `background_mode="static"` is enforced.
- **Adding approval logic to the pipeline run itself:** Approval happens AFTER the run completes, as a separate user action. Don't mix it into the orchestrator.
- **Storing solid color palette in the database:** Colors go in themes.yaml (config file). No migration needed for colors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image composition | Custom canvas rendering | `image_maker.create_image()` | Already handles text wrapping, stroke, shadow, vignette, watermark, 4 layouts |
| Pipeline orchestration | New pipeline class | `AsyncPipelineOrchestrator` with `manual_topics` + `background_mode="static"` | Already has shortcut mode that bypasses L1/L2/L3 |
| File upload validation | Manual MIME checking | FastAPI's `UploadFile` + python-multipart | Built-in content type detection |
| Form state management | Custom form library | React useState (existing pattern) | Project already uses this approach on the Pipeline page |
| Database migration | Raw SQL ALTER TABLE | Alembic `op.add_column()` | Project standard for all schema changes |

**Key insight:** Almost every backend piece exists. The orchestrator already supports `background_mode="static"` and `manual_topics`. The work is (1) adding solid color support to the composition engine, (2) adding a "literal phrase" path that skips PhraseWorker, (3) an approval_status column + API, and (4) a significant frontend rebuild per the UI-SPEC.

## Common Pitfalls

### Pitfall 1: Accidentally calling Gemini Image API
**What goes wrong:** If `use_gemini_image` is not explicitly set to `False` or `background_mode` is not `"static"`, the ImageWorker may attempt Gemini Image generation.
**Why it happens:** `PipelineRunRequest.use_gemini_image` defaults to `None` (which falls through to config), and `background_mode` defaults to `"auto"`.
**How to avoid:** The manual run endpoint MUST force `background_mode="static"` and `use_gemini_image=False` regardless of what the user sends. The orchestrator should never reach the Gemini code path.
**Warning signs:** Any import of `GeminiImageClient` in the manual run flow.

### Pitfall 2: PhraseWorker still called in "Use my phrase" mode
**What goes wrong:** Even when user provides literal phrases, the pipeline still calls Gemini to generate phrases (wasting API credits and replacing user text).
**Why it happens:** GenerationLayer.process() always calls `self.phrase_worker.generate()`. There's no path to inject pre-written phrases.
**How to avoid:** Add a `pre_phrases` field to WorkOrder (or use a flag). When present, GenerationLayer skips PhraseWorker and uses the provided phrases directly.
**Warning signs:** Gemini API calls appearing in logs during "Use my phrase" runs.

### Pitfall 3: Missing approval_status migration
**What goes wrong:** Frontend sends approval status updates but the column doesn't exist, causing 500 errors.
**Why it happens:** ContentPackage model has no `approval_status` field currently.
**How to avoid:** Create Alembic migration FIRST, run it, then add the ORM column and API endpoints.
**Warning signs:** `OperationalError: Unknown column 'approval_status'`

### Pitfall 4: create_image() fails with hex color string
**What goes wrong:** `Image.open("#2C3E50")` raises `FileNotFoundError`.
**Why it happens:** `create_image()` currently only handles file paths.
**How to avoid:** Add hex color detection at the top of `create_image()` before calling `Image.open()`.
**Warning signs:** `FileNotFoundError` or `IsADirectoryError` in Pillow calls.

### Pitfall 5: Large file uploads blocking the event loop
**What goes wrong:** Uploading a 5MB image blocks the async event loop.
**Why it happens:** File I/O is sync by default.
**How to avoid:** Use `await file.read()` (FastAPI's async UploadFile) and write with aiofiles or `asyncio.to_thread()`.
**Warning signs:** API becomes unresponsive during uploads.

### Pitfall 6: Frontend not refreshing results after approval
**What goes wrong:** User clicks approve but the UI doesn't update.
**Why it happens:** Optimistic UI update not implemented, or SWR cache not invalidated.
**How to avoid:** Use optimistic state update in the frontend (update local state immediately, then confirm with API response).
**Warning signs:** Badge shows wrong status until page refresh.

## Code Examples

### Solid Color Background (extending image_maker.py)
```python
# Source: image_maker.py create_image() — proposed modification
def create_image(text, background_path, output_path=None, watermark_text=None, layout=None):
    # NEW: detect hex color
    if isinstance(background_path, str) and background_path.startswith("#"):
        hex_color = background_path.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        bg = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (r, g, b, 255))
    else:
        bg = Image.open(background_path).convert("RGBA")
        bg = _crop_center(bg, IMAGE_WIDTH, IMAGE_HEIGHT)
    # ... rest unchanged
```

### Per-Theme Color Palettes (themes.yaml addition)
```yaml
# Source: config/themes.yaml — proposed addition per D-02
- key: sabedoria
  label: Sabedoria
  colors: ["#1A1A3E", "#2C3E6B", "#0D1B2A", "#1B3A5C", "#2E4057"]
  # deep blues/midnight — mystic wisdom
  acao: wise elderly wizard...
  cenario: mystical library...

- key: cafe
  label: Cafe
  colors: ["#3E2723", "#5D4037", "#4E342E", "#6D4C41", "#795548"]
  # warm browns — cozy coffee vibes
  acao: wizard lovingly holding...
  cenario: cozy tavern corner...
```

### Approval Status Migration
```python
# Source: standard Alembic pattern from project
def upgrade():
    op.add_column("content_packages", sa.Column(
        "approval_status", sa.String(20),
        server_default="pending", nullable=False
    ))
    op.create_index("idx_pkg_approval_status", "content_packages", ["approval_status"])

def downgrade():
    op.drop_index("idx_pkg_approval_status", "content_packages")
    op.drop_column("content_packages", "approval_status")
```

### Manual Run API Endpoint (new Pydantic model)
```python
# Source: pattern from existing PipelineRunRequest
class ManualRunRequest(BaseModel):
    """Manual pipeline run — zero Gemini Image calls."""
    input_mode: str = Field(description="'topic' or 'phrase'")
    topic: str = Field(default="", description="Topic for Gemini phrase generation")
    phrases: list[str] = Field(default=[], description="Literal phrases (one per meme)")
    count: int = Field(default=3, ge=1, le=10)
    theme_key: str = Field(default="sabedoria")
    background_type: str = Field(default="solid", description="'solid' or 'image'")
    background_color: str = Field(default="", description="Hex color e.g. '#1A1A3E'")
    background_image: str = Field(default="", description="Filename from character backgrounds")
    character_slug: str | None = Field(default=None)
    enable_l5: bool = Field(default=True, description="Run L5 post-production")
    layout: str = Field(default="bottom")
```

### Approve/Reject API Endpoints
```python
@router.patch("/content/{package_id}/approve")
async def approve_content(package_id: int, ...):
    repo = ContentPackageRepository(session)
    pkg = await repo.update(package_id, {"approval_status": "approved"})
    ...

@router.patch("/content/{package_id}/reject")
async def reject_content(package_id: int, ...):
    repo = ContentPackageRepository(session)
    pkg = await repo.update(package_id, {"approval_status": "rejected"})
    ...

@router.patch("/content/bulk-approve")
async def bulk_approve(package_ids: list[int], ...):
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gemini Image for all backgrounds | Static backgrounds + Pillow composition | Phase 12 (now) | Zero API image costs, instant generation |
| Full L1-L5 pipeline always | Manual shortcut bypassing L1-L3 | Already exists | Foundation for manual mode |
| No approval workflow | Approve/reject per meme | Phase 12 (now) | User control before publishing |

## Open Questions

1. **Theme color palette curation**
   - What we know: D-02 says 3-5 colors per theme matching its mood
   - What's unclear: Exact hex values for all 13+ base themes
   - Recommendation: Define palettes for the 13 original themes. AI-generated themes get a default neutral palette. Colors can be refined later.

2. **"Generate from topic" with zero Gemini Image calls**
   - What we know: D-06 says "Generate from topic" uses Gemini to generate the phrase text
   - What's unclear: Is Gemini text generation (phrase) acceptable? Only Gemini IMAGE is excluded.
   - Recommendation: Yes, Gemini text (PhraseWorker via `generate()`) is fine. The constraint is zero Gemini Image API calls. Phrase generation uses the text model (gemini-2.5-flash), not the image model.

3. **Upload storage and character_slug validation**
   - What we know: D-05 says upload per-character, D-04 says `assets/backgrounds/{character}/`
   - What's unclear: Should we validate character_slug exists in DB before saving?
   - Recommendation: Yes, validate character exists. Create directory if needed. Max 5MB, accept jpg/png/webp only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (async with pytest-asyncio) |
| Config file | None explicit (uses pytest defaults) |
| Quick run command | `python -m pytest tests/ -x --timeout=30` |
| Full suite command | `python -m pytest tests/ -v --timeout=60` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | Manual pipeline run produces memes with zero Gemini Image calls | integration | `python -m pytest tests/test_manual_pipeline.py::test_manual_run_static_only -x` | Wave 0 |
| PIPE-02 | User selects theme and background (solid color or image) | unit | `python -m pytest tests/test_manual_pipeline.py::test_solid_color_background -x` | Wave 0 |
| PIPE-03 | Approve/reject workflow on content packages | unit | `python -m pytest tests/test_manual_pipeline.py::test_approval_status -x` | Wave 0 |
| PIPE-04 | Pillow composes image with static background + phrase text | unit | `python -m pytest tests/test_manual_pipeline.py::test_create_image_hex_color -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_manual_pipeline.py -x --timeout=30`
- **Per wave merge:** `python -m pytest tests/ -v --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_manual_pipeline.py` -- covers PIPE-01 through PIPE-04
- [ ] `tests/conftest.py` -- may need async DB session fixture if not present

## Project Constraints (from CLAUDE.md)

- Python project with Pillow for image composition, Google Gemini API for text generation
- Image format: 4:5 (1080x1350px) vertical
- Watermark: @magomestre420 (default, per-character override)
- 4 layout templates: bottom, top, center, split_top
- Background directories: `assets/backgrounds/mago/` (existing), `assets/backgrounds/{character}/` (pattern)
- Frontend: Next.js with shadcn/ui components, Radix UI primitives
- Database: MySQL (aiomysql) + SQLAlchemy 2.0 async + Alembic migrations
- API: FastAPI on 127.0.0.1 (Windows), Swagger at /docs
- Models available: gemini-2.5-flash for text (PhraseWorker), no Gemini Image in this phase

## Sources

### Primary (HIGH confidence)
- Direct code reading: `src/image_maker.py`, `src/pipeline/async_orchestrator.py`, `src/pipeline/workers/image_worker.py`, `src/pipeline/workers/generation_layer.py`, `src/pipeline/workers/phrase_worker.py`
- Direct code reading: `src/api/routes/pipeline.py`, `src/api/models.py`, `src/database/models.py`, `src/database/repositories/content_repo.py`
- Direct code reading: `memelab/src/app/(app)/pipeline/page.tsx`, `memelab/src/lib/api.ts`, `memelab/src/hooks/use-pipeline.ts`
- Direct code reading: `config/themes.yaml`, `config.py`
- Phase context: `12-CONTEXT.md`, `12-UI-SPEC.md`

### Secondary (MEDIUM confidence)
- CLAUDE.md project instructions
- MEMORY.md project memory

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and in use
- Architecture: HIGH -- extending existing patterns, not creating new ones
- Pitfalls: HIGH -- identified from direct code reading of existing pipeline flow
- Frontend: MEDIUM -- UI-SPEC exists but implementation details for complex interactions (color picker, image picker, upload) need careful implementation

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable project stack, no external dependencies changing)
