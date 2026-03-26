"""add scheduled_posts table for publishing queue

Revision ID: 004
Revises: 003
Create Date: 2026-03-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_package_id", sa.Integer(), sa.ForeignKey("content_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("platform", sa.String(30), server_default="instagram", nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("publish_result", sa.JSON(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indices para consultas frequentes
    op.create_index("idx_sched_status", "scheduled_posts", ["status"])
    op.create_index("idx_sched_platform", "scheduled_posts", ["platform"])
    op.create_index("idx_sched_scheduled_at", "scheduled_posts", ["scheduled_at"])
    op.create_index("idx_sched_character_id", "scheduled_posts", ["character_id"])
    op.create_index("idx_sched_status_scheduled", "scheduled_posts", ["status", "scheduled_at"])


def downgrade() -> None:
    op.drop_index("idx_sched_status_scheduled", table_name="scheduled_posts")
    op.drop_index("idx_sched_character_id", table_name="scheduled_posts")
    op.drop_index("idx_sched_scheduled_at", table_name="scheduled_posts")
    op.drop_index("idx_sched_platform", table_name="scheduled_posts")
    op.drop_index("idx_sched_status", table_name="scheduled_posts")
    op.drop_table("scheduled_posts")
