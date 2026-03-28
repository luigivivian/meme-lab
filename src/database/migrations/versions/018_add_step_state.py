"""add step_state JSON column to reels_jobs

Revision ID: 018
Revises: 017
Create Date: 2026-03-28

Phase 999.5: Interactive Reels Pipeline
- step_state: JSON column for per-step state persistence during interactive execution
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reels_jobs", sa.Column("step_state", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("reels_jobs", "step_state")
