"""Add model_feedback table and update model_metrics.

Model Feedback: Add table for tracking individual model performance feedback
and update model_metrics with aggregate feedback statistics.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "002_add_model_feedback"
down_revision = "001_add_billing_tables"  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Model Feedback: Create FeedbackOutcome enum type
    # For SQLite, we'll use String instead of Enum (SQLite doesn't support native enums)
    # For PostgreSQL, we could use sa.Enum, but we'll use String for compatibility
    
    # Model Feedback: Create model_feedback table
    op.create_table(
        "model_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("session_id", sa.String(128), nullable=True, index=True),
        sa.Column("model_name", sa.String(128), nullable=False, index=True),
        sa.Column(
            "outcome",
            sa.String(32),
            nullable=False,
            default="unknown",
            index=True,
        ),  # Maps to FeedbackOutcome enum
        sa.Column("was_used_in_final", sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )
    
    # Model Feedback: Add new columns to model_metrics table
    op.add_column(
        "model_metrics",
        sa.Column("historical_success_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "model_metrics",
        sa.Column("avg_response_time_ms", sa.Float(), nullable=True),
    )
    op.add_column(
        "model_metrics",
        sa.Column("total_feedback_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    # Model Feedback: Remove columns from model_metrics
    op.drop_column("model_metrics", "total_feedback_count")
    op.drop_column("model_metrics", "avg_response_time_ms")
    op.drop_column("model_metrics", "historical_success_rate")
    
    # Model Feedback: Drop model_feedback table
    op.drop_table("model_feedback")

