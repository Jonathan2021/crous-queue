from datetime import UTC, datetime
from uuid import uuid4

from playwright.sync_api import expect

from crous_queue.services.hours import FixtureHoursProvider, HoursImporter
from tests.integration.test_hours import HTML


def test_hours_inline_and_identity(browser_page, engine):
    page, _, origin = browser_page
    HoursImporter(engine, lambda: datetime.now(UTC)).refresh(
        FixtureHoursProvider({"paris:r177": HTML}), ["paris:r177"]
    )
    page.goto(origin + "/?q=Cuvier&type=all")
    card = page.locator('[data-hours="paris:r177"]')
    expect(card).to_contain_text("Source officielle")
    expect(card).to_contain_text("Europe/Paris")
    expect(page.locator('[data-hours="paris:r889"]')).to_contain_text("inconnue")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.goto(origin + "/v/paris:r177")
    expect(page.locator(".official-hours")).to_contain_text("Dernier relevé")
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    page.screenshot(
        path=f"docs/evidence/q08-20261008-b72e/hours-mobile-{uuid4().hex[:8]}.png",
        full_page=True,
    )
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(
        path=f"docs/evidence/q08-20261008-b72e/hours-desktop-{uuid4().hex[:8]}.png",
        full_page=True,
    )


def test_hours_refresh_replaces_intervals_and_check_time(browser_page, engine):
    page, _, origin = browser_page
    HoursImporter(engine, lambda: datetime.now(UTC)).refresh(
        FixtureHoursProvider({"paris:r177": HTML}), ["paris:r177"]
    )
    page.goto(origin + "/v/paris:r177")
    updated = page.request.get(origin + "/venues/paris:r177/hours").json()
    updated.update(intervals=["12:00–15:00"], checked_at="2026-10-08T09:17:00Z")
    page.route("**/venues/*/hours", lambda route: route.fulfill(json=updated))
    page.evaluate("window.dispatchEvent(new Event('online'))")
    box = page.locator(".official-hours")
    expect(box).to_contain_text("12:00–15:00")
    expect(box).not_to_contain_text("11:30–14:00")
    expect(box).to_contain_text("09:17")
    updated.update(intervals=[], checked_at=None)
    page.evaluate("window.dispatchEvent(new Event('online'))")
    expect(box).not_to_contain_text("12:00–15:00")
    expect(box).not_to_contain_text("Dernier relevé")
