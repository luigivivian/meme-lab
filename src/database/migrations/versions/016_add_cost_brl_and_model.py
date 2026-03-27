"""add cost_brl and model columns to api_usage

Revision ID: 016
Revises: 015
Create Date: 2026-03-27

Phase 20: Kie.ai Credits & Cost Tracking
- api_usage: cost_brl (Float, server_default 0.0) for BRL-native cost tracking
- api_usage: model (String(100), nullable) for per-model identification
- api_usage: tier widened from String(20) to String(100) to fit model IDs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- api_usage: BRL cost tracking ---
    op.add_column(
        'api_usage',
        sa.Column('cost_brl', sa.Float(), server_default='0.0', nullable=False),
    )
    op.add_column(
        'api_usage',
        sa.Column('model', sa.String(100), nullable=True),
    )
    # Widen tier from String(20) to String(100) to fit model IDs
    # e.g. "hailuo/2-3-image-to-video-standard" is 43 chars
    op.alter_column(
        'api_usage',
        'tier',
        existing_type=sa.String(20),
        type_=sa.String(100),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverse in reverse order
    op.alter_column(
        'api_usage',
        'tier',
        existing_type=sa.String(100),
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.drop_column('api_usage', 'model')
    op.drop_column('api_usage', 'cost_brl')
