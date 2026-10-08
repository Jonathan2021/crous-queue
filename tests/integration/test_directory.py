import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crous_queue.app import create_app
from crous_queue.config import Settings
from crous_queue.models import Coverage, Venue
from crous_queue.services.directory import (
    DirectoryImporter,
    FixtureProvider,
    parse_feed,
    plain_text,
)
from tests.conftest import NOW, ROOT


def test_observed_snapshot_idempotent_search_and_provenance(engine):
    importer = DirectoryImporter(engine, lambda: NOW)
    importer.import_snapshot(ROOT / "fixtures/venues-2026-10-07.json")
    importer.import_snapshot(ROOT / "fixtures/venues-2026-10-07.json")
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
    importer.import_snapshot(ROOT / "fixtures/venues-2026-10-07.json")
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
