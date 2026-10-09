import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crous_queue.app import create_app
from crous_queue.config import Settings
from crous_queue.models import Coverage, Venue
from crous_queue.services.directory import (
    ALLOWLIST,
    DirectoryImporter,
    FixtureProvider,
    HTTPDirectoryProvider,
    parse_feed,
    plain_text,
    venue_query,
)
from tests.conftest import NOW, ROOT, SNAPSHOT


def test_observed_snapshot_idempotent_search_and_provenance(engine):
    importer = DirectoryImporter(engine, lambda: NOW)
    importer.import_snapshot(SNAPSHOT)
    importer.import_snapshot(SNAPSHOT)
    with Session(engine) as db:
        venues = db.scalars(select(Venue)).all()
        assert len(venues) == 972
        assert len(db.scalars(select(Coverage)).all()) == 26
        for venue_id in ["paris:r177", "paris:r175", "paris:r889", "paris:r1149"]:
            venue = db.get(Venue, venue_id)
            assert venue is not None and venue.license == "fr-lo"
            assert venue.source_url and venue.source_type and venue.last_seen_at
        assert (
            db.get(Venue, "paris:r177").latitude == db.get(Venue, "paris:r889").latitude
        )
        assert db.get(Venue, "paris:r1149").venue_type == "administrative"
    settings = Settings(
        environment="test",
        database_url=str(engine.url),
        session_secret="x" * 40,
        ip_secret="y" * 40,
    )
    with TestClient(create_app(settings, engine=engine, clock=lambda: NOW)) as client:
        result = client.get(
            "/venues", params={"q": "chatelet", "region": "paris"}
        ).json()
        assert result["items"][0]["id"] == "paris:r175"
        assert (
            len(
                client.get("/venues", params={"q": "Cuvier", "type": "all"}).json()[
                    "items"
                ]
            )
            == 2
        )
        assert client.get("/venues/paris:r177").json()["source_name"] == "RU Cuvier"
        assert client.get("/venues/no:such").status_code == 404


def test_failed_malformed_and_missing_feed_retain_last_good(engine):
    importer = DirectoryImporter(engine, lambda: NOW)
    importer.import_snapshot(SNAPSHOT)
    bad = FixtureProvider({"paris": b"<broken", "lyon": b"<root/>"})
    results = importer.refresh(bad, regions=["paris", "lyon"])
    assert results == {"paris": "stale", "lyon": "stale"}
    with Session(engine) as db:
        assert db.get(Venue, "paris:r177") is not None
        assert db.get(Coverage, "paris").status == "stale"
    # Missing from one *valid* refresh is retained and marked unseen, never deleted.
    importer.refresh(
        FixtureProvider({"paris": (ROOT / "fixtures/xml/paris.xml").read_bytes()}),
        regions=["paris"],
    )
    with Session(engine) as db:
        assert db.get(Venue, "paris:r175") is not None
        assert db.get(Venue, "paris:r177").address == "4 place Jussieu"


def test_hostile_xml_text_and_coordinates():
    assert (
        plain_text('<script>alert(1)</script><b>RU</b><img src="https://bad.test">')
        == "RU"
    )
    payload = (ROOT / "fixtures/xml/paris.xml").read_bytes()
    rows = parse_feed("paris", payload)
    assert rows[0].name == "RU Cuvier"
    assert "alert" not in rows[0].hours
    for value in ["NaN", "inf", "91"]:
        with pytest.raises(ValueError):
            parse_feed("paris", payload.replace(b"48.84752", value.encode()))
    with pytest.raises(ValueError):
        parse_feed(
            "paris",
            b'<!DOCTYPE x [<!ENTITY y SYSTEM "file:///etc/passwd">]><root>&y;</root>',
        )
    with pytest.raises(ValueError):
        parse_feed("paris", b"x" * 2_000_001)
    with pytest.raises(ValueError):
        parse_feed("unknown", payload)


def test_catalog_attribute_shape_and_plain_infos():
    rows = parse_feed("paris", (ROOT / "fixtures/xml/attribute-feed.xml").read_bytes())
    assert rows[0].name == "RU Cuvier"
    assert "personnels" in rows[0].access
    assert "11h30" in rows[0].hours
    assert rows[0].address == "4 place Jussieu"


def test_one_search_definition_backs_api_pages_and_map(application):
    app, _ = application
    with Session(app.state.engine) as db:

        def ids(**filters):
            return {v.id for v in db.scalars(venue_query(**filters))}

        assert len(ids()) == 972
        assert "paris:r175" in ids(q="CHÂTELET")  # case and accents are folded
        assert ids(q="Cuvier") == {"paris:r177", "paris:r889"}
        assert ids(q="Cuvier", venue_type="restaurant") == {"paris:r177"}
        assert ids(q="%") == set()  # user text is a literal, never a LIKE pattern
        lyon = ids(region="lyon")
        assert lyon and all(venue_id.startswith("lyon:") for venue_id in lyon)
    with TestClient(app) as client:
        params = {"q": "Cuvier", "type": "all"}
        api = {v["id"] for v in client.get("/venues", params=params).json()["items"]}
        mapped = {
            v["id"] for v in client.get("/map-data", params=params).json()["items"]
        }
        page = client.get("/", params=params).text
        assert api == mapped == {"paris:r177", "paris:r889"}
        assert all(f"/v/{venue_id}" in page for venue_id in api)
        restaurants = client.get("/map-data", params={"q": "Cuvier"}).json()
        assert [v["id"] for v in restaurants["items"]] == ["paris:r177"]


def test_http_feed_provider_is_bounded_allowlisted_and_never_redirected(engine):
    feed = (ROOT / "fixtures/xml/paris.xml").read_bytes()
    seen = []

    def respond(request):
        seen.append(str(request.url))
        if "/feed/paris/" in request.url.path:
            return httpx.Response(200, content=feed)
        if "/feed/lyon/" in request.url.path:
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/"})
        return httpx.Response(200, content=b"x" * 2_000_001)

    provider = HTTPDirectoryProvider(transport=httpx.MockTransport(respond))
    assert provider.fetch("paris") == feed
    with pytest.raises(httpx.HTTPStatusError):
        provider.fetch("lyon")
    with pytest.raises(ValueError, match="2 MB"):
        provider.fetch("nice")
    with pytest.raises(KeyError):
        provider.fetch("not-a-region")
    assert seen == [ALLOWLIST["paris"], ALLOWLIST["lyon"], ALLOWLIST["nice"]]
    importer = DirectoryImporter(engine, lambda: NOW)
    importer.import_snapshot(SNAPSHOT)
    assert importer.refresh(provider, regions=["paris", "lyon", "nice"]) == {
        "paris": "good",
        "lyon": "stale",
        "nice": "stale",
    }
