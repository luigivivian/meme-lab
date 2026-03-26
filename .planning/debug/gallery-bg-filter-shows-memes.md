---
status: awaiting_human_verify
trigger: "Gallery backgrounds filter showing meme images (with phrases/text overlaid) instead of only clean backgrounds without text."
created: 2026-03-26T00:00:00Z
updated: 2026-03-26T00:03:00Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED
test: Regex pattern validation against all 467 files in backgrounds_generated/; file move verification; import check
expecting: n/a — fix applied and self-verified
next_action: Await human verification in browser (/gallery -> Backgrounds filter)

## Symptoms

expected: When selecting "Backgrounds" category filter in the gallery, only clean background images (no text/phrases) should appear.
actual: The "Backgrounds" filter still shows images that have phrases composed on them (memes).
errors: No errors — images load fine, just wrong category assignment.
reproduction: Go to /gallery → select "Backgrounds" from category dropdown → meme images with text appear.
started: Started after reorganizing output/ directory. Files were moved: memes → output/memes/, backgrounds → output/backgrounds_generated/.

## Eliminated

## Evidence

- timestamp: 2026-03-26T00:00:30Z
  checked: output/backgrounds_generated/ file count and naming patterns
  found: 467 total PNG files. 318 have background naming patterns (api_*, bg_*, mago_*, lote_*, single_*). 149 have phrase-slug names (a_alquimia_da_manha.png, etc.) matching create_image() output pattern.
  implication: 149 meme files are misplaced in backgrounds_generated/

- timestamp: 2026-03-26T00:00:45Z
  checked: create_image() in src/image_maker.py lines 309-314
  found: When output_path is None, create_image saves to GENERATED_MEMES_DIR with slug from first 4 words of phrase. Slug pattern: lowercase, underscore-separated, max 40 chars. This matches the 149 misplaced files exactly.
  implication: These files are definitely composed memes (background + text overlay), not clean backgrounds

- timestamp: 2026-03-26T00:00:50Z
  checked: _list_drive_images() in src/api/routes/drive.py lines 28-59
  found: Categorization is purely directory-based: all files in bg_dir -> "background", all in GENERATED_MEMES_DIR -> "meme". No filename pattern validation.
  implication: Any file physically in backgrounds_generated/ is shown as "background" regardless of content

- timestamp: 2026-03-26T00:00:55Z
  checked: Gemini background naming vs meme naming
  found: Gemini saves backgrounds as bg_{situacao_key}_{timestamp}.png. API route saves as api_{theme}_{timestamp}.png. ComfyUI saves as mago_{timestamp}_{random}.png. Memes use phrase slug (first 4 words).
  implication: Background files always have a recognizable prefix with timestamp pattern. Memes never have these prefixes.

- timestamp: 2026-03-26T00:02:00Z
  checked: Regex validation against all 467 files
  found: _BG_FILENAME_RE correctly classifies all 318 backgrounds as True and all 149 memes as False. Zero false positives or false negatives.
  implication: The code fix is accurate

- timestamp: 2026-03-26T00:02:30Z
  checked: File move from backgrounds_generated/ to memes/
  found: 149 meme files successfully moved. backgrounds_generated/ now has 318 files (all backgrounds). memes/ now has 301 files (152 original + 149 moved).
  implication: Data is now clean

## Resolution

root_cause: Two combined issues: (1) During the output/ directory reorganization, 149 meme files (composed images with text overlays from create_image()) were placed in output/backgrounds_generated/ instead of output/memes/. The DB-based classification used during the move only identified files referenced in content_packages as memes; the remaining memes (not in DB) were misclassified as backgrounds. (2) The _list_drive_images() API function categorized files purely by directory location with no content/naming validation, so misplaced memes appeared as "background" in the gallery.
fix: Two-part fix applied. CODE: Added _is_background_filename() regex validator in drive.py that checks for known background naming patterns (api_/bg_/mago_/single_/gemini_/lote_ prefix + 8+ digit timestamp). Files in backgrounds_generated/ that don't match are reclassified as "meme". DATA: Moved 149 misplaced meme files from output/backgrounds_generated/ to output/memes/.
verification: Self-verified: regex tested against all 467 files with 100% accuracy. Module imports successfully. Syntax valid. File counts confirmed (318 backgrounds, 301 memes). Awaiting human verification in browser.
files_changed: [src/api/routes/drive.py]
