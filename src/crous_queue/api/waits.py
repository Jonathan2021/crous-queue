from fastapi import APIRouter, Request

from crous_queue.contracts import EmptyInput, QueueKind, ReportInput, TimerInput
from crous_queue.security import Identity
from crous_queue.services.waits import WaitService

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
