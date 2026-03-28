"""Reels pipeline configuration constants with env var fallback."""

import os

# Feature flag
REELS_ENABLED = os.getenv("REELS_ENABLED", "false").lower() == "true"

# Images
REELS_IMAGE_COUNT = int(os.getenv("REELS_IMAGE_COUNT", "5"))
REELS_IMAGE_ASPECT_RATIO = "9:16"
REELS_IMAGE_WIDTH = 1080
REELS_IMAGE_HEIGHT = 1920

# Script (Gemini multimodal)
REELS_SCRIPT_MODEL = os.getenv("REELS_SCRIPT_MODEL", "gemini-2.5-flash")
REELS_SCRIPT_LANGUAGE = os.getenv("REELS_SCRIPT_LANGUAGE", "pt-BR")

# TTS (Gemini Flash TTS — same GOOGLE_API_KEY, zero extra dependency)
REELS_TTS_PROVIDER = os.getenv("REELS_TTS_PROVIDER", "gemini")
REELS_TTS_MODEL = os.getenv("REELS_TTS_MODEL", "gemini-2.5-flash-preview-tts")
REELS_TTS_VOICE = os.getenv("REELS_TTS_VOICE", "Puck")

# Transcription (Gemini multimodal — same API key)
REELS_TRANSCRIPTION_PROVIDER = os.getenv("REELS_TRANSCRIPTION_PROVIDER", "gemini")

# Video assembly
REELS_IMAGE_DURATION = float(os.getenv("REELS_IMAGE_DURATION", "4.0"))
REELS_TRANSITION_DURATION = float(os.getenv("REELS_TRANSITION_DURATION", "0.5"))
REELS_TRANSITION_TYPE = os.getenv("REELS_TRANSITION_TYPE", "fade")
REELS_FPS = 30
REELS_VIDEO_CRF = 18

# Output
REELS_OUTPUT_DIR = os.getenv("REELS_OUTPUT_DIR", "output/reels")

# Cost tracking (USD to BRL)
REELS_USD_TO_BRL = float(os.getenv("REELS_USD_TO_BRL", "5.75"))
