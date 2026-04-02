"""create enhance_theme_cache table

Revision ID: 022
Revises: 021
Create Date: 2026-03-31

Phase 999.8-A: Cache AI-generated topic suggestions per niche/sub-theme
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '022'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enhance_theme_cache",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("niche_id", sa.String(100), nullable=False),
        sa.Column("sub_theme", sa.String(200), nullable=False),
        sa.Column("suggestions", sa.JSON, nullable=False),
        sa.Column("used_suggestions", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "niche_id", "sub_theme", name="uq_enhance_cache_user_niche_sub"),
    )
    op.create_index("idx_enhance_cache_user_id", "enhance_theme_cache", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_enhance_cache_user_id", table_name="enhance_theme_cache")
    op.drop_table("enhance_theme_cache")
