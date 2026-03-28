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

import re

from src.reels_pipeline.config import (
    REELS_FPS,
    REELS_IMAGE_DURATION,
    REELS_SEGMENT_MAX_DURATION,
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


# ------------------------------------------------------------------
# SRT timestamp helpers
# ------------------------------------------------------------------

def _parse_srt_time(time_str: str) -> float:
    """Parse SRT timestamp 'HH:MM:SS,mmm' to seconds."""
    match = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", time_str.strip())
    if not match:
        return 0.0
    h, m, s, ms = match.groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp 'HH:MM:SS,mmm'."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ------------------------------------------------------------------
# Video segmentation for >30s content
# ------------------------------------------------------------------

def segment_roteiro(
    script: dict, max_segment_duration: float = REELS_SEGMENT_MAX_DURATION
) -> list[dict]:
    """Split script cenas into segments of ~max_segment_duration seconds.

    Args:
        script: Script dict with 'cenas' list, each cena has 'duracao_segundos'.
        max_segment_duration: Max duration per segment in seconds.

    Returns:
        List of segment dicts: {"cenas": [...], "duration": float, "index": int}.
    """
    cenas = script.get("cenas", [])
    if not cenas:
        return []

    segments = []
    current_cenas = []
    current_duration = 0.0

    for cena in cenas:
        cena_dur = cena.get("duracao_segundos", 0)
        # If adding this cena would exceed max and we already have cenas, start new segment
        if current_cenas and current_duration + cena_dur > max_segment_duration:
            segments.append({
                "cenas": current_cenas,
                "duration": current_duration,
                "index": len(segments),
            })
            current_cenas = []
            current_duration = 0.0
        current_cenas.append(cena)
        current_duration += cena_dur

    # Flush remaining
    if current_cenas:
        segments.append({
            "cenas": current_cenas,
            "duration": current_duration,
            "index": len(segments),
        })

    return segments


def _slice_srt(srt_path: str, start_s: float, end_s: float, output_path: str) -> str:
    """Extract SRT entries within a time range, reindex and adjust timestamps.

    Args:
        srt_path: Path to source SRT file.
        start_s: Start time in seconds.
        end_s: End time in seconds.
        output_path: Path to write the sliced SRT.

    Returns:
        output_path.
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")
    filtered = []
    idx = 1

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # Parse timestamp line: "00:00:01,000 --> 00:00:03,500"
        ts_line = lines[1]
        parts = ts_line.split(" --> ")
        if len(parts) != 2:
            continue
        entry_start = _parse_srt_time(parts[0])
        entry_end = _parse_srt_time(parts[1])

        # Keep entries that overlap with the slice range
        if entry_end <= start_s or entry_start >= end_s:
            continue

        # Adjust timestamps relative to segment start
        adj_start = max(entry_start - start_s, 0.0)
        adj_end = min(entry_end - start_s, end_s - start_s)
        text = "\n".join(lines[2:])

        filtered.append(
            f"{idx}\n{_format_srt_time(adj_start)} --> {_format_srt_time(adj_end)}\n{text}"
        )
        idx += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(filtered) + "\n" if filtered else "")

    return output_path


def build_segment_videos(
    segments: list[dict],
    image_paths_by_segment: list[list[str]],
    audio_path: str,
    srt_path: str,
    job_dir: str,
    config_override: dict | None = None,
) -> list[str]:
    """Build individual video segments from sliced audio/SRT.

    Args:
        segments: List of segment dicts from segment_roteiro().
        image_paths_by_segment: Images for each segment.
        audio_path: Full audio file path.
        srt_path: Full SRT file path.
        job_dir: Job working directory for temp files.
        config_override: Optional config overrides.

    Returns:
        List of segment video file paths.
    """
    segment_paths = []
    cumulative_start = 0.0

    for i, seg in enumerate(segments):
        seg_duration = seg["duration"]
        seg_end = cumulative_start + seg_duration

        # Slice audio
        seg_audio = os.path.join(job_dir, f"segment_audio_{i}.wav")
        audio_cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-ss", str(cumulative_start), "-to", str(seg_end),
            "-c", "copy", seg_audio,
        ]
        result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.warning(f"Audio slice failed for segment {i}: {result.stderr[:200]}")
            # Fallback: copy full audio
            seg_audio = audio_path

        # Slice SRT
        seg_srt = os.path.join(job_dir, f"segment_subtitles_{i}.srt")
        _slice_srt(srt_path, cumulative_start, seg_end, seg_srt)

        # Build segment video
        seg_video = os.path.join(job_dir, f"segment_{i}.mp4")
        images = image_paths_by_segment[i] if i < len(image_paths_by_segment) else []
        if not images:
            logger.warning(f"No images for segment {i}, skipping")
            cumulative_start = seg_end
            continue

        build_reel_video(
            image_paths=images,
            audio_path=seg_audio,
            srt_path=seg_srt,
            output_path=seg_video,
            config_override=config_override,
        )
        segment_paths.append(seg_video)
        cumulative_start = seg_end

    return segment_paths


def concat_segments(
    segment_paths: list[str],
    output_path: str,
    transition_duration: float = 0.5,
) -> str:
    """Concatenate segment videos with xfade crossfade transitions.

    Args:
        segment_paths: Paths to segment MP4 files.
        output_path: Path for the concatenated output.
        transition_duration: Duration of crossfade between segments.

    Returns:
        output_path.
    """
    if not segment_paths:
        raise ValueError("No segment paths to concatenate")

    if len(segment_paths) == 1:
        # Single segment: just copy
        import shutil
        shutil.copy2(segment_paths[0], output_path)
        return output_path

    # Get durations for xfade offset calculation
    durations = [get_video_duration(p) for p in segment_paths]

    # Build xfade filter chain
    cmd = ["ffmpeg", "-y"]
    for p in segment_paths:
        cmd += ["-i", p]

    n = len(segment_paths)
    xfade_filters = []
    prev = "0:v"

    for i in range(1, n):
        # offset = sum of durations so far minus accumulated transitions
        offset = sum(durations[:i]) - i * transition_duration
        offset = max(offset, 0)
        out = f"v{i}" if i < n - 1 else "vout"
        xfade_filters.append(
            f"[{prev}][{i}:v]xfade=transition=fade:duration={transition_duration}:offset={offset}[{out}]"
        )
        prev = out

    # Audio: concat all audio streams
    audio_inputs = "".join(f"[{i}:a]" for i in range(n))
    audio_filter = f"{audio_inputs}concat=n={n}:v=0:a=1[aout]"

    filter_complex = ";".join(xfade_filters + [audio_filter])

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info(f"Concatenating {n} segments with xfade")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise RuntimeError(
            f"Segment concat failed (exit {result.returncode}): {result.stderr[:1000]}"
        )

    logger.info(f"Segments concatenated: {output_path}")
    return output_path
