"""Generate platform-specific metadata (captions, hashtags, titles) for reels.

Called after video step completes. Uses Gemini to adapt the script's content
for each target platform's format and tone requirements.

Phase E: Multi-Platform Output
"""

import asyncio
import json
import logging

from google.genai import types

logger = logging.getLogger("clip-flow.reels.platform_metadata")

PLATFORM_SPECS = {
    "instagram": {
        "max_caption": 2200,
        "max_hashtags": 8,
        "tone": "engaging, visual, use emojis sparingly",
        "fields": ["caption", "hashtags"],
    },
    "youtube_shorts": {
        "max_title": 100,
        "max_description": 5000,
        "max_hashtags": 5,
        "tone": "SEO-friendly, informative, searchable",
        "fields": ["title", "description", "tags"],
    },
    "tiktok": {
        "max_caption": 2200,
        "max_hashtags": 5,
        "tone": "casual, trendy, conversational, use hashtags inline",
        "fields": ["caption", "hashtags"],
    },
    "facebook": {
        "max_caption": 3000,
        "max_hashtags": 10,
        "tone": "descriptive, engagement-focused, community-oriented",
        "fields": ["caption", "hashtags"],
    },
}


def _build_prompt(script_json: dict, platform: str, video_url: str | None) -> str:
    spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["instagram"])
    titulo = script_json.get("titulo", "")
    gancho = script_json.get("gancho", "")
    narracao = script_json.get("narracao_completa", "")
    hashtags_orig = script_json.get("hashtags", [])
    cta = script_json.get("cta", "")

    fields_str = ", ".join(spec["fields"])

    prompt = f"""Generate {platform} metadata for a short vertical video (Reel/Short).

VIDEO CONTEXT:
- Title: {titulo}
- Hook: {gancho}
- Full narration: {narracao[:500]}
- Original hashtags: {', '.join(hashtags_orig[:10])}
- CTA: {cta}

PLATFORM: {platform}
TONE: {spec['tone']}
REQUIRED FIELDS: {fields_str}

RULES:
- Write in Brazilian Portuguese (pt-BR)
- Caption must be engaging and platform-appropriate
"""
    if platform == "instagram":
        prompt += (
            "- Caption: Write a keyword-rich caption like a mini blog post (3-5 lines). "
            "Integrate the primary topic keywords naturally into the text. "
            "This is critical for Instagram SEO — the algorithm reads captions as searchable text content.\n"
        )
    if "max_caption" in spec:
        prompt += f"- Caption max {spec['max_caption']} characters\n"
    if "max_title" in spec:
        prompt += f"- Title max {spec['max_title']} characters\n"
    if "max_description" in spec:
        prompt += f"- Description max {spec['max_description']} characters\n"

    if "max_hashtags" in spec:
        prompt += (
            f"- Hashtags: Generate EXACTLY {spec['max_hashtags']} hashtags following this formula:\n"
            "  - 1 broad/trending hashtag (ex: #viral, #dicas)\n"
            "  - 2 niche-specific hashtags (ex: #marketingdigital, #empreendedorismo)\n"
            "  - 2 micro-niche hashtags (ex: #reelsparainiciantes, #tiktokbrasil2026)\n"
            "  NEVER use #fyp, #foryou, or #viral as primary hashtags.\n"
            f"  Total: exactly {spec['max_hashtags']} hashtags, no more.\n"
        )

    prompt += f"""
Return ONLY valid JSON with these exact keys: {fields_str}
- hashtags/tags should be arrays of strings (without # prefix)
- caption/title/description should be strings
"""
    return prompt


async def generate_platform_metadata(
    script_json: dict,
    platforms: list[str],
    video_url: str | None = None,
) -> dict[str, dict]:
    """Generate adapted metadata for each platform using Gemini.

    Args:
        script_json: The reel's script dict (titulo, gancho, narracao_completa, etc).
        platforms: List of platform names (e.g. ["instagram", "youtube_shorts"]).
        video_url: Optional video URL to include in outputs.

    Returns:
        Dict keyed by platform name, each containing platform-specific metadata.
    """
    from src.llm_client import _get_client, _extract_text

    client = _get_client()
    results = {}

    for platform in platforms:
        if platform not in PLATFORM_SPECS:
            logger.warning(f"Unknown platform '{platform}', skipping")
            continue

        prompt = _build_prompt(script_json, platform, video_url)
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.7,
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw = _extract_text(response)
            parsed = json.loads(raw)

            # Ensure hashtags have # prefix for display
            if "hashtags" in parsed and isinstance(parsed["hashtags"], list):
                parsed["hashtags"] = [
                    f"#{h.lstrip('#')}" for h in parsed["hashtags"]
                ]
            if "tags" in parsed and isinstance(parsed["tags"], list):
                parsed["tags"] = [t.lstrip("#") for t in parsed["tags"]]

            if video_url:
                parsed["video_url"] = video_url

            results[platform] = parsed
            logger.info(f"Platform metadata generated for {platform}")

        except Exception as e:
            logger.error(f"Failed to generate metadata for {platform}: {e}")
            # Fallback: use original script data
            results[platform] = _fallback_metadata(script_json, platform, video_url)

    return results


def _fallback_metadata(
    script_json: dict, platform: str, video_url: str | None
) -> dict:
    """Create basic metadata from script when Gemini call fails."""
    titulo = script_json.get("titulo", "")
    caption = script_json.get("caption_instagram", titulo)
    hashtags = [f"#{h.lstrip('#')}" for h in script_json.get("hashtags", [])]

    base = {"caption": caption, "hashtags": hashtags}
    if video_url:
        base["video_url"] = video_url

    if platform == "youtube_shorts":
        base["title"] = titulo[:100]
        base["description"] = script_json.get("narracao_completa", "")[:5000]
        base["tags"] = [h.lstrip("#") for h in hashtags]

    return base
