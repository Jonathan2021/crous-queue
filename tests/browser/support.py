"""Shared local-server and screenshot helpers for the browser suite."""

import os
import socket
import subprocess
import sys
import time
from typing import IO
from uuid import uuid4

import httpx

from tests.conftest import ROOT

# One ignored screenshot prefix per run; set CQ_EVIDENCE_PREFIX to retain a run.
EVIDENCE_PREFIX = os.getenv("CQ_EVIDENCE_PREFIX") or "run-" + uuid4().hex[:8]


def evidence(name: str) -> str:
    return str(ROOT / f"docs/evidence/{EVIDENCE_PREFIX}-{name}.png")


def free_origin() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{sock.getsockname()[1]}"


def server_env(database_url: str, origin: str) -> dict[str, str]:
    return {
        **os.environ,
        "CQ_ENVIRONMENT": "test",
        "CQ_DATABASE_URL": database_url,
        "CQ_SESSION_SECRET": "a" * 40,
        "CQ_IP_SECRET": "b" * 40,
        "CQ_ADMIN_TOKEN": "c" * 40,
        "CQ_ORIGIN": origin,
    }


def start_server(
    app: str,
    origin: str,
    env: dict[str, str],
    *,
    log: IO[str] | int = subprocess.DEVNULL,
    app_dir: str | None = None,
) -> subprocess.Popen[bytes]:
    """Run a loopback uvicorn factory and wait for /health, or stop it and raise."""
    argv = [sys.executable, "-m", "uvicorn", app, "--factory", "--no-access-log"]
    argv += ["--app-dir", app_dir] if app_dir else []
    argv += ["--host", "127.0.0.1", "--port", origin.rsplit(":", 1)[1]]
    process = subprocess.Popen(argv, env=env, stdout=log, stderr=log)
    # A wall-clock budget, not a poll count: cold starts on a loaded host are slow.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and process.poll() is None:
        try:
            if httpx.get(origin + "/health").status_code == 200:
                return process
        except httpx.TransportError:
            pass
        time.sleep(0.05)
    process.terminate()
    process.wait(timeout=10)
    raise RuntimeError("Local test server did not start.")
