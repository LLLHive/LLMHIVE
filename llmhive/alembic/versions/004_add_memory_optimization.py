"""Add memory optimization: user isolation, encryption, and indexing.

Memory Optimization: Add user_id, content_encrypted fields and indexes for:
- User isolation (user_id field and index)
- Encryption support (content_encrypted flag)
- Retention policy (indexed created_at for efficient pruning)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_add_memory_optimization"
down_revision = "003_add_user_tier"  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Memory Optimization: Add user_id column for user isolation
    op.add_column(
        "memory_entries",
        sa.Column("user_id", sa.String(128), nullable=True),
    )
    
    # Memory Optimization: Add index on user_id for efficient user isolation queries
    op.create_index(
        "ix_memory_entries_user_id",
        "memory_entries",
        ["user_id"],
        unique=False,
    )
    
    # Memory Optimization: Add content_encrypted flag for encryption support
    op.add_column(
        "memory_entries",
        sa.Column("content_encrypted", sa.Boolean(), nullable=False, server_default="0"),
    )
    
    # Memory Optimization: Add index on created_at for efficient retention policy pruning
    # (Note: created_at may already have an index, but we ensure it exists)
    # Check if index exists first (SQLite doesn't support IF NOT EXISTS for indexes)
    from sqlalchemy import inspect
    from alembic import context
    
    conn = context.get_bind()
    inspector = inspect(conn)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('memory_entries')]
    
    if 'ix_memory_entries_created_at' not in existing_indexes:
        op.create_index(
            "ix_memory_entries_created_at",
            "memory_entries",
            ["created_at"],
            unique=False,
        )
    
    # Memory Optimization: Migrate existing entries - set user_id from conversation
    op.execute("""
        UPDATE memory_entries
        SET user_id = (
            SELECT conversations.user_id
            FROM conversations
            WHERE conversations.id = memory_entries.conversation_id
        )
        WHERE user_id IS NULL
    """)


def downgrade() -> None:
    # Memory Optimization: Remove indexes
    try:
        op.drop_index("ix_memory_entries_created_at", table_name="memory_entries")
    except Exception:
        pass
    op.drop_index("ix_memory_entries_user_id", table_name="memory_entries")
    
    # Memory Optimization: Remove columns
    op.drop_column("memory_entries", "content_encrypted")
    op.drop_column("memory_entries", "user_id")

