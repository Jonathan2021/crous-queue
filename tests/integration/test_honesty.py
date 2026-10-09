"""P5 UI honesty: no empty service line, human region labels, dated directory."""

import re
from datetime import timedelta

from fastapi.testclient import TestClient

from crous_queue.services.directory import REGION_LABELS, REGIONS
from tests.integration.test_hours import refresh

RAW_SLUG = re.compile(r">\s*(Orleans\.tours|Nancy\.metz|Reunion|Bfc|Corte)\s*<")


def test_every_region_has_a_human_label_and_no_raw_slug_is_rendered(application):
    app, _ = application
    assert set(REGION_LABELS) == set(REGIONS)
    assert REGION_LABELS["orleans.tours"] == "Orléans-Tours"
    assert REGION_LABELS["reunion"] == "La Réunion"
    with TestClient(app) as client:
        for path in ["/", "/map", "/?region=nancy.metz&type=all"]:
            html = client.get(path).text
            assert not RAW_SLUG.search(html), path
            assert "Orléans-Tours" in html and "Bourgogne-Franche-Comté" in html
        assert "Nancy-Metz" in client.get("/?region=nancy.metz&type=all").text
        # Query values stay the stable slugs.
        assert 'value="orleans.tours"' in client.get("/").text
        assert "Paris</span>" in client.get("/v/paris:r177").text


def test_unknown_hours_render_no_service_line(application):
    app, _ = application
    with TestClient(app) as client:
        for path in ["/v/paris:r177", "/?q=Cuvier&type=all"]:
            html = client.get(path).text
            assert "Service :" not in html, path
            assert "horaire historique" not in html, path
            # One date format in the UI: DD/MM/YYYY, never ISO next to it.
            assert "· 07/10/2026" in html and "· 2026-10-07" not in html, path


def test_stale_and_conflicting_intervals_say_why(application):
    app, clock = application
    refresh(app.state.engine, clock[0])
    with TestClient(app) as client:
        fresh = client.get("/v/paris:r177").text
        assert "Service : 11:30–14:00</p>" in fresh
        clock[0] += timedelta(days=1)
        stale = client.get("/v/paris:r177").text
        assert "Service : 11:30–14:00 (horaire ancien, non vérifié)" in stale
        assert "horaire historique" not in stale


def test_attribution_carries_dataset_date_and_age_notice(application):
    app, clock = application
    with TestClient(app) as client:
        for path in ["/", "/v/paris:r177", "/map", "/privacy"]:
            html = client.get(path).text
            assert "Annuaire CNOUS / CROUS relevé le 07/10/2026" in html, path
            assert "Licence Ouverte" in html
            assert "Annuaire ancien" not in html
        assert "972 lieux relevés le 07/10/2026" in client.get("/").text
        clock[0] += timedelta(days=31)
        home = client.get("/").text
        assert "Annuaire ancien : relevé il y a 31 jours" in home
        assert "Annuaire ancien" in client.get("/v/paris:r177").text


def test_empty_directory_is_not_dated(tmp_path, engine):
    from crous_queue.app import create_app
    from crous_queue.config import Settings

    settings = Settings(
        environment="test",
        database_url=str(engine.url),
        session_secret="x" * 40,
        ip_secret="y" * 40,
    )
    with TestClient(create_app(settings, engine=engine)) as client:
        html = client.get("/").text
        assert "Annuaire non importé" in html and "relevé le" not in html
