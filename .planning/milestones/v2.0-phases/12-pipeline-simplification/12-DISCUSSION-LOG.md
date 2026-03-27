# Phase 12: Pipeline Simplification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 12-pipeline-simplification
**Areas discussed:** Background selection, Pipeline trigger flow, Preview & approval, Trend decoupling

---

## Background Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Solid color palette | Curated palette of solid colors per theme. Simplest, zero asset management. | |
| Image library browser | Browse uploaded background images from assets/backgrounds/. | |
| Both (colors + images) | Solid colors as quick option, plus image library for custom backgrounds. | ✓ |

**User's choice:** Both (colors + images)
**Notes:** Solid colors for quick default, image library for users with custom backgrounds.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-theme palettes | Each theme gets 3-5 curated colors matching its mood. | ✓ |
| One global palette | Single set of 8-12 colors for all themes. | |
| You decide | Claude picks. | |

**User's choice:** Per-theme palettes

| Option | Description | Selected |
|--------|-------------|----------|
| Per-character | Each character has own background library. Matches existing folder structure. | ✓ |
| Shared library | One global library shared by all characters. | |
| Both (shared + per-char) | Shared backgrounds plus per-character overrides. | |

**User's choice:** Per-character

| Option | Description | Selected |
|--------|-------------|----------|
| Upload via frontend | Users can upload backgrounds through the UI, stored per-character. | ✓ |
| Filesystem only | Backgrounds placed manually in assets/backgrounds/{char}/. | |
| You decide | Claude picks. | |

**User's choice:** Upload via frontend

| Option | Description | Selected |
|--------|-------------|----------|
| Solid only | Flat solid colors. Clean look, easy to implement. | ✓ |
| Solid + gradients | Optional 2-color gradients per palette color. | |
| You decide | Claude picks. | |

**User's choice:** Solid only

---

## Pipeline Trigger Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Free-text topic | User types topic, Gemini generates phrase. Same as shortcut mode. | |
| Write your own phrase | User writes exact phrase text. No Gemini text call. | |
| Both (topic OR custom phrase) | Toggle between generate and custom. Most flexible. | ✓ |

**User's choice:** Both (topic OR custom phrase)

| Option | Description | Selected |
|--------|-------------|----------|
| Existing Pipeline page | Add form to existing pipeline page alongside 5-layer diagram. | ✓ |
| New dedicated page | Create /compose or /create page. | |
| You decide | Claude picks. | |

**User's choice:** Existing Pipeline page

| Option | Description | Selected |
|--------|-------------|----------|
| User chooses (1-10) | User sets count in form, default 3. | ✓ |
| Fixed at 5 | Always 5 memes per run. | |
| You decide | Claude picks. | |

**User's choice:** User chooses (1-10)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep L5 | Still generate captions + hashtags + quality score. | |
| Skip L5 entirely | Just compose image, no enrichment. | |
| Optional toggle | User toggles enrichment on/off, default on. | ✓ |

**User's choice:** Optional toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Use sidebar selection | Character from sidebar selector. No extra input. | ✓ |
| Explicit in form | Character dropdown in the run form. | |
| You decide | Claude picks. | |

**User's choice:** Use sidebar selection

| Option | Description | Selected |
|--------|-------------|----------|
| Multiple phrases | Multiple phrases (one per line), each becomes one meme. | ✓ |
| One phrase, multiple backgrounds | One phrase, pick multiple backgrounds. | |
| One phrase, one meme | One phrase = one meme. Count only for topic mode. | |

**User's choice:** Multiple phrases

---

## Preview & Approval

| Option | Description | Selected |
|--------|-------------|----------|
| Inline results | Results appear on Pipeline page as grid with approve/reject per meme. | ✓ |
| Redirect to Gallery | Redirect to gallery page filtered by run. | |
| Both (inline + gallery) | Quick inline preview plus 'Open in Gallery' link. | |

**User's choice:** Inline results

| Option | Description | Selected |
|--------|-------------|----------|
| Mark as rejected, keep in DB | Soft delete — rejected status, visible in gallery with filter. | ✓ |
| Delete immediately | Removed from disk and DB. Irreversible. | |
| You decide | Claude picks. | |

**User's choice:** Mark as rejected, keep in DB

| Option | Description | Selected |
|--------|-------------|----------|
| Just mark approved | Approved status only. Publishing in Phase 15. | ✓ |
| Download button | Download button for manual posting. | |
| Both (approve + download) | Mark approved and show download. | |

**User's choice:** Just mark approved

---

## Trend Decoupling

| Option | Description | Selected |
|--------|-------------|----------|
| Fully decoupled | Manual pipeline never calls L1/L2/L3. Trends stay standalone. | ✓ |
| Optional 'Suggest topics' button | Button runs trends and fills topic field. | |
| You decide | Claude picks. | |

**User's choice:** Fully decoupled

| Option | Description | Selected |
|--------|-------------|----------|
| Manual only in Phase 12 | Only simplified flow exposed. Full pipeline code stays but hidden. | ✓ |
| Both modes available | Toggle between Manual and Full pipeline. | |
| You decide | Claude picks. | |

**User's choice:** Manual only in Phase 12

---

## Claude's Discretion

- Upload endpoint implementation details (storage, validation, max size)
- Default meme count and form layout
- Pipeline page split between form and results grid

## Deferred Ideas

None — discussion stayed within phase scope
