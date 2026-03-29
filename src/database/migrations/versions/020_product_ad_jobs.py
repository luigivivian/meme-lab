"""create product_ad_jobs table

Revision ID: 020
Revises: 018
Create Date: 2026-03-29

Phase 421: Product Studio AI Video Ads Generator
- product_ad_jobs table for tracking ad generation jobs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '020'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_ad_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(36), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_images", sa.JSON, nullable=True),
        sa.Column("config", sa.JSON, nullable=True),
        sa.Column("style", sa.String(20), nullable=False, server_default="cinematic"),
        sa.Column("video_model", sa.String(100), server_default="wan2.1-i2v"),
        sa.Column("audio_mode", sa.String(20), server_default="music"),
        sa.Column("output_formats", sa.JSON, server_default='["9:16"]'),
        sa.Column("target_duration", sa.Integer, server_default="15"),
        sa.Column("tone", sa.String(50), server_default="premium"),
        sa.Column("niche", sa.String(100), server_default=""),
        sa.Column("audience", sa.String(255), server_default=""),
        sa.Column("scene_description", sa.Text, nullable=True),
        sa.Column("prompt_generated", sa.Text, nullable=True),
        sa.Column("step_state", sa.JSON, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("current_step", sa.String(30), nullable=True),
        sa.Column("progress_pct", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("cost_usd", sa.Float, server_default="0"),
        sa.Column("cost_brl", sa.Float, server_default="0"),
        sa.Column("outputs", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_product_ad_jobs_user_id", "product_ad_jobs", ["user_id"])
    op.create_index("idx_product_ad_jobs_status", "product_ad_jobs", ["status"])
    op.create_index("idx_product_ad_jobs_job_id", "product_ad_jobs", ["job_id"])


def downgrade() -> None:
    op.drop_index("idx_product_ad_jobs_job_id", table_name="product_ad_jobs")
    op.drop_index("idx_product_ad_jobs_status", table_name="product_ad_jobs")
    op.drop_index("idx_product_ad_jobs_user_id", table_name="product_ad_jobs")
    op.drop_table("product_ad_jobs")
