"""Exercise the PostgreSQL branch against a disposable, test-named database.

Operator-run (not in CI): needs a local throwaway PostgreSQL. Refuses any database
whose name lacks "test". Writes synthetic data only. Checks migration up/down,
concurrent identical retries, concurrent throttle races (advisory locks), the
per-network budget, admin version conflicts, UTC round-trips, retention, and a
pg_dump/pg_restore round-trip into a second disposable database.
"""

import argparse
import json
import subprocess
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from threading import Barrier

from alembic import command
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from crous_queue.contracts import HideInput, ReportInput
from crous_queue.db import make_engine
from crous_queue.distribution import directory_snapshot, migration_configuration
from crous_queue.models import WaitReport
from crous_queue.security import Identity
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.maintenance import purge
from crous_queue.services.moderation import ModerationService
from crous_queue.services.waits import DomainError, WaitService

NOW = datetime.now(UTC).replace(microsecond=0)
CUVIER = "paris:r177"


def identity(label: str, network: str = "net-a") -> Identity:
    return Identity(
        sha256(f"device-{label}".encode()).hexdigest(),
        sha256(f"network-{network}".encode()).hexdigest(),
    )


def estimate(minutes: int, key: str) -> ReportInput:
    return ReportInput(
        kind="estimate",
        minutes=minutes,
        observed_at=NOW,
        queue_kind="student",
        idempotency_key=key,
    )


def race[T](calls: Sequence[T], fn: Callable[[T], str]) -> list[str]:
    """Start all calls together; return "ok:<value>" or the domain error code."""
    barrier = Barrier(len(calls))

    def run(arg: T) -> str:
        barrier.wait()
        try:
            return "ok:" + fn(arg)
        except DomainError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return list(pool.map(run, calls))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", required=True, help="postgresql+psycopg://.../NAME_test"
    )
    parser.add_argument("--restore-url", required=True, help="second empty *_test DB")
    args = parser.parse_args()
    for url in (args.url, args.restore_url):
        parsed = make_url(url)
        if parsed.drivername != "postgresql+psycopg" or "test" not in (
            parsed.database or ""
        ):
            parser.error("Use postgresql+psycopg URLs naming disposable *test* DBs.")
    results: dict[str, object] = {"started_at": NOW.isoformat()}
    with migration_configuration(args.url) as config:
        command.upgrade(config, "head")
        command.downgrade(config, "0006")
        command.upgrade(config, "head")
    engine = make_engine(args.url)
    with engine.connect() as db:
        results["server_version"] = db.execute(text("SHOW server_version")).scalar()
        results["schema_head"] = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    results["migrations"] = "head -> 0006 -> head passed"
    with directory_snapshot() as path:
        DirectoryImporter(engine, lambda: NOW).import_snapshot(path)
    service = WaitService(engine, lambda: NOW)

    # 1. Eight concurrent identical retries from one device: one row, one id.
    same = identity("retry")
    ids = race(
        [0] * 8, lambda _: service.submit(same, CUVIER, estimate(10, "retry-key-1")).id
    )
    with Session(engine) as db:
        rows = db.scalar(
            select(func.count()).where(WaitReport.idempotency_key == "retry-key-1")
        )
    assert len(set(ids)) == 1 and ids[0].startswith("ok:") and rows == 1, ids
    results["concurrent_identical_retries"] = {"calls": 8, "rows": rows}

    # 2. Eight concurrent different keys from one device: advisory lock + 2-min
    #    throttle allow exactly one.
    racer = identity("throttle")
    outcomes = race(
        list(range(8)),
        lambda i: service.submit(racer, "paris:r175", estimate(5, f"throttle-{i}")).id,
    )
    accepted = sum(o.startswith("ok:") for o in outcomes)
    assert accepted == 1 and outcomes.count("contribution_too_soon") == 7, outcomes
    results["concurrent_throttle_race"] = {"calls": 8, "accepted": accepted}

    # 3. Network budget: six devices on one network, cap 2, concurrent.
    burst = [identity(f"burst-{i}", "net-b") for i in range(6)]
    race(
        burst,
        lambda who: service.submit(who, "paris:r889", estimate(120, "burst-key-1")).id,
    )
    state = service.state("paris:r889")
    assert (state.count, state.sources, state.excluded) == (2, 1, 4), state
    results["network_budget"] = {"count": 2, "sources": 1, "excluded": 4}

    # 4. Admin hide version conflict under concurrency: one success, one 409.
    moderation = ModerationService(engine, lambda: NOW)
    report_id = ids[0].removeprefix("ok:")

    def hide(version: int) -> str:
        payload = HideInput(
            rationale="Synthetic conflict check", expected_version=version
        )
        return str(moderation.hide(report_id, payload)["version"])

    hides = race([0, 0], hide)
    assert sorted(hides) == ["moderation_conflict", "ok:1"], hides
    results["admin_version_conflict"] = hides

    # 5. UTC round trip and retention.
    with Session(engine) as db:
        stored = db.get(WaitReport, report_id)
        assert stored is not None and stored.received_at == NOW
        assert stored.received_at.utcoffset() == timedelta(0)
    removed = purge(engine, NOW + timedelta(days=7))
    assert removed["reports"] >= 1, removed
    results["utc_round_trip"] = "passed"
    results["retention_after_7_days"] = removed

    # 6. pg_dump / pg_restore into a second disposable DB; compare row counts.
    service.submit(identity("restore"), CUVIER, estimate(7, "restore-key-1"))
    source, target = make_url(args.url), make_url(args.restore_url)

    def libpq(url: object) -> str:
        return str(url).replace("postgresql+psycopg", "postgresql")

    dump = subprocess.run(
        ["pg_dump", "--format=custom", libpq(source.render_as_string(False))],
        check=True,
        capture_output=True,
    ).stdout
    subprocess.run(
        ["pg_restore", "--no-owner", "--dbname", libpq(target.render_as_string(False))],
        input=dump,
        check=True,
    )
    counts = []
    for url in (args.url, args.restore_url):
        with make_engine(url).connect() as db:
            counts.append(
                [
                    db.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                    for table in ("venues", "wait_reports", "moderation_audits")
                ]
            )
    assert counts[0] == counts[1], counts
    results["dump_restore_counts"] = dict(
        zip(("venues", "wait_reports", "moderation_audits"), counts[1], strict=True)
    )
    results["data"] = "synthetic only"
    print(json.dumps(results, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
