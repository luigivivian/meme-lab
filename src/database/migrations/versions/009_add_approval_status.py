"""add approval_status to content_packages

Revision ID: 009
Revises: 008
Create Date: 2026-03-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_packages", sa.Column(
        "approval_status", sa.String(20),
        server_default="pending", nullable=False
    ))
    op.create_index("idx_pkg_approval_status", "content_packages", ["approval_status"])


def downgrade() -> None:
    op.drop_index("idx_pkg_approval_status", table_name="content_packages")
    op.drop_column("content_packages", "approval_status")
