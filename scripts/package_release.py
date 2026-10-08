"""Reproducible source kit without operator data, secrets or environments."""

import gzip
import tarfile
from hashlib import sha256
from pathlib import Path

from crous_queue import __version__

ROOT = Path(__file__).resolve().parents[1]

VERSION = __version__
output = ROOT / "dist" / f"crous-queue-{VERSION}-local.tar.gz"
roots = [
    ".github",
    "src",
    "scripts",
    "alembic",
    "tests",
    "fixtures",
    "docs",
    "acceptance",
    "deploy",
]
files = []
for root in roots:
    files.extend(
        p
        for p in (ROOT / root).rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
        and "evidence" not in p.parts
    )
files.extend(
    ROOT / p
    for p in [
        "README.md",
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        "alembic.ini",
        ".env.example",
        ".gitignore",
    ]
)
with (
    output.open("wb") as out,
    gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0) as compressed,
    tarfile.open(fileobj=compressed, mode="w") as archive,
):
    for path in sorted(files):
        info = archive.gettarinfo(
            str(path), arcname=f"crous-queue-{VERSION}/" + str(path.relative_to(ROOT))
        )
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        with path.open("rb") as stream:
            archive.addfile(info, stream)
for path in sorted((ROOT / "dist").glob("*")):
    if VERSION in path.name and path.suffix in {".whl", ".gz"}:
        print(sha256(path.read_bytes()).hexdigest() + "  " + path.name)
