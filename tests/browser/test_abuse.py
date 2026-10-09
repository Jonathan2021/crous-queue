"""Visible P3 semantics: devices and networks, never implied people."""

from datetime import UTC, datetime
from uuid import uuid4

from playwright.sync_api import expect

from tests.browser.support import evidence
from tests.browser.test_mobile import select_cuvier


def test_burst_from_one_network_shows_devices_networks_and_uncounted(browser_page):
    page, context, origin = browser_page
    select_cuvier(page, origin)
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="10 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#wait-detail")).to_contain_text("1 appareil · non confirmé")
    # Two more fresh cookies from the same loopback network (no trusted proxy).
    browser = context.browser
    assert browser is not None
    for _ in range(2):
        other = browser.new_context()
        other.request.get(origin + "/health")
        response = other.request.post(
            origin + "/venues/paris:r177/reports",
            headers={"X-CQ-Request": "1", "Origin": origin},
            data={
                "kind": "estimate",
                "minutes": 12,
                "observed_at": datetime.now(UTC).isoformat(),
                "queue_kind": "student",
                "idempotency_key": uuid4().hex,
            },
        )
        assert response.status == 201
        other.close()
    page.reload()
    detail = page.locator("#wait-detail")
    expect(detail).to_contain_text("2 appareils · 1 seul réseau")
    expect(detail).to_contain_text("1 autre du même réseau non compté")
    expect(page.locator("#wait-value")).to_have_text("12 min")
    page.screenshot(path=evidence("network-budget"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
