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
    REELS_KENBURNS_ENABLED,
    REELS_SEGMENT_MAX_DURATION,
    REELS_SUB_COLOR,
    REELS_SUB_FONT,
    REELS_SUB_FONTSIZE,
    REELS_SUB_MARGIN_H,
    REELS_SUB_MARGIN_V,
    REELS_SUB_OUTLINE,
    REELS_SUB_OUTLINE_COLOR,
    REELS_TRANSITION_DURATION,
    REELS_TRANSITION_TYPE,
    REELS_VIDEO_CRF,
)

logger = logging.getLogger("clip-flow.reels.video_builder")


def _build_sub_style() -> str:
    """Build ASS subtitle force_style string from config values."""
    return (
        f"FontName={REELS_SUB_FONT},"
        f"FontSize={REELS_SUB_FONTSIZE},"
        f"Bold=0,"
        f"PrimaryColour={REELS_SUB_COLOR},"
        f"OutlineColour={REELS_SUB_OUTLINE_COLOR},"
        f"BackColour=&H00000000&,"
        f"Outline={REELS_SUB_OUTLINE},"
        f"Shadow=0,"
        f"Alignment=2,"
        f"MarginV={REELS_SUB_MARGIN_V},"
        f"MarginL={REELS_SUB_MARGIN_H},"
        f"MarginR={REELS_SUB_MARGIN_H}"
    )


def compute_scene_durations_from_script(
    script_json: dict,
    total_audio_duration: float,
    n_scenes: int,
    transition_duration: float = 0.3,
) -> list[float]:
    """Compute per-scene durations weighted by narration length.

    Allocates durations proportionally based on each scene's narration character
    count. Compensates for xfade overlap: with n clips and transition_duration t,
    xfade shortens the assembled video by (n-1)*t. We pad the target so that
    the final assembled video duration equals total_audio_duration.

    Args:
        script_json: Script dict with 'cenas' list, each having 'narracao'.
        total_audio_duration: Total audio duration in seconds.
        n_scenes: Number of scenes (clips/images).
        transition_duration: Duration of xfade between clips (default 0.3s).

    Returns:
        List of durations in seconds, one per scene.
    """
    cenas = script_json.get("cenas", [])
    min_duration = 3.0

    # Compensate for xfade overlap: each transition eats transition_duration
    # from the total assembled video length, so clips need to be longer.
    xfade_compensation = (n_scenes - 1) * transition_duration if n_scenes > 1 else 0
    target_total = total_audio_duration + xfade_compensation

    # Compute weights from narration char count
    weights = []
    for i in range(n_scenes):
        if i < len(cenas):
            narracao = cenas[i].get("narracao", "")
            weights.append(max(len(narracao), 1))
        else:
            weights.append(1)

    total_weight = sum(weights)
    if total_weight == 0:
        return [target_total / n_scenes] * n_scenes

    # Proportional allocation against padded target
    durations = [(w / total_weight) * target_total for w in weights]

    # Enforce minimum 3s per scene, redistribute excess
    deficit = 0.0
    above_min_indices = []
    for i, d in enumerate(durations):
        if d < min_duration:
            deficit += min_duration - d
            durations[i] = min_duration
        else:
            above_min_indices.append(i)

    if deficit > 0 and above_min_indices:
        above_total = sum(durations[i] for i in above_min_indices)
        for i in above_min_indices:
            share = (durations[i] / above_total) * deficit if above_total > 0 else deficit / len(above_min_indices)
            durations[i] = max(durations[i] - share, min_duration)

    return durations


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

    # Scale filters: force all images to 1080x1920, with optional ken-burns effect
    scale_filters = []
    for i in range(n):
        if REELS_KENBURNS_ENABLED:
            # Ken-burns (zoom-pan) effect for visual dynamism on static images
            if i % 2 == 0:
                # Zoom in: start at 100%, end at 115%
                zoom = "min(zoom+0.0008,1.15)"
            else:
                # Zoom out: start at 115%, end at 100%
                zoom = "if(eq(on\\,1)\\,1.15\\,max(zoom-0.0008\\,1.0))"

            frames = int(image_duration * fps)
            scale_filters.append(
                f"[{i}]scale=1920:-1,zoompan=z='{zoom}'"
                f":d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":s=1080x1920:fps={fps}[s{i}]"
            )
        else:
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

    # 4. Subtitle overlay — uses config values (configurable via painel)
    abs_srt = os.path.abspath(srt_path)
    fontsdir = os.path.abspath("assets/fonts")
    sub_style = (
        f"FontName={REELS_SUB_FONT},"
        f"FontSize={REELS_SUB_FONTSIZE},"
        f"Bold=0,"
        f"PrimaryColour={REELS_SUB_COLOR},"
        f"OutlineColour={REELS_SUB_OUTLINE_COLOR},"
        f"BackColour=&H00000000&,"
        f"Outline={REELS_SUB_OUTLINE},"
        f"Shadow=0,"
        f"Alignment=2,"
        f"MarginV={REELS_SUB_MARGIN_V},"
        f"MarginL={REELS_SUB_MARGIN_H},"
        f"MarginR={REELS_SUB_MARGIN_H}"
    )
    subtitle_filter = (
        f"[vout]subtitles=filename='{abs_srt}'"
        f":fontsdir='{fontsdir}'"
        f":force_style='{sub_style}'[final]"
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


def _align_srt_to_scenes(
    srt_path: str,
    scene_durations: list[float],
    script_json: dict,
) -> str:
    """Align SRT subtitle entries to scene time windows.

    Maps each SRT entry to its corresponding scene based on timestamp overlap
    with computed scene time windows. Writes an aligned SRT file alongside
    the original.
    """
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.strip().split("\n\n")

    windows: list[tuple[float, float]] = []
    t = 0.0
    for dur in scene_durations:
        windows.append((t, t + dur))
        t += dur

    aligned_blocks = []
    idx = 1

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        ts_line = lines[1]
        parts = ts_line.split(" --> ")
        if len(parts) != 2:
            continue
        entry_start = _parse_srt_time(parts[0])
        entry_end = _parse_srt_time(parts[1])
        entry_mid = (entry_start + entry_end) / 2.0
        text = "\n".join(lines[2:])

        best_scene = 0
        for si, (ws, we) in enumerate(windows):
            if ws <= entry_mid < we:
                best_scene = si
                break
        else:
            if entry_mid >= windows[-1][1]:
                best_scene = len(windows) - 1

        ws, we = windows[best_scene]
        clamped_start = max(entry_start, ws)
        clamped_end = min(entry_end, we)
        if clamped_end <= clamped_start:
            clamped_end = clamped_start + 0.1

        aligned_blocks.append(
            f"{idx}\n{_format_srt_time(clamped_start)} --> {_format_srt_time(clamped_end)}\n{text}"
        )
        idx += 1

    aligned_path = srt_path.replace(".srt", "_aligned.srt")
    with open(aligned_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(aligned_blocks) + "\n" if aligned_blocks else "")

    logger.info(f"SRT aligned to {len(scene_durations)} scenes: {aligned_path}")
    return aligned_path


def _validate_video_duration(
    output_path: str,
    expected_duration: float,
    tolerance: float = 2.0,
) -> dict:
    """Validate final video duration against expected value using ffprobe."""
    try:
        actual = get_video_duration(output_path)
    except RuntimeError as e:
        logger.error(f"Duration validation failed (ffprobe error): {e}")
        return {
            "actual_duration": 0.0,
            "expected_duration": expected_duration,
            "drift": expected_duration,
            "valid": False,
            "error": str(e),
        }

    drift = abs(actual - expected_duration)
    valid = drift <= tolerance

    level = logging.WARNING if not valid else logging.INFO
    logger.log(
        level,
        f"Duration check: actual={actual:.2f}s expected={expected_duration:.2f}s "
        f"drift={drift:.2f}s {'OK' if valid else 'EXCEEDED TOLERANCE'}",
    )

    return {
        "actual_duration": round(actual, 3),
        "expected_duration": round(expected_duration, 3),
        "drift": round(drift, 3),
        "valid": valid,
    }


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


def _compute_scene_durations_from_srt(
    srt_path: str, n_scenes: int, transition_duration: float = 0.3,
) -> list[float]:
    """Compute per-scene target durations from SRT timestamps.

    Divides total audio duration (from SRT) equally among N scenes,
    using SRT entry boundaries as split points when possible.
    Adds transition overlap so clips cover xfade regions.

    Returns list of durations in seconds, one per scene.
    Returns empty list if SRT can't be parsed.
    """
    entries = []
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.split(r"\n\s*\n", content.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        ts_match = re.match(
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
            lines[1].strip(),
        )
        if ts_match:
            entries.append({
                "start": _parse_srt_time(ts_match.group(1)),
                "end": _parse_srt_time(ts_match.group(2)),
            })

    if not entries or n_scenes < 1:
        return []

    audio_end = entries[-1]["end"]

    # Split audio into N equal time slices, then snap to nearest SRT boundary
    slice_dur = audio_end / n_scenes
    durations = []
    for i in range(n_scenes):
        scene_start = i * slice_dur
        scene_end = (i + 1) * slice_dur if i < n_scenes - 1 else audio_end
        dur = scene_end - scene_start + transition_duration
        durations.append(max(dur, 1.0))

    return durations


def _trim_clips_to_durations(
    clip_paths: list[str], durations: list[float],
) -> list[str]:
    """Trim clips to target durations, writing trimmed files alongside originals.

    Returns list of trimmed clip paths.
    """
    # Clean previous trimmed files to avoid _trimmed_trimmed chains
    seen_dirs = set()
    for cp in clip_paths:
        d = os.path.dirname(cp)
        if d not in seen_dirs:
            seen_dirs.add(d)
            for f in os.listdir(d):
                if "_trimmed" in f and f.endswith(".mp4"):
                    os.remove(os.path.join(d, f))

    trimmed = []
    for clip_path, target_dur in zip(clip_paths, durations):
        actual_dur = get_video_duration(clip_path)
        base, ext = os.path.splitext(clip_path)
        trimmed_path = f"{base}_trimmed{ext}"

        # Build video filter: normalize resolution + extend short clips with last-frame freeze
        vf_parts = ["scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1:color=black"]
        if actual_dur < target_dur - 0.05:
            pad_dur = target_dur - actual_dur + 0.5  # buffer for precision
            vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad_dur:.3f}")
            logger.info(f"Extending {os.path.basename(clip_path)}: {actual_dur:.2f}s -> {target_dur:.2f}s (freeze last frame)")

        subprocess.run(
            [
                "ffmpeg", "-y", "-i", clip_path,
                "-t", str(target_dur),
                "-vf", ",".join(vf_parts),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-r", "30", "-an", trimmed_path,
            ],
            capture_output=True, timeout=60,
        )
        if os.path.isfile(trimmed_path) and os.path.getsize(trimmed_path) > 0:
            trimmed.append(trimmed_path)
            if actual_dur > target_dur + 0.1:
                logger.info(f"Trimmed {os.path.basename(clip_path)}: {actual_dur:.2f}s -> {target_dur:.2f}s")
        else:
            trimmed.append(clip_path)

    return trimmed


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
    transition_type: str = "fade",
) -> str:
    """Concatenate segment videos with xfade crossfade transitions.

    Args:
        segment_paths: Paths to segment MP4 files.
        output_path: Path for the concatenated output.
        transition_duration: Duration of crossfade between segments.
        transition_type: FFmpeg xfade transition name (fade, dissolve, etc).

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
        offset = round(sum(durations[:i]) - i * transition_duration, 3)
        offset = max(offset, 0)
        out = f"v{i}" if i < n - 1 else "vout"
        xfade_filters.append(
            f"[{prev}][{i}:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[{out}]"
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


def concat_clips_with_audio(
    clip_paths: list[str],
    audio_path: str,
    srt_path: str,
    output_path: str,
    transition_duration: float = 0.3,
    transition_type: str = "fade",
    script_json: dict | None = None,
) -> str:
    """Concatenate Hailuo video clips, overlay audio and subtitles.

    Uses xfade for clip transitions, adds TTS audio and SRT subtitle overlay.
    Per REELV2-03: final assembly of Hailuo-generated scene clips.

    Args:
        clip_paths: Paths to scene video clips (MP4).
        audio_path: Path to TTS narration audio.
        srt_path: Path to SRT subtitle file.
        output_path: Path for final output MP4.
        transition_duration: Duration of xfade between clips.
        transition_type: FFmpeg xfade transition name (fade, dissolve, etc).
        script_json: Optional script dict for proportional scene duration and SRT alignment.

    Returns:
        output_path on success.
    """
    if not clip_paths:
        raise ValueError("No clip paths to concatenate")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Loop phrase: append first scene clip at end to create seamless loop
    if script_json and script_json.get("frase_loop"):
        import shutil as _shutil
        frase_loop = script_json["frase_loop"]
        # Copy the first clip so _trim_clips_to_durations doesn't overwrite the original's trimmed file
        first_clip = clip_paths[0]
        loop_clip = first_clip.replace(".mp4", "_loop.mp4")
        _shutil.copy2(first_clip, loop_clip)
        clip_paths = list(clip_paths) + [loop_clip]
        # Add synthetic cena so duration computation includes the loop segment
        script_json = dict(script_json)
        cenas = list(script_json.get("cenas", []))
        cenas.append({
            "narracao": frase_loop,
            "duracao_segundos": 3,
            "imagem_index": 0,
            "legenda_overlay": "",
        })
        script_json["cenas"] = cenas
        logger.info(f"Loop phrase enabled: '{frase_loop}' — appended first clip as loop scene")

    # Trim clips to match narration timing — proportional if script available
    if script_json:
        total_dur = get_video_duration(audio_path) if os.path.exists(audio_path) else 30.0
        scene_durs = compute_scene_durations_from_script(
            script_json, total_dur, len(clip_paths), transition_duration
        )
        # Skip SRT alignment — original timestamps match the TTS audio exactly.
        # Proportional clip durations + tpad extension ensure visuals align with
        # narration naturally. Clamping SRT to scene windows only introduces
        # desync since windows don't account for xfade overlap.
        logger.info(f"Using proportional durations from script ({len(scene_durs)} scenes)")
    else:
        scene_durs = _compute_scene_durations_from_srt(
            srt_path, len(clip_paths), transition_duration,
        )
    if scene_durs and len(scene_durs) == len(clip_paths):
        clip_paths = _trim_clips_to_durations(clip_paths, scene_durs)
        logger.info(f"Clips trimmed to narration timing ({len(clip_paths)} scenes)")

    if len(clip_paths) == 1:
        abs_srt = os.path.abspath(srt_path)
        fontsdir = os.path.abspath("assets/fonts")
        sub_style = _build_sub_style()
        subtitle_filter = (
            f"[0:v]subtitles=filename='{abs_srt}'"
            f":fontsdir='{fontsdir}'"
            f":force_style='{sub_style}'[final]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", clip_paths[0], "-i", audio_path,
            "-filter_complex", subtitle_filter,
            "-map", "[final]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg single clip failed: {result.stderr[:500]}")
        return output_path

    # Multiple clips: xfade concat + audio + subtitles
    durations = [get_video_duration(p) for p in clip_paths]

    cmd = ["ffmpeg", "-y"]
    for p in clip_paths:
        cmd += ["-i", p]
    audio_idx = len(clip_paths)
    cmd += ["-i", audio_path]

    # xfade chain
    n = len(clip_paths)
    xfade_filters = []
    prev = "0:v"
    for i in range(1, n):
        offset = round(sum(durations[:i]) - i * transition_duration, 3)
        offset = max(offset, 0)
        out = f"v{i}" if i < n - 1 else "vconcat"
        xfade_filters.append(
            f"[{prev}][{i}:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[{out}]"
        )
        prev = out

    # Subtitle overlay on concatenated video
    abs_srt = os.path.abspath(srt_path)
    fontsdir = os.path.abspath("assets/fonts")
    sub_style = _build_sub_style()
    sub_filter = (
        f"[vconcat]subtitles=filename='{abs_srt}'"
        f":fontsdir='{fontsdir}'"
        f":force_style='{sub_style}'[final]"
    )
    xfade_filters.append(sub_filter)

    filter_complex = ";".join(xfade_filters)

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    logger.info(f"Concat {n} Hailuo clips with audio + subtitles")
    logger.debug(f"FFmpeg cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        # Strip FFmpeg banner to show actual error
        stderr_lines = result.stderr.splitlines()
        error_lines = [l for l in stderr_lines if not l.startswith(("  ", "ffmpeg version", "  built", "  configuration", "  lib"))]
        raise RuntimeError(f"Clip concat failed: {''.join(error_lines[-20:])}")

    logger.info(f"Final video assembled: {output_path}")
    return output_path
