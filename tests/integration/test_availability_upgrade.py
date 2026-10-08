"""Synthetic 0.1.2 schema/data, never the operator's application database."""

import json
from hashlib import sha256

from alembic import command
from sqlalchemy import text
from sqlalchemy.orm import Session

from crous_queue.contracts import ReportInput
from crous_queue.db import make_engine
from crous_queue.distribution import directory_snapshot, migration_configuration
from crous_queue.models import ModerationAudit, ReportFlag, WaitReport, WaitTimer
from crous_queue.security import Identity
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.maintenance import backup_sqlite, restore_sqlite
from crous_queue.services.waits import WaitService
from tests.conftest import NOW


def test_012_upgrade_preserves_links_legacy_retry_and_recovery(tmp_path):
    url = f"sqlite:///{tmp_path / 'test-old.db'}"
    with migration_configuration(url) as config:
        command.upgrade(config, "0003")
    engine = make_engine(url)
    with directory_snapshot() as path:
        DirectoryImporter(engine, lambda: NOW).import_snapshot(path)
    payload = dict(
        kind="estimate",
        minutes=0,
        observed_at=NOW.isoformat().replace("+00:00", "Z"),
        queue_kind="student",
        idempotency_key="legacy-retry-001",
    )
    digest = sha256(
        json.dumps(dict(venue="paris:r177", **payload), sort_keys=True).encode()
    ).hexdigest()
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO wait_reports (id,venue_id,queue_kind,kind,minutes,observed_at,received_at,device_hash,idempotency_key,payload_digest,visibility,moderation_version) VALUES (:id,:venue,:queue,:kind,0,:now,:now,:device,:key,:digest,:visibility,1)"
            ),
            dict(
                id="old-report",
                venue="paris:r177",
                queue="student",
                kind="estimate",
                now=NOW.replace(tzinfo=None).isoformat(sep=" "),
                device="old-device",
                key="legacy-retry-001",
                digest=digest,
                visibility="visible",
            ),
        )
        db.execute(
            text(
                "INSERT INTO wait_timers (id,venue_id,queue_kind,device_hash,idempotency_key,started_at,report_id) VALUES ('old-timer','paris:r177','student','old-device','old-timer-key',:now,'old-report')"
            ),
            dict(now=NOW.replace(tzinfo=None).isoformat(sep=" ")),
        )
        db.execute(
            text(
                "INSERT INTO report_flags (id,report_id,device_hash,reason,received_at) VALUES ('old-flag','old-report','other','suspected_false',:now)"
            ),
            dict(now=NOW.replace(tzinfo=None).isoformat(sep=" ")),
        )
        db.execute(
            text(
                "INSERT INTO moderation_audits (id,report_id,action,rationale,created_at,version) VALUES ('old-audit','old-report','hide','Synthetic old audit',:now,1)"
            ),
            dict(now=NOW.replace(tzinfo=None).isoformat(sep=" ")),
        )
    backup = tmp_path / "test-backup.db"
    backup_sqlite(url, backup, environment="test")
    with migration_configuration(url) as config:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
    with Session(engine) as db:
        report = db.get(WaitReport, "old-report")
        assert (
            report.minutes == 0 and report.comment == "" and report.vegetarian is None
        )
        assert db.get(WaitTimer, "old-timer").report_id == "old-report"
        assert db.get(ReportFlag, "old-flag").report_id == "old-report"
        assert db.get(ModerationAudit, "old-audit").version == 1
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
    assert (
        WaitService(engine, lambda: NOW)
        .submit(
            Identity("old-device", "old-network"),
            "paris:r177",
            ReportInput.model_validate(payload),
        )
        .id
        == "old-report"
    )
    restored = tmp_path / "test-restored.db"
    restore_sqlite(backup, restored, environment="test")
    with migration_configuration(f"sqlite:///{restored}") as config:
        command.upgrade(config, "head")
    with make_engine(f"sqlite:///{restored}").connect() as db:
        assert db.execute(text("SELECT count(*) FROM wait_reports")).scalar() == 1
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
