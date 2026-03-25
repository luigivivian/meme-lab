"""tenant isolation: backfill + NOT NULL + Theme.user_id

Revision ID: 010
Revises: 009
Create Date: 2026-03-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # D-08: Backfill orphan characters to admin user (id=1)
    op.execute("UPDATE characters SET user_id = 1 WHERE user_id IS NULL")

    # D-08: Backfill orphan pipeline_runs to default character (mago-mestre)
    op.execute(
        "UPDATE pipeline_runs SET character_id = "
        "(SELECT id FROM characters WHERE slug = 'mago-mestre' LIMIT 1) "
        "WHERE character_id IS NULL"
    )

    # D-09: Enforce NOT NULL on characters.user_id
    op.alter_column(
        'characters', 'user_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    # D-10: Enforce NOT NULL on pipeline_runs.character_id
    op.alter_column(
        'pipeline_runs', 'character_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    # D-03: Add user_id to themes for user-owned themes
    op.add_column(
        'themes',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('idx_themes_user_id', 'themes', ['user_id'])


def downgrade() -> None:
    # Reverse in reverse order
    op.drop_index('idx_themes_user_id', table_name='themes')
    op.drop_column('themes', 'user_id')

    op.alter_column(
        'pipeline_runs', 'character_id',
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.alter_column(
        'characters', 'user_id',
        existing_type=sa.Integer(),
        nullable=True,
    )
