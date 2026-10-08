"""Replay documented setup inside a disposable release copy, no Foundry."""

import json
import os
import socket
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import httpx
from artifact_browser import exercise

from crous_queue import __version__

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / f"dist/crous-queue-{__version__}-local.tar.gz"
base_env = {k: v for k, v in os.environ.items() if not k.startswith("CQ_")}
with tempfile.TemporaryDirectory(prefix="crous-release-") as folder:
    with tarfile.open(archive) as stream:
        stream.extractall(folder, filter="data")
    checkout = Path(folder) / f"crous-queue-{__version__}"
    commands = [
        ["make", "install"],
        ["make", "migrate"],
        ["uv", "run", "crous-queue", "import-directory"],
        ["make", "check"],
        [
            "uv",
            "run",
            "crous-queue",
            "backup",
            "--output",
            ".local/development-backup.db",
        ],
        [
            "uv",
            "run",
            "crous-queue",
            "restore",
            "--input",
            ".local/development-backup.db",
            "--output",
            ".local/development-restored.db",
        ],
        ["uv", "run", "crous-queue", "retain"],
        ["make", "seed-demo"],
    ]
    for argv in commands:
        print("RUN " + " ".join(argv), flush=True)
        run = subprocess.run(
            argv, cwd=checkout, env=base_env, text=True, capture_output=True
        )
        print(run.stdout, flush=True)
        if run.returncode:
            print(run.stderr, flush=True)
            raise SystemExit(run.returncode)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    admin_token = "source-synthetic-admin-" + "b" * 32
    env = {
        **base_env,
        "CQ_PORT": str(port),
        "CQ_ORIGIN": origin,
        "CQ_ADMIN_TOKEN": admin_token,
    }
    with (checkout / ".local/server.log").open("w") as log:
        server = subprocess.Popen(
            ["uv", "run", "crous-queue", "serve"],
            cwd=checkout,
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
                raise RuntimeError("Release server failed to start.")
            assert httpx.get(origin + "/").status_code == 200
            assert (
                httpx.get(origin + "/venues/paris:r177/waits").json()["state"]
                == "unknown"
            )
            assert (
                httpx.get(origin + "/venues", params={"q": "Cuvier"}).json()["items"][
                    0
                ]["id"]
                == "paris:r177"
            )
            assert httpx.get(origin + "/privacy").status_code == 200
            assert httpx.get(origin + "/admin/reports").status_code == 401
            print(json.dumps(exercise(origin, admin_token)), flush=True)
            print(
                json.dumps(
                    {
                        "release_smoke": "passed",
                        "real_waits": "unknown",
                        "standalone_without_foundry": True,
                    }
                ),
                flush=True,
            )
        finally:
            server.terminate()
            server.wait(timeout=10)
