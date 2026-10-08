import re
from datetime import UTC, datetime
from uuid import uuid4

from playwright.sync_api import expect
from sqlalchemy.orm import Session

from crous_queue.models import WaitReport


def seed(engine, venue, minutes, queue="student"):
    now = datetime.now(UTC)
    with Session(engine) as db, db.begin():
        db.add(
            WaitReport(
                id=str(uuid4()),
                venue_id=venue,
                queue_kind=queue,
                kind="estimate",
                minutes=minutes,
                observed_at=now,
                received_at=now,
                device_hash=str(uuid4()),
                idempotency_key=str(uuid4()),
                payload_digest="synthetic",
                visibility="visible",
            )
        )


def test_map_parity_coincident_location_denial_expiry_failed_tiles(
    browser_page, engine
):
    page, context, origin = browser_page
    context.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
    page.add_init_script(
        "navigator.geolocation.getCurrentPosition = (_success, error) => error({code:1});"
    )
    seed(engine, "paris:r177", 0)
    seed(engine, "paris:r175", 40)
    page.clock.install()
    failures = []
    page.on("pageerror", lambda error: failures.append(str(error)))
    page.goto(origin + "/map?region=paris&type=all")
    expect(
        page.locator('#map-list [data-map-venue="paris:r177"] .map-wait')
    ).to_have_text("0 min")
    expect(
        page.locator('#map-list [data-map-venue="paris:r177"] .map-wait')
    ).to_have_class("map-wait crowd-zero")
    expect(
        page.locator('#map-list [data-map-venue="paris:r175"] .map-wait')
    ).to_have_class("map-wait crowd-busy")
    expect(page.locator("#tile-status")).to_contain_text("indisponible")
    busy = page.locator('.crowd-marker[data-band="busy"]')
    expect(busy).to_have_count(1)
    expect(busy).to_have_text("40")
    page.locator("#venue-map").screenshot(
        path=f"docs/evidence/q09-20261008-b72e/map-paris-{uuid4().hex[:8]}.png"
    )
    page.get_by_role("button", name="Autour de moi").click()
    expect(page.locator("#location-status")).to_contain_text("refusée")
    page.get_by_label("Ville, campus ou restaurant").fill("Cuvier")
    page.get_by_role("button", name="Rechercher sur la carte").click()
    expect(page.locator("#map-list .venue-card")).to_have_count(2)
    marker = page.locator(".crowd-marker")
    expect(marker).to_have_count(1)
    # A shared address keeps one colour per venue; nothing is pooled.
    ru = marker.locator('[data-segment-venue="paris:r177"]')
    cafeteria = marker.locator('[data-segment-venue="paris:r889"]')
    expect(marker.locator(".crowd-segment")).to_have_count(2)
    expect(ru).to_have_class("crowd-segment crowd-zero")
    expect(ru).to_have_text("0")
    expect(cafeteria).to_have_class("crowd-segment crowd-unknown")
    expect(cafeteria).to_have_text("?")
    expect(marker).to_have_attribute("aria-label", re.compile(r"RU Cuvier, 0 min"))
    page.locator("#venue-map").screenshot(
        path=f"docs/evidence/q09-20261008-b72e/map-shared-{uuid4().hex[:8]}.png"
    )
    marker.focus()
    page.keyboard.press("Enter")
    expect(page.locator(".map-popup a")).to_have_count(2)
    expect(page.locator(".map-popup")).to_contain_text("Cafétéria Cuvier")
    page.screenshot(
        path=f"docs/evidence/q09-20261008-b72e/map-mobile-{uuid4().hex[:8]}.png",
        full_page=True,
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.evaluate("Object.keys(localStorage).every(k=>!k.includes('location'))")
    page.clock.fast_forward(15 * 60 * 1000)
    expect(
        page.locator('#map-list [data-map-venue="paris:r177"] .map-wait')
    ).to_have_text("Aucun signalement récent")
    expect(
        page.locator('#map-list [data-map-venue="paris:r177"] .map-wait')
    ).to_have_class("map-wait crowd-unknown")
    expect(
        page.locator('.map-popup [data-popup-venue="paris:r177"] .popup-wait')
    ).to_contain_text("Aucun signalement récent")
    expect(ru).to_have_class("crowd-segment crowd-unknown")
    expect(ru).to_have_text("?")
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator("#venue-map").focus()
    page.keyboard.press("ArrowRight")
    page.screenshot(
        path=f"docs/evidence/q09-20261008-b72e/map-desktop-{uuid4().hex[:8]}.png",
        full_page=True,
    )
    page.get_by_label("Ville, campus ou restaurant").fill("no-such-place-000")
    page.get_by_role("button", name="Rechercher sur la carte").click()
    expect(page.locator("#map-count")).to_have_text("0 lieux")
    expect(page.locator("#map-error")).to_contain_text("Aucun lieu")
    assert not failures


def test_map_location_is_click_only_and_transient(browser_page):
    import base64

    page, context, origin = browser_page
    context.route(
        "https://tile.openstreetmap.org/**",
        lambda route: route.fulfill(
            status=200,
            content_type="image/png",
            body=base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
        ),
    )
    page.add_init_script(
        "window.locationCalls=0; navigator.geolocation.getCurrentPosition = success => {window.locationCalls++;success({coords:{latitude:48.847512345,longitude:2.355012345}});};"
    )
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    page.goto(origin + "/map")
    expect(page.locator("#map-list .venue-card").first).to_be_visible()
    expect(page.locator(".leaflet-tile-loaded").first).to_be_visible()
    assert page.evaluate("window.locationCalls") == 0
    page.get_by_role("button", name="Autour de moi").click()
    expect(page.locator("#location-status")).to_contain_text("non conservée")
    assert page.evaluate("window.locationCalls") == 1
    assert not any("847512345" in r or "355012345" in r for r in requests)
    assert "847512345" not in page.evaluate(
        "JSON.stringify(localStorage)+JSON.stringify(sessionStorage)"
    )
    response = page.request.get(origin + "/map")
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert "unsafe-eval" not in response.headers["content-security-policy"]


def test_unlocated_venue_remains_listed_without_false_marker(browser_page):
    page, context, origin = browser_page
    context.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
    page.goto(origin + "/map?q=Dembeni&type=all")
    expect(page.locator("#map-list .venue-card")).to_have_count(1)
    expect(page.locator("#map-list")).to_contain_text("coordonnées indisponibles")
    expect(page.locator(".crowd-marker")).to_have_count(0)
