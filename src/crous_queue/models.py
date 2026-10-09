from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from crous_queue.db import UTCDateTime


class Base(DeclarativeBase):
    pass


class Venue(Base):
    __tablename__ = "venues"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    region: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(60))
    source_name: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    venue_type: Mapped[str] = mapped_column(String(30), index=True)
    search_text: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(Text, default="")
    access: Mapped[str] = mapped_column(Text, default="")
    hours: Mapped[str] = mapped_column(Text, default="")
    zone: Mapped[str] = mapped_column(Text, default="")
    source_closing: Mapped[str] = mapped_column(String(100), default="")
    source_opening: Mapped[str] = mapped_column(String(300), default="")
    source_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime)
    source_url: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(String(30), default="fr-lo")


class Coverage(Base):
    __tablename__ = "directory_coverage"
    region: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_good_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    payload_sha256: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str] = mapped_column(String(100), default="")


class WaitReport(Base):
    __tablename__ = "wait_reports"
    __table_args__ = (
        UniqueConstraint("device_hash", "idempotency_key"),
        CheckConstraint("minutes >= 0 AND minutes <= 120"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), index=True)
    queue_kind: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20))
    minutes: Mapped[int | None]
    grill: Mapped[str | None] = mapped_column(String(20))
    vegetarian: Mapped[str | None] = mapped_column(String(20))
    standard: Mapped[str | None] = mapped_column(String(20))
    seating: Mapped[str | None] = mapped_column(String(20))
    comment: Mapped[str] = mapped_column(String(280), default="")
    comment_status: Mapped[str] = mapped_column(String(20), default="none")
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    source_window_start: Mapped[datetime | None] = mapped_column(UTCDateTime)
    device_hash: Mapped[str] = mapped_column(String(64), index=True)
    # Daily-rotating keyed hash of the coarse network; cleared after 24 hours.
    network_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    payload_digest: Mapped[str] = mapped_column(String(64))
    visibility: Mapped[str] = mapped_column(String(20), default="visible")
    moderation_version: Mapped[int] = mapped_column(default=0)


class WaitTimer(Base):
    __tablename__ = "wait_timers"
    __table_args__ = (UniqueConstraint("device_hash", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"))
    queue_kind: Mapped[str] = mapped_column(String(20))
    device_hash: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    report_id: Mapped[str | None] = mapped_column(
        ForeignKey("wait_reports.id", ondelete="SET NULL")
    )


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    count: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class ReportFlag(Base):
    __tablename__ = "report_flags"
    __table_args__ = (UniqueConstraint("report_id", "device_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(
        ForeignKey("wait_reports.id", ondelete="CASCADE"), index=True
    )
    device_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(30))
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ModerationAudit(Base):
    __tablename__ = "moderation_audits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    report_id: Mapped[str] = mapped_column(
        ForeignKey("wait_reports.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    version: Mapped[int]


class OfficialHours(Base):
    __tablename__ = "official_hours"
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.id"), primary_key=True)
    official_url: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(40))
    source_timestamp: Mapped[datetime | None] = mapped_column(UTCDateTime)
    retrieved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime)
    raw_schedule: Mapped[str] = mapped_column(Text, default="")
    last_attempt_raw: Mapped[str] = mapped_column(Text, default="")
    last_attempt_sha256: Mapped[str] = mapped_column(String(64), default="")
    normalized: Mapped[str] = mapped_column(Text, default="null")
    payload_sha256: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str] = mapped_column(String(100), default="")
