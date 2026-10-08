"""Inspect current release artifacts without publishing or including operator data."""

import argparse
import json
import os
import tarfile
import zipfile
from hashlib import sha256
from pathlib import Path

from crous_queue import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = [
        Path(f"dist/crous_queue-{__version__}-py3-none-any.whl"),
        Path(f"dist/crous-queue-{__version__}-local.tar.gz"),
    ]
    artifacts = []
    for path in paths:
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            for required in [
                "migrations/env.py",
                "migrations/versions/0006_hours_attempts.py",
                "services/hours.py",
                "services/availability.py",
                "static/map.js",
                "static/availability.js",
                "static/vendor/leaflet/leaflet.js",
                "static/vendor/leaflet/leaflet.css",
                "static/vendor/leaflet/LICENSE",
                "templates/hours.html",
            ]:
                assert "crous_queue/" + required in names, required
            assert "crous_queue/resources/venues-2026-10-07.json" in names
            assert (
                len(
                    [
                        n
                        for n in names
                        if n.startswith("crous_queue/migrations/versions/")
                        and n.endswith(".py")
                    ]
                )
                == 6
            )
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
        for name in names:
            parts = Path(name).parts
            assert not any(
                p in {".env", ".venv", ".local", ".foundry", "__pycache__"}
                for p in parts
            ), name
            assert not name.endswith((".db", ".sqlite", ".sqlite3", ".pyc")), name
        artifacts.append(
            dict(
                name=path.name,
                sha256=sha256(path.read_bytes()).hexdigest(),
                bytes=path.stat().st_size,
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            dict(
                version=__version__,
                source_commit=os.getenv("GITHUB_SHA"),
                supported=["standalone-wheel", "complete-source-kit"],
                artifacts=artifacts,
            ),
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(artifacts))


if __name__ == "__main__":
    main()
