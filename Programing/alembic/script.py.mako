"""Generic Alembic revision script."""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
