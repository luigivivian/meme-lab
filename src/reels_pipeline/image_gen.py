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
        character_id: Optional character ID (for future ref image lookup).
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

    prompt_base = (
        f"Instagram Reels vertical 9:16, {tema}. "
        "High quality, photographic, vibrant colors, professional. "
        "Full vertical composition 1080x1920 pixels."
    )

    for i in range(n_images):
        if i > 0:
            await asyncio.sleep(_PAUSE_BETWEEN_GENERATIONS)

        image_path = str(Path(output_dir) / f"image_{i:02d}.jpg")
        prompt = f"{prompt_base} Variation {i + 1} of {n_images}."

        img = await _generate_single_image(client, prompt)
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


async def _generate_single_image(client, prompt: str) -> PIL.Image.Image | None:
    """Generate a single image with retry on 429."""
    from io import BytesIO

    for attempt in range(_MAX_RETRIES_429 + 1):
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=_IMAGE_MODEL,
                contents=prompt,
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
