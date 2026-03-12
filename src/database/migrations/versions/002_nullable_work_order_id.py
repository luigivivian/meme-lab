"""make work_order_id nullable on content_packages

Revision ID: 002
Revises: ee583b64523f
Create Date: 2026-03-11 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = 'ee583b64523f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK constraint, modify column to nullable, recreate FK with SET NULL
    op.drop_constraint('content_packages_ibfk_2', 'content_packages', type_='foreignkey')
    op.alter_column('content_packages', 'work_order_id',
                     existing_type=sa.Integer(),
                     nullable=True)
    op.create_foreign_key(
        'content_packages_ibfk_2', 'content_packages', 'work_orders',
        ['work_order_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.execute("UPDATE content_packages SET work_order_id = 0 WHERE work_order_id IS NULL")
    op.drop_constraint('content_packages_ibfk_2', 'content_packages', type_='foreignkey')
    op.alter_column('content_packages', 'work_order_id',
                     existing_type=sa.Integer(),
                     nullable=False)
    op.create_foreign_key(
        'content_packages_ibfk_2', 'content_packages', 'work_orders',
        ['work_order_id'], ['id'], ondelete='CASCADE'
    )
