import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from crous_queue import __version__
from crous_queue.api.moderation import router as moderation_router
from crous_queue.api.pages import router as pages_router
from crous_queue.api.waits import router as waits_router
from crous_queue.config import Settings, load_settings
from crous_queue.contracts import VenueType, VenueView
from crous_queue.db import make_engine
from crous_queue.models import Venue
from crous_queue.security import COOKIE, coarse_ip_hash, device_session
from crous_queue.services.directory import folded
from crous_queue.services.maintenance import purge
from crous_queue.services.waits import DomainError


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async def retention() -> None:
            while True:
                try:
                    await asyncio.to_thread(purge, engine, app.state.clock())
                except SQLAlchemyError:
                    logging.getLogger("crous_queue.operations").error(
                        "retention_failed: run migrations and retention command; no SQL parameters logged"
                    )
                await asyncio.sleep(60)

        task = asyncio.create_task(retention())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Crous Queue", version=__version__, lifespan=lifespan)
    app.state.settings, app.state.engine = settings, engine
    app.state.clock = clock or (lambda: datetime.now(UTC))

    app.include_router(waits_router)
    app.include_router(pages_router)
    app.include_router(moderation_router)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(
        request: Request, error: SQLAlchemyError
    ) -> JSONResponse:
        logging.getLogger("crous_queue.operations").error(
            "database_unavailable: check migrations/storage; parameters redacted"
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "database_unavailable",
                    "message": "Service indisponible. Vérifiez les migrations et réessayez.",
                }
            },
        )

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status,
            content={"detail": {"code": error.code, "message": error.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_payload(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        # Never echo rejected values, cookie tokens, location or free text.
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "invalid_payload",
                    "message": "Valeurs invalides. Minutes entières 0–120, date avec fuseau horaire, champs autorisés uniquement.",
                }
            },
        )

    @app.middleware("http")
    async def session_and_safety(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        device, cookie, valid = device_session(settings, request.cookies.get(COOKIE))
        request.state.device_hash = device
        request.state.ip_hash = coarse_ip_hash(
            settings,
            request.client.host if request.client else "",
            app.state.clock().date().isoformat(),
        )
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if (
                not valid
                or request.headers.get("X-CQ-Request") != "1"
                or request.headers.get("origin", settings.origin) != settings.origin
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "session_required",
                            "message": "Rechargez la page avant de contribuer.",
                        }
                    },
                )
            if (
                request.headers.get("content-type", "").split(";")[0]
                != "application/json"
            ):
                return JSONResponse(
                    status_code=415,
                    content={
                        "detail": {
                            "code": "json_required",
                            "message": "Une contribution JSON est requise.",
                        }
                    },
                )
            size = 0
            parts = []
            async for part in request.stream():
                size += len(part)
                if size > 4096:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": {
                                "code": "payload_too_large",
                                "message": "Contribution trop volumineuse (4 Ko maximum).",
                            }
                        },
                    )
                parts.append(part)
            request._body = b"".join(parts)
        request_id = str(uuid4())
        response = await call_next(request)
        route = request.scope.get("route")
        logging.getLogger("crous_queue.requests").info(
            json.dumps(
                dict(
                    event="request",
                    request_id=request_id,
                    method=request.method,
                    route=getattr(route, "path", "unmatched"),
                    status=response.status_code,
                ),
                sort_keys=True,
            )
        )
        response.headers["X-Request-ID"] = request_id
        if not valid:
            response.set_cookie(
                COOKIE,
                cookie,
                max_age=30 * 24 * 3600,
                httponly=True,
                secure=settings.secure_cookies,
                samesite="lax",
            )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.get("/venues")
    def venues(
        q: Annotated[str, Query(max_length=100)] = "",
        region: Annotated[str, Query(max_length=40)] = "",
        type: VenueType = "restaurant",
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        with Session(engine) as db:
            query = select(Venue)
            if q:
                query = query.where(
                    Venue.search_text.contains(folded(q), autoescape=True)
                )
            if region:
                query = query.where(Venue.region == region)
            if type != "all":
                query = query.where(Venue.venue_type == type)
            items = db.scalars(
                query.order_by(Venue.name, Venue.id).offset(offset).limit(51)
            ).all()
            return {
                "items": [VenueView.model_validate(item) for item in items[:50]],
                "next_offset": offset + 50 if len(items) > 50 else None,
            }

    @app.get("/venues/{venue_id}", response_model=VenueView)
    def venue(venue_id: str) -> VenueView:
        with Session(engine) as db:
            value = db.get(Venue, venue_id)
            if value is None:
                raise HTTPException(
                    404,
                    detail={
                        "code": "venue_not_found",
                        "message": "Restaurant introuvable.",
                    },
                )
            return VenueView.model_validate(value)

    return app
