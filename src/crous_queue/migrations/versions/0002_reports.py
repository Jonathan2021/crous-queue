"""Reports, device-owned timers and short-lived aggregate rate counters."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wait_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "venue_id", sa.String(100), sa.ForeignKey("venues.id"), nullable=False
        ),
        sa.Column("queue_kind", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        *[
            sa.Column(k, sa.DateTime(timezone=True), nullable=False)
            for k in ["observed_at", "received_at"]
        ],
        sa.Column("source_window_start", sa.DateTime(timezone=True)),
        sa.Column("device_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.UniqueConstraint("device_hash", "idempotency_key"),
        sa.CheckConstraint("minutes >= 0 AND minutes <= 120"),
    )
    for field in ["venue_id", "received_at", "device_hash"]:
        op.create_index("ix_wait_reports_" + field, "wait_reports", [field])
    op.create_table(
        "wait_timers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "venue_id", sa.String(100), sa.ForeignKey("venues.id"), nullable=False
        ),
        sa.Column("queue_kind", sa.String(20), nullable=False),
        sa.Column("device_hash", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "report_id",
            sa.String(36),
            sa.ForeignKey("wait_reports.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint("device_hash", "idempotency_key"),
    )
    op.create_index("ix_wait_timers_device_hash", "wait_timers", ["device_hash"])
    op.create_table(
        "rate_buckets",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_buckets_expires_at", "rate_buckets", ["expires_at"])


def downgrade() -> None:
    op.drop_table("rate_buckets")
    op.drop_table("wait_timers")
    op.drop_table("wait_reports")
