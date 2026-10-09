"""P5 at 390px: visible dated attribution, labels, no empty service line."""

import re

from playwright.sync_api import expect

from tests.browser.support import evidence


def test_home_and_venue_copy_is_honest_at_390px(browser_page):
    page, _, origin = browser_page
    page.goto(origin + "/")
    footer = page.locator("footer")
    expect(footer).to_contain_text("Annuaire CNOUS / CROUS relevé le 07/10/2026")
    expect(footer).to_contain_text("Licence Ouverte")
    options = page.locator("select[name=region] option").all_inner_texts()
    assert "Orléans-Tours" in options and "La Réunion" in options
    assert "Nancy-Metz" in options and "Bourgogne-Franche-Comté" in options
    assert not any("." in o for o in options), options
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.goto(origin + "/v/paris:r177")
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    page.wait_for_timeout(300)
    text = page.locator("main").inner_text()
    assert "Service :" not in text
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", text), "ISO date shown"
    expect(page.locator(".venue-heading .eyebrow")).to_contain_text("Paris")
    expect(page.locator("footer")).to_contain_text("07/10/2026")
    page.screenshot(path=evidence("honesty-venue"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.goto(origin + "/map")
    options = page.locator("select[name=region] option").all_inner_texts()
    assert "Orléans-Tours" in options and not any("." in o for o in options)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
