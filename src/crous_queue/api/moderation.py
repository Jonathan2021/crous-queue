import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import Response

from crous_queue.api.pages import templates
from crous_queue.api.waits import identity
from crous_queue.contracts import (
    CommentModerationInput,
    FlagInput,
    HideInput,
    NetworkHideInput,
)
from crous_queue.services.moderation import ModerationService

router = APIRouter()


def require_admin(request: Request) -> None:
    expected = request.app.state.settings.admin_token
    presented = request.headers.get("authorization", "")
    if not expected or not hmac.compare_digest(presented, "Bearer " + expected):
        raise HTTPException(
            401,
            detail={
                "code": "admin_auth_required",
                "message": "Identifiant administrateur requis.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def service(request: Request) -> ModerationService:
    return ModerationService(
        request.app.state.engine,
        request.app.state.clock,
        network_limit=request.app.state.settings.network_hourly_limit,
    )


@router.post("/reports/{report_id}/flags", status_code=201)
def flag(report_id: str, payload: FlagInput, request: Request) -> dict[str, str]:
    return service(request).flag(identity(request), report_id, payload)


@router.get("/admin/reports", dependencies=[Depends(require_admin)])
def reports(
    request: Request, offset: Annotated[int, Query(ge=0)] = 0
) -> dict[str, object]:
    return service(request).list_reports(offset)


@router.post("/admin/reports/{report_id}/hide", dependencies=[Depends(require_admin)])
def hide(report_id: str, payload: HideInput, request: Request) -> dict[str, object]:
    return service(request).hide(report_id, payload)


@router.post(
    "/admin/reports/{report_id}/hide-network", dependencies=[Depends(require_admin)]
)
def hide_network(
    report_id: str, payload: NetworkHideInput, request: Request
) -> dict[str, int]:
    return service(request).hide_network(report_id, payload)


@router.get("/admin/metrics", dependencies=[Depends(require_admin)])
def metrics(request: Request) -> dict[str, object]:
    return service(request).metrics()


@router.get("/admin")
def admin_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"environment": request.app.state.settings.environment},
    )


@router.get("/privacy")
def privacy(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"environment": request.app.state.settings.environment},
    )


@router.post(
    "/admin/reports/{report_id}/comment", dependencies=[Depends(require_admin)]
)
def moderate_comment(
    report_id: str, payload: CommentModerationInput, request: Request
) -> dict[str, object]:
    return service(request).moderate_comment(report_id, payload)
