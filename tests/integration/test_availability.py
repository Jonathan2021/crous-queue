from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.models import WaitReport
from crous_queue.services.maintenance import purge
from tests.conftest import ADMIN, HEADERS


def post(client, clock, **fields):
    payload = dict(
        kind=fields.pop("kind", "availability"),
        queue_kind="student",
        observed_at=clock[0].isoformat(),
        idempotency_key=str(uuid4()),
        **fields,
    )
    return client.post(
        "/venues/paris:r177/reports", json=payload, headers=HEADERS
    ), payload


def state(client):
    return client.get("/venues/paris:r177/availability").json()


def test_dimensions_conflict_recovery_expiry_and_zero(application):
    app, clock = application
    with TestClient(app) as a, TestClient(app) as b:
        a.get("/")
        b.get("/")
        first, payload = post(
            a,
            clock,
            vegetarian="unavailable",
            seating="unavailable",
            comment="Il reste des tables dehors.",
        )
        assert first.status_code == 201
        assert first.json()["report"]["comment_status"] == "pending"
        data = state(a)
        assert data["dimensions"]["vegetarian"]["state"] == "unavailable"
        assert data["dimensions"]["grill"]["state"] == "unknown"
        assert data["comments"] == []
        assert (
            a.post("/venues/paris:r177/reports", json=payload, headers=HEADERS).json()[
                "report"
            ]["id"]
            == first.json()["report"]["id"]
        )
        assert a.get("/venues/paris:r177/waits").json()["state"] == "unknown"
        second, _ = post(b, clock, vegetarian="available", grill="not_offered")
        assert second.status_code == 201
        assert state(a)["dimensions"]["vegetarian"]["state"] == "conflicting"
        assert state(a)["dimensions"]["grill"]["state"] == "not_offered"
        clock[0] += timedelta(minutes=3)
        assert post(a, clock, vegetarian="available")[0].status_code == 201
        assert state(a)["dimensions"]["vegetarian"]["state"] == "available"
        assert state(a)["dimensions"]["seating"]["state"] == "unavailable"
        clock[0] += timedelta(minutes=2)
        assert state(a)["dimensions"]["seating"]["state"] == "unknown"
        assert state(a)["dimensions"]["vegetarian"]["state"] == "available"
        assert (
            post(a, clock, standard="available", minutes=0, kind="estimate")[
                0
            ].status_code
            == 201
        )
        assert a.get("/venues/paris:r177/waits").json()["minutes"] == 0
        clock[0] += timedelta(minutes=10)
        assert state(a)["dimensions"]["standard"]["state"] == "unknown"
        assert a.get("/venues/paris:r177/waits").json()["minutes"] == 0


def test_comment_review_escape_delete_hide_retention(application):
    app, clock = application
    with TestClient(app) as client:
        client.get("/")
        text = "<img src=x onerror=alert(1)> https://unsafe.test contact@example.test"
        report, _ = post(client, clock, grill="unknown", comment=text)
        assert report.status_code == 201
        rid = report.json()["report"]["id"]
        assert text not in client.get("/venues/paris:r177/waits").text
        assert state(client)["comments"] == []
        path = f"/admin/reports/{rid}/comment"
        action = dict(
            action="approve", rationale="Synthetic escaping check", expected_version=0
        )
        assert client.post(path, json=action, headers=HEADERS).status_code == 401
        assert client.post(path, json=action, headers=ADMIN).status_code == 200
        assert state(client)["comments"][0]["text"] == text
        action["action"] = "hide"
        assert client.post(path, json=action, headers=ADMIN).status_code == 409
        action["expected_version"] = 1
        assert client.post(path, json=action, headers=ADMIN).status_code == 200
        assert not state(client)["comments"]
        action.update(action="delete", expected_version=2)
        assert client.post(path, json=action, headers=ADMIN).status_code == 200
        with Session(app.state.engine) as db:
            assert db.get(WaitReport, rid).comment == ""
        action.update(action="approve", expected_version=3)
        assert client.post(path, json=action, headers=ADMIN).status_code == 422
        clock[0] += timedelta(minutes=2)
        report, _ = post(
            client, clock, vegetarian="available", comment="Sans identité."
        )
        rid = report.json()["report"]["id"]
        assert (
            client.post(
                f"/admin/reports/{rid}/hide",
                json=dict(rationale="Synthetic hide check", expected_version=0),
                headers=ADMIN,
            ).status_code
            == 200
        )
        assert state(client)["dimensions"]["vegetarian"]["state"] == "unknown"
        purge(app.state.engine, clock[0] + timedelta(days=7))
        with Session(app.state.engine) as db:
            assert db.scalar(select(func.count()).select_from(WaitReport)) == 0


def test_validation_csrf_rates_and_old_retry(application):
    app, clock = application
    with TestClient(app) as client:
        client.get("/")
        for fields in [
            dict(comment="x" * 281),
            dict(vegetarian="bad"),
            dict(minutes=0),
            dict(),
        ]:
            assert post(client, clock, **fields)[0].status_code == 422
        response, payload = post(client, clock, seating="available")
        assert response.status_code == 201
        assert (
            client.post(
                "/venues/paris:r177/reports",
                json=payload,
                headers={**HEADERS, "Origin": "https://evil.test"},
            ).status_code
            == 403
        )
        assert post(client, clock, vegetarian="unavailable")[0].status_code == 429
        clock[0] += timedelta(minutes=11)
        assert (
            client.post(
                "/venues/paris:r177/reports", json=payload, headers=HEADERS
            ).status_code
            == 201
        )
        assert state(client)["dimensions"]["seating"]["state"] == "unknown"
        with Session(app.state.engine) as db:
            assert db.scalar(select(func.count()).select_from(WaitReport)) == 1


def test_concurrent_availability_retry_and_hidden_latest(application):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from crous_queue.contracts import ReportInput
    from crous_queue.security import Identity
    from crous_queue.services.waits import WaitService

    app, clock = application
    payload = ReportInput(
        kind="availability",
        vegetarian="available",
        observed_at=clock[0],
        queue_kind="student",
        idempotency_key="concurrent-meal-1",
    )
    service = WaitService(app.state.engine, lambda: clock[0])
    identity = Identity("synthetic-device", "synthetic-network")
    barrier = Barrier(2)

    def submit(_):
        barrier.wait()
        return service.submit(identity, "paris:r177", payload).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit, range(2)))
    assert ids[0] == ids[1]
    clock[0] += timedelta(minutes=2)
    next_report = service.submit(
        identity,
        "paris:r177",
        payload.model_copy(
            update={
                "vegetarian": "unknown",
                "observed_at": clock[0],
                "idempotency_key": "concurrent-meal-2",
            }
        ),
    )
    with TestClient(app) as client:
        client.get("/")
        assert state(client)["dimensions"]["vegetarian"]["state"] == "unknown"
        assert state(client)["dimensions"]["vegetarian"]["count"] == 1
        client.post(
            f"/admin/reports/{next_report.id}/hide",
            json=dict(rationale="Hide latest observation", expected_version=0),
            headers=ADMIN,
        )
        assert state(client)["dimensions"]["vegetarian"]["state"] == "unknown"
        assert state(client)["dimensions"]["vegetarian"]["count"] == 0
