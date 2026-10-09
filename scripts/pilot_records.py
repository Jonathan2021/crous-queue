"""Prepare blank local records, pin a five-day plan, or summarize approved records."""

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from uuid import uuid4

from crous_queue.config import load_settings
from crous_queue.db import make_engine
from crous_queue.services.pilot_records import (
    TIMES,
    VENUES,
    FrictionObservation,
    PilotPlan,
    ScheduledCheck,
    data_mode,
    store_id,
    summarize,
)


def local_path(value: str) -> Path:
    path = Path(value)
    if not path.resolve().is_relative_to(Path(".local").resolve()):
        raise argparse.ArgumentTypeError(
            "Records must stay in ignored .local/ storage."
        )
    return path


def prepare_blanks(folder: Path) -> None:
    # Exclusive creation: never reset filled operator records.
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "fixed-checks.csv").open("x", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(
            [
                "day",
                "date_to_assign",
                "slot_id",
                "local_time_Europe_Paris",
                "venue_id",
                "queue_category_to_confirm_R011",
                "actual_checked_at",
                "state",
                "report_count",
                "newest_age_seconds",
                "missed_reason_enum",
            ]
        )
        for day in range(1, 6):
            for local in TIMES:
                for venue in VENUES:
                    writer.writerow(
                        [
                            day,
                            "",
                            f"d{day}-{local.replace(':', '')}",
                            local,
                            venue,
                            "student_declared_not_field_verified",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )
    with (folder / "contribution-friction.csv").open("x", newline="") as out:
        csv.writer(out).writerow(
            [
                "day",
                "venue_id",
                "outcome_completed_abandoned_error",
                "duration_seconds_if_measured",
                "interactions_if_counted",
            ]
        )
    with (folder / "README.txt").open("x") as out:
        out.write(
            "Blank preparation only. Dates/access/queues remain unconfirmed via R011. Missing rows stay missing; never fill 0 or unknown for an unperformed check. No real intake is authorized. Keep consented observations private and delete within 7 days.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    blank = commands.add_parser("prepare")
    blank.add_argument("--output", type=local_path, required=True)
    plan = commands.add_parser("plan")
    plan.add_argument(
        "--days",
        required=True,
        help="Five comma-separated ISO weekdays, after private access is approved",
    )
    plan.add_argument("--output", type=local_path, required=True)
    report = commands.add_parser("summarize")
    report.add_argument("--plan", type=local_path, required=True)
    report.add_argument("--records", type=local_path, required=True)
    report.add_argument("--friction", type=local_path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare_blanks(args.output)
            print(
                "40 blank venue checks and separate friction header prepared; no visits or data intake approved."
            )
        elif args.command == "plan":
            settings = load_settings()
            engine = make_engine(settings.database_url)
            value = PilotPlan(
                environment=settings.environment,
                data_mode=data_mode(settings.environment),
                store_id=store_id(engine),
                pilot_id="pilot_" + uuid4().hex,
                days=[date.fromisoformat(day) for day in args.days.split(",")],
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x") as out:
                out.write(value.model_dump_json(indent=2) + "\n")
            args.output.chmod(0o600)
            print("Plan pinned. This file grants no permission for a real trial.")
        else:
            value = PilotPlan.model_validate_json(args.plan.read_text())
            records = [
                ScheduledCheck.model_validate_json(line)
                for line in args.records.read_text().splitlines()
                if line
            ]
            friction = (
                [
                    FrictionObservation.model_validate_json(line)
                    for line in args.friction.read_text().splitlines()
                    if line
                ]
                if args.friction
                else []
            )
            print(json.dumps(summarize(value, records, friction), ensure_ascii=False))
    except (ValueError, OSError):
        parser.error(
            "Invalid or existing records, mixed provenance, or unavailable file. Preserve originals and use a new matching plan/directory."
        )


if __name__ == "__main__":
    main()
