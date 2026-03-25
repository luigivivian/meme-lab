"""Tests for Phase 12 Plan 01: manual pipeline backend foundation.

Covers:
- create_image() hex color support (solid backgrounds)
- create_image() 3-char hex shorthand
- create_image() regression: file path still works
- ContentPackage.approval_status defaults to "pending"
- ContentPackageRepository.update() changes approval_status
- ContentPackageRepository.list_packages(approval_status=...) filters
- themes.yaml has colors key per theme with 3-5 hex strings
"""

import os
import re
import tempfile

import pytest
import yaml


# ── Image maker tests (no DB needed) ───────────────────────────────────────

def test_create_image_hex_color(tmp_path):
    """create_image('#2C3E50', ...) produces a 1080x1350 image."""
    from src.image_maker import create_image

    out = str(tmp_path / "hex_test.png")
    result = create_image("Test phrase", "#2C3E50", output_path=out)
    assert os.path.isfile(result)

    from PIL import Image
    img = Image.open(result)
    assert img.size == (1080, 1350)


def test_create_image_short_hex(tmp_path):
    """create_image('#FFF', ...) works with 3-char hex."""
    from src.image_maker import create_image

    out = str(tmp_path / "short_hex.png")
    result = create_image("Short hex", "#FFF", output_path=out)
    assert os.path.isfile(result)

    from PIL import Image
    img = Image.open(result)
    assert img.size == (1080, 1350)


def test_create_image_file_path_regression(tmp_path):
    """create_image() still works with a regular file path."""
    from PIL import Image as PILImage
    from src.image_maker import create_image

    # Create a dummy background
    bg = PILImage.new("RGB", (1080, 1350), (50, 50, 50))
    bg_path = str(tmp_path / "bg.png")
    bg.save(bg_path)

    out = str(tmp_path / "regression.png")
    result = create_image("File path test", bg_path, output_path=out)
    assert os.path.isfile(result)


def test_create_image_invalid_hex():
    """create_image() raises ValueError for invalid hex."""
    from src.image_maker import create_image

    with pytest.raises(ValueError, match="Invalid hex color"):
        create_image("Bad hex", "#ZZZZZZ")


# ── ORM model tests ────────────────────────────────────────────────────────

def test_content_package_approval_status_default():
    """ContentPackage ORM has approval_status field defaulting to 'pending'."""
    from src.database.models import ContentPackage

    # Verify the field exists and has proper default
    assert hasattr(ContentPackage, "approval_status")
    col = ContentPackage.__table__.columns["approval_status"]
    assert col.default is not None or col.server_default is not None


# ── Repository tests (async, in-memory SQLite) ─────────────────────────────

@pytest.fixture
async def async_session():
    """Create an in-memory SQLite async session for testing."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from src.database.base import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_approval_status_update(async_session):
    """update(id, {'approval_status': 'approved'}) changes status."""
    from src.database.models import ContentPackage, PipelineRun
    from src.database.repositories.content_repo import ContentPackageRepository

    # Create pipeline run first (FK constraint)
    run = PipelineRun(run_id="test0001", status="completed", mode="manual")
    async_session.add(run)
    await async_session.flush()

    repo = ContentPackageRepository(async_session)
    pkg = await repo.create({
        "pipeline_run_id": run.id,
        "phrase": "Test phrase",
        "source": "manual",
        "image_path": "/tmp/test.png",
    })
    assert pkg.approval_status == "pending"

    updated = await repo.update(pkg.id, {"approval_status": "approved"})
    assert updated.approval_status == "approved"


@pytest.mark.asyncio
async def test_list_packages_filter_approval_status(async_session):
    """list_packages(approval_status='pending') filters correctly."""
    from src.database.models import PipelineRun
    from src.database.repositories.content_repo import ContentPackageRepository

    run = PipelineRun(run_id="test0002", status="completed", mode="manual")
    async_session.add(run)
    await async_session.flush()

    repo = ContentPackageRepository(async_session)
    await repo.create({
        "pipeline_run_id": run.id,
        "phrase": "Pending one",
        "source": "manual",
        "image_path": "/tmp/p1.png",
        "approval_status": "pending",
    })
    await repo.create({
        "pipeline_run_id": run.id,
        "phrase": "Approved one",
        "source": "manual",
        "image_path": "/tmp/p2.png",
        "approval_status": "approved",
    })

    pending = await repo.list_packages(approval_status="pending")
    assert len(pending) == 1
    assert pending[0].phrase == "Pending one"


@pytest.mark.asyncio
async def test_bulk_update_approval(async_session):
    """bulk_update_approval changes multiple packages at once."""
    from src.database.models import PipelineRun
    from src.database.repositories.content_repo import ContentPackageRepository

    run = PipelineRun(run_id="test0003", status="completed", mode="manual")
    async_session.add(run)
    await async_session.flush()

    repo = ContentPackageRepository(async_session)
    p1 = await repo.create({
        "pipeline_run_id": run.id,
        "phrase": "Bulk 1",
        "source": "manual",
        "image_path": "/tmp/b1.png",
    })
    p2 = await repo.create({
        "pipeline_run_id": run.id,
        "phrase": "Bulk 2",
        "source": "manual",
        "image_path": "/tmp/b2.png",
    })

    count = await repo.bulk_update_approval([p1.id, p2.id], "approved")
    assert count == 2


# ── themes.yaml tests ──────────────────────────────────────────────────────

def test_themes_yaml_has_colors():
    """Every theme in themes.yaml has a 'colors' key with 3-5 hex strings."""
    themes_path = os.path.join(os.path.dirname(__file__), "..", "config", "themes.yaml")
    with open(themes_path) as f:
        themes = yaml.safe_load(f)

    assert isinstance(themes, list)
    hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")

    for theme in themes:
        assert "colors" in theme, f"Theme '{theme.get('key', '?')}' missing 'colors' key"
        colors = theme["colors"]
        assert isinstance(colors, list), f"Theme '{theme.get('key')}' colors is not a list"
        assert 3 <= len(colors) <= 5, f"Theme '{theme.get('key')}' has {len(colors)} colors, expected 3-5"
        for c in colors:
            assert hex_pattern.match(c), f"Invalid hex color '{c}' in theme '{theme.get('key')}'"
