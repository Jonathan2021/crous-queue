from datetime import UTC, datetime, timedelta
from uuid import uuid4

from playwright.sync_api import expect
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from crous_queue.models import WaitReport


def submit_shortage(page, origin):
    page.goto(origin + "/v/paris:r177")
    page.locator("#availability-panel summary").click()
    page.get_by_label("Végétarien", exact=True).select_option("unavailable")
    page.get_by_label("Places assises", exact=True).select_option("unavailable")
    page.get_by_label("Commentaire facultatif", exact=False).fill(
        "Le comptoir végétarien attend un réassort."
    )
    page.get_by_role("button", name="Partager ces observations").click()
    expect(page.locator("#availability-status")).to_contain_text("attend la modération")


def test_availability_comment_review_expiry_and_recovery(browser_page, engine):
    page, _, origin = browser_page
    submit_shortage(page, origin)
    expect(page.locator('[data-dimension="vegetarian"] .dimension-value')).to_have_text(
        "Temporairement indisponible"
    )
    expect(page.locator('[data-dimension="seating"] .dimension-value')).to_have_text(
        "Temporairement indisponible"
    )
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    expect(page.locator("#comments")).not_to_contain_text("réassort")
    page.goto(origin + "/admin")
    page.get_by_label("Clé d’administration").fill("c" * 40)
    page.get_by_role("button", name="Ouvrir la modération").click()
    expect(page.locator(".admin-comment")).to_contain_text("pending")
    page.get_by_label("Motif de modération").fill(
        "Texte synthétique sans identité ni lien"
    )
    page.get_by_role("button", name="Approuver le commentaire").click()
    expect(page.locator(".admin-comment")).to_contain_text("approved")
    page.goto(origin + "/v/paris:r177")
    expect(page.locator("#comments")).to_contain_text("réassort")
    page.screenshot(
        path=f"docs/evidence/q10-20261008-b72e/availability-mobile-{uuid4().hex[:8]}.png",
        full_page=True,
    )
    # Advance retained synthetic observations, not production app clock/API.
    with Session(engine) as db, db.begin():
        db.execute(
            update(WaitReport).values(
                observed_at=datetime.now(UTC) - timedelta(minutes=6),
                received_at=datetime.now(UTC) - timedelta(minutes=6),
            )
        )
    page.get_by_role("button", name="Actualiser", exact=True).click()
    expect(page.locator('[data-dimension="seating"] .dimension-value')).to_have_text(
        "Inconnu"
    )
    expect(page.locator('[data-dimension="vegetarian"] .dimension-value')).to_have_text(
        "Temporairement indisponible"
    )
    page.locator("#availability-panel summary").click()
    page.get_by_label("Végétarien", exact=True).select_option("available")
    page.get_by_label("Places assises", exact=True).select_option("available")
    page.get_by_role("button", name="Partager ces observations").click()
    expect(page.locator('[data-dimension="vegetarian"] .dimension-value')).to_have_text(
        "Disponible"
    )
    expect(page.locator("#wait-value")).to_have_text("Aucun signalement récent")
    page.clock.install()
    page.clock.fast_forward(10 * 60 * 1000)
    expect(page.locator('[data-dimension="vegetarian"] .dimension-value')).to_have_text(
        "Inconnu"
    )
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(
        path=f"docs/evidence/q10-20261008-b72e/availability-desktop-{uuid4().hex[:8]}.png",
        full_page=True,
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_availability_lost_response_retry_offline_and_plain_text(browser_page, engine):
    page, context, origin = browser_page
    count = [0]

    def lose(route):
        count[0] += 1
        if count[0] == 1:
            route.fetch()
            route.abort("failed")
        else:
            route.continue_()

    page.route("**/venues/*/reports", lose)
    page.goto(origin + "/v/paris:r177")
    page.locator("#availability-panel summary").click()
    page.get_by_label("Végétarien", exact=True).select_option("unavailable")
    page.get_by_label("Commentaire facultatif", exact=False).fill(
        '<img src=x onerror="window.injection=true"> https://invalid.test'
    )
    page.get_by_role("button", name="Partager ces observations").click()
    expect(page.locator("#availability-status")).to_contain_text("Réessayer")
    context.set_offline(True)
    page.get_by_role("button", name="Réessayer ces observations").click()
    expect(page.locator("#availability-status")).to_contain_text("Hors ligne")
    context.set_offline(False)
    page.get_by_role("button", name="Réessayer ces observations").click()
    expect(page.locator("#availability-status")).to_contain_text("attend la modération")
    with Session(engine) as db, db.begin():
        assert db.scalar(select(func.count()).select_from(WaitReport)) == 1
        report = db.scalar(select(WaitReport))
        report.comment_status = "approved"
    page.get_by_role("button", name="Actualiser", exact=True).click()
    expect(page.locator("#comments")).to_contain_text("<img src=x")
    assert page.locator("#comments img, #comments a").count() == 0
    assert page.evaluate("window.injection === undefined")

    page.goto(origin + "/admin")
    page.get_by_label("Clé d’administration").fill("c" * 40)
    page.get_by_role("button", name="Ouvrir la modération").click()
    page.get_by_label("Motif de modération").fill("Texte synthétique à retirer")
    page.get_by_role("button", name="Masquer", exact=True).click()
    expect(page.get_by_role("button", name="Masquer", exact=True)).to_be_disabled()
    expect(page.get_by_role("button", name="Approuver le commentaire")).to_have_count(0)
    page.get_by_label("Motif de modération").fill("Texte synthétique à effacer")
    page.get_by_role("button", name="Supprimer le texte").click()
    expect(page.locator(".admin-comment")).to_have_text("Commentaire (deleted) : aucun")
