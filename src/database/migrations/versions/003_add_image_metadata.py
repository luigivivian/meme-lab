"""add image_metadata JSON column to content_packages and generated_images

Revision ID: 003
Revises: 002
Create Date: 2026-03-11 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # content_packages: adicionar image_metadata JSON
    op.add_column('content_packages', sa.Column('image_metadata', sa.JSON(), nullable=True))

    # generated_images: adicionar image_metadata JSON
    op.add_column('generated_images', sa.Column('image_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('generated_images', 'image_metadata')
    op.drop_column('content_packages', 'image_metadata')
