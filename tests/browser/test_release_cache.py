"""Real worker + changed disposable assets: retain no application data."""

import shutil

from playwright.sync_api import expect, sync_playwright

from tests.browser.support import free_origin, server_env, start_server
from tests.browser.worker import wait_for_worker_control
from tests.conftest import ROOT


def test_changed_release_assets_and_offline_after_server_restart(engine, tmp_path):
    assets = tmp_path / "static"
    shutil.copytree(ROOT / "src/crous_queue/static", assets)
    with (assets / "app.css").open("a") as out:
        out.write("\nbody {--release-marker: first;}\n")
    (tmp_path / "release_app.py").write_text("""from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from crous_queue.app import create_app as base_app
from crous_queue.api import pages
ROOT=Path(__file__).parent / 'static'
def create_app():
    app=base_app()
    app.router.routes[:]=[r for r in app.router.routes if getattr(r,'path',None) not in {'/static','/sw.js'}]
    app.mount('/static',StaticFiles(directory=ROOT))
    @app.get('/sw.js')
    def worker():
        source=pages.worker_source(ROOT) if hasattr(pages,'worker_source') else (ROOT/'sw.js').read_text()
        return Response(source,media_type='application/javascript',headers={'Service-Worker-Allowed':'/'})
    return app
""")
    origin = free_origin()
    env = server_env(str(engine.url), origin)

    def start():
        return start_server(
            "release_app:create_app", origin, env, app_dir=str(tmp_path)
        )

    process = start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.goto(origin + "/")
            wait_for_worker_control(page)
            page.reload()
            assert (
                page.evaluate(
                    "getComputedStyle(document.body).getPropertyValue('--release-marker').trim()"
                )
                == "first"
            )
            with (assets / "app.css").open("a") as out:
                out.write("\nbody {--release-marker: second;}\n")
            process.terminate()
            process.wait(timeout=10)
            process = start()
            # A normal online reload must not retain the previous release CSS.
            page.reload()
            assert (
                page.evaluate(
                    "getComputedStyle(document.body).getPropertyValue('--release-marker').trim()"
                )
                == "second"
            )
            page.evaluate(
                "navigator.serviceWorker.getRegistration().then(r => r.update())"
            )
            page.wait_for_timeout(250)
            context.set_offline(True)
            page.goto(origin + "/v/paris:r175")
            expect(
                page.get_by_role("heading", name="On se retrouve à la reconnexion.")
            ).to_be_visible()
            assert (
                page.evaluate(
                    "getComputedStyle(document.body).getPropertyValue('--release-marker').trim()"
                )
                == "second"
            )
            context.close()
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=10)
