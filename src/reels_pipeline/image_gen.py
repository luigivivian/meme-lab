"""Reels image generation — Gemini API direct calls for 9:16 vertical images."""

import asyncio
import logging
import os
from pathlib import Path

import PIL.Image
from google.genai import types

from src.llm_client import _get_client
from src.reels_pipeline.config import (
    REELS_IMAGE_COUNT,
    REELS_IMAGE_HEIGHT,
    REELS_IMAGE_WIDTH,
)

logger = logging.getLogger("clip-flow.reels.image_gen")

# Model for image generation (same as notebook)
_IMAGE_MODEL = "gemini-2.5-flash-image"

# Rate limit settings
_PAUSE_BETWEEN_GENERATIONS = 2.0  # seconds between API calls
_MAX_RETRIES_429 = 2
_RETRY_BASE_WAIT = 60  # seconds, doubles each retry


def _scale_and_pad(img: PIL.Image.Image, width: int, height: int) -> PIL.Image.Image:
    """Scale image to fit within target dimensions and pad to exact size.

    Uses force_original_aspect_ratio=decrease + pad pattern
    (same as FFmpeg scale+pad for xfade compatibility).
    """
    img_ratio = img.width / img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        new_w = width
        new_h = int(width / img_ratio)
    else:
        new_h = height
        new_w = int(height * img_ratio)

    img_resized = img.resize((new_w, new_h), PIL.Image.LANCZOS)

    canvas = PIL.Image.new("RGB", (width, height), (0, 0, 0))
    offset_x = (width - new_w) // 2
    offset_y = (height - new_h) // 2
    canvas.paste(img_resized, (offset_x, offset_y))
    return canvas


async def _load_character_context(character_id: int) -> dict | None:
    """Load character DNA, refs, and persona from DB for image generation."""
    from src.database.session import get_session_factory
    from src.database.models import Character, CharacterRef
    from sqlalchemy import select
    from io import BytesIO

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Character).where(Character.id == character_id)
        )
        char = result.scalar_one_or_none()
        if not char:
            return None

        # Load approved refs
        refs_result = await session.execute(
            select(CharacterRef).where(
                CharacterRef.character_id == character_id,
                CharacterRef.status == "approved",
            ).limit(3)
        )
        refs = refs_result.scalars().all()

        # Load ref images
        ref_images = []
        from config import BASE_DIR
        for ref in refs:
            ref_path = BASE_DIR / ref.file_path
            if ref_path.exists():
                try:
                    ref_images.append(PIL.Image.open(ref_path))
                except Exception:
                    pass

        return {
            "name": char.name,
            "character_dna": char.character_dna,
            "negative_traits": char.negative_traits,
            "composition": char.composition,
            "system_prompt": char.system_prompt,
            "humor_style": char.humor_style,
            "tone": char.tone,
            "ref_images": ref_images,
        }


async def generate_reel_images(
    tema: str,
    character_id: int | None,
    output_dir: str,
    count: int | None = None,
    db_config: dict | None = None,
) -> list[str]:
    """Generate vertical 9:16 images for a Reel via Gemini API.

    Args:
        tema: Theme/topic for image generation.
        character_id: Optional character ID — loads DNA + refs for consistent character.
        output_dir: Directory to save generated images.
        count: Number of images to generate (overrides config).
        db_config: Optional DB config dict with image_count override.

    Returns:
        List of saved image file paths (1080x1920 JPEG).
    """
    n_images = count or (db_config or {}).get("image_count") or REELS_IMAGE_COUNT
    os.makedirs(output_dir, exist_ok=True)

    client = _get_client()
    saved_paths: list[str] = []

    # Load character context if provided
    char_ctx = None
    if character_id:
        char_ctx = await _load_character_context(character_id)
        if char_ctx:
            logger.info(f"Using character '{char_ctx['name']}' with {len(char_ctx['ref_images'])} refs")

    # Build prompt based on whether character is attached
    if char_ctx and char_ctx.get("character_dna"):
        prompt_base = (
            f"Instagram Reels vertical 9:16 scene. Theme: {tema}.\n\n"
            f"CHARACTER (replicate precisely from reference images):\n"
            f"{char_ctx['character_dna']}\n\n"
            f"COMPOSITION: Vertical 9:16 (1080x1920). {char_ctx.get('composition', '')}\n\n"
            f"NEGATIVE: {char_ctx.get('negative_traits', '')}\n\n"
            "High quality, cinematic lighting, professional."
        )
    else:
        prompt_base = (
            f"Instagram Reels vertical 9:16, {tema}. "
            "High quality, photographic, vibrant colors, professional. "
            "Full vertical composition 1080x1920 pixels."
        )

    for i in range(n_images):
        if i > 0:
            await asyncio.sleep(_PAUSE_BETWEEN_GENERATIONS)

        image_path = str(Path(output_dir) / f"image_{i:02d}.jpg")
        prompt = f"{prompt_base}\nScene {i + 1} of {n_images} — vary pose and angle."

        # Pass ref images for character consistency
        ref_images = char_ctx["ref_images"] if char_ctx else []
        img = await _generate_single_image(client, prompt, ref_images=ref_images)
        if img is None:
            logger.error(f"Failed to generate image {i}, skipping")
            continue

        img_padded = _scale_and_pad(img, REELS_IMAGE_WIDTH, REELS_IMAGE_HEIGHT)
        img_padded.save(image_path, "JPEG", quality=95)
        saved_paths.append(image_path)
        logger.info(f"Saved reel image {i + 1}/{n_images}: {image_path}")

    if not saved_paths:
        raise RuntimeError(f"Failed to generate any images for tema='{tema}'")

    return saved_paths


async def generate_reel_images_per_cena(
    cenas: list[dict],
    character_id: int | None,
    output_dir: str,
) -> list[str]:
    """Generate one image per cena using script context. Per REELV2-02.

    Each image prompt includes character DNA + cena narracao + legenda_overlay + position.
    Generates exactly len(cenas) images (1 per cena).
    """
    os.makedirs(output_dir, exist_ok=True)
    client = _get_client()
    saved_paths: list[str] = []

    char_ctx = None
    if character_id:
        char_ctx = await _load_character_context(character_id)
        if char_ctx:
            logger.info(f"Per-cena gen: character '{char_ctx['name']}' with {len(char_ctx['ref_images'])} refs")

    ref_images = char_ctx["ref_images"] if char_ctx else []
    n = len(cenas)

    for i, cena in enumerate(cenas):
        if i > 0:
            await asyncio.sleep(_PAUSE_BETWEEN_GENERATIONS)

        image_path = str(Path(output_dir) / f"image_{i:02d}.jpg")
        narracao = cena.get("narracao", "")
        overlay = cena.get("legenda_overlay", "")

        if char_ctx and char_ctx.get("character_dna"):
            prompt = (
                f"Instagram Reels vertical 9:16 scene.\n"
                f"CHARACTER (replicate precisely from reference images):\n"
                f"{char_ctx['character_dna']}\n\n"
                f"SCENE {i+1} of {n}:\n"
                f"Narration: {narracao}\n"
                f"Visual: {overlay}\n\n"
                f"COMPOSITION: Vertical 9:16 (1080x1920). {char_ctx.get('composition', '')}\n"
                f"NEGATIVE: {char_ctx.get('negative_traits', '')}\n"
                f"High quality, cinematic lighting, professional."
            )
        else:
            prompt = (
                f"Instagram Reels vertical 9:16 scene {i+1} of {n}.\n"
                f"Narration: {narracao}\n"
                f"Visual: {overlay}\n"
                f"High quality, photographic, vibrant colors, professional. "
                f"Full vertical composition 1080x1920 pixels."
            )

        img = await _generate_single_image(client, prompt, ref_images=ref_images)
        if img is None:
            logger.error(f"Failed to generate per-cena image {i}, skipping")
            continue

        img_padded = _scale_and_pad(img, REELS_IMAGE_WIDTH, REELS_IMAGE_HEIGHT)
        img_padded.save(image_path, "JPEG", quality=95)
        saved_paths.append(image_path)
        logger.info(f"Saved per-cena image {i+1}/{n}: {image_path}")

    if not saved_paths:
        raise RuntimeError("Failed to generate any per-cena images")

    return saved_paths


async def _generate_single_image(
    client, prompt: str, ref_images: list[PIL.Image.Image] | None = None,
) -> PIL.Image.Image | None:
    """Generate a single image with retry on 429. Optionally includes ref images for character consistency."""
    from io import BytesIO

    # Build contents: ref images first, then prompt text
    contents: list = []
    for ref in (ref_images or []):
        buf = BytesIO()
        ref.save(buf, format="JPEG", quality=85)
        contents.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
    contents.append(prompt)

    for attempt in range(_MAX_RETRIES_429 + 1):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=_IMAGE_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return PIL.Image.open(BytesIO(part.inline_data.data))

            logger.warning("Gemini response had no image parts")
            return None

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < _MAX_RETRIES_429:
                    wait = _RETRY_BASE_WAIT * (2 ** attempt)
                    logger.warning(f"Rate limited (429), waiting {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"Rate limit exceeded after {_MAX_RETRIES_429} retries")
                return None
            raise
