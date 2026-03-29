"""FFmpeg multi-format export with blur padding, text overlay, and audio mixing.

Per D-16 (text overlay), D-13/D-14 (audio mixing), D-18 (blur pad export).
Uses subprocess.run with list args per existing video_builder.py pattern.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.product_studio.config import ADS_EXPORT_FORMATS, ADS_MASTER_FORMAT, TEXT_LAYOUTS

logger = logging.getLogger("clip-flow.ads.exporter")

# Format string -> (width, height)
FORMAT_DIMENSIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


def overlay_text(
    input_path: str,
    output_path: str,
    headline: str | None,
    cta: str | None,
    style: str,
) -> str:
    """Overlay headline and CTA text on video using FFmpeg drawtext.

    Per D-16: FFmpeg drawtext for text overlay.
    Text written to tempfiles to avoid shell escaping (per Phase 999.2 pattern).

    Args:
        input_path: Source video path.
        output_path: Output video path.
        headline: Headline text (None to skip).
        cta: Call-to-action text (None to skip).
        style: Style key for TEXT_LAYOUTS positioning.

    Returns:
        output_path on success.
    """
    layout = TEXT_LAYOUTS.get(style, TEXT_LAYOUTS["cinematic"])
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    filters = []
    tmp_files = []

    try:
        # Headline drawtext
        if headline and layout.get("headline_y") is not None:
            tmp_h = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            tmp_h.write(headline)
            tmp_h.close()
            tmp_files.append(tmp_h.name)
            fontsize_h = layout.get("fontsize_h", 52)
            headline_y = layout["headline_y"]
            filters.append(
                f"drawtext=textfile='{tmp_h.name}'"
                f":fontsize={fontsize_h}"
                f":fontcolor=white:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h*{headline_y}"
            )

        # CTA drawtext
        if cta and layout.get("cta_y") is not None:
            tmp_c = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            tmp_c.write(cta)
            tmp_c.close()
            tmp_files.append(tmp_c.name)
            fontsize_cta = layout.get("fontsize_cta", 36)
            cta_y = layout["cta_y"]
            filters.append(
                f"drawtext=textfile='{tmp_c.name}'"
                f":fontsize={fontsize_cta}"
                f":fontcolor=white:borderw=2:bordercolor=black"
                f":x=(w-text_w)/2:y=h*{cta_y}"
            )

        if not filters:
            # No text to overlay, just copy
            shutil.copy2(input_path, output_path)
            return output_path

        filter_str = ",".join(filters)

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_str,
            "-c:v", "libx264", "-crf", "18",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]

        logger.info("Overlaying text on %s (style=%s)", input_path, style)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        logger.info("Text overlay complete: %s", output_path)
        return output_path

    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


def mix_audio(
    tts_path: str | None,
    music_path: str,
    output_path: str,
    video_duration: float,
    audio_mode: str,
) -> str | None:
    """Mix TTS narration and background music per audio_mode.

    Per D-13: TTS volume 100%, music ~20% background.
    Per D-14: Handle mute/music/narrated/ambient modes.
    Per D-12: Trim music to video duration with fade-out.
    Per Pitfall 4: amix weights=1 0.2 for narrated mode.

    Args:
        tts_path: Path to TTS narration audio (None for non-narrated modes).
        music_path: Path to background music file.
        output_path: Output mixed audio path.
        video_duration: Video duration in seconds for trimming.
        audio_mode: One of "mute", "music", "narrated", "ambient".

    Returns:
        output_path on success, None for mute mode.
    """
    if audio_mode == "mute":
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fade_start = max(0, video_duration - 1)

    if audio_mode in ("music", "ambient"):
        # Just trim music to video duration with fade-out
        cmd = [
            "ffmpeg", "-y",
            "-i", music_path,
            "-af", f"atrim=0:{video_duration},afade=t=out:st={fade_start}:d=1",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        logger.info("Mixing audio (mode=%s): trimming music to %.1fs", audio_mode, video_duration)
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        return output_path

    if audio_mode == "narrated":
        if not tts_path:
            raise ValueError("tts_path required for narrated audio mode")
        # Mix TTS (100%) + music (20%) using amix, duration=first
        cmd = [
            "ffmpeg", "-y",
            "-i", tts_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]atrim=0:{video_duration},afade=t=out:st={fade_start}:d=1[music];"
            f"[0:a][music]amix=inputs=2:duration=first:weights=1 0.2[out]",
            "-map", "[out]",
            "-c:a", "aac", "-b:a", "192k",
            output_path,
        ]
        logger.info("Mixing audio (mode=narrated): TTS + music")
        subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
        return output_path

    raise ValueError(f"Unknown audio_mode: {audio_mode}")


def export_blur_pad(
    input_path: str,
    output_path: str,
    target_w: int,
    target_h: int,
) -> str:
    """Export video with blur-padded background for aspect ratio conversion.

    Per D-18: Crop inteligente + pad com background blur.
    Uses split -> scale+crop+gblur for background, scale for foreground, overlay centered.

    Args:
        input_path: Source video path.
        output_path: Output video path.
        target_w: Target width in pixels.
        target_h: Target height in pixels.

    Returns:
        output_path on success.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    filter_str = (
        f"[0:v]split[orig][copy];"
        f"[copy]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},gblur=sigma=20[bg];"
        f"[orig]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info("Exporting blur pad %dx%d: %s", target_w, target_h, input_path)
    subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=True)
    logger.info("Blur pad export complete: %s", output_path)
    return output_path


def export_all_formats(
    input_path: str,
    output_dir: str,
    formats: list[str] | None = None,
) -> dict[str, str]:
    """Export video in multiple aspect ratio formats.

    Per D-18: Produce each format variant using blur pad.
    Master format (9:16) is copied as-is; others get blur pad conversion.

    Args:
        input_path: Source video (assumed to be in master 9:16 format).
        output_dir: Directory for output files.
        formats: List of format strings (default: ADS_EXPORT_FORMATS).

    Returns:
        Dict mapping format string to output file path.
    """
    formats = formats or ADS_EXPORT_FORMATS
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    base_name = Path(input_path).stem

    for fmt in formats:
        dims = FORMAT_DIMENSIONS.get(fmt)
        if not dims:
            logger.warning("Unknown format %s, skipping", fmt)
            continue

        target_w, target_h = dims
        safe_fmt = fmt.replace(":", "x")
        out_path = os.path.join(output_dir, f"{base_name}_{safe_fmt}.mp4")

        if fmt == ADS_MASTER_FORMAT:
            # Master format: copy as-is
            shutil.copy2(input_path, out_path)
            logger.info("Master format %s copied: %s", fmt, out_path)
        else:
            # Non-master: blur pad conversion
            export_blur_pad(input_path, out_path, target_w, target_h)

        results[fmt] = out_path

    return results
