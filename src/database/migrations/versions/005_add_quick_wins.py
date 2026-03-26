"""add quick wins columns to content_packages (A/B testing + carousel)

Revision ID: 005
Revises: 004
Create Date: 2026-03-12 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL nao suporta server_default em colunas JSON — defaults ficam no ORM
    # A/B testing: alternativas de frase com scores
    op.add_column(
        "content_packages",
        sa.Column("phrase_alternatives", sa.JSON(), nullable=True),
    )
    # Carousel: paths dos slides (vazio = imagem unica)
    op.add_column(
        "content_packages",
        sa.Column("carousel_slides", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("content_packages", "carousel_slides")
    op.drop_column("content_packages", "phrase_alternatives")
