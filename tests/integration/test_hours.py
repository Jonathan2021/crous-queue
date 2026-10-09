from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from crous_queue.models import OfficialHours, Venue
from crous_queue.services.hours import (
    FixtureHoursProvider,
    HoursImporter,
    HTTPHoursProvider,
    hours_state,
    parse_schedule,
    timezone_for,
)

NOW = datetime(2026, 10, 8, 10, 0, tzinfo=UTC)
HTML = b"<h1>RU Cuvier</h1><h3>Horaires</h3><p>Du lundi au vendredi de 11h30 a 14h00</p><h3>Adresse</h3><p>Paris</p>"


def refresh(engine, now=NOW, body=HTML):
    return HoursImporter(engine, lambda: now).refresh(
        FixtureHoursProvider({"paris:r177": body}), ["paris:r177"]
    )


def state(engine, now=NOW, venue_id="paris:r177"):
    with Session(engine) as db:
        return hours_state(db, db.get(Venue, venue_id), now)


def test_official_identity_dates_and_failure_recovery(application):
    app, clock = application
    clock[0] = NOW
    engine = app.state.engine
    assert refresh(engine) == {"paris:r177": "good"}
    s = state(engine)
    assert s.today == "open" and s.now == "open"
    assert s.intervals == ["11:30–14:00"] and s.timezone == "Europe/Paris"
    assert s.checked_at == NOW and s.source_timestamp is None
    assert state(engine, venue_id="paris:r889").today == "unknown"
    assert state(engine, NOW.replace(hour=12)).now == "closed"
    assert state(engine, NOW.replace(hour=9)).now == "closed"
    assert state(engine, NOW + timedelta(days=1)).today == "unknown"
    assert state(engine, NOW + timedelta(days=1)).freshness == "stale"
    assert refresh(engine, body=b"<h1>Changed source</h1>") == {"paris:r177": "failed"}
    with Session(engine) as db:
        assert db.get(OfficialHours, "paris:r177").raw_schedule
    assert state(engine).today == "unknown"
    refresh(engine)
    with TestClient(app) as client:
        assert client.get("/venues/paris:r177/hours").json()["today"] == "open"
        for path in ["/?q=Cuvier&type=all", "/v/paris:r177"]:
            html = client.get(path).text
            assert "Ouvert aujourd" in html and "11:30–14:00" in html
            assert "https://www.crous-paris.fr/restaurant/ru-cuvier/" in html
        assert client.get("/venues/paris:r177/waits").json()["state"] == "unknown"


def test_weekend_exceptions_dst_unknown_and_conflict(application):
    app, _ = application
    engine = app.state.engine
    saturday = datetime(2026, 10, 10, 10, tzinfo=UTC)
    refresh(engine, saturday)
    assert state(engine, saturday).today == "closed"
    special = HTML.replace(b"</p><h3>", b". Ferme le 08/10/2026.</p><h3>", 1)
    refresh(engine, body=special)
    assert state(engine).today == "closed"
    assert state(engine).intervals == []
    for instant in [
        datetime(2026, 3, 27, 10, 30, tzinfo=UTC),
        datetime(2026, 3, 30, 9, 30, tzinfo=UTC),
    ]:
        refresh(engine, instant)
        assert state(engine, instant).now == "open"
        assert state(engine, instant - timedelta(seconds=1)).now == "closed"
    assert parse_schedule("010 010 010 010 010 000 000") is None
    assert (
        parse_schedule(
            "Du lundi au vendredi de 11h30 a 14h00. Fermeture exceptionnelle demain"
        )
        is None
    )
    assert parse_schedule("Du lundi au vendredi de 14h a 11h") is None
    with Session(engine) as db, db.begin():
        venue = db.get(Venue, "paris:r177")
        venue.hours = "Du lundi au vendredi de 12h00 a 13h00"
        venue.last_seen_at = NOW
    refresh(engine)
    assert state(engine).freshness == "conflict"
    assert state(engine).today == "unknown"


def test_feed_reuse_and_overseas_timezones(application):
    app, _ = application
    engine = app.state.engine
    with Session(engine) as db, db.begin():
        v = db.get(Venue, "paris:r889")
        v.hours = "Du lundi au vendredi de 08h00 a 17h00"
        v.last_seen_at = NOW
        assert timezone_for(v) == "Europe/Paris"
        v.region = "reunion"
        v.latitude, v.longitude = -20.9, 55.48
        assert timezone_for(v) == "Indian/Reunion"
        v.region = "antilles.guyane"
        v.latitude, v.longitude = 4.9, -52.3
        assert timezone_for(v) == "America/Cayenne"
        v.latitude, v.longitude = 14.6, -61.0
        assert timezone_for(v) == "America/Martinique"
        v.latitude, v.longitude = 16.2, -61.5
        assert timezone_for(v) == "America/Guadeloupe"
    assert state(engine, venue_id="paris:r889").now == "closed"  # 06:00 local
    assert state(engine, NOW.replace(hour=2), "paris:r889").local_date == "2026-10-07"


def test_network_bounds_and_untrusted_content():
    for response in [
        httpx.Response(302, headers={"Location": "http://127.0.0.1/"}),
        httpx.Response(200, content=b"x" * 500001),
    ]:
        provider = HTTPHoursProvider(
            transport=httpx.MockTransport(lambda req, response=response: response)
        )
        with pytest.raises((ValueError, httpx.HTTPError)):
            provider.fetch("paris:r177")
    with pytest.raises(ValueError):
        HTTPHoursProvider().fetch("paris:r889")
    assert (
        parse_schedule("<script>boom()</script>Du lundi au vendredi de 11h30 a 14h00")
        is not None
    )


def test_daily_closure_badge_overrides_weekly_service(application):
    app, _ = application
    body = HTML.replace(
        b"RU Cuvier</h1>", b"RU Cuvier <span>Ferme aujourd'hui</span></h1>"
    )
    refresh(app.state.engine, body=body)
    assert state(app.state.engine).today == "closed"
    assert state(app.state.engine).now == "closed"
    assert state(app.state.engine, NOW + timedelta(days=1)).today == "unknown"
    refresh(app.state.engine)
    assert state(app.state.engine).today == "open"
    schedule = parse_schedule(
        "Du lundi au vendredi de 11h30 a 14h00 et de 18h00 a 20h00"
    )
    assert schedule.weekly["0"] == [("11:30", "14:00"), ("18:00", "20:00")]


def test_official_page_request_and_last_modified_provenance():
    requests = []

    def provider(last_modified):
        headers = {} if last_modified is None else {"Last-Modified": last_modified}

        def respond(request):
            requests.append(request)
            return httpx.Response(200, content=HTML, headers=headers)

        return HTTPHoursProvider(transport=httpx.MockTransport(respond))

    document = provider("Wed, 07 Oct 2026 08:00:00 GMT").fetch("paris:r177")
    assert document.payload == HTML
    assert document.source_timestamp == datetime(2026, 10, 7, 8, tzinfo=UTC)
    assert str(requests[0].url) == "https://www.crous-paris.fr/restaurant/ru-cuvier/"
    assert requests[0].headers["user-agent"] == "CrousQueue/official-hours-local"
    # Naive (-0000), malformed or absent dates are not invented as source times.
    for value in ["Wed, 07 Oct 2026 08:00:00 -0000", "not a date", None]:
        assert provider(value).fetch("paris:r177").source_timestamp is None
