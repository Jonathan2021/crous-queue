import pytest
from playwright.sync_api import sync_playwright

from crous_queue.services.directory import DirectoryImporter
from tests.browser.support import free_origin, server_env, start_server
from tests.conftest import NOW, SNAPSHOT


@pytest.fixture
def browser_page(engine, tmp_path, request):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(SNAPSHOT)
    origin = free_origin()
    with (tmp_path / "server.log").open("w") as log:
        try:
            process = start_server(
                "crous_queue.app:create_app",
                origin,
                server_env(str(engine.url), origin),
                log=log,
            )
        except RuntimeError:
            pytest.fail(
                "Local browser server failed to start: "
                + (tmp_path / "server.log").read_text()
            )
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    permissions=[],
                    service_workers="block"
                    if "lost_response" in request.node.name
                    or "rejected_contribution" in request.node.name
                    else "allow",
                )
                page = context.new_page()
                yield page, context, origin
                context.close()
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=10)
