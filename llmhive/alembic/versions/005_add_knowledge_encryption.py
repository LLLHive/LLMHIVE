"""Add encryption support to KnowledgeDocument.

Security: Add content_encrypted field to knowledge_documents table for
field-level encryption support.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_add_knowledge_encryption"
down_revision = "004_add_memory_optimization"  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Security: Add content_encrypted flag to knowledge_documents
    op.add_column(
        "knowledge_documents",
        sa.Column("content_encrypted", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # Security: Remove content_encrypted column
    op.drop_column("knowledge_documents", "content_encrypted")

