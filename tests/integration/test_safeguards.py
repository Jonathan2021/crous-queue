import stat
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.db import make_engine
from crous_queue.models import ModerationAudit, RateBucket, ReportFlag, WaitReport
from crous_queue.services.maintenance import backup_sqlite, purge, restore_sqlite
from tests.conftest import ADMIN, HEADERS, NOW
from tests.integration.test_reports import report


def test_concurrent_duplicate_and_conflicting_hide(application, engine):
    app, current = application
    with TestClient(app) as seed:
        seed.get("/health")
        cookie = seed.cookies.get("cq_device")
    barrier = Barrier(2)
    key = str(uuid4())

    def write():
        with TestClient(app) as c:
            c.cookies.set("cq_device", cookie)
            barrier.wait()
            r = report(c, current, key=key)
            return r.status_code, r.json()["report"]["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(lambda _: write(), range(2)))
    assert a == b and a[0] == 201
    with TestClient(app) as client:
        client.get("/health")
        assert (
            client.post(
                f"/admin/reports/{a[1]}/hide",
                headers=HEADERS,
                json={"rationale": "Valeur suspecte", "expected_version": 0},
            ).status_code
            == 401
        )
        payload = {"rationale": "Valeur suspecte", "expected_version": 0}
        assert (
            client.post(
                f"/admin/reports/{a[1]}/hide", headers=ADMIN, json=payload
            ).status_code
            == 200
        )
        assert client.get("/venues/paris:r177/waits").json()["state"] == "unknown"
        assert (
            client.post(
                f"/admin/reports/{a[1]}/hide", headers=ADMIN, json=payload
            ).status_code
            == 409
        )
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(WaitReport)) == 1
        assert db.scalar(select(func.count()).select_from(ModerationAudit)) == 1


def test_flags_auth_history_and_metrics(application):
    app, current = application
    with TestClient(app) as c:
        c.get("/health")
        item = report(c, current).json()["report"]
        url = f"/reports/{item['id']}/flags"
        assert (
            c.post(url, headers=HEADERS, json={"reason": "suspected_false"}).status_code
            == 201
        )
        assert (
            c.post(url, headers=HEADERS, json={"reason": "suspected_false"}).status_code
            == 201
        )
        assert (
            c.post(
                url, headers=HEADERS, json={"reason": "personal complaint"}
            ).status_code
            == 422
        )
        assert c.get("/admin/reports").status_code == 401
        items = c.get("/admin/reports", headers=ADMIN).json()["items"]
        assert items[0]["flag_count"] == 1 and "device" not in str(items)
        assert c.get("/admin/metrics", headers=ADMIN).json()["reports_total"] == 1
        assert c.get("/privacy").status_code == 200


def test_exact_retention_backup_restore(application, engine, tmp_path):
    app, current = application
    with TestClient(app) as c:
        c.get("/health")
        first = report(c, current).json()["report"]["id"]
        current[0] += timedelta(minutes=2)
        second = report(c, current).json()["report"]["id"]
        c.post(
            f"/reports/{first}/flags",
            headers=HEADERS,
            json={"reason": "suspected_false"},
        )
    with Session(engine) as db, db.begin():
        db.get(WaitReport, first).received_at = NOW - timedelta(days=7)
        db.get(WaitReport, second).received_at = (
            NOW - timedelta(days=7) + timedelta(microseconds=1)
        )
        db.add_all(
            [
                RateBucket(key="expired-test", count=1, expires_at=NOW),
                RateBucket(
                    key="future-test",
                    count=1,
                    expires_at=NOW + timedelta(microseconds=1),
                ),
            ]
        )
    result = purge(engine, NOW)
    assert result["reports"] == 1
    with Session(engine) as db:
        assert (
            db.get(WaitReport, first) is None and db.get(WaitReport, second) is not None
        )
        assert db.scalar(select(func.count()).select_from(ReportFlag)) == 0
        assert (
            db.get(RateBucket, "expired-test") is None
            and db.get(RateBucket, "future-test") is not None
        )
    backup = tmp_path / "test-backup.db"
    target = tmp_path / "test-restored.db"
    backup_sqlite(str(engine.url), backup, environment="test")
    restore_sqlite(backup, target, environment="test")
    with Session(make_engine(f"sqlite:///{target}")) as db:
        assert db.get(WaitReport, second) is not None
    with pytest.raises(ValueError):
        restore_sqlite(backup, target, environment="test")
    with pytest.raises(ValueError):
        restore_sqlite(backup, tmp_path / "production.db", environment="production")


def test_bounds_origin_and_redacted_request_logs(application, caplog):
    app, current = application
    caplog.set_level("INFO", logger="crous_queue.requests")
    with TestClient(app) as c:
        c.get("/health")
        token = c.cookies.get("cq_device")
        assert (
            c.post(
                "/venues/paris:r177/reports",
                headers=HEADERS,
                json={"lat": 48.84752, "token": token},
            ).status_code
            == 422
        )
        assert (
            c.post(
                "/venues/paris:r177/reports",
                headers={**HEADERS, "Origin": "https://attacker.test"},
                json={},
            ).status_code
            == 403
        )
        assert (
            c.post(
                "/venues/paris:r177/reports",
                headers=HEADERS,
                json={"stuff": "x" * 5000},
            ).status_code
            == 413
        )
        report(c, current)
    assert caplog.records
    assert (
        token not in caplog.text
        and "48.84752" not in caplog.text
        and "attacker.test" not in caplog.text
    )
    assert '"route"' in caplog.text and '"status"' in caplog.text


def test_backup_restore_refuse_unsafe_sources_overwrites_and_tampering(
    engine, tmp_path
):
    for url in ["postgresql+psycopg://app@db/crous", "sqlite:///:memory:"]:
        with pytest.raises(ValueError, match="SQLite file required"):
            backup_sqlite(url, tmp_path / "test-x.db", environment="test")
    missing = f"sqlite:///{tmp_path / 'test-absent.db'}"
    with pytest.raises(ValueError, match="no files are overwritten"):
        backup_sqlite(missing, tmp_path / "test-y.db", environment="test")
    backup = tmp_path / "test-backup.db"
    backup_sqlite(str(engine.url), backup, environment="test")
    manifest = tmp_path / "test-backup.db.json"
    for path in [backup, manifest]:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(ValueError, match="matching environment"):
        restore_sqlite(backup, tmp_path / "demo-restored.db", environment="demo")
    backup.write_bytes(backup.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        restore_sqlite(backup, tmp_path / "test-restored.db", environment="test")
    assert not (tmp_path / "test-restored.db").exists()
