from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine

from crous_queue.services.moderation import ModerationService
from crous_queue.services.pilot_records import Snapshot, store_id
from crous_queue.services.waits import WaitService

PILOT_VENUES = ("paris:r177", "paris:r175")


def pilot_check(
    engine: Engine, clock: Callable[[], datetime], *, environment: str
) -> dict[str, object]:
    now = clock()
    service = WaitService(engine, lambda: now)
    checks = []
    fresh = 0
    for venue in PILOT_VENUES:
        state = service.state(venue)
        fresh += int(state.count > 0)
        checks.append(
            dict(
                venue_id=venue,
                state=state.state,
                report_count=state.count,
                newest_age_seconds=max(0, (now - state.newest_at).total_seconds())
                if state.newest_at
                else None,
            )
        )
    metrics = ModerationService(engine, lambda: now).metrics(venue_ids=PILOT_VENUES)
    return Snapshot.model_validate(
        dict(
            schema_version=2,
            store_id=store_id(engine),
            data_mode="synthetic" if environment in {"demo", "test"} else "real",
            environment=environment,
            checked_at=now.isoformat(),
            fresh_checks=fresh,
            total_checks=len(checks),
            venues=checks,
            returning_devices_7d=metrics["returning_devices_7d"],
        )
    ).model_dump(mode="json")
