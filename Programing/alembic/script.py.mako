"""Generic Alembic migration template."""

from __future__ import annotations

revision = "${up_revision}"
down_revision = ${down_revision | repr}
branch_labels = ${branch_labels | repr}
depends_on = ${depends_on | repr}

def upgrade() -> None:
    ${upgrades if upgrades else 'pass'}


def downgrade() -> None:
    ${downgrades if downgrades else 'pass'}
