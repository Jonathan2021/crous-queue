from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.app import create_app
from crous_queue.models import WaitReport
from tests.conftest import NOW

HEADERS = {"X-CQ-Request": "1"}


def report(
    client,
    current,
    minutes=10,
    *,
    key=None,
    kind="estimate",
    venue="paris:r177",
    observed=None,
):
    return client.post(
        f"/venues/{venue}/reports",
        headers=HEADERS,
        json={
            "kind": kind,
            "minutes": minutes,
            "observed_at": (observed or current[0]).isoformat(),
            "queue_kind": "student",
            "idempotency_key": key or str(uuid4()),
        },
    )


def test_empty_zero_exact_expiry_latest_conflict_and_completed(application):
    app, current = application
    with TestClient(app) as a, TestClient(app) as b:
        assert a.get("/venues/paris:r177/waits").json()["state"] == "unknown"
        b.get("/venues/paris:r177/waits")
        zero = report(a, current, 0).json()
        state = a.get("/venues/paris:r177/waits").json()
        assert (state["state"], state["minutes"], state["count"]) == ("single", 0, 1)
        assert report(b, current, 40).status_code == 201
        state = a.get("/venues/paris:r177/waits").json()
        assert state["state"] == "conflicting" and state["minutes"] is None
        assert state["range"] == [0, 40]
        assert a.get("/venues/paris:r889/waits").json()["state"] == "unknown"
        current[0] += timedelta(minutes=2)
        assert report(a, current, 30).status_code == 201
        state = a.get("/venues/paris:r177/waits").json()
        assert state["count"] == 2 and state["minutes"] == 35
        current[0] += timedelta(minutes=15)
        assert a.get("/venues/paris:r177/waits").json()["state"] == "unknown"
        assert report(a, current, 12, kind="completed").status_code == 201
        state = a.get("/venues/paris:r177/waits").json()
        assert state["state"] == "unknown" and state["completed"][0]["minutes"] == 12
        assert "device" not in str(zero)


def test_retry_throttle_payload_and_cookie(application, engine):
    app, current = application
    with TestClient(app) as client:
        client.get("/health")
        key = str(uuid4())
        first = report(client, current, key=key)
        assert first.status_code == 201
        assert (
            report(client, current, key=key).json()["report"]["id"]
            == first.json()["report"]["id"]
        )
        assert report(client, current, 20, key=key).status_code == 409
        assert report(client, current, 20).status_code == 429
        current[0] += timedelta(minutes=2)
        for observed in [
            current[0] + timedelta(minutes=2, seconds=1),
            current[0] - timedelta(minutes=60, seconds=1),
        ]:
            assert report(client, current, observed=observed).status_code == 422
        for minutes in [-1, 121, 1.5, True, "10"]:
            assert report(client, current, minutes).status_code == 422
        assert client.post("/venues/paris:r177/reports", json={}).status_code == 403
        assert report(client, current, venue="no:such").status_code == 404
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(WaitReport)) == 1
        client.cookies.set("cq_device", "forged")
        assert report(client, current).status_code == 403


def test_timer_ownership_idempotency_and_restart(application):
    app, current = application
    with TestClient(app) as a, TestClient(app) as b:
        a.get("/health")
        b.get("/health")
        payload = {
            "venue_id": "paris:r177",
            "queue_kind": "student",
            "idempotency_key": str(uuid4()),
        }
        timer = a.post("/timers/start", headers=HEADERS, json=payload).json()
        assert (
            a.post("/timers/start", headers=HEADERS, json=payload).json()["id"]
            == timer["id"]
        )
        current[0] += timedelta(minutes=8)
        assert (
            b.post(
                f"/timers/{timer['id']}/finish", headers=HEADERS, json={}
            ).status_code
            == 404
        )
        finished = a.post(f"/timers/{timer['id']}/finish", headers=HEADERS, json={})
        assert finished.status_code == 201 and finished.json()["report"]["minutes"] == 8
        assert (
            a.post(f"/timers/{timer['id']}/finish", headers=HEADERS, json={}).json()[
                "report"
            ]["id"]
            == finished.json()["report"]["id"]
        )
        cookie = a.cookies.get("cq_device")
    restarted = create_app(
        app.state.settings, engine=app.state.engine, clock=lambda: current[0]
    )
    with TestClient(restarted) as client:
        client.cookies.set("cq_device", cookie)
        state = client.get("/venues/paris:r177/waits").json()
        assert state["state"] == "unknown" and state["completed"][0][
            "source_window_start"
        ] == NOW.isoformat().replace("+00:00", "Z")
        assert client.get("/timers/active").json()["items"] == []


def test_old_observation_cannot_become_fresh_by_resending(application):
    app, current = application
    with TestClient(app) as client:
        client.get("/health")
        assert (
            report(
                client, current, observed=current[0] - timedelta(minutes=15)
            ).status_code
            == 201
        )
        assert client.get("/venues/paris:r177/waits").json()["state"] == "unknown"
