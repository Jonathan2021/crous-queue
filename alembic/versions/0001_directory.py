"""Directory and provenance. Immutable schema version 1."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "venues",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("region", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(60), nullable=False),
        *[
            sa.Column(key, sa.Text(), nullable=False)
            for key in [
                "source_name",
                "source_type",
                "name",
                "search_text",
                "address",
                "access",
                "hours",
                "zone",
                "source_url",
            ]
        ],
        sa.Column("venue_type", sa.String(30), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("source_closing", sa.String(100), nullable=False),
        sa.Column("source_opening", sa.String(300), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("license", sa.String(30), nullable=False),
    )
    op.create_index("ix_venues_region", "venues", ["region"])
    op.create_index("ix_venues_venue_type", "venues", ["venue_type"])
    op.create_table(
        "directory_coverage",
        sa.Column("region", sa.String(40), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_good_at", sa.DateTime(timezone=True)),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("error", sa.String(100), nullable=False),
    )


def downgrade():
    op.drop_table("directory_coverage")
    op.drop_table("venues")
