"""Reels TTS narration — Gemini Flash TTS gemini-2.5-flash-preview-tts (same GOOGLE_API_KEY, zero extra dependency)."""

import logging
import os
import wave

from google.genai import types

from src.llm_client import _get_client
from src.reels_pipeline.config import (
    REELS_TTS_MODEL,
    REELS_TTS_VOICE,
)

logger = logging.getLogger("clip-flow.reels.tts")

# Gemini Flash TTS audio output: raw PCM 24kHz mono 16-bit
_SAMPLE_RATE = 24000
_SAMPLE_WIDTH = 2  # 16-bit
_CHANNELS = 1

# Available Gemini TTS voices (subset, all support PT-BR)
AVAILABLE_VOICES = [
    "Puck",    # upbeat, energetic
    "Aoede",   # bright, warm
    "Kore",    # firm, clear
    "Charon",  # serious, deep
    "Leda",    # calm, gentle
    "Zephyr",  # neutral, balanced
]


def _wrap_pcm_as_wav(pcm_data: bytes, output_path: str) -> str:
    """Wrap raw PCM 24kHz mono 16-bit data in a WAV container."""
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm_data)
    return output_path


async def generate_narration(
    text: str,
    output_path: str,
    voice: str | None = None,
    provider: str | None = None,
) -> str:
    """Generate narration audio from text via TTS.

    Args:
        text: Narration text to synthesize.
        output_path: Path to save the WAV file.
        voice: Voice name (default from config).
        provider: TTS provider ("gemini" or "elevenlabs").

    Returns:
        Path to the saved WAV file.
    """
    import asyncio

    provider = provider or "gemini"

    if provider == "elevenlabs":
        raise NotImplementedError("ElevenLabs TTS deferred to follow-up")

    if provider != "gemini":
        raise ValueError(f"Unknown TTS provider: {provider}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    voice_name = voice or REELS_TTS_VOICE
    client = _get_client()

    logger.info(f"Generating TTS via {REELS_TTS_MODEL}, voice={voice_name}, text_len={len(text)}")

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=REELS_TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    ),
                ),
            ),
        ),
    )

    pcm_data = response.candidates[0].content.parts[0].inline_data.data
    _wrap_pcm_as_wav(pcm_data, output_path)
    logger.info(f"TTS saved: {output_path} ({len(pcm_data)} bytes PCM)")
    return output_path


def estimate_tts_cost(text: str) -> float:
    """Estimate TTS cost in USD for Gemini Flash TTS.

    Gemini Flash TTS: ~$0.019/min, estimate ~150 chars/min for PT-BR narration.
    """
    chars = len(text)
    minutes = chars / 150
    return minutes * 0.019 / 60
