import json
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from statistics import median
from uuid import uuid4

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from crous_queue.contracts import ReportInput, ReportView, TimerInput, WaitState
from crous_queue.models import RateBucket, Venue, WaitReport, WaitTimer
from crous_queue.security import Identity


class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status, self.code, self.message = status, code, message


def queues_for(venue: Venue) -> list[str]:
    if venue.venue_type == "administrative":
        return ["staff"]
    if venue.id in {"paris:r177", "paris:r175", "paris:r889"}:
        return ["student"]
    return ["unspecified"]


def require_venue(db: Session, venue_id: str, queue: str) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise DomainError(404, "venue_not_found", "Restaurant introuvable.")
    if queue not in queues_for(venue):
        raise DomainError(
            422,
            "queue_not_supported",
            "Choisissez la file indiquée pour cet établissement.",
        )
    return venue


def aggregate(reports: list[WaitReport], now: datetime) -> WaitState:
    latest: dict[str, WaitReport] = {}
    for report in sorted(reports, key=lambda r: (r.received_at, r.id)):
        if report.kind == "estimate":
            latest[report.device_hash] = report
    valid = [
        r
        for r in latest.values()
        if r.visibility == "visible"
        and r.minutes is not None
        and min(r.observed_at, r.received_at) > now - timedelta(minutes=15)
    ]
    valid.sort(key=lambda r: r.received_at, reverse=True)
    completed = [
        ReportView.model_validate(r)
        for r in reports
        if r.kind == "completed"
        and r.visibility == "visible"
        and min(r.observed_at, r.received_at) > now - timedelta(minutes=60)
    ]
    state = WaitState(
        state="unknown",
        server_now=now,
        completed=completed[:10],
        estimates=[ReportView.model_validate(r) for r in valid],
    )
    if valid:
        values = [r.minutes for r in valid if r.minutes is not None]
        conflict = max(values) - min(values) > 15
        state.state = (
            "conflicting" if conflict else "single" if len(valid) == 1 else "recent"
        )
        state.minutes = None if conflict else float(median(values))
        state.count, state.range = len(valid), [min(values), max(values)]
        state.newest_at = max(min(r.observed_at, r.received_at) for r in valid)
        # Earliest contributing expiry forces recomputation when any vote expires.
        state.expires_at = min(
            min(r.observed_at, r.received_at) for r in valid
        ) + timedelta(minutes=15)
    return state


def lock_writes(db: Session, identity: Identity) -> None:
    if db.get_bind().dialect.name == "postgresql":
        for key in sorted([identity.device_hash, identity.ip_hash]):
            lock_id = int.from_bytes(
                sha256(key.encode()).digest()[:8], "big", signed=True
            )
            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})


def rate_limit(db: Session, identity: Identity, now: datetime, action: str) -> None:
    hour = now.replace(minute=0, second=0, microsecond=0)
    for scope, key, maximum in [
        ("device", identity.device_hash, 30),
        ("network", identity.ip_hash, 120),
    ]:
        bucket_key = f"{action}:{scope}:{key}:{hour.isoformat()}"
        bucket = db.get(RateBucket, bucket_key)
        if bucket is None:
            bucket = RateBucket(
                key=bucket_key, count=0, expires_at=hour + timedelta(hours=2)
            )
            db.add(bucket)
        if bucket.count >= maximum:
            raise DomainError(
                429, "rate_limited", "Trop de contributions. Réessayez dans une heure."
            )
        bucket.count += 1


def contribution_limit(db: Session, device: str, venue: str, now: datetime) -> None:
    previous = db.scalar(
        select(WaitReport)
        .where(
            WaitReport.device_hash == device,
            WaitReport.venue_id == venue,
            WaitReport.received_at > now - timedelta(minutes=2),
        )
        .limit(1)
    )
    if previous:
        raise DomainError(
            429,
            "contribution_too_soon",
            "Attendez 2 minutes avant une nouvelle contribution ici.",
        )


class WaitService:
    def __init__(self, engine: Engine, clock: Callable[[], datetime]) -> None:
        self.engine, self.clock = engine, clock

    def state(self, venue_id: str, queue: str | None = None) -> WaitState:
        now = self.clock()
        with Session(self.engine) as db:
            venue = db.get(Venue, venue_id)
            if venue is None:
                raise DomainError(404, "venue_not_found", "Restaurant introuvable.")
            queue = queue or queues_for(venue)[0]
            require_venue(db, venue_id, queue)
            reports = list(
                db.scalars(
                    select(WaitReport)
                    .where(
                        WaitReport.venue_id == venue_id,
                        WaitReport.queue_kind == queue,
                        WaitReport.received_at > now - timedelta(minutes=120),
                    )
                    .order_by(WaitReport.received_at.desc())
                )
            )
            return aggregate(reports, now)

    def submit(
        self, identity: Identity, venue: str, payload: ReportInput
    ) -> ReportView:
        now = self.clock()
        digest = sha256(
            json.dumps(
                {
                    "venue": venue,
                    **payload.model_dump(
                        mode="json",
                        exclude_none=True,
                        exclude={"comment"} if not payload.comment else set(),
                    ),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with Session(self.engine) as db, db.begin():
            lock_writes(db, identity)
            prior = db.scalar(
                select(WaitReport).where(
                    WaitReport.device_hash == identity.device_hash,
                    WaitReport.idempotency_key == payload.idempotency_key,
                )
            )
            if prior:
                if prior.payload_digest != digest:
                    raise DomainError(
                        409,
                        "idempotency_conflict",
                        "Cette clé a déjà servi pour une autre contribution.",
                    )
                return ReportView.model_validate(prior)
            require_venue(db, venue, payload.queue_kind)
            observed = payload.observed_at.astimezone(UTC)
            if (
                not now - timedelta(minutes=60)
                <= observed
                <= now + timedelta(minutes=2)
            ):
                raise DomainError(
                    422,
                    "observation_out_of_range",
                    "Observation autorisée : dernières 60 minutes, au plus 2 minutes dans le futur.",
                )
            contribution_limit(db, identity.device_hash, venue, now)
            rate_limit(db, identity, now, "contribution")
            report = WaitReport(
                id=str(uuid4()),
                venue_id=venue,
                queue_kind=payload.queue_kind,
                kind=payload.kind,
                minutes=payload.minutes,
                grill=payload.grill,
                vegetarian=payload.vegetarian,
                standard=payload.standard,
                seating=payload.seating,
                comment=payload.comment,
                comment_status="pending" if payload.comment else "none",
                observed_at=observed,
                received_at=now,
                source_window_start=None,
                device_hash=identity.device_hash,
                idempotency_key=payload.idempotency_key,
                payload_digest=digest,
                visibility="visible",
            )
            db.add(report)
            db.flush()
            return ReportView.model_validate(report)

    def start(self, identity: Identity, payload: TimerInput) -> dict[str, object]:
        now = self.clock()
        with Session(self.engine) as db, db.begin():
            lock_writes(db, identity)
            prior = db.scalar(
                select(WaitTimer).where(
                    WaitTimer.device_hash == identity.device_hash,
                    WaitTimer.idempotency_key == payload.idempotency_key,
                )
            )
            if prior:
                if (prior.venue_id, prior.queue_kind) != (
                    payload.venue_id,
                    payload.queue_kind,
                ):
                    raise DomainError(
                        409,
                        "idempotency_conflict",
                        "Clé déjà utilisée pour un autre chronomètre.",
                    )
                return self.timer_view(prior)
            require_venue(db, payload.venue_id, payload.queue_kind)
            active = db.scalar(
                select(WaitTimer).where(
                    WaitTimer.device_hash == identity.device_hash,
                    WaitTimer.finished_at.is_(None),
                    WaitTimer.started_at > now - timedelta(minutes=120),
                )
            )
            if active:
                raise DomainError(
                    409, "timer_already_active", "Terminez le chronomètre déjà démarré."
                )
            rate_limit(db, identity, now, "timer_start")
            timer = WaitTimer(
                id=str(uuid4()),
                venue_id=payload.venue_id,
                queue_kind=payload.queue_kind,
                device_hash=identity.device_hash,
                idempotency_key=payload.idempotency_key,
                started_at=now,
                finished_at=None,
                report_id=None,
            )
            db.add(timer)
            db.flush()
            return self.timer_view(timer)

    def finish(self, identity: Identity, timer_id: str) -> ReportView:
        now = self.clock()
        with Session(self.engine) as db, db.begin():
            lock_writes(db, identity)
            timer = db.get(WaitTimer, timer_id)
            if timer is None or timer.device_hash != identity.device_hash:
                raise DomainError(
                    404, "timer_not_found", "Chronomètre introuvable sur cet appareil."
                )
            if timer.report_id:
                prior = db.get(WaitReport, timer.report_id)
                if prior is not None:
                    return ReportView.model_validate(prior)
            if (
                timer.finished_at is not None
                or not 0 <= (now - timer.started_at).total_seconds() <= 7200
            ):
                raise DomainError(
                    422, "timer_expired", "Ce chronomètre a expiré (maximum 2 heures)."
                )
            contribution_limit(db, identity.device_hash, timer.venue_id, now)
            rate_limit(db, identity, now, "contribution")
            report = WaitReport(
                id=str(uuid4()),
                venue_id=timer.venue_id,
                queue_kind=timer.queue_kind,
                kind="completed",
                minutes=math.ceil((now - timer.started_at).total_seconds() / 60),
                observed_at=now,
                received_at=now,
                source_window_start=timer.started_at,
                device_hash=identity.device_hash,
                idempotency_key="timer_" + timer.id,
                payload_digest=sha256(timer.id.encode()).hexdigest(),
                visibility="visible",
            )
            db.add(report)
            db.flush()
            timer.finished_at, timer.report_id = now, report.id
            return ReportView.model_validate(report)

    @staticmethod
    def timer_view(timer: WaitTimer) -> dict[str, object]:
        return dict(
            id=timer.id,
            venue_id=timer.venue_id,
            queue_kind=timer.queue_kind,
            started_at=timer.started_at,
            finished_at=timer.finished_at,
        )

    def active(self, identity: Identity) -> list[dict[str, object]]:
        with Session(self.engine) as db:
            timers = db.scalars(
                select(WaitTimer).where(
                    WaitTimer.device_hash == identity.device_hash,
                    WaitTimer.finished_at.is_(None),
                    WaitTimer.started_at > self.clock() - timedelta(minutes=120),
                )
            )
            return [self.timer_view(t) for t in timers]
