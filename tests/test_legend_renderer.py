"""Tests for LegendRenderer — FFmpeg drawtext filter chain builder + subprocess executor.

TDD RED phase for Task 2 of plan 999.2-01.
Covers: word wrap, filter chain construction, escaping, output paths, render with mocked subprocess.
"""

import os
import platform
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from PIL import ImageFont


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def font_path():
    """Return path to the real Cinzel font in assets/fonts/."""
    p = Path(__file__).parent.parent / "assets" / "fonts" / "Cinzel.ttf"
    if not p.exists():
        pytest.skip("Cinzel.ttf not found in assets/fonts/")
    return str(p)


@pytest.fixture
def pil_font(font_path):
    """Load the real Pillow font at size 48."""
    return ImageFont.truetype(font_path, 48)


@pytest.fixture
def renderer(font_path):
    """Create a LegendRenderer instance with the real font."""
    from src.video_gen.legend_renderer import LegendRenderer
    return LegendRenderer(font_path=font_path, font_size=48)


# ---------------------------------------------------------------------------
# Word wrap tests
# ---------------------------------------------------------------------------

def test_word_wrap_matches_image_maker(pil_font):
    """wrap_text_for_video produces the same output as image_maker._wrap_text."""
    from src.video_gen.legend_renderer import wrap_text_for_video
    from src.image_maker import _wrap_text

    text = "MINHA BOLA DE CRISTAL MOSTRA LARICA NO SEU FUTURO PROXIMO"
    max_width = 920

    video_lines = wrap_text_for_video(text, pil_font, max_width)
    image_lines = _wrap_text(text, pil_font, max_width)

    assert video_lines == image_lines
    assert len(video_lines) >= 1


def test_word_wrap_single_word(pil_font):
    """A single word should produce a single-element list."""
    from src.video_gen.legend_renderer import wrap_text_for_video
    result = wrap_text_for_video("MAGO", pil_font, 920)
    assert result == ["MAGO"]


def test_word_wrap_empty_text(pil_font):
    """Empty string should return the original text as single element."""
    from src.video_gen.legend_renderer import wrap_text_for_video
    result = wrap_text_for_video("", pil_font, 920)
    assert result == [""]


# ---------------------------------------------------------------------------
# Static filter tests
# ---------------------------------------------------------------------------

def test_static_filter_contains_required_params(renderer):
    """Static mode filter should contain all required drawtext parameters."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("TEST LINE\nSECOND LINE")
        tf_path = f.name
    try:
        result = renderer._build_phrase_filter(tf_path, 1350, mode="static")
        assert "drawtext=" in result
        assert "fontcolor=white" in result
        assert "borderw=2" in result
        assert "bordercolor=black" in result
        assert "shadowcolor=black@0.47" in result
        assert "shadowx=3" in result
        assert "shadowy=3" in result
        assert "x=(w-text_w)/2" in result
        assert "line_spacing=14" in result
        # Static mode should not have fade alpha expression
        assert "if(lt(t" not in result
    finally:
        os.unlink(tf_path)


# ---------------------------------------------------------------------------
# Fade filter tests
# ---------------------------------------------------------------------------

def test_fade_filter_contains_alpha_expression(renderer):
    """Fade mode filter should contain the alpha fade-in expression."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("TEST LINE")
        tf_path = f.name
    try:
        result = renderer._build_phrase_filter(tf_path, 1350, mode="fade")
        assert "alpha=" in result
        assert "if(lt(t" in result
        # Should still have base params
        assert "fontcolor=white" in result
        assert "borderw=2" in result
    finally:
        os.unlink(tf_path)


# ---------------------------------------------------------------------------
# Typewriter filter tests
# ---------------------------------------------------------------------------

def test_typewriter_filter_produces_multiple_drawtext(renderer):
    """Typewriter mode should produce one drawtext per line, comma-separated."""
    lines = ["MINHA BOLA DE CRISTAL", "MOSTRA LARICA", "NO SEU FUTURO"]

    # _build_typewriter_filters returns (filter_chain_str, list_of_temp_files)
    result, temp_files = renderer._build_typewriter_filters(lines, "dummy.txt", 1080, 1350)

    try:
        # Should have multiple drawtext entries
        drawtext_count = result.count("drawtext=")
        assert drawtext_count == len(lines), f"Expected {len(lines)} drawtext entries, got {drawtext_count}"

        # Each should have enable timing
        assert "enable=" in result
        assert "gte(t," in result

        # Should create temp files for each line
        assert len(temp_files) == len(lines)
    finally:
        # Clean up temp files
        import os
        for tf in temp_files:
            try:
                os.unlink(tf)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Watermark filter tests
# ---------------------------------------------------------------------------

def test_watermark_filter_contains_required_params(renderer):
    """Watermark filter should escape @ and contain the correct style."""
    result = renderer._build_watermark_filter("@magomestre420", 1080, 1350)
    assert "\\@magomestre420" in result
    assert "fontsize=22" in result
    assert "fontcolor=#C8B482@0.47" in result
    assert "x=w-text_w-20" in result
    assert "y=h-50" in result


# ---------------------------------------------------------------------------
# Windows path escaping tests
# ---------------------------------------------------------------------------

def test_windows_path_escaping():
    """On Windows, backslashes become forward slashes and colon is escaped."""
    from src.video_gen.legend_renderer import _escape_ffmpeg_path

    # Test basic forward slash conversion
    assert _escape_ffmpeg_path("C:/Users/test/font.ttf") == (
        "C\\:/Users/test/font.ttf" if platform.system() == "Windows"
        else "C:/Users/test/font.ttf"
    )

    # Backslash conversion (always)
    result = _escape_ffmpeg_path("C:\\Users\\test\\font.ttf")
    assert "\\" not in result or result.startswith("C\\:")  # no raw backslashes in path

    # Non-Windows-like path (no colon)
    assert _escape_ffmpeg_path("/home/user/font.ttf") == "/home/user/font.ttf"


# ---------------------------------------------------------------------------
# Output path suffix tests
# ---------------------------------------------------------------------------

def test_output_path_suffix():
    """legend_output_path should insert _legend before the extension (per D-10)."""
    from src.video_gen.legend_renderer import LegendRenderer

    # Normalize to forward slashes for cross-platform comparison
    def norm(p):
        return p.replace("\\", "/")

    assert norm(LegendRenderer.legend_output_path("output/videos/meme_1.mp4")) == "output/videos/meme_1_legend.mp4"
    assert norm(LegendRenderer.legend_output_path("video.avi")) == "video_legend.avi"
    assert norm(LegendRenderer.legend_output_path("/path/to/clip.mp4")) == "/path/to/clip_legend.mp4"


# ---------------------------------------------------------------------------
# is_available tests
# ---------------------------------------------------------------------------

def test_is_available_checks_ffmpeg():
    """is_available returns bool based on shutil.which('ffmpeg')."""
    from src.video_gen.legend_renderer import LegendRenderer
    with patch("src.video_gen.legend_renderer.shutil.which", return_value="/usr/bin/ffmpeg"):
        assert LegendRenderer.is_available() is True
    with patch("src.video_gen.legend_renderer.shutil.which", return_value=None):
        assert LegendRenderer.is_available() is False


# ---------------------------------------------------------------------------
# Render tests (mocked subprocess)
# ---------------------------------------------------------------------------

def test_render_calls_subprocess_with_correct_args(renderer):
    """render() should call subprocess.run with ffmpeg command."""
    with patch("src.video_gen.legend_renderer.shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("src.video_gen.legend_renderer.subprocess.run") as mock_run, \
         patch("src.video_gen.legend_renderer.Path.mkdir"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = renderer.render(
            video_path="input.mp4",
            output_path="output.mp4",
            phrase="Test phrase",
            watermark="@magomestre420",
            mode="static",
        )

        assert result == "output.mp4"
        mock_run.assert_called()
        # Verify first call args contain ffmpeg and the required flags
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args[0] == "ffmpeg"
        assert "-y" in first_call_args
        assert "-i" in first_call_args
        assert "input.mp4" in first_call_args
        assert "-vf" in first_call_args
        assert "-c:v" in first_call_args
        assert "libx264" in first_call_args


def test_render_raises_on_ffmpeg_failure(renderer):
    """render() should raise RuntimeError when FFmpeg fails with non-audio error."""
    with patch("src.video_gen.legend_renderer.shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("src.video_gen.legend_renderer.subprocess.run") as mock_run, \
         patch("src.video_gen.legend_renderer.Path.mkdir"):
        mock_run.return_value = MagicMock(returncode=1, stderr="Unknown encoder libx999")

        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            renderer.render(
                video_path="input.mp4",
                output_path="output.mp4",
                phrase="Test phrase",
            )


def test_render_audio_fallback(renderer):
    """render() retries with -an when first attempt fails due to missing audio stream."""
    with patch("src.video_gen.legend_renderer.shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("src.video_gen.legend_renderer.subprocess.run") as mock_run, \
         patch("src.video_gen.legend_renderer.Path.mkdir"):
        # First call fails with audio error, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="could not find tag for codec none in stream"),
            MagicMock(returncode=0, stderr=""),
        ]

        result = renderer.render(
            video_path="input.mp4",
            output_path="output.mp4",
            phrase="Test phrase",
        )

        assert result == "output.mp4"
        assert mock_run.call_count == 2
        # Second call should contain -an flag
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-an" in second_call_args


def test_render_raises_when_ffmpeg_not_found(renderer):
    """render() raises RuntimeError when FFmpeg is not installed."""
    with patch("src.video_gen.legend_renderer.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            renderer.render(
                video_path="input.mp4",
                output_path="output.mp4",
                phrase="Test phrase",
            )


# ---------------------------------------------------------------------------
# Textfile creation tests
# ---------------------------------------------------------------------------

def test_textfile_written_with_utf8(renderer):
    """render() should write wrapped text to a temp file in UTF-8."""
    with patch("src.video_gen.legend_renderer.shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("src.video_gen.legend_renderer.subprocess.run") as mock_run, \
         patch("src.video_gen.legend_renderer.Path.mkdir"):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # Track temp files created
        original_write = open
        written_content = {}

        import tempfile
        original_ntf = tempfile.NamedTemporaryFile

        class TrackingTempFile:
            def __init__(self, *args, **kwargs):
                self._file = original_ntf(*args, **kwargs)
                self.name = self._file.name

            def write(self, data):
                written_content[self.name] = data
                return self._file.write(data)

            def close(self):
                return self._file.close()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self._file.__exit__(*args)

        with patch("src.video_gen.legend_renderer.tempfile.NamedTemporaryFile", TrackingTempFile):
            renderer.render(
                video_path="input.mp4",
                output_path="output.mp4",
                phrase="Cafe e o unico relacionamento estavel",
            )

        # At least one temp file should have been written with UTF-8 text
        assert len(written_content) >= 1
        for path, content in written_content.items():
            assert isinstance(content, str)
            # Text should be uppercased
            assert content == content.upper()
