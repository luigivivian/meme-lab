"""add billing fields to users table

Revision ID: 013
Revises: 012
Create Date: 2026-03-26

Phase 17: Billing & Stripe
- users: stripe_customer_id, stripe_subscription_id, plan_tier, subscription_status, subscription_ends_at
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(100), nullable=True))
    op.add_column(
        "users",
        sa.Column("plan_tier", sa.String(20), nullable=False, server_default="free"),
    )
    op.add_column("users", sa.Column("subscription_status", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("subscription_ends_at", sa.DateTime, nullable=True))

    op.create_index("idx_users_plan_tier", "users", ["plan_tier"])
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_index("idx_users_stripe_customer_id", table_name="users")
    op.drop_index("idx_users_plan_tier", table_name="users")

    op.drop_column("users", "subscription_ends_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "plan_tier")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
