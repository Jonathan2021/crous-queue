"""Real browser replay against an installed artifact, using synthetic inputs only."""

from playwright.sync_api import expect, sync_playwright


def exercise(origin: str, admin_token: str) -> dict[str, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Separate synthetic devices respect the existing per-venue throttle.
        wait_context = browser.new_context(viewport={"width": 390, "height": 844})
        page = wait_context.new_page()
        page.goto(origin + "/")
        page.get_by_label("Rechercher un établissement").fill("Cuvier")
        page.get_by_role("button", name="Rechercher", exact=True).click()
        page.get_by_role("link", name="RU Cuvier", exact=True).click()
        expect(page.locator(".official-hours")).to_contain_text("Source officielle")
        page.get_by_role("button", name="Signaler une attente", exact=True).click()
        page.get_by_role("button", name="0 min", exact=True).click()
        page.get_by_role("button", name="Confirmer", exact=True).click()
        expect(page.locator("#wait-value")).to_have_text("0 min")
        wait_context.close()
        context = browser.new_context(viewport={"width": 390, "height": 844})
        context.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
        page = context.new_page()
        page.goto(origin + "/v/paris:r177")
        page.locator("#availability-panel summary").click()
        page.get_by_label("Végétarien", exact=True).select_option("unavailable")
        page.get_by_label("Places assises", exact=True).select_option("unavailable")
        page.get_by_label("Commentaire facultatif", exact=False).fill(
            "Relecture synthétique du paquet installé."
        )
        page.get_by_role("button", name="Partager ces observations").click()
        expect(page.locator("#availability-status")).to_contain_text(
            "attend la modération"
        )
        expect(page.locator("#wait-value")).to_have_text("0 min")
        page.goto(origin + "/admin")
        page.get_by_label("Clé d’administration").fill(admin_token)
        page.get_by_role("button", name="Ouvrir la modération").click()
        card = page.locator("#admin-list article").filter(
            has_text="Relecture synthétique"
        )
        card.get_by_label("Motif de modération").fill(
            "Vérification synthétique sans identité"
        )
        card.get_by_role("button", name="Approuver le commentaire").click()
        expect(card.locator(".admin-comment")).to_contain_text("approved")
        page.goto(origin + "/v/paris:r177")
        expect(page.locator("#comments")).to_contain_text("Relecture synthétique")
        page.goto(origin + "/map?q=Cuvier&type=all")
        expect(page.locator("#map-list .venue-card")).to_have_count(2)
        expect(
            page.locator('#map-list [data-map-venue="paris:r177"] .map-wait')
        ).to_have_text("0 min")
        # Co-located RU and cafeteria keep separate colours in one shared marker.
        marker = page.locator(".crowd-marker")
        expect(marker).to_have_count(1)
        expect(marker.locator('[data-segment-venue="paris:r177"]')).to_have_class(
            "crowd-segment crowd-zero"
        )
        expect(marker.locator('[data-segment-venue="paris:r889"]')).to_have_text("?")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        response = page.request.get(origin + "/v/paris:r177")
        assert "unsafe-eval" not in response.headers["content-security-policy"]
        assert "unsafe-inline" not in response.headers["content-security-policy"]
        context.close()
        browser.close()
    return dict(
        browser="Chromium",
        installed_core_flow="passed",
        providers="synthetic/offline tiles",
    )
