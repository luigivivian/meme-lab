"""add platforms and platform_outputs columns to reels_jobs

Revision ID: 023
Revises: 022
Create Date: 2026-03-31

Phase E: Multi-Platform Output
- platforms JSON list (default ["instagram"])
- platform_outputs JSON dict (per-platform metadata)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reels_jobs", sa.Column("platforms", sa.JSON(), nullable=True))
    op.add_column("reels_jobs", sa.Column("platform_outputs", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reels_jobs", "platform_outputs")
    op.drop_column("reels_jobs", "platforms")
