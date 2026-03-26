"""add api_usage table

Revision ID: 008
Revises: 007
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "service", "tier", "date", name="uq_api_usage_user_service_tier_date"),
    )
    op.create_index("idx_api_usage_user_id", "api_usage", ["user_id"])
    op.create_index("idx_api_usage_date", "api_usage", ["date"])
    op.create_index("idx_api_usage_service", "api_usage", ["service"])


def downgrade() -> None:
    op.drop_index("idx_api_usage_service", table_name="api_usage")
    op.drop_index("idx_api_usage_date", table_name="api_usage")
    op.drop_index("idx_api_usage_user_id", table_name="api_usage")
    op.drop_table("api_usage")
