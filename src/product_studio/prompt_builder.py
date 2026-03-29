"""LLM cinematic video prompt generation per style.

Per D-10: LLM generates cinematic prompt automatically including shot type,
camera movement, lighting, aesthetic, and negative prompt.
"""

import asyncio
import logging

from src.llm_client import _get_client, _extract_text
from src.product_studio.config import NEGATIVE_PROMPTS

logger = logging.getLogger("clip-flow.ads.prompt_builder")

_STYLE_INSTRUCTIONS = {
    "cinematic": (
        "Style: CINEMATIC. Use orbital or dolly camera movement. "
        "Dramatic rim lighting with shallow depth of field. "
        "Single product hero shot, slow motion feel. "
        "Anamorphic lens flare, moody color grading."
    ),
    "narrated": (
        "Style: NARRATED. Quick cuts between close-ups and wide shots. "
        "Dynamic camera movement with rack focus transitions. "
        "Bright, editorial lighting. Multiple angles showing product details "
        "and usage context. Energetic pacing."
    ),
    "lifestyle": (
        "Style: LIFESTYLE. Tracking or POV camera following product in use. "
        "Natural, soft lighting with warm tones. "
        "Contextual environment showing real-world usage. "
        "Smooth steadicam feel, authentic and aspirational."
    ),
}

_SYSTEM_PROMPT = (
    "You are a professional video director specializing in product ad cinematography. "
    "Generate a single motion prompt for an AI video generation model. "
    "The prompt must describe: camera movement, lighting, subject action, "
    "aesthetic mood, and composition. "
    "Output ONLY the prompt text, no explanations or formatting."
)


async def build_video_prompt(
    product_description: str,
    scene_description: str,
    style: str,
    video_model: str,
    tone: str,
) -> str:
    """Generate a cinematic video prompt via Gemini for the given style.

    Returns the prompt string ready for Kie.ai video generation,
    with negative prompt appended.
    """
    style_instruction = _STYLE_INSTRUCTIONS.get(style, _STYLE_INSTRUCTIONS["cinematic"])

    user_message = (
        f"Product: {product_description}\n"
        f"Scene: {scene_description}\n"
        f"Video model: {video_model}\n"
        f"Tone: {tone}\n\n"
        f"{style_instruction}\n\n"
        "Generate the motion prompt for this product video ad. "
        "Include specific camera movement, lighting setup, and product interaction."
    )

    client = _get_client()
    from google.genai import types

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=300,
            temperature=0.8,
        ),
    )

    prompt = _extract_text(response).strip()
    negative = NEGATIVE_PROMPTS.get(style, NEGATIVE_PROMPTS["cinematic"])
    full_prompt = f"{prompt}\n\nNegative: {negative}"

    logger.info("Video prompt built for style=%s, model=%s (%d chars)", style, video_model, len(full_prompt))
    return full_prompt
