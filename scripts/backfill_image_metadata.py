"""Backfill image_metadata for ContentPackages missing scene/theme_key.

Derives scene description from image filename and phrase context.
Run: python -m scripts.backfill_image_metadata [--dry-run]
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from src.database.session import get_session_factory
from src.database.models import ContentPackage


def derive_scene_from_filename(image_path: str | None) -> str:
    """Extract readable scene from filename like 'mago_meditando_20260311_042925.png'."""
    if not image_path:
        return ""
    fname = Path(image_path).stem
    # Remove timestamp suffix (2026MMDD_HHMMSS pattern)
    scene = fname.replace("_", " ").split("2026")[0].strip()
    # Remove common prefixes
    for prefix in ["api ", "manual ", "gemini ", "comfyui "]:
        if scene.lower().startswith(prefix):
            scene = scene[len(prefix):]
    return scene.strip()


def infer_theme_key(scene: str) -> str:
    """Try to match scene to a known theme key."""
    known_keys = [
        "sabedoria", "confusao", "segunda_feira", "vitoria", "tecnologia",
        "cafe", "comida", "trabalho", "relaxando", "meditando",
        "relacionamento", "confronto", "surpresa", "internet",
        "generico", "cotidiano", "descanso",
    ]
    scene_lower = scene.lower()
    for key in known_keys:
        if key in scene_lower.replace(" ", "_") or key in scene_lower:
            return key
    return ""


async def backfill(dry_run: bool = False):
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(ContentPackage))
        packages = result.scalars().all()

        updated = 0
        for pkg in packages:
            meta = pkg.image_metadata if isinstance(pkg.image_metadata, dict) else {}
            changed = False

            # Add scene if missing
            if not meta.get("scene"):
                scene = derive_scene_from_filename(pkg.background_path or pkg.image_path)
                if scene:
                    meta["scene"] = scene
                    changed = True

            # Add scene_from_phrase if we have a phrase but no scene
            if not meta.get("scene") and pkg.phrase:
                meta["scene"] = pkg.phrase[:100]
                changed = True

            # Add theme_key if missing
            if not meta.get("theme_key"):
                scene = meta.get("scene", "")
                key = infer_theme_key(scene)
                if key:
                    meta["theme_key"] = key
                    changed = True

            # Add image_description from phrase
            if not meta.get("image_description") and pkg.phrase:
                meta["image_description"] = pkg.phrase
                changed = True

            if changed:
                updated += 1
                if dry_run:
                    print(f"  #{pkg.id}: scene='{meta.get('scene', '')[:40]}' theme={meta.get('theme_key', '')}")
                else:
                    pkg.image_metadata = meta

        if dry_run:
            print(f"\nDry run: {updated}/{len(packages)} packages would be updated")
        else:
            await session.commit()
            print(f"Updated {updated}/{len(packages)} packages")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN ===")
    asyncio.run(backfill(dry_run))
