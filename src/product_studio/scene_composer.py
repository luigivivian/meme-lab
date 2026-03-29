"""Gemini Image scene composition — places product cutout into AI-generated scene.

Per D-06: Gemini Image inpainting for scene generation.
Per D-07: product cutout + scene prompt -> composed image.
"""

import asyncio
import json
import logging
from io import BytesIO
from pathlib import Path

from PIL import Image
from google.genai import types

from src.llm_client import _get_client

logger = logging.getLogger("clip-flow.ads.scene_composer")


async def compose_scene(product_cutout_path: str, scene_prompt: str, output_path: str) -> str:
    """Compose product cutout onto AI-generated scene via Gemini Image.

    Returns path to composed image (1080x1920 9:16).
    """
    client = _get_client()
    cutout = Image.open(product_cutout_path)
    buf = BytesIO()
    cutout.save(buf, format="PNG")

    contents = [
        types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
        (
            f"Place this exact product into the following scene: {scene_prompt}. "
            "Keep the product IDENTICAL - same shape, color, details, proportions. "
            "Do not modify, distort, or recolor the product in any way. "
            "Professional product photography, commercial advertising quality. "
            "Vertical 9:16 composition (1080x1920). "
            "Clean, well-lit scene with the product as the focal point."
        ),
    ]

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash-image",
        contents=contents,
        config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            composed = Image.open(BytesIO(part.inline_data.data))
            composed = composed.resize((1080, 1920), Image.LANCZOS)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            composed.save(output_path, "JPEG", quality=95)
            logger.info("Scene composed: %s", output_path)
            return output_path

    raise RuntimeError("Gemini returned no image for scene composition")


async def analyze_product(image_path: str) -> dict:
    """Per D-02: Gemini Vision analyzes product photo and suggests defaults.

    Returns dict with: niche, tone, audience, scene_suggestions, product_description.
    """
    client = _get_client()
    img = Image.open(image_path)
    buf = BytesIO()
    img.save(buf, format="JPEG")

    contents = [
        types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"),
        (
            "Analyze this product photo for a commercial video ad. "
            "Return a JSON object with exactly these fields:\n"
            '- "niche": product category (e.g., "moda", "tech", "food", "beauty", "fitness")\n'
            '- "tone": recommended advertising tone (one of: "premium", "energetico", "divertido", "minimalista", "profissional", "natural")\n'
            '- "audience": target audience description in Portuguese\n'
            '- "scene_suggestions": array of 3 scene descriptions in English for product placement\n'
            '- "product_description": brief product description in Portuguese\n'
            "Return ONLY valid JSON, no markdown."
        ),
    ]

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=contents,
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
