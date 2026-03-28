"""Reels video builder — FFmpeg slideshow with xfade crossfade + audio + SRT subtitles.

Assembles generated images into a slideshow with smooth crossfade transitions,
overlays SRT subtitles, and mixes with TTS audio. Uses subprocess (same pattern
as legend_renderer.py) — no ffmpeg-python dependency.

Phase 999.4 — Instagram Reels Pipeline
"""

import logging
import os
import platform
import shutil
import subprocess

from src.reels_pipeline.config import (
    REELS_FPS,
    REELS_IMAGE_DURATION,
    REELS_TRANSITION_DURATION,
    REELS_TRANSITION_TYPE,
    REELS_VIDEO_CRF,
)

logger = logging.getLogger("clip-flow.reels.video_builder")


def is_ffmpeg_available() -> bool:
    """Check if FFmpeg is installed and on PATH."""
    return shutil.which("ffmpeg") is not None


def _escape_srt_path(path: str) -> str:
    """Escape SRT file path for FFmpeg subtitles filter.

    FFmpeg subtitles filter treats : [ ] ; ' as special chars.
    All must be escaped with backslash for the path portion.
    """
    p = os.path.abspath(path).replace("\\", "/")
    # Escape special FFmpeg filter chars in path
    for ch in (":", "'", "[", "]", ";", ","):
        p = p.replace(ch, f"\\{ch}")
    return p


def build_reel_video(
    image_paths: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str,
    config_override: dict | None = None,
) -> str:
    """Assemble images + audio + SRT subtitles into a Reel MP4 via FFmpeg xfade.

    Args:
        image_paths: Paths to 1080x1920 JPEG images (already scaled).
        audio_path: Path to narration audio file (WAV or MP3).
        srt_path: Path to SRT subtitle file.
        output_path: Path for the output MP4 file.
        config_override: Optional dict to override default config values.

    Returns:
        output_path on success.

    Raises:
        RuntimeError: If FFmpeg is not available or encoding fails.
    """
    if not is_ffmpeg_available():
        raise RuntimeError("FFmpeg not found. Install via: brew install ffmpeg")

    if not image_paths:
        raise ValueError("No image paths provided")

    cfg = config_override or {}
    image_duration = cfg.get("image_duration", REELS_IMAGE_DURATION)
    transition_duration = cfg.get("transition_duration", REELS_TRANSITION_DURATION)
    transition_type = cfg.get("transition_type", REELS_TRANSITION_TYPE)
    fps = cfg.get("fps", REELS_FPS)
    crf = cfg.get("crf", REELS_VIDEO_CRF)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Build FFmpeg command
    cmd = ["ffmpeg", "-y"]

    # 1. Inputs: each image as looping input + audio
    for img_path in image_paths:
        cmd += ["-loop", "1", "-t", str(image_duration), "-framerate", str(fps), "-i", img_path]
    audio_index = len(image_paths)
    cmd += ["-i", audio_path]

    # 2. Build filter_complex
    n = len(image_paths)

    # Scale filters: force all images to 1080x1920
    scale_filters = []
    for i in range(n):
        scale_filters.append(
            f"[{i}]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:-1:-1:color=black[s{i}]"
        )

    # 3. xfade chain
    xfade_filters = []
    if n == 1:
        # Single image: no xfade, just copy
        xfade_filters.append("[s0]copy[vout]")
    else:
        prev = "s0"
        for i in range(1, n):
            offset = i * image_duration - i * transition_duration
            out = f"f{i}" if i < n - 1 else "vout"
            xfade_filters.append(
                f"[{prev}][s{i}]xfade=transition={transition_type}"
                f":duration={transition_duration}:offset={offset}[{out}]"
            )
            prev = out

    # 4. Subtitle overlay
    # FFmpeg subtitles filter: filename and force_style are colon-separated options.
    # The filename must have special chars escaped, but force_style uses its own quoting.
    abs_srt = os.path.abspath(srt_path)
    # Use the filename option with single-quote wrapping to avoid path parsing issues
    subtitle_filter = (
        f"[vout]subtitles=filename='{abs_srt}'"
        f":force_style='FontSize=52,PrimaryColour=&HFFFFFF&,"
        f"OutlineColour=&H000000&,Outline=2,Alignment=2,MarginV=200'[final]"
    )

    filter_complex = ";".join(scale_filters + xfade_filters + [subtitle_filter])

    cmd += ["-filter_complex", filter_complex]

    # 5. Output args
    cmd += [
        "-map", "[final]",
        "-map", f"{audio_index}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(fps),
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info(f"Running FFmpeg with {n} images, transition={transition_type}")
    logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed (exit {result.returncode}): {result.stderr[:1000]}"
        )

    logger.info(f"Video assembled: {output_path}")
    return output_path


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds via ffprobe.

    Args:
        video_path: Path to a video file.

    Returns:
        Duration in seconds as float.
    """
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[:500]}")

    return float(result.stdout.strip())
