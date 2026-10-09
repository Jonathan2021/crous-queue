import os
import socket
import subprocess
import sys
import time

import httpx
import pytest
from playwright.sync_api import sync_playwright

from crous_queue.services.directory import DirectoryImporter
from tests.conftest import NOW, SNAPSHOT


@pytest.fixture
def browser_page(engine, tmp_path, request):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(SNAPSHOT)
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
    with (tmp_path / "server.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "crous_queue.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                try:
                    if httpx.get(origin + "/health").status_code == 200:
                        break
                except httpx.TransportError:
                    time.sleep(0.05)
            else:
                pytest.fail(
                    "Local browser server failed to start: "
                    + (tmp_path / "server.log").read_text()
                )
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
