from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.responses import Response

from crous_queue.contracts import VenueType
from crous_queue.models import Coverage, Venue
from crous_queue.services.directory import REGIONS, region_label, venue_query
from crous_queue.services.hours import HoursState, hours_state
from crous_queue.services.waits import queues_for

router = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=ROOT / "templates")
DIRECTORY_STALE_DAYS = 30


def directory_info(db: Session, now: datetime) -> dict[str, object]:
    """Dataset dates for the attribution footer and the age notice.

    The age is measured from the oldest retained regional observation, so a
    partial refresh never makes the whole directory look newer than it is.
    Uses the caller's session: SQLite transactions here are BEGIN IMMEDIATE.
    """
    count, oldest, newest = db.execute(
        select(
            func.count(Venue.id),
            func.min(Venue.last_seen_at),
            func.max(Venue.last_seen_at),
        )
    ).one()
    if not count or oldest is None or newest is None:
        return dict(count=0, dates="", label="non importé", stale=False, notice="")
    age = max(0, (now - oldest).days)
    first, last = oldest.strftime("%d/%m/%Y"), newest.strftime("%d/%m/%Y")
    dates = f"le {first}" if first == last else f"du {first} au {last}"
    stale = age > DIRECTORY_STALE_DAYS
    return dict(
        count=count,
        dates=dates,
        label=f"relevé {dates}",
        age_days=age,
        stale=stale,
        notice=(
            f"Annuaire ancien : relevé il y a {age} jours. Lieux, horaires et accès "
            "ont pu changer ; vérifiez auprès du CROUS."
            if stale
            else ""
        ),
    )


def page_context(request: Request, **values: object) -> dict[str, object]:
    """Common page context for routes that hold no open session."""
    with Session(request.app.state.engine) as db:
        directory = directory_info(db, request.app.state.clock())
    return dict(
        environment=request.app.state.settings.environment,
        directory=directory,
        **values,
    )


def fr_date(value: str) -> str:
    """ISO YYYY-MM-DD as the DD/MM/YYYY used everywhere else in the UI."""
    year, month, day = value.split("-")
    return f"{day}/{month}/{year}"


templates.env.filters["region_label"] = region_label
templates.env.filters["fr_date"] = fr_date
TYPE_LABELS = {
    "restaurant": "Restaurant",
    "cafeteria": "Cafétéria",
    "administrative": "Administratif · accès réservé",
    "other": "Autre lieu",
}


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    region: Annotated[str, Query(max_length=40)] = "",
    type: VenueType = "restaurant",
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    with Session(request.app.state.engine) as db:
        query = venue_query(q, region, type)
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        venues = db.scalars(
            query.order_by(Venue.name, Venue.id).offset(offset).limit(24)
        ).all()
        coverage = db.scalars(select(Coverage)).all()
        return templates.TemplateResponse(
            request=request,
            name="home.html",
            context=dict(
                venues=venues,
                hours={
                    v.id: hours_state(db, v, request.app.state.clock()) for v in venues
                },
                q=q,
                region=region,
                selected_type=type,
                total=total,
                regions=REGIONS,
                types=TYPE_LABELS,
                offset=offset,
                coverage=coverage,
                environment=request.app.state.settings.environment,
                directory=directory_info(db, request.app.state.clock()),
            ),
        )


@router.get("/v/{venue_id}", response_class=HTMLResponse)
def detail(venue_id: str, request: Request) -> Response:
    with Session(request.app.state.engine) as db:
        venue = db.get(Venue, venue_id)
        if venue is None:
            raise HTTPException(404, detail="Restaurant introuvable.")
        coverage = db.get(Coverage, venue.region)
        return templates.TemplateResponse(
            request=request,
            name="venue.html",
            context=dict(
                venue=venue,
                hours=hours_state(db, venue, request.app.state.clock()),
                coverage=coverage,
                queue=queues_for(venue)[0],
                types=TYPE_LABELS,
                environment=request.app.state.settings.environment,
                directory=directory_info(db, request.app.state.clock()),
            ),
        )


@router.get("/offline", response_class=HTMLResponse)
def offline(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="offline.html",
        context=page_context(request),
    )


def worker_source(static_root: Path) -> str:
    digest = sha256()
    files = sorted(path for path in static_root.rglob("*") if path.is_file())
    files += [ROOT / "templates/base.html", ROOT / "templates/offline.html"]
    for path in files:
        digest.update(
            str(
                path.relative_to(static_root)
                if path.is_relative_to(static_root)
                else path.name
            ).encode()
        )
        digest.update(path.read_bytes())
    return (
        (static_root / "sw.js")
        .read_text()
        .replace("__ASSET_REVISION__", digest.hexdigest()[:20])
    )


@router.get("/sw.js")
def worker() -> Response:
    return Response(
        worker_source(ROOT / "static"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@router.get("/venues/{venue_id}/hours", response_model=HoursState)
def official_hours(venue_id: str, request: Request) -> HoursState:
    with Session(request.app.state.engine) as db:
        venue = db.get(Venue, venue_id)
        if venue is None:
            raise HTTPException(404, detail="Restaurant introuvable.")
        return hours_state(db, venue, request.app.state.clock())
