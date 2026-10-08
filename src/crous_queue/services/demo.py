"""Synthetic provider: impossible to invoke against a non-demo configuration."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from crous_queue.config import Settings
from crous_queue.contracts import ReportInput, TimerInput
from crous_queue.db import make_engine
from crous_queue.models import WaitReport
from crous_queue.security import Identity
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.waits import WaitService


def seed_demo(
    settings: Settings, snapshot: Path, clock: Callable[[], datetime]
) -> None:
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError(
            "Synthetic demo requires local SQLite, never an external database."
        )
    if settings.environment != "demo" or "demo" not in Path(settings.database_url).name:
        raise ValueError(
            "Synthetic waits require a separate marked demo database; refusing real/test/production data."
        )
    engine = make_engine(settings.database_url)
    DirectoryImporter(engine, clock).import_snapshot(snapshot)
    now = clock()
    slot = int(now.timestamp() // 120)
    observed = datetime.fromtimestamp(slot * 120, UTC)
    for label, venue, minutes in [
        ("a", "paris:r177", 10),
        ("b", "paris:r177", 15),
        ("d", "paris:r175", 0),
    ]:
        device = sha256(("synthetic-demo-" + label).encode()).hexdigest()
        identity = Identity(device, sha256(b"synthetic-demo-network").hexdigest())
        with Session(engine) as db:
            recent = db.scalar(
                select(WaitReport).where(
                    WaitReport.device_hash == device,
                    WaitReport.received_at > now - timedelta(minutes=2),
                )
            )
            if recent:
                continue
        WaitService(engine, clock).submit(
            identity,
            venue,
            ReportInput(
                kind="estimate",
                minutes=minutes,
                vegetarian="unavailable" if label == "a" else None,
                seating="unavailable" if label == "a" else None,
                comment="Démonstration : réassort végétarien attendu, sans garantie."
                if label == "a"
                else "",
                observed_at=observed,
                queue_kind="student",
                idempotency_key=f"demo_{label}_{slot}",
            ),
        )
    identity = Identity(
        sha256(b"synthetic-demo-completed").hexdigest(),
        sha256(b"synthetic-demo-network").hexdigest(),
    )
    with Session(engine) as db:
        recent = db.scalar(
            select(WaitReport).where(
                WaitReport.device_hash == identity.device_hash,
                WaitReport.received_at > now - timedelta(minutes=2),
            )
        )
    if recent is None:
        timer = WaitService(engine, lambda: now - timedelta(minutes=8)).start(
            identity,
            TimerInput(
                venue_id="paris:r177",
                queue_kind="student",
                idempotency_key=f"demo_timer_{slot}",
            ),
        )
        WaitService(engine, clock).finish(identity, str(timer["id"]))
    engine.dispose()
