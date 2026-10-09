from playwright.sync_api import expect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.models import WaitReport
from tests.browser.support import evidence
from tests.browser.worker import wait_for_worker_control


def select_cuvier(page, origin):
    page.goto(origin + "/")
    page.get_by_label("Rechercher un établissement").fill("Cuvier")
    page.get_by_role("button", name="Rechercher", exact=True).click()
    page.get_by_role("link", name="RU Cuvier", exact=True).click()
    expect(page.get_by_role("heading", name="RU Cuvier")).to_be_visible()


def test_mobile_three_taps_favorites_expiry_offline(browser_page, engine):
    page, context, origin = browser_page
    page.clock.install()
    select_cuvier(page, origin)
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    # Exactly three clicks after venue selection: open, choose 10, confirm.
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="10 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#wait-value")).to_have_text("10 min")
    expect(page.locator("#wait-detail")).to_contain_text("non confirmé")
    page.get_by_role("button", name="Ajouter aux favoris").click()
    page.screenshot(
        path=evidence("mobile"),
        full_page=True,
    )
    page.reload()
    expect(page.get_by_role("button", name="Retirer des favoris")).to_be_visible()
    page.clock.fast_forward(15 * 60 * 1000)
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    context.set_offline(True)
    expect(page.locator("#network-status")).to_contain_text("Hors ligne")
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="20 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#form-status")).to_contain_text("Hors ligne")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(WaitReport)) == 1
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_lost_response_retry_does_not_duplicate(browser_page, engine):
    page, context, origin = browser_page
    select_cuvier(page, origin)
    # Server receives first POST, then transport loses its response.
    count = [0]

    def lose_first(route):
        count[0] += 1
        if count[0] == 1:
            route.fetch()
            route.abort("failed")
        else:
            route.continue_()

    page.route("**/venues/*/reports", lose_first)
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="10 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#form-status")).to_contain_text("Réessayer")
    page.get_by_role("button", name="Réessayer", exact=True).click()
    expect(page.locator("#wait-value")).to_have_text("10 min")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(WaitReport)) == 1
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(origin + "/")
    page.screenshot(
        path=evidence("desktop"),
        full_page=True,
    )


def test_pwa_offline_shell(browser_page):
    page, context, origin = browser_page
    response = page.goto(origin + "/")
    assert response is not None
    assert "'unsafe-eval'" not in response.headers["content-security-policy"]
    wait_for_worker_control(page)
    manifest = page.request.get(origin + "/static/manifest.webmanifest").json()
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) == 2
    context.set_offline(True)
    page.goto(origin + "/v/paris:r175")
    expect(
        page.get_by_role("heading", name="On se retrouve à la reconnexion.")
    ).to_be_visible()


def test_flag_and_admin_hide_in_browser(browser_page):
    page, context, origin = browser_page
    select_cuvier(page, origin)
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="10 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#wait-value")).to_have_text("10 min")
    page.get_by_role("button", name="Signaler un abus", exact=True).click()
    expect(page.locator("#flag-status")).to_contain_text("transmis")
    page.goto(origin + "/admin")
    page.locator("#admin-key").fill("c" * 40)
    page.get_by_role("button", name="Ouvrir la modération").click()
    expect(page.locator("#admin-list")).to_contain_text("1 abus")
    page.get_by_label("Motif de modération").fill(
        "Estimation suspecte du test synthétique"
    )
    page.get_by_role("button", name="Masquer", exact=True).click()
    expect(page.locator("#admin-status")).to_contain_text("Signalement masqué")
    page.screenshot(
        path=evidence("admin"),
        full_page=True,
    )
    page.goto(origin + "/v/paris:r177")
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")


def test_own_timer_separate_from_live_estimate(browser_page):
    page, context, origin = browser_page
    page.goto(origin + "/v/paris:r175")
    page.get_by_role("button", name="Démarrer mon chronomètre", exact=True).click()
    expect(
        page.get_by_role("button", name="Terminer mon attente", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="Terminer mon attente", exact=True).click()
    expect(page.locator("#observations")).to_contain_text(
        "Attente personnelle terminée"
    )
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")


def test_rejected_contribution_can_be_corrected(browser_page):
    page, context, origin = browser_page
    select_cuvier(page, origin)
    attempts = [0]

    def reject_first(route):
        attempts[0] += 1
        if attempts[0] == 1:
            route.fulfill(
                status=422,
                content_type="application/json",
                body='{"detail":{"message":"Valeur invalide, corrigez la durée."}}',
            )
        else:
            route.continue_()

    page.route("**/venues/*/reports", reject_first)
    page.get_by_role("button", name="Signaler une attente", exact=True).click()
    page.get_by_role("button", name="10 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#form-status")).to_contain_text("Valeur invalide")
    page.get_by_role("button", name="5 min", exact=True).click()
    page.get_by_role("button", name="Confirmer", exact=True).click()
    expect(page.locator("#wait-value")).to_have_text("5 min")
