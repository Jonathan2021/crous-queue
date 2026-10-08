"""Moderation history and optimistic versioning."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "wait_reports",
        sa.Column(
            "moderation_version", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.create_table(
        "report_flags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "report_id",
            sa.String(36),
            sa.ForeignKey("wait_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("report_id", "device_hash"),
    )
    op.create_index("ix_report_flags_report_id", "report_flags", ["report_id"])
    op.create_table(
        "moderation_audits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "report_id",
            sa.String(36),
            sa.ForeignKey("wait_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("rationale", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_moderation_audits_report_id", "moderation_audits", ["report_id"]
    )


def downgrade() -> None:
    op.drop_table("moderation_audits")
    op.drop_table("report_flags")
    op.drop_column("wait_reports", "moderation_version")
