"""Add billing tables (subscriptions and usage_records).

Revision ID: 001_add_billing_tables
Revises: 
Create Date: 2025-11-17 13:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_billing_tables'
down_revision = '20240305_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create subscription and usage_record tables."""
    # Create subscription_status enum
    op.execute("""
        CREATE TYPE subscriptionstatus AS ENUM ('active', 'cancelled', 'past_due', 'trialing', 'expired');
    """)
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('tier_name', sa.String(length=32), nullable=False),
        sa.Column('status', sa.Enum('active', 'cancelled', 'past_due', 'trialing', 'expired', name='subscriptionstatus'), nullable=False),
        sa.Column('billing_cycle', sa.String(length=16), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=128), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_tier_name'), 'subscriptions', ['tier_name'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_subscriptions_current_period_end'), 'subscriptions', ['current_period_end'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=False)
    
    # Create usage_records table
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('requests_count', sa.Integer(), nullable=False),
        sa.Column('tokens_count', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_records_id'), 'usage_records', ['id'], unique=False)
    op.create_index(op.f('ix_usage_records_subscription_id'), 'usage_records', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_usage_records_user_id'), 'usage_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_usage_records_period_start'), 'usage_records', ['period_start'], unique=False)
    op.create_index(op.f('ix_usage_records_period_end'), 'usage_records', ['period_end'], unique=False)


def downgrade() -> None:
    """Drop subscription and usage_record tables."""
    op.drop_index(op.f('ix_usage_records_period_end'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_period_start'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_user_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_subscription_id'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_id'), table_name='usage_records')
    op.drop_table('usage_records')
    
    op.drop_index(op.f('ix_subscriptions_stripe_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_current_period_end'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_tier_name'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    op.execute("DROP TYPE subscriptionstatus;")

