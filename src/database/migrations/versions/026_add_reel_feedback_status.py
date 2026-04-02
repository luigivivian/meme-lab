"""Add feedback_status and posted_platforms to reels_jobs.

Tracks the approval/posting lifecycle of generated reels:
  null -> 'approved' -> 'posted'

Revision ID: 026
Revises: 025
"""

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"


def upgrade() -> None:
    op.add_column("reels_jobs", sa.Column("feedback_status", sa.String(20), nullable=True))
    op.add_column("reels_jobs", sa.Column("posted_platforms", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("reels_jobs", "posted_platforms")
    op.drop_column("reels_jobs", "feedback_status")
