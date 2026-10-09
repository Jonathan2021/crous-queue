from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crous_queue.models import OfficialHours, Venue
from crous_queue.services.hours import timezone_for
from tests.integration.test_hours import HTML, refresh, state


def test_unparseable_refresh_preserves_last_good_and_rejected_provenance(application):
    app, _ = application
    refresh(app.state.engine)
    with Session(app.state.engine) as db:
        old = db.get(OfficialHours, "paris:r177").normalized
    body = HTML.replace(
        b"Du lundi au vendredi de 11h30 a 14h00",
        b"Horaires variables, consulter sur place",
    )
    assert refresh(app.state.engine, body=body) == {"paris:r177": "unknown"}
    with Session(app.state.engine) as db:
        cached = db.get(OfficialHours, "paris:r177")
        assert cached.normalized == old
        assert "variables" in cached.last_attempt_raw
        assert cached.last_attempt_sha256 != cached.payload_sha256
    assert state(app.state.engine).today == "unknown"
    assert state(app.state.engine).intervals == ["11:30–14:00"]


def test_zero_coordinates_and_overseas_missing_coverage(application):
    app, _ = application
    with Session(app.state.engine) as db:
        v = db.get(Venue, "reunion:r1381")
        assert timezone_for(v) is None
        v.latitude, v.longitude = -12.85, 45.12
        assert timezone_for(v) == "Indian/Mayotte"
    with TestClient(app) as client:
        row = client.get("/map-data?q=Dembeni&type=all").json()["items"][0]
        assert row["has_coordinates"] is False


def test_hidden_report_comment_can_be_deleted_but_never_approved(application):
    from tests.conftest import ADMIN
    from tests.integration.test_availability import post

    app, clock = application
    with TestClient(app) as client:
        client.get("/")
        response, _ = post(client, clock, comment="Texte synthétique à effacer.")
        rid = response.json()["report"]["id"]
        assert (
            client.post(
                f"/admin/reports/{rid}/hide",
                json=dict(rationale="Synthetic hidden report", expected_version=0),
                headers=ADMIN,
            ).status_code
            == 200
        )
        action = dict(
            action="approve", rationale="Synthetic delete check", expected_version=1
        )
        path = f"/admin/reports/{rid}/comment"
        assert client.post(path, json=action, headers=ADMIN).status_code == 422
        action["action"] = "delete"
        assert client.post(path, json=action, headers=ADMIN).status_code == 200
        row = client.get("/admin/reports", headers=ADMIN).json()["items"][0]
        assert row["comment"] == ""
        assert row["visibility"] == "hidden"
        assert row["history"][-1]["action"] == "comment_delete"
