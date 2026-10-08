"""Install only a built wheel and locked runtime deps into a new empty directory."""

import argparse
import json
import os
import socket
import stat
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from artifact_browser import exercise

from crous_queue import __version__

ROOT = Path(__file__).resolve().parents[1]


def verify(wheel: Path) -> dict[str, object]:
    wheel = wheel.resolve()
    base_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("CQ_") and key not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }
    with tempfile.TemporaryDirectory(prefix="crous-wheel-only-") as temporary:
        root = Path(temporary)
        work = root / "empty-work"
        work.mkdir()
        requirements = root / "runtime-requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=ROOT,
            env=base_env,
            check=True,
            capture_output=True,
            text=True,
        )
        commands = [
            ["uv", "venv", "--python", "3.13", str(root / "venv")],
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(root / "venv/bin/python"),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(root / "venv/bin/python"),
                "--no-deps",
                str(wheel),
            ],
        ]
        exits = []

        def run(argv: list[str]) -> None:
            completed = subprocess.run(
                argv, cwd=work, env=base_env, text=True, capture_output=True
            )
            exits.append(
                {
                    "command": argv[0]
                    if argv[0].endswith("crous-queue")
                    else " ".join(argv[:3]),
                    "exit": completed.returncode,
                }
            )
            if completed.returncode:
                print(completed.stdout)
                print(completed.stderr)
                raise RuntimeError(
                    "Installed-wheel verification failed: " + str(argv[-1])
                )

        for argv in commands:
            run(argv)
        cli = str(root / "venv/bin/crous-queue")
        python = str(root / "venv/bin/python")
        run([cli, "configure"])
        original_config = (work / ".env").read_bytes()
        assert stat.S_IMODE((work / ".env").stat().st_mode) == 0o600
        run([cli, "configure"])
        assert (work / ".env").read_bytes() == original_config
        run([cli, "migrate"])
        run([cli, "import-directory"])
        run([cli, "backup", "--output", ".local/development-backup.db"])
        run(
            [
                cli,
                "restore",
                "--input",
                ".local/development-backup.db",
                "--output",
                ".local/development-restored.db",
            ]
        )
        run([cli, "retain"])
        run([cli, "seed-demo"])
        run(
            [
                python,
                "-c",
                "import importlib.util,pathlib,crous_queue; assert 'site-packages' in crous_queue.__file__; assert importlib.util.find_spec('startup_foundry') is None; assert not pathlib.Path('alembic.ini').exists(); assert not pathlib.Path('fixtures').exists()",
            ]
        )
        run(
            [
                python,
                "-c",
                "from crous_queue.config import load_settings; from crous_queue.db import make_engine; from crous_queue.services.hours import HoursImporter, FixtureHoursProvider; from datetime import datetime,UTC; s=load_settings(); p=FixtureHoursProvider({'paris:r177':b'<h1>RU Cuvier</h1><h3>Horaires</h3><p>Du lundi au vendredi de 11h30 a 14h00</p><h3>Adresse</h3>'}); assert HoursImporter(make_engine(s.database_url),lambda:datetime.now(UTC)).refresh(p,['paris:r177'])=={'paris:r177':'good'}",
            ]
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        admin_token = "installed-synthetic-admin-" + "a" * 32
        env = {
            **base_env,
            "CQ_PORT": str(port),
            "CQ_ORIGIN": origin,
            "CQ_ADMIN_TOKEN": admin_token,
        }
        with (root / "server.log").open("w") as log:
            server = subprocess.Popen(
                [cli, "serve"], cwd=work, env=env, stdout=log, stderr=log
            )
            try:
                for _ in range(100):
                    try:
                        if httpx.get(origin + "/health").status_code == 200:
                            break
                    except httpx.TransportError:
                        time.sleep(0.05)
                else:
                    raise RuntimeError("Installed-wheel server failed to start.")
                assert httpx.get(origin + "/").status_code == 200
                assert (
                    httpx.get(origin + "/venues/paris:r177/waits").json()["state"]
                    == "unknown"
                )
                assert httpx.get(origin + "/privacy").status_code == 200
                assert (
                    httpx.get(origin + "/static/vendor/leaflet/leaflet.js").status_code
                    == 200
                )
                browser_result = exercise(origin, admin_token)
                assert httpx.get(origin + "/admin/reports").status_code == 401
                assert (
                    httpx.get(origin + "/openapi.json").json()["info"]["version"]
                    == __version__
                )
            finally:
                server.terminate()
                server.wait(timeout=10)
        # Restart the installed server, then recover into a new DB and verify writes.
        run([cli, "backup", "--output", ".local/development-after-browser.db"])
        run(
            [
                cli,
                "restore",
                "--input",
                ".local/development-after-browser.db",
                "--output",
                ".local/development-recovered.db",
            ]
        )
        for database in [".local/development.db", ".local/development-recovered.db"]:
            restarted = subprocess.Popen(
                [cli, "serve"],
                cwd=work,
                env={**env, "CQ_DATABASE_URL": "sqlite:///" + database},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(100):
                    try:
                        response = httpx.get(origin + "/venues/paris:r177/availability")
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        time.sleep(0.05)
                else:
                    raise RuntimeError("Installed artifact restart/recovery failed.")
                assert (
                    response.json()["dimensions"]["vegetarian"]["state"]
                    == "unavailable"
                )
                assert len(response.json()["comments"]) == 1
                assert (
                    httpx.get(origin + "/venues/paris:r177/waits").json()["minutes"]
                    == 0
                )
            finally:
                restarted.terminate()
                restarted.wait(timeout=10)
        return {
            "browser": browser_result,
            "restart_and_recovered_store": "passed",
            "contract": "standalone-wheel-with-locked-runtime-dependencies",
            "version": __version__,
            "checkout_resources_copied": False,
            "foundry_absent": True,
            "commands": exits,
            "http_smoke": "passed",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel",
        type=Path,
        default=ROOT / f"dist/crous_queue-{__version__}-py3-none-any.whl",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.wheel)
    if args.output:
        with args.output.open("x") as out:
            json.dump(result, out, indent=2)
            out.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
