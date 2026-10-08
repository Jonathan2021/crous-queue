from datetime import timedelta

from fastapi.testclient import TestClient


def test_map_data_same_waits_identity_no_location_input(application):
    app, clock = application
    with TestClient(app) as client:
        client.get("/")
        result = client.get("/map-data?q=Cuvier&type=all")
        assert result.status_code == 200
        rows = result.json()["items"]
        assert {r["id"] for r in rows} == {"paris:r177", "paris:r889"}
        assert len({(r["latitude"], r["longitude"]) for r in rows}) == 1
        assert all(r["waits"]["state"] == "unknown" for r in rows)
        payload = dict(
            kind="estimate",
            minutes=0,
            queue_kind="student",
            observed_at=clock[0].isoformat(),
            idempotency_key="map-zero-001",
        )
        response = client.post(
            "/venues/paris:r177/reports", json=payload, headers={"X-CQ-Request": "1"}
        )
        assert response.status_code == 201
        row = next(
            r
            for r in client.get("/map-data?q=Cuvier&type=all").json()["items"]
            if r["id"] == "paris:r177"
        )
        assert row["waits"] == client.get("/venues/paris:r177/waits").json()
        assert row["queue_kind"] == "student" and row["waits"]["minutes"] == 0
        clock[0] += timedelta(minutes=15)
        assert all(
            r["waits"]["state"] == "unknown"
            for r in client.get("/map-data?q=Cuvier&type=all").json()["items"]
        )
        assert client.get("/map-data?q=doesnotexist").json()["items"] == []
        assert client.get("/map").status_code == 200
