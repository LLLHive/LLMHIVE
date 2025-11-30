"""Add User model with account tier attribute.

Tier-aware Rate Limiting: Create users table and add account_tier field.
Existing users (identified by user_id in conversations/usage) will be migrated
to have Free tier by default.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "003_add_user_tier"
down_revision = "002_add_model_feedback"  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tier-aware Rate Limiting: Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column(
            "account_tier",
            sa.String(32),
            nullable=False,
            server_default="free",  # Backwards compatibility: Default to free for existing records
            index=True,
        ),  # Maps to AccountTier enum (free, pro, enterprise)
        sa.Column("email", sa.String(256), nullable=True, unique=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )
    
    # Tier-aware Rate Limiting: Migrate existing users from conversations/usage_records
    # Extract unique user_ids and create User records with Free tier
    op.execute("""
        INSERT INTO users (user_id, account_tier, created_at, updated_at)
        SELECT DISTINCT user_id, 'free', datetime('now'), datetime('now')
        FROM conversations
        WHERE user_id IS NOT NULL AND user_id != ''
        AND user_id NOT IN (SELECT user_id FROM users)
    """)
    
    op.execute("""
        INSERT INTO users (user_id, account_tier, created_at, updated_at)
        SELECT DISTINCT user_id, 'free', datetime('now'), datetime('now')
        FROM usage_records
        WHERE user_id IS NOT NULL AND user_id != ''
        AND user_id NOT IN (SELECT user_id FROM users)
    """)


def downgrade() -> None:
    # Tier-aware Rate Limiting: Drop users table
    op.drop_table("users")

