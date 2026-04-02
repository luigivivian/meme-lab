"""Add language column to reels_jobs and reels_config

Revision ID: 024
Revises: 023
Create Date: 2026-03-31

Phase F: Multi-Language Support for Reels Pipeline
- language column on reels_jobs to persist per-job language choice
- language column on reels_config for default language per config
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '024'
down_revision: Union[str, None] = '023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reels_jobs",
        sa.Column("language", sa.String(10), nullable=True, server_default="pt-BR"),
    )


def downgrade() -> None:
    op.drop_column("reels_jobs", "language")
