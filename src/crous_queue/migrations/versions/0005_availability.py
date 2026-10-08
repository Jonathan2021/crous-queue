"""Independent observations and pending-by-default comments; preserve old reports."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite's migration connection has FK enforcement off during table rebuild.
    # Validate all retained child links after the copy; runtime enables FKs.
    table = sa.Table("wait_reports", sa.MetaData(), autoload_with=op.get_bind())
    for constraint in table.constraints:
        if isinstance(constraint, sa.CheckConstraint) and constraint.name is None:
            constraint.name = "wait_minutes_range"
    with op.batch_alter_table("wait_reports", copy_from=table) as batch:
        batch.alter_column("minutes", existing_type=sa.Integer(), nullable=True)
        for name in ("grill", "vegetarian", "standard", "seating"):
            batch.add_column(sa.Column(name, sa.String(20), nullable=True))
        batch.add_column(
            sa.Column("comment", sa.String(280), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column(
                "comment_status", sa.String(20), nullable=False, server_default="none"
            )
        )
        batch.create_check_constraint(
            "report_kind_minutes",
            "(kind = 'availability' AND minutes IS NULL) OR (kind IN ('estimate', 'completed') AND minutes IS NOT NULL)",
        )
    if op.get_bind().dialect.name == "sqlite":
        if op.get_bind().exec_driver_sql("PRAGMA foreign_key_check").fetchone():
            raise RuntimeError(
                "Upgrade found broken report links; restore the pre-upgrade backup and inspect integrity."
            )


def downgrade() -> None:
    raise RuntimeError(
        "Restore a checked pre-upgrade backup with release 0.1.2; availability reports cannot be losslessly downgraded."
    )
