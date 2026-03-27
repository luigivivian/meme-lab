"""add legend columns to content_packages

Revision ID: 015
Revises: 014
Create Date: 2026-03-26

Phase 999.2: Video Legends & Subtitles
- content_packages: legend_status (tracking overlay progress), legend_path (output file)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- content_packages: legend overlay fields ---
    op.add_column(
        'content_packages',
        sa.Column('legend_status', sa.String(20), nullable=True),
    )
    op.add_column(
        'content_packages',
        sa.Column('legend_path', sa.String(1000), nullable=True),
    )
    op.create_index('idx_pkg_legend_status', 'content_packages', ['legend_status'])


def downgrade() -> None:
    # Reverse in reverse order
    op.drop_index('idx_pkg_legend_status', table_name='content_packages')
    op.drop_column('content_packages', 'legend_path')
    op.drop_column('content_packages', 'legend_status')
