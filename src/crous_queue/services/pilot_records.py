"""Fixed five-lunch diagnostics. Aggregate records only, with explicit provenance."""

import fcntl
import json
import os
from collections import Counter
from datetime import UTC, date, datetime, time
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)
from sqlalchemy import Engine

Environment = Literal["development", "demo", "test", "production"]
State = Literal["unknown", "single", "recent", "conflicting"]
VENUES = ("paris:r177", "paris:r175")
TIMES = ("11:45", "12:15", "12:45", "13:15")
PARIS = ZoneInfo("Europe/Paris")


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2] = 2
    environment: Environment
    data_mode: Literal["synthetic", "real"]
    store_id: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def consistent_mode(self) -> "Provenance":
        if self.data_mode != (
            "synthetic" if self.environment in {"demo", "test"} else "real"
        ):
            raise ValueError("Environment and synthetic/real provenance disagree.")
        return self


def store_id(engine: Engine) -> str:
    url = engine.url
    database = (
        str(Path(url.database or "").resolve())
        if engine.dialect.name == "sqlite"
        else url.database
    )
    # Credential-free storage identity; no device identifiers or connection secrets.
    return sha256(
        json.dumps([url.drivername, url.host, url.port, database]).encode()
    ).hexdigest()


class VenueCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    venue_id: Literal["paris:r177", "paris:r175"]
    queue_kind: Literal["student"] = "student"
    state: State
    report_count: int = Field(ge=0)
    newest_age_seconds: float | None = Field(default=None, ge=0, lt=900)

    @model_validator(mode="after")
    def honest_state(self) -> "VenueCheck":
        if (self.state == "unknown") != (self.report_count == 0) or (
            self.state == "unknown"
        ) != (self.newest_age_seconds is None):
            raise ValueError(
                "Unknown cannot stand in for a fresh zero-minute estimate."
            )
        return self


class Snapshot(Provenance):
    checked_at: AwareDatetime
    venues: list[VenueCheck] = Field(min_length=2, max_length=2)
    returning_devices_7d: int = Field(ge=0)
    fresh_checks: int = Field(ge=0, le=2)
    total_checks: Literal[2] = 2

    @model_validator(mode="after")
    def selected_sites(self) -> "Snapshot":
        if {v.venue_id for v in self.venues} != set(VENUES) or self.fresh_checks != sum(
            v.report_count > 0 for v in self.venues
        ):
            raise ValueError(
                "Each snapshot must check both distinct selected sites exactly once."
            )
        return self


class PilotPlan(Provenance):
    pilot_id: str = Field(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    days: list[date] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def five_days(self) -> "PilotPlan":
        if self.days != sorted(set(self.days)) or any(
            d.weekday() > 4 for d in self.days
        ):
            raise ValueError(
                "Choose five distinct ordered weekdays; this does not approve a real visit."
            )
        return self

    def slots(self) -> dict[str, datetime]:
        return {
            f"d{index}-{local.replace(':', '')}": datetime.combine(
                day, time.fromisoformat(local), PARIS
            ).astimezone(UTC)
            for index, day in enumerate(self.days, 1)
            for local in TIMES
        }


class ScheduledCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pilot_id: str
    slot_id: str
    snapshot: Snapshot


class FrictionObservation(Provenance):
    pilot_id: str
    venue_id: Literal["paris:r177", "paris:r175"]
    outcome: Literal["completed", "abandoned", "error"]
    duration_seconds: float | None = Field(default=None, ge=0, le=3600)
    interactions: int | None = Field(default=None, ge=0, le=100)


def provenance(value: Provenance) -> tuple[str, str, str]:
    return value.environment, value.data_mode, value.store_id


def validate_check(plan: PilotPlan, check: ScheduledCheck) -> None:
    slots = plan.slots()
    if (
        check.pilot_id != plan.pilot_id
        or provenance(check.snapshot) != provenance(plan)
        or check.slot_id not in slots
    ):
        raise ValueError(
            "Pilot/slot/store provenance mismatch; never merge synthetic and real records."
        )
    if (
        check.snapshot.checked_at.astimezone(PARIS).date()
        != slots[check.slot_id].astimezone(PARIS).date()
    ):
        raise ValueError(
            "Observation belongs to another lunch day; keep it outside this fixed check."
        )


def append_record(path: Path, record: Snapshot | ScheduledCheck) -> None:
    """Preserve existing bytes on conflict, serialize concurrent local appenders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_APPEND, 0o600)
    current = record.snapshot if isinstance(record, ScheduledCheck) else record
    pilot = record.pilot_id if isinstance(record, ScheduledCheck) else None
    with os.fdopen(fd, "a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        if os.fstat(stream.fileno()).st_size > 2_000_000:
            raise ValueError(
                "Pilot log exceeds 2 MB; preserve it and start a new reviewed record file."
            )
        stream.seek(0)
        for line in stream:
            try:
                value = json.loads(line)
                previous: Snapshot | ScheduledCheck = (
                    ScheduledCheck.model_validate(value)
                    if "snapshot" in value
                    else Snapshot.model_validate(value)
                )
            except (ValueError, ValidationError):
                raise ValueError(
                    "Legacy or invalid pilot records; preserve this file and choose a new file."
                ) from None
            previous_snapshot = (
                previous.snapshot if isinstance(previous, ScheduledCheck) else previous
            )
            previous_pilot = (
                previous.pilot_id if isinstance(previous, ScheduledCheck) else None
            )
            if (
                provenance(previous_snapshot) != provenance(current)
                or previous_pilot != pilot
            ):
                raise ValueError(
                    "Pilot environment/store mismatch; use a separate record file."
                )
            if (
                isinstance(previous, ScheduledCheck)
                and isinstance(record, ScheduledCheck)
                and previous.slot_id == record.slot_id
            ):
                if previous == record:
                    return
                raise ValueError(
                    "Fixed check already recorded; retain the original and review corrections separately."
                )
        stream.write(record.model_dump_json() + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def summarize(
    plan: PilotPlan, records: list[ScheduledCheck], friction: list[FrictionObservation]
) -> dict[str, object]:
    slots = plan.slots()
    seen = set()
    counts: Counter[str] = Counter()
    fresh = 0
    contributions = 0
    reuse = 0
    late = 0
    for record in records:
        validate_check(plan, record)
        if record.slot_id in seen:
            raise ValueError(
                "Duplicate fixed slot: do not count an extra observation or silently replace it."
            )
        seen.add(record.slot_id)
        late += int(
            abs((record.snapshot.checked_at - slots[record.slot_id]).total_seconds())
            > 600
        )
        reuse = max(reuse, record.snapshot.returning_devices_7d)
        for venue in record.snapshot.venues:
            counts[venue.state] += 1
            fresh += int(venue.report_count > 0)
            contributions += venue.report_count
    for observation in friction:
        if observation.pilot_id != plan.pilot_id or provenance(
            observation
        ) != provenance(plan):
            raise ValueError(
                "Friction provenance mismatch; keep separate trials separate."
            )
    actual = len(records) * 2
    planned = len(slots) * 2
    durations = [f.duration_seconds for f in friction if f.duration_seconds is not None]
    interactions = [f.interactions for f in friction if f.interactions is not None]
    return dict(
        schema_version=2,
        pilot_id=plan.pilot_id,
        environment=plan.environment,
        data_mode=plan.data_mode,
        planned_checks=planned,
        actual_checks=actual,
        missing_checks=planned - actual,
        missing_slots=sorted(set(slots) - seen),
        late_slots=late,
        states={
            key: counts[key] for key in ["unknown", "single", "recent", "conflicting"]
        },
        fresh_estimate_contributions=contributions,
        fresh_over_actual=dict(
            numerator=fresh, denominator=actual, rate=fresh / actual if actual else None
        ),
        fresh_over_planned=dict(
            numerator=fresh, denominator=planned, rate=fresh / planned
        ),
        distinct_day_device_reuse_7d_max=reuse,
        friction=dict(
            recorded_attempts=len(friction),
            outcomes=dict(Counter(f.outcome for f in friction)),
            timed_attempts=len(durations),
            interaction_counted_attempts=len(interactions),
            median_seconds=median(durations) if durations else None,
            median_interactions=median(interactions) if interactions else None,
        ),
    )
