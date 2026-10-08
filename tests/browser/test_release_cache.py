"""Real worker + changed disposable assets: retain no application data."""

import os
import shutil
import socket
import subprocess
import sys
import time

import httpx
from playwright.sync_api import expect, sync_playwright

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
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "CQ_ENVIRONMENT": "test",
        "CQ_DATABASE_URL": str(engine.url),
        "CQ_SESSION_SECRET": "a" * 40,
        "CQ_IP_SECRET": "b" * 40,
        "CQ_ADMIN_TOKEN": "c" * 40,
        "CQ_ORIGIN": origin,
    }

    def start():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "release_app:create_app",
                "--factory",
                "--app-dir",
                str(tmp_path),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                if httpx.get(origin + "/health").status_code == 200:
                    return process
            except httpx.TransportError:
                time.sleep(0.05)
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("Disposable release server did not start.")

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
