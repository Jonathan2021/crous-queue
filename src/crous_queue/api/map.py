"""Public venue coordinates, never user coordinates, on one shared read clock."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from crous_queue.api.pages import TYPE_LABELS, templates
from crous_queue.contracts import VenueType
from crous_queue.models import Venue, WaitReport
from crous_queue.services.directory import REGIONS, venue_query
from crous_queue.services.hours import hours_state
from crous_queue.services.waits import aggregate, queues_for

router = APIRouter()


@router.get("/map")
def map_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="map.html",
        context=dict(
            environment=request.app.state.settings.environment,
            regions=REGIONS,
            types=TYPE_LABELS,
            map_tiles=request.app.state.settings.map_tiles,
        ),
    )


@router.get("/map-data")
def map_data(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    region: Annotated[str, Query(max_length=40)] = "",
    type: VenueType = "restaurant",
) -> dict[str, object]:
    now = request.app.state.clock()
    with Session(request.app.state.engine) as db:
        venues = db.scalars(
            venue_query(q, region, type).order_by(Venue.name, Venue.id).limit(2001)
        ).all()
        by_venue: dict[str, list[WaitReport]] = {}
        reports = db.scalars(
            select(WaitReport).where(
                WaitReport.received_at > now - timedelta(minutes=120)
            )
        ).all()
        for report in reports:
            by_venue.setdefault(report.venue_id, []).append(report)
        return dict(
            items=[
                dict(
                    id=v.id,
                    name=v.name,
                    venue_type=TYPE_LABELS[v.venue_type],
                    region=v.region,
                    has_coordinates=(v.latitude, v.longitude) != (0, 0),
                    latitude=v.latitude,
                    longitude=v.longitude,
                    queue_kind=queues_for(v)[0],
                    waits=aggregate(
                        [
                            r
                            for r in by_venue.get(v.id, [])
                            if r.queue_kind == queues_for(v)[0]
                        ],
                        now,
                    ),
                    hours=hours_state(db, v, now),
                )
                for v in venues[:2000]
            ],
            truncated=len(venues) > 2000,
            server_now=now,
        )
