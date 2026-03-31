"""Add scene_assets table for semantic asset reuse

Revision ID: 025
Revises: 024
Create Date: 2026-03-31

Phase G: Scene Asset Registry with Semantic Reuse
- scene_assets table stores generated images/videos with embeddings
- Enables cosine similarity search to reuse existing assets
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '025'
down_revision: Union[str, None] = '024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scene_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=True),
        sa.Column("asset_type", sa.String(10), nullable=False),
        sa.Column("scene_description", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("kie_task_id", sa.String(100), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=False, server_default=""),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "idx_scene_assets_user_type_char",
        "scene_assets",
        ["user_id", "asset_type", "character_id"],
    )
    op.create_index("idx_scene_assets_user_id", "scene_assets", ["user_id"])
    op.create_index("idx_scene_assets_file_hash", "scene_assets", ["file_hash"])


def downgrade() -> None:
    op.drop_index("idx_scene_assets_file_hash", table_name="scene_assets")
    op.drop_index("idx_scene_assets_user_id", table_name="scene_assets")
    op.drop_index("idx_scene_assets_user_type_char", table_name="scene_assets")
    op.drop_table("scene_assets")
