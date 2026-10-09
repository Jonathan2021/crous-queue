"""Independent expiring observations, not inventory or seat guarantees."""

from collections.abc import Callable
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from crous_queue.models import WaitReport
from crous_queue.services.waits import (
    DEFAULT_NETWORK_CAP,
    network_budget,
    require_venue,
    source_key,
)

EXPIRY = {"grill": 10, "vegetarian": 10, "standard": 10, "seating": 5}


class Observation(BaseModel):
    id: str
    value: str
    observed_at: datetime
    expires_at: datetime


class DimensionState(BaseModel):
    state: str = "unknown"
    count: int = 0
    newest_at: datetime | None = None
    expires_at: datetime | None = None
    observations: list[Observation] = Field(default_factory=list)


class PublicComment(BaseModel):
    id: str
    text: str
    observed_at: datetime
    expires_at: datetime


class AvailabilityState(BaseModel):
    dimensions: dict[str, DimensionState]
    comments: list[PublicComment]
    server_now: datetime


def effective(report: WaitReport) -> datetime:
    return min(report.observed_at, report.received_at)


def dimension(
    reports: list[WaitReport],
    name: str,
    now: datetime,
    *,
    network_cap: int = DEFAULT_NETWORK_CAP,
) -> DimensionState:
    latest: dict[str, WaitReport] = {}
    for report in sorted(reports, key=lambda r: (effective(r), r.received_at, r.id)):
        if getattr(report, name) is not None:
            latest[report.device_hash] = report
    fresh = sorted(
        (
            r
            for r in latest.values()
            if r.visibility == "visible"
            and effective(r) > now - timedelta(minutes=EXPIRY[name])
        ),
        key=lambda r: (effective(r), r.received_at, r.id),
        reverse=True,
    )
    # Same cookie-churn budget as waits: at most network_cap per network.
    counted, _ = network_budget(fresh, network_cap, source_key)
    observations = [
        Observation(
            id=r.id,
            value=getattr(r, name),
            observed_at=effective(r),
            expires_at=effective(r) + timedelta(minutes=EXPIRY[name]),
        )
        for r in counted
    ]
    if not observations:
        return DimensionState()
    newest = max(o.observed_at for o in observations)
    cohort = [o for o in observations if o.observed_at >= newest - timedelta(minutes=2)]
    values = {o.value for o in cohort}
    return DimensionState(
        state=next(iter(values)) if len(values) == 1 else "conflicting",
        count=len(cohort),
        newest_at=newest,
        expires_at=min(o.expires_at for o in cohort),
        observations=observations,
    )


class AvailabilityService:
    def __init__(
        self,
        engine: Engine,
        clock: Callable[[], datetime],
        *,
        network_cap: int = DEFAULT_NETWORK_CAP,
    ) -> None:
        self.engine, self.clock, self.network_cap = engine, clock, network_cap

    def state(self, venue: str, queue: str) -> AvailabilityState:
        now = self.clock()
        with Session(self.engine) as db:
            require_venue(db, venue, queue)
            reports = list(
                db.scalars(
                    select(WaitReport).where(
                        WaitReport.venue_id == venue,
                        WaitReport.queue_kind == queue,
                        WaitReport.received_at > now - timedelta(minutes=120),
                    )
                ).all()
            )
            comments = [
                PublicComment(
                    id=r.id,
                    text=r.comment,
                    observed_at=effective(r),
                    expires_at=effective(r) + timedelta(minutes=60),
                )
                for r in sorted(reports, key=effective, reverse=True)
                if r.visibility == "visible"
                and r.comment_status == "approved"
                and r.comment
                and effective(r) > now - timedelta(minutes=60)
            ]
            return AvailabilityState(
                dimensions={
                    name: dimension(reports, name, now, network_cap=self.network_cap)
                    for name in EXPIRY
                },
                comments=comments[:20],
                server_now=now,
            )
