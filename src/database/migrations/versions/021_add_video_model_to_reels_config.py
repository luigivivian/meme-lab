"""add video_model column to reels_config

Revision ID: 021
Revises: 020
Create Date: 2026-03-31

Phase D: Kie.ai Model Selection + Retry Logic
- video_model String(100) column on reels_config for per-config model selection
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '021'
down_revision: Union[str, None] = '020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reels_config",
        sa.Column("video_model", sa.String(100), nullable=False, server_default="hailuo/2-3-image-to-video-standard"),
    )


def downgrade() -> None:
    op.drop_column("reels_config", "video_model")
