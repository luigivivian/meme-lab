"""add rendering column to characters

Revision ID: ee583b64523f
Revises: 001
Create Date: 2026-03-11 17:31:18.257908
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'ee583b64523f'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona coluna rendering JSON com default vazio
    op.add_column('characters', sa.Column('rendering', sa.JSON(), nullable=True))
    op.execute("UPDATE characters SET rendering = '{}' WHERE rendering IS NULL")


def downgrade() -> None:
    op.drop_column('characters', 'rendering')
