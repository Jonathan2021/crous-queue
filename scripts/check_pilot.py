"""Append aggregate fixed-check evidence to ignored local storage, never fixtures."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from crous_queue.config import load_settings
from crous_queue.db import make_engine
from crous_queue.services.pilot import pilot_check
from crous_queue.services.pilot_records import (
    PilotPlan,
    ScheduledCheck,
    Snapshot,
    append_record,
    validate_check,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--slot-id")
    args = parser.parse_args()
    settings = load_settings()
    args.output = args.output or Path(
        f".local/{settings.environment}-pilot-checks-v2.jsonl"
    )
    if not args.output.resolve().is_relative_to(Path(".local").resolve()):
        parser.error(
            "Pilot observations must remain in ignored .local/ storage, never fixtures or Git."
        )
    result = pilot_check(
        make_engine(settings.database_url),
        lambda: datetime.now(UTC),
        environment=settings.environment,
        network_cap=settings.network_estimate_cap,
    )
    try:
        record: Snapshot | ScheduledCheck = Snapshot.model_validate(result)
        if args.plan or args.slot_id:
            if not args.plan or not args.slot_id:
                parser.error("Scheduled checks require both --plan and --slot-id.")
            plan = PilotPlan.model_validate_json(args.plan.read_text())
            record = ScheduledCheck(
                pilot_id=plan.pilot_id, slot_id=args.slot_id, snapshot=record
            )
            validate_check(plan, record)
        append_record(args.output, record)
    except (ValueError, ValidationError):
        parser.error(
            "Pilot/slot/environment/store conflict or invalid legacy file. Preserve the original; use a matching plan and a separate new record file."
        )
    print(record.model_dump_json())


if __name__ == "__main__":
    main()
