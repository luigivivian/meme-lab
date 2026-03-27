"""LegendRenderer — FFmpeg drawtext filter chain builder + subprocess executor.

Renders meme phrase text + watermark overlays onto video files using FFmpeg's
drawtext filter. Supports 3 animation modes:
  - static: full-duration visibility (default, per D-05)
  - fade: 0.5s fade-in then stays visible (per D-06)
  - typewriter: line-by-line reveal with per-line fade-in (per D-07)

Text wrapping is ported from image_maker.py _wrap_text() using identical Pillow
font metrics (getbbox) to ensure visual consistency between image and video text.

Windows path escaping follows FFmpeg conventions: forward slashes, escaped colon
in drive letters (per Pitfall 1 from RESEARCH.md).

Text content is written to temp files (textfile= param) to avoid FFmpeg escaping
nightmares with special characters (per Pitfall 2).

Phase 999.2 — Video Legends & Subtitles
"""

import logging
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import ImageFont

logger = logging.getLogger("clip-flow.legend_renderer")


# ── Config fallback helper (same pattern as kie_client.py) ────────────────


def _get_config(attr: str, default):
    """Try to read from config module, fall back to default."""
    try:
        import config as cfg
        return getattr(cfg, attr, default)
    except (ImportError, AttributeError):
        return default


# ── Path escaping (per Pitfall 1 from RESEARCH.md) ────────────────────────


def _escape_ffmpeg_path(path: str) -> str:
    """Escape file path for FFmpeg filter strings.

    On Windows, converts backslashes to forward slashes and escapes the colon
    in the drive letter (C: -> C\\:).
    """
    p = str(path).replace("\\", "/")
    if platform.system() == "Windows" and len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p


# ── Font resolution (port from image_maker.py _load_font) ────────────────


def _resolve_font(size: int | None = None) -> tuple[str, ImageFont.FreeTypeFont]:
    """Resolve font file path and load Pillow font.

    Returns (path_str, pil_font). Uses FONTS_DIR from config, falls back to
    system fonts.
    """
    font_size = size or _get_config("VIDEO_LEGEND_FONT_SIZE", 48)
    fonts_dir = _get_config("FONTS_DIR", Path("assets/fonts"))

    # Try custom fonts
    for ext in ("*.ttf", "*.otf"):
        for font_file in Path(fonts_dir).glob(ext):
            return str(font_file), ImageFont.truetype(str(font_file), font_size)

    # System fallback
    system_fonts = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for fp in system_fonts:
        if os.path.exists(fp):
            return fp, ImageFont.truetype(fp, font_size)

    raise FileNotFoundError("No font found in assets/fonts/ or system fonts")


# ── Word-wrap (exact port from image_maker.py _wrap_text) ─────────────────


def wrap_text_for_video(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text using Pillow font metrics (identical to image_maker.py _wrap_text).

    Uses actual glyph widths via getbbox(), not character counts.
    """
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


# ── LegendRenderer class ─────────────────────────────────────────────────


class LegendRenderer:
    """Renders text overlays on video using FFmpeg drawtext filter.

    Per D-01: White text, black stroke 2px, shadow matching image_maker.py.
    Per D-02: Only text + watermark overlay, no other effects.
    Per D-03: Same font file from assets/fonts/.
    Per D-04: Text at vertical 0.80 position.
    Per D-10: Output file has _legend suffix.
    Per D-12: 10% vertical safe margin for Instagram Reels.
    """

    def __init__(self, font_path: str | None = None, font_size: int | None = None):
        self._font_size = font_size or _get_config("VIDEO_LEGEND_FONT_SIZE", 48)
        if font_path:
            self._font_path = font_path
            self._pil_font = ImageFont.truetype(font_path, self._font_size)
        else:
            self._font_path, self._pil_font = _resolve_font(self._font_size)
        self._wm_font_size = _get_config("WATERMARK_FONT_SIZE", 22)

    @staticmethod
    def is_available() -> bool:
        """Check if FFmpeg is installed and on PATH."""
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def legend_output_path(video_path: str) -> str:
        """Generate output path with _legend suffix (per D-10)."""
        p = Path(video_path)
        return str(p.with_name(f"{p.stem}_legend{p.suffix}"))

    def render(
        self,
        video_path: str,
        output_path: str,
        phrase: str,
        watermark: str = "",
        mode: str = "static",
        video_width: int = 1080,
        video_height: int = 1350,
    ) -> str:
        """Burn text overlay into video. Returns output_path on success.

        Args:
            video_path: Input video file path
            output_path: Output video file path (per D-10: _legend suffix)
            phrase: Meme text to overlay (will be uppercased and wrapped)
            watermark: Watermark text (default: empty, caller passes WATERMARK_TEXT)
            mode: Animation mode - "static", "fade", or "typewriter" (per D-05/D-06/D-07)
            video_width: Video width in pixels (default 1080)
            video_height: Video height in pixels (default 1350)

        Handles Sora 2 videos that may lack an audio track (RESEARCH.md Open Question 3):
        First attempts -c:a copy; if FFmpeg fails with audio-related error, retries with -an.
        """
        if not self.is_available():
            raise RuntimeError("FFmpeg not found. Install via: winget install Gyan.FFmpeg")

        # Pre-wrap using Pillow font metrics (per D-01, identical to image_maker.py)
        margin = 80
        max_width = video_width - (margin * 2)
        lines = wrap_text_for_video(phrase.upper(), self._pil_font, max_width)
        wrapped_text = "\n".join(lines)

        # Write text to temp file (per Pitfall 2: avoids all escaping issues)
        textfile = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        textfile.write(wrapped_text)
        textfile.close()
        textfile_path = textfile.name

        # Collect all temp files for cleanup
        temp_files = [textfile_path]

        try:
            # Build filter chain based on mode
            if mode == "typewriter":
                filters, extra_temps = self._build_typewriter_filters(
                    lines, textfile_path, video_width, video_height
                )
                temp_files.extend(extra_temps)
            elif mode == "fade":
                filters = self._build_phrase_filter(
                    textfile_path, video_height, mode="fade"
                )
            else:  # static (default, per D-05)
                filters = self._build_phrase_filter(
                    textfile_path, video_height, mode="static"
                )

            # Add watermark if provided (per D-01)
            if watermark:
                filters += "," + self._build_watermark_filter(
                    watermark, video_width, video_height
                )

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Execute FFmpeg -- try with audio copy first, fall back to no-audio
            # (Sora 2 videos may have no audio track -- RESEARCH.md Open Question 3)
            cmd_base = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", filters,
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            ]

            # First attempt: copy audio stream
            cmd_with_audio = cmd_base + ["-c:a", "copy", "-movflags", "+faststart", output_path]
            result = subprocess.run(cmd_with_audio, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                stderr_lower = result.stderr.lower()
                # Detect audio-related failures (no audio stream to copy)
                audio_error_indicators = [
                    "could not find tag for codec",
                    "no audio",
                    "audio in output",
                    "encoder for codec",
                    "stream specifier",
                    "does not contain any stream",
                ]
                is_audio_error = any(ind in stderr_lower for ind in audio_error_indicators)

                if is_audio_error:
                    logger.info("No audio stream detected, retrying with -an flag")
                    cmd_no_audio = cmd_base + ["-an", "-movflags", "+faststart", output_path]
                    result = subprocess.run(
                        cmd_no_audio, capture_output=True, text=True, timeout=120
                    )
                    if result.returncode != 0:
                        raise RuntimeError(
                            f"FFmpeg failed (exit {result.returncode}): {result.stderr[:500]}"
                        )
                else:
                    raise RuntimeError(
                        f"FFmpeg failed (exit {result.returncode}): {result.stderr[:500]}"
                    )

            return output_path
        finally:
            # Clean up temp files
            for tf in temp_files:
                try:
                    os.unlink(tf)
                except OSError:
                    pass

    # ── Filter builders ───────────────────────────────────────────────────

    def _build_phrase_filter(
        self, textfile_path: str, video_height: int, mode: str = "static"
    ) -> str:
        """Build drawtext filter for phrase text.

        Per D-01: fontcolor=white, borderw=2, bordercolor=black, shadow.
        Per D-04: y=h*0.80-text_h/2 (clamped to safe zone per D-12).
        """
        fp = _escape_ffmpeg_path(self._font_path)
        tf = _escape_ffmpeg_path(textfile_path)

        parts = [
            f"drawtext=textfile='{tf}'",
            f"fontfile='{fp}'",
            f"fontsize={self._font_size}",
            "fontcolor=white",
            "borderw=2",
            "bordercolor=black",
            "shadowcolor=black@0.47",
            "shadowx=3:shadowy=3",
            "x=(w-text_w)/2",
            "y='min(h*0.80-text_h/2,h*0.90-text_h)'",
            "line_spacing=14",
        ]

        # Add alpha expression for fade mode (per D-06)
        if mode == "fade":
            parts.append("alpha='if(lt(t\\,0.5)\\,t/0.5\\,1)'")

        return ":".join(parts)

    def _build_typewriter_filters(
        self,
        lines: list[str],
        textfile_path: str,
        video_width: int,
        video_height: int,
    ) -> tuple[str, list[str]]:
        """Build chained drawtext filters for typewriter mode (per D-07).

        Per RESEARCH.md: line-by-line reveal with per-line fade-in.
        Each line appears after the previous one, with ~30 chars/sec timing.

        Returns (filter_chain_str, list_of_temp_file_paths).
        """
        chars_per_sec = 30
        fp = _escape_ffmpeg_path(self._font_path)
        temp_files: list[str] = []
        filter_parts: list[str] = []

        # Calculate total text height for centering
        line_height = self._font_size + 14  # font_size + line_spacing
        total_text_height = line_height * len(lines)
        base_y_ratio = 0.80
        safe_bottom_ratio = 0.90

        line_start = 0.0

        for i, line in enumerate(lines):
            # Write each line to its own temp file
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_line{i}.txt", delete=False, encoding="utf-8"
            )
            tf.write(line)
            tf.close()
            temp_files.append(tf.name)
            line_tf = _escape_ffmpeg_path(tf.name)

            # Calculate Y position for this line
            # Start from center point, offset per line
            y_expr = (
                f"min(h*{base_y_ratio}-{total_text_height}/2+{i * line_height}"
                f",h*{safe_bottom_ratio}-{(len(lines) - i) * line_height})"
            )

            parts = [
                f"drawtext=textfile='{line_tf}'",
                f"fontfile='{fp}'",
                f"fontsize={self._font_size}",
                "fontcolor=white",
                "borderw=2",
                "bordercolor=black",
                "shadowcolor=black@0.47",
                "shadowx=3:shadowy=3",
                "x=(w-text_w)/2",
                f"y='{y_expr}'",
                f"enable='gte(t,{line_start:.2f})'",
                f"alpha='if(lt(t-{line_start:.2f}\\,0.3)\\,(t-{line_start:.2f})/0.3\\,1)'",
            ]
            filter_parts.append(":".join(parts))

            # Timing: advance by line duration + gap
            line_duration = len(line) / chars_per_sec
            line_start += line_duration + 0.1

        return ",".join(filter_parts), temp_files

    def _build_watermark_filter(
        self, watermark_text: str, video_width: int, video_height: int
    ) -> str:
        """Build drawtext filter for watermark (per config: bottom-right, gold).

        Per config.py: fontsize=22, WATERMARK_COLOR (200,180,130,120) -> #C8B482@0.47.
        Escapes @ and : in watermark text for FFmpeg safety.
        """
        fp = _escape_ffmpeg_path(self._font_path)
        # Escape special characters in watermark text
        safe_wm = watermark_text.replace("@", "\\@").replace(":", "\\:")

        parts = [
            f"drawtext=text='{safe_wm}'",
            f"fontfile='{fp}'",
            f"fontsize={self._wm_font_size}",
            "fontcolor=#C8B482@0.47",
            "x=w-text_w-20",
            "y=h-50",
        ]

        return ":".join(parts)
