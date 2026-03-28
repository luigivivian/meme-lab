"""Reels audio transcription — Gemini multimodal audio to SRT subtitles."""

import asyncio
import logging
import os
import re
from pathlib import Path

from google.genai import types

from src.llm_client import _get_client
from src.reels_pipeline.config import REELS_SCRIPT_LANGUAGE

logger = logging.getLogger("clip-flow.reels.transcriber")

# Model for transcription (Gemini multimodal handles audio input)
_TRANSCRIPTION_MODEL = "gemini-2.5-flash"


async def transcribe_to_srt(
    audio_path: str,
    output_path: str,
    language: str | None = None,
    provider: str | None = None,
) -> str:
    """Transcribe audio to SRT subtitle format.

    Args:
        audio_path: Path to the WAV audio file.
        output_path: Path to save the SRT file.
        language: Language code (default from config).
        provider: Transcription provider ("gemini" or "whisper_local").

    Returns:
        Path to the saved SRT file.
    """
    provider = provider or "gemini"

    if provider == "whisper_local":
        raise NotImplementedError("Local Whisper deferred to follow-up")

    if provider != "gemini":
        raise ValueError(f"Unknown transcription provider: {provider}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    lang = language or REELS_SCRIPT_LANGUAGE
    audio_bytes = Path(audio_path).read_bytes()

    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
    prompt_text = (
        f"Transcribe this audio to SRT subtitle format with timestamps. "
        f"Language: {lang}. "
        f"Group words in chunks of 4-5 words per subtitle entry. "
        f"Return ONLY the SRT content, no markdown."
    )

    client = _get_client()

    logger.info(f"Transcribing audio ({len(audio_bytes)} bytes) to SRT via Gemini, lang={lang}")

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=_TRANSCRIPTION_MODEL,
        contents=[audio_part, prompt_text],
    )

    srt_text = response.text or ""
    # Strip markdown code fences if Gemini wraps the output
    if srt_text.startswith("```"):
        lines = srt_text.strip().split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        srt_text = "\n".join(lines)

    srt_text = _normalize_srt_timestamps(srt_text)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_text)

    logger.info(f"SRT saved: {output_path} ({len(srt_text)} chars)")
    return output_path


def _normalize_srt_timestamps(srt_text: str) -> str:
    """Fix malformed SRT timestamps from Gemini.

    Gemini sometimes returns timestamps like '00:00:270' (MM:SS:mmm)
    instead of the correct SRT format '00:00:00,270' (HH:MM:SS,mmm).
    Also handles '00:00:270' -> '00:00:00,270' and variants.
    """
    def fix_timestamp(match: re.Match) -> str:
        ts = match.group(0)
        # Already correct format: HH:MM:SS,mmm
        if re.match(r"\d{2}:\d{2}:\d{2},\d{3}$", ts):
            return ts
        # Format: MM:SS:mmm (Gemini's common mistake) -> HH:MM:SS,mmm
        m = re.match(r"(\d{2}):(\d{2}):(\d{2,3})$", ts)
        if m:
            a, b, c = m.groups()
            if len(c) == 3:
                # a:b:ccc -> 00:a:b,ccc (treat as MM:SS,mmm)
                return f"00:{a}:{b},{c}"
            else:
                # a:b:cc -> 00:a:b,cc0 (treat as MM:SS,cs)
                return f"00:{a}:{b},{c}0"
        # Format: HH:MM:SS.mmm (dot instead of comma)
        m = re.match(r"(\d{2}:\d{2}:\d{2})\.(\d{3})$", ts)
        if m:
            return f"{m.group(1)},{m.group(2)}"
        return ts

    # Match timestamp patterns in arrow lines: "TS --> TS"
    return re.sub(
        r"\d{2}:\d{2}:\d{2}[,:\.]\d{2,3}|\d{2}:\d{2}:\d{2,3}",
        fix_timestamp,
        srt_text,
    )


def estimate_transcription_cost(audio_duration_seconds: float) -> float:
    """Estimate transcription cost in USD for Gemini multimodal audio input.

    Gemini Flash audio input: ~$0.001/min (negligible).
    """
    return (audio_duration_seconds / 60) * 0.001
