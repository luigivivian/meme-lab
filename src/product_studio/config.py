"""Product Studio configuration constants with env var fallback."""

import os

# Feature flag
ADS_ENABLED = os.getenv("ADS_ENABLED", "false").lower() == "true"

# Output
ADS_OUTPUT_DIR = os.getenv("ADS_OUTPUT_DIR", "output/ads")

# Cost tracking (USD to BRL)
ADS_USD_TO_BRL = float(os.getenv("ADS_USD_TO_BRL", "5.75"))

# Background removal model
ADS_REMBG_MODEL = os.getenv("ADS_REMBG_MODEL", "u2net")

# Video defaults
ADS_DEFAULT_VIDEO_MODEL = os.getenv("ADS_DEFAULT_VIDEO_MODEL", "wan2.1-i2v")
ADS_DEFAULT_STYLE = os.getenv("ADS_DEFAULT_STYLE", "cinematic")

# Master format (per D-17)
ADS_MASTER_FORMAT = "9:16"

# Export formats (per D-18)
ADS_EXPORT_FORMATS = ["9:16", "16:9", "1:1"]

# Image dimensions
ADS_IMAGE_WIDTH = 1080
ADS_IMAGE_HEIGHT = 1920

# Step order for pipeline (per D-21)
ADS_STEP_ORDER = ["analysis", "scene", "prompt", "video", "copy", "audio", "assembly", "export"]

# Music genre mapping (per design doc MUSIC_MAP)
MUSIC_MAP = {
    "premium": "cinematic ambient piano, luxury, elegant",
    "energetico": "upbeat electronic, energetic, dynamic",
    "divertido": "happy pop, cheerful, playful",
    "minimalista": "minimal ambient, subtle, clean",
    "profissional": "corporate, modern, confident",
    "natural": "acoustic guitar, warm, organic",
}

# Negative prompts by style
NEGATIVE_PROMPTS = {
    "cinematic": "text, watermark, logo, blurry, low quality, distorted product, human hands, person",
    "narrated": "text, watermark, logo, blurry, low quality, distorted product, nudity",
    "lifestyle": "text, watermark, logo, blurry, low quality, distorted product, nudity, gore",
}

# Text overlay layout by style
TEXT_LAYOUTS = {
    "cinematic": {"headline_y": 0.12, "cta_y": 0.88, "fontsize_h": 52, "fontsize_cta": 36},
    "narrated": {"headline_y": None, "cta_y": 0.90, "fontsize_h": 0, "fontsize_cta": 32},
    "lifestyle": {"headline_y": 0.08, "cta_y": 0.92, "fontsize_h": 40, "fontsize_cta": 28},
}

# Style -> scene count mapping (per D-09)
STYLE_SCENE_COUNT = {"cinematic": 1, "narrated": 4, "lifestyle": 5}

# Style -> audio mode defaults (per D-14)
STYLE_AUDIO_DEFAULTS = {"cinematic": "music", "narrated": "narrated", "lifestyle": "ambient"}

# Style -> duration range (per design doc)
STYLE_DURATION = {"cinematic": (8, 15), "narrated": (15, 30), "lifestyle": (15, 30)}

# Style -> default video model (per D-08)
STYLE_VIDEO_MODEL = {"cinematic": "wan2.1-i2v", "narrated": "wan2.1-i2v", "lifestyle": "kling2.1-i2v"}
