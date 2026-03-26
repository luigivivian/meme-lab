"""add subscriptions table and billing columns to users

Revision ID: 013
Revises: 012
Create Date: 2026-03-26

Phase 17: Billing & Stripe
- users: stripe_customer_id, subscription_plan, subscription_status, plan_period_end
- new table: subscriptions (Stripe subscription lifecycle tracking)
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
    # --- users: billing columns ---
    op.add_column(
        'users',
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
    )
    op.create_unique_constraint('uq_users_stripe_customer_id', 'users', ['stripe_customer_id'])
    op.create_index('idx_users_stripe_customer_id', 'users', ['stripe_customer_id'])

    op.add_column(
        'users',
        sa.Column('subscription_plan', sa.String(20), nullable=False, server_default='free'),
    )
    op.add_column(
        'users',
        sa.Column('subscription_status', sa.String(20), nullable=False, server_default='active'),
    )
    op.add_column(
        'users',
        sa.Column('plan_period_end', sa.DateTime(), nullable=True),
    )

    # --- subscriptions table ---
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(100), unique=True, nullable=False),
        sa.Column('stripe_price_id', sa.String(100), nullable=False),
        sa.Column('plan', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='active'),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sub_user_id', 'subscriptions', ['user_id'])
    op.create_index('idx_sub_status', 'subscriptions', ['status'])
    op.create_index('idx_sub_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])


def downgrade() -> None:
    # Drop subscriptions table
    op.drop_index('idx_sub_stripe_subscription_id', table_name='subscriptions')
    op.drop_index('idx_sub_status', table_name='subscriptions')
    op.drop_index('idx_sub_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    # Drop user billing columns
    op.drop_column('users', 'plan_period_end')
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_plan')
    op.drop_index('idx_users_stripe_customer_id', table_name='users')
    op.drop_constraint('uq_users_stripe_customer_id', 'users', type_='unique')
    op.drop_column('users', 'stripe_customer_id')
