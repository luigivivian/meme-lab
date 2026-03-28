"""Add subtitle config columns to reels_config + update defaults

Revision ID: 019
Revises: 018
Create Date: 2026-03-28

Phase 999.6: Reels Pipeline v2 — subtitle styling configurable via panel
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reels_config", sa.Column("subtitle_font", sa.String(50), nullable=True, server_default="MedievalSharp"))
    op.add_column("reels_config", sa.Column("subtitle_outline", sa.Integer, nullable=True, server_default="1"))
    op.add_column("reels_config", sa.Column("subtitle_margin_v", sa.Integer, nullable=True, server_default="35"))
    op.add_column("reels_config", sa.Column("subtitle_margin_h", sa.Integer, nullable=True, server_default="15"))
    # Update existing defaults
    op.execute("UPDATE reels_config SET subtitle_font_size = 12 WHERE subtitle_font_size = 52")
    op.execute("UPDATE reels_config SET subtitle_color = '&H00B4EBFF&' WHERE subtitle_color = '#FFFFFF'")
    op.execute("UPDATE reels_config SET tts_voice = 'Charon' WHERE tts_voice = 'Puck'")


def downgrade() -> None:
    op.drop_column("reels_config", "subtitle_margin_h")
    op.drop_column("reels_config", "subtitle_margin_v")
    op.drop_column("reels_config", "subtitle_outline")
    op.drop_column("reels_config", "subtitle_font")
