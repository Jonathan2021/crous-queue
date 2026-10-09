"""Short-lived coarse network key on reports for per-network counting budgets."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: existing reports have no network key and each counts as its own source.
    op.add_column(
        "wait_reports", sa.Column("network_hash", sa.String(64), nullable=True)
    )
    op.create_index("ix_wait_reports_network_hash", "wait_reports", ["network_hash"])


def downgrade() -> None:
    op.drop_index("ix_wait_reports_network_hash", table_name="wait_reports")
    op.drop_column("wait_reports", "network_hash")
