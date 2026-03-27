"""Tests for VIDEO_LEGEND_* config constants and ContentPackage legend columns.

TDD RED phase for Task 1 of plan 999.2-01.
"""

import pytest


def test_config_video_legend_enabled():
    """VIDEO_LEGEND_ENABLED defaults to False."""
    from config import VIDEO_LEGEND_ENABLED
    assert VIDEO_LEGEND_ENABLED is False


def test_config_video_legend_mode():
    """VIDEO_LEGEND_MODE defaults to 'static'."""
    from config import VIDEO_LEGEND_MODE
    assert VIDEO_LEGEND_MODE == "static"


def test_config_video_legend_font_size():
    """VIDEO_LEGEND_FONT_SIZE defaults to 48."""
    from config import VIDEO_LEGEND_FONT_SIZE
    assert VIDEO_LEGEND_FONT_SIZE == 48


def test_content_package_legend_status_column():
    """ContentPackage has legend_status column."""
    from src.database.models import ContentPackage
    assert hasattr(ContentPackage, "legend_status")


def test_content_package_legend_path_column():
    """ContentPackage has legend_path column."""
    from src.database.models import ContentPackage
    assert hasattr(ContentPackage, "legend_path")


def test_content_package_legend_status_index():
    """ContentPackage has idx_pkg_legend_status index."""
    from src.database.models import ContentPackage
    index_names = [idx.name for idx in ContentPackage.__table_args__ if hasattr(idx, "name")]
    assert "idx_pkg_legend_status" in index_names
