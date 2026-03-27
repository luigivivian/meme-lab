"""add video columns to content_packages and themes

Revision ID: 012
Revises: 011
Create Date: 2026-03-26

Phase 999.1: Video Generation (Kie.ai Sora 2)
- content_packages: video_path, video_source, video_prompt_used, video_task_id, video_metadata, video_status
- themes: video_prompt_notes (per D-03: accumulated learnings for LLM prompt generation)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- content_packages: video generation fields ---
    op.add_column(
        'content_packages',
        sa.Column('video_path', sa.String(1000), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('video_source', sa.String(30), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('video_prompt_used', sa.Text(), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('video_task_id', sa.String(100), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('video_metadata', sa.JSON(), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('video_status', sa.String(20), nullable=True),
    )
    op.create_index('idx_pkg_video_status', 'content_packages', ['video_status'])

    # --- themes: video prompt improvement notes (per D-03) ---
    op.add_column(
        'themes',
        sa.Column('video_prompt_notes', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Reverse in reverse order
    op.drop_column('themes', 'video_prompt_notes')

    op.drop_index('idx_pkg_video_status', table_name='content_packages')
    op.drop_column('content_packages', 'video_status')
    op.drop_column('content_packages', 'video_metadata')
    op.drop_column('content_packages', 'video_task_id')
    op.drop_column('content_packages', 'video_prompt_used')
    op.drop_column('content_packages', 'video_source')
    op.drop_column('content_packages', 'video_path')
