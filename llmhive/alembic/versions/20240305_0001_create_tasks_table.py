"""create tasks table"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20240305_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("model_names", sa.JSON(), nullable=False),
        sa.Column("initial_responses", sa.JSON(), nullable=True),
        sa.Column("critiques", sa.JSON(), nullable=True),
        sa.Column("improvements", sa.JSON(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("tasks")
