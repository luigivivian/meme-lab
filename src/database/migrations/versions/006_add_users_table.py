"""add users table and characters.user_id FK

Revision ID: 006
Revises: 005
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("gemini_free_key", sa.Text(), nullable=True),
        sa.Column("gemini_paid_key", sa.Text(), nullable=True),
        sa.Column("active_key_tier", sa.String(20), server_default="free", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_is_active", "users", ["is_active"])

    # Add user_id FK to characters (per D-07)
    op.add_column("characters", sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("idx_characters_user_id", "characters", ["user_id"])


def downgrade() -> None:
    # CRITICAL: drop FK from characters BEFORE dropping users table
    op.drop_index("idx_characters_user_id", table_name="characters")
    op.drop_column("characters", "user_id")
    op.drop_index("idx_users_is_active", table_name="users")
    op.drop_index("idx_users_role", table_name="users")
    op.drop_table("users")
