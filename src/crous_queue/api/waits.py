from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from crous_queue.contracts import EmptyInput, QueueKind, ReportInput, TimerInput
from crous_queue.models import Venue
from crous_queue.security import Identity
from crous_queue.services.availability import AvailabilityService, AvailabilityState
from crous_queue.services.waits import DomainError, WaitService, queues_for

router = APIRouter()


def service(request: Request) -> WaitService:
    return WaitService(request.app.state.engine, request.app.state.clock)


def identity(request: Request) -> Identity:
    return Identity(request.state.device_hash, request.state.ip_hash)


@router.get("/venues/{venue_id}/waits")
def waits(
    venue_id: str, request: Request, queue_kind: QueueKind | None = None
) -> object:
    return service(request).state(venue_id, queue_kind)


@router.post("/venues/{venue_id}/reports", status_code=201)
def submit(venue_id: str, payload: ReportInput, request: Request) -> dict[str, object]:
    report = service(request).submit(identity(request), venue_id, payload)
    return {
        "report": report,
        "waits": service(request).state(venue_id, payload.queue_kind),
        "availability": AvailabilityService(
            request.app.state.engine, request.app.state.clock
        ).state(venue_id, payload.queue_kind),
    }


@router.post("/timers/start", status_code=201)
def start(payload: TimerInput, request: Request) -> dict[str, object]:
    return service(request).start(identity(request), payload)


@router.post("/timers/{timer_id}/finish", status_code=201)
def finish(timer_id: str, payload: EmptyInput, request: Request) -> dict[str, object]:
    report = service(request).finish(identity(request), timer_id)
    return {
        "report": report,
        "waits": service(request).state(report.venue_id, report.queue_kind),
    }


@router.get("/timers/active")
def active(request: Request) -> dict[str, object]:
    return {"items": service(request).active(identity(request))}


@router.get("/venues/{venue_id}/availability", response_model=AvailabilityState)
def availability(
    venue_id: str, request: Request, queue_kind: QueueKind | None = None
) -> AvailabilityState:
    with Session(request.app.state.engine) as db:
        venue = db.get(Venue, venue_id)
        if venue is None:
            raise DomainError(404, "venue_not_found", "Restaurant introuvable.")
        queue = queue_kind or queues_for(venue)[0]
    return AvailabilityService(request.app.state.engine, request.app.state.clock).state(
        venue_id, queue
    )
