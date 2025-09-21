"""Initial database schema."""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202309201200"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "example",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("example")
