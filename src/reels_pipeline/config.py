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
REELS_TTS_VOICE = os.getenv("REELS_TTS_VOICE", "Charon")

# Transcription (Gemini multimodal — same API key)
REELS_TRANSCRIPTION_PROVIDER = os.getenv("REELS_TRANSCRIPTION_PROVIDER", "gemini")

# Subtitle styling (ASS format)
REELS_SUB_FONT = os.getenv("REELS_SUB_FONT", "MedievalSharp")
REELS_SUB_FONTSIZE = int(os.getenv("REELS_SUB_FONTSIZE", "12"))
REELS_SUB_COLOR = os.getenv("REELS_SUB_COLOR", "&H00B4EBFF&")  # warm yellow (ASS BBGGRR)
REELS_SUB_OUTLINE_COLOR = os.getenv("REELS_SUB_OUTLINE_COLOR", "&H000000&")
REELS_SUB_OUTLINE = int(os.getenv("REELS_SUB_OUTLINE", "1"))
REELS_SUB_MARGIN_V = int(os.getenv("REELS_SUB_MARGIN_V", "35"))
REELS_SUB_MARGIN_H = int(os.getenv("REELS_SUB_MARGIN_H", "15"))

# Video assembly
REELS_IMAGE_DURATION = float(os.getenv("REELS_IMAGE_DURATION", "4.0"))
REELS_TRANSITION_DURATION = float(os.getenv("REELS_TRANSITION_DURATION", "0.5"))
REELS_TRANSITION_TYPE = os.getenv("REELS_TRANSITION_TYPE", "fade")
REELS_SEGMENT_MAX_DURATION = float(os.getenv("REELS_SEGMENT_MAX_DURATION", "30.0"))
REELS_FPS = 30
REELS_VIDEO_CRF = 18

# Available FFmpeg xfade transitions (for frontend config panel)
REELS_AVAILABLE_TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "dissolve",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circlecrop", "circleopen", "circleclose",
    "radial", "smoothleft", "smoothright", "zoomin",
    "pixelize", "diagtl", "diagtr",
]

# Default video model for Kie.ai
REELS_VIDEO_MODEL = os.getenv("REELS_VIDEO_MODEL", "hailuo/2-3-image-to-video-standard")

# Available Kie.ai video models for reels (label, price per scene in BRL, durations, resolution)
REELS_AVAILABLE_MODELS = {
    "hailuo/2-3-image-to-video-standard": {"label": "Hailuo 2.3 Standard", "price_brl": 0.86, "durations": [6, 10], "resolution": "720p"},
    "hailuo/2-3-image-to-video-pro": {"label": "Hailuo 2.3 Pro", "price_brl": 0.86, "durations": [6, 10], "resolution": "1080p"},
    "wan/2-6-flash-image-to-video": {"label": "Wan 2.6 Flash", "price_brl": 1.05, "durations": [5, 10, 15], "resolution": "720p"},
    "wan/2-6-image-to-video": {"label": "Wan 2.6", "price_brl": 1.83, "durations": [5, 10, 15], "resolution": "720p"},
    "kling/v2-1-standard": {"label": "Kling v2.1", "price_brl": 1.44, "durations": [5, 10], "resolution": "720p"},
    "bytedance/seedance-1.5-pro": {"label": "Seedance 1.5 Pro", "price_brl": 2.62, "durations": [4, 8, 12], "resolution": "1080p"},
    "kling-3.0/video": {"label": "Kling 3.0", "price_brl": 2.10, "durations": [3, 5, 10, 15], "resolution": "1080p"},
}

# Output
REELS_OUTPUT_DIR = os.getenv("REELS_OUTPUT_DIR", "output/reels")

# Cost tracking (USD to BRL)
REELS_USD_TO_BRL = float(os.getenv("REELS_USD_TO_BRL", "5.75"))
