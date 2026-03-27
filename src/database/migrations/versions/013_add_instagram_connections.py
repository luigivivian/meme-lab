"""add instagram_connections table

Revision ID: 013
Revises: 012
Create Date: 2026-03-26

Phase 14: Instagram Connection & CDN
- instagram_connections table for storing Instagram Business Account OAuth data
- Fernet-encrypted access tokens at rest
- Unique constraint on (user_id, ig_user_id)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instagram_connections',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ig_user_id', sa.String(50), nullable=False),
        sa.Column('ig_username', sa.String(200), nullable=False),
        sa.Column('page_id', sa.String(50), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=False),
        sa.Column('connected_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Indexes
    op.create_index('idx_ig_conn_user_id', 'instagram_connections', ['user_id'])
    op.create_index('idx_ig_conn_status', 'instagram_connections', ['status'])

    # Unique constraint: one IG account per user
    op.create_unique_constraint(
        'uq_ig_conn_user_ig', 'instagram_connections', ['user_id', 'ig_user_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_ig_conn_user_ig', 'instagram_connections', type_='unique')
    op.drop_index('idx_ig_conn_status', table_name='instagram_connections')
    op.drop_index('idx_ig_conn_user_id', table_name='instagram_connections')
    op.drop_table('instagram_connections')
