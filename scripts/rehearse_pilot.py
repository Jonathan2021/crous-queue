"""Five synthetic lunch days in disposable stores; never reads the app database."""

import argparse
import json
import tempfile
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.config import Settings
from crous_queue.contracts import ReportInput, TimerInput
from crous_queue.db import make_engine
from crous_queue.models import WaitReport
from crous_queue.security import Identity
from crous_queue.services.demo import seed_demo
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.maintenance import backup_sqlite, restore_sqlite
from crous_queue.services.pilot import pilot_check
from crous_queue.services.pilot_records import (
    FrictionObservation,
    PilotPlan,
    ScheduledCheck,
    Snapshot,
    append_record,
    store_id,
    summarize,
)
from crous_queue.services.waits import WaitService

ROOT = Path(__file__).resolve().parents[1]


def rehearse() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="crous-q06-synthetic-") as temporary:
        folder = Path(temporary)

        def migrate(name: str) -> str:
            url = f"sqlite:///{folder / name}"
            config = Config(str(ROOT / "alembic.ini"))
            config.set_main_option("sqlalchemy.url", url)
            command.upgrade(config, "head")
            DirectoryImporter(
                make_engine(url), lambda: datetime(2026, 10, 12, tzinfo=UTC)
            ).import_snapshot(ROOT / "fixtures/venues-2026-10-07.json")
            return url

        url = migrate("demo-rehearsal.db")
        engine = make_engine(url)
        plan = PilotPlan(
            pilot_id="synthetic-five-lunch-q06",
            environment="demo",
            data_mode="synthetic",
            store_id=store_id(engine),
            days=[date(2026, 10, 12) + timedelta(days=i) for i in range(5)],
        )
        records = []
        current = [next(iter(plan.slots().values()))]
        service = WaitService(engine, lambda: current[0])

        def identity(label: str) -> Identity:
            return Identity(
                sha256(("synthetic-" + label).encode()).hexdigest(),
                sha256(b"synthetic-network").hexdigest(),
            )

        def report(label: str, venue: str, minutes: int, key: str) -> None:
            service.submit(
                identity(label),
                venue,
                ReportInput(
                    kind="estimate",
                    minutes=minutes,
                    observed_at=current[0],
                    queue_kind="student",
                    idempotency_key=key,
                ),
            )

        # Unrelated repeat device must not count as pilot retention.
        for day in range(2):
            current[0] = plan.slots()[f"d{day + 1}-1145"] - timedelta(minutes=10)
            service.submit(
                identity("elsewhere-repeat"),
                "paris:r889",
                ReportInput(
                    kind="estimate",
                    minutes=5,
                    observed_at=current[0],
                    queue_kind="student",
                    idempotency_key=f"elsewhere_day_{day}",
                ),
            )
        for slot, scheduled_at in plan.slots().items():
            if slot == "d3-1215":
                continue  # Deliberately absent: two missing venue checks, never unknown/zero.
            current[0] = scheduled_at
            if slot.endswith("1145"):
                report("pilot-repeat", "paris:r177", 0, slot + "_zero")
            elif slot.endswith("1215"):
                report(slot + "_conflict_a", "paris:r177", 0, slot + "_a")
                report(slot + "_conflict_b", "paris:r177", 40, slot + "_b")
                joined = WaitService(
                    engine, lambda: current[0] - timedelta(minutes=8)
                ).start(
                    identity(slot + "_timer"),
                    TimerInput(
                        venue_id="paris:r175",
                        queue_kind="student",
                        idempotency_key=slot + "_timer",
                    ),
                )
                service.finish(identity(slot + "_timer"), str(joined["id"]))
            elif slot.endswith("1245"):
                report(slot + "_new_device", "paris:r175", 5, slot + "_estimate")
            else:
                report("pilot-repeat", "paris:r177", 10, slot + "_old")
                current[0] += timedelta(minutes=2)
                report("pilot-repeat", "paris:r177", 20, slot + "_new")
            record = ScheduledCheck(
                pilot_id=plan.pilot_id,
                slot_id=slot,
                snapshot=Snapshot.model_validate(
                    pilot_check(engine, lambda: current[0], environment="demo")
                ),
            )
            append_record(folder / "checks.jsonl", record)
            records.append(record)
        base = plan.model_dump(exclude={"days"})
        friction = [
            FrictionObservation(
                **base,
                venue_id="paris:r177",
                outcome="completed",
                duration_seconds=8,
                interactions=3,
            ),
            FrictionObservation(
                **base, venue_id="paris:r175", outcome="abandoned", interactions=1
            ),
            FrictionObservation(
                **base, venue_id="paris:r177", outcome="error", duration_seconds=20
            ),
        ]
        summary = summarize(plan, records, friction)
        assert (
            summary["planned_checks"] == 40
            and summary["actual_checks"] == 38
            and summary["missing_checks"] == 2
        )
        assert summary["states"] == dict(unknown=19, single=15, recent=0, conflicting=4)
        assert summary["fresh_over_actual"] == dict(
            numerator=19, denominator=38, rate=0.5
        )
        assert summary["fresh_over_planned"] == dict(
            numerator=19, denominator=40, rate=0.475
        )
        assert summary["distinct_day_device_reuse_7d_max"] == 1
        backup = folder / "demo-backup.db"
        restored = folder / "demo-restored.db"
        backup_sqlite(url, backup, environment="demo")
        restore_sqlite(backup, restored, environment="demo")
        restored_engine = make_engine(f"sqlite:///{restored}")
        assert (
            WaitService(restored_engine, lambda: current[0]).state("paris:r177").minutes
            == 20
        )
        assert (
            WaitService(restored_engine, lambda: current[0] + timedelta(minutes=15))
            .state("paris:r177")
            .state
            == "unknown"
        )
        other = migrate("development-disposable.db")
        rejected = False
        try:
            seed_demo(
                Settings(
                    environment="development",
                    database_url=other,
                    session_secret="a" * 40,
                    ip_secret="b" * 40,
                ),
                ROOT / "fixtures/venues-2026-10-07.json",
                lambda: current[0],
            )
        except ValueError:
            rejected = True
        assert rejected
        with Session(make_engine(other)) as db:
            assert db.scalar(select(func.count()).select_from(WaitReport)) == 0
        engine.dispose()
        restored_engine.dispose()
        return dict(
            kind="synthetic_rehearsal_not_real_usefulness",
            summary=summary,
            checks=[r.model_dump(mode="json") for r in records],
            friction=[f.model_dump(mode="json") for f in friction],
            demo_restore_and_exact_expiry="passed",
            non_demo_seed_refused=True,
            other_store_reports=0,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(
            "Use a new evidence filename; prior rehearsal results are immutable."
        )
    result = rehearse()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        json.dump(result, out, indent=2, ensure_ascii=False)
        out.write("\n")
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
