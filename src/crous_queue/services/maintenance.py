import json
import os
import sqlite3
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from sqlalchemy import Engine, delete, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from crous_queue.models import (
    ModerationAudit,
    RateBucket,
    ReportFlag,
    WaitReport,
    WaitTimer,
)


def purge(engine: Engine, now: datetime) -> dict[str, int]:
    cutoff = now - timedelta(days=7)
    removed: dict[str, int] = {}
    with Session(engine) as db, db.begin():
        # Explicit child cleanup works with either database dialect.
        old_ids = select(WaitReport.id).where(WaitReport.received_at <= cutoff)
        db.execute(delete(ReportFlag).where(ReportFlag.report_id.in_(old_ids)))
        db.execute(
            delete(ModerationAudit).where(ModerationAudit.report_id.in_(old_ids))
        )
        # Timers must not retain a link to a deleted report.
        db.execute(
            update(WaitTimer)
            .where(WaitTimer.report_id.in_(old_ids))
            .values(report_id=None)
        )
        # Network keys serve live budgets and bulk moderation only: <=24 h.
        cleared = db.execute(
            update(WaitReport)
            .where(
                WaitReport.received_at <= now - timedelta(hours=24),
                WaitReport.network_hash.is_not(None),
            )
            .values(network_hash=None)
        )
        removed["network_keys"] = int(getattr(cleared, "rowcount", 0))
        for label, model, predicate in [
            ("timers", WaitTimer, WaitTimer.started_at <= cutoff),
            ("reports", WaitReport, WaitReport.received_at <= cutoff),
            ("flags", ReportFlag, ReportFlag.received_at <= cutoff),
            ("audits", ModerationAudit, ModerationAudit.created_at <= cutoff),
            ("rate_buckets", RateBucket, RateBucket.expires_at <= now),
        ]:
            result = db.execute(delete(model).where(predicate))
            removed[label] = int(getattr(result, "rowcount", 0))
    return removed


def sqlite_path(url: str) -> Path:
    parsed = make_url(url)
    if (
        not parsed.drivername.startswith("sqlite")
        or not parsed.database
        or parsed.database == ":memory:"
    ):
        raise ValueError(
            "SQLite file required. For PostgreSQL use the documented pg_dump/pg_restore procedure."
        )
    return Path(parsed.database).resolve()


def backup_sqlite(url: str, output: Path, *, environment: str) -> None:
    source = sqlite_path(url)
    manifest = output.with_suffix(output.suffix + ".json")
    if not source.is_file() or output.exists() or manifest.exists():
        raise ValueError(
            "Backup requires an existing source and a new output path; no files are overwritten."
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with (
            sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as src,
            sqlite3.connect(output) as dst,
        ):
            src.backup(dst)
            if dst.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise ValueError("Backup integrity check failed.")
        with manifest.open("x") as stream:
            json.dump(
                dict(
                    schema=1,
                    environment=environment,
                    sha256=sha256(output.read_bytes()).hexdigest(),
                ),
                stream,
            )
        manifest.chmod(0o600)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def restore_sqlite(backup: Path, output: Path, *, environment: str) -> None:
    meta = json.loads(backup.with_suffix(backup.suffix + ".json").read_text())
    if (
        output.exists()
        or (environment != "production" and environment not in output.name)
        or meta["environment"] != environment
        or meta["sha256"] != sha256(backup.read_bytes()).hexdigest()
    ):
        raise ValueError(
            "Restore requires a new marked path, matching environment and checksum; never overwrite live data."
        )
    with sqlite3.connect(f"{backup.resolve().as_uri()}?mode=ro", uri=True) as src:
        if src.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("Restore source failed integrity check.")
        output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(output) as dst:
            src.backup(dst)
