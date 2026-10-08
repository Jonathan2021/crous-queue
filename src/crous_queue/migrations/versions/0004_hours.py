"""Official hours cache with independent source and retrieval timestamps."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_hours",
        sa.Column(
            "venue_id", sa.String(100), sa.ForeignKey("venues.id"), primary_key=True
        ),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_schedule", sa.Text(), nullable=False),
        sa.Column("normalized", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("error", sa.String(100), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("official_hours")
