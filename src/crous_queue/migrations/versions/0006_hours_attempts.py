"""Retain rejected source interpretation without overwriting a good schedule."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "official_hours",
        sa.Column("last_attempt_raw", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "official_hours",
        sa.Column(
            "last_attempt_sha256", sa.String(64), nullable=False, server_default=""
        ),
    )


def downgrade() -> None:
    op.drop_column("official_hours", "last_attempt_sha256")
    op.drop_column("official_hours", "last_attempt_raw")
