"""Create private local profiles without revealing or replacing existing secrets."""

import os
from pathlib import Path
from secrets import token_urlsafe


def configure(*, demo: bool = False) -> Path:
    path = Path(".local/demo.env") if demo else Path(".env")
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    profile = "demo" if demo else "development"
    # Create with private permissions before writing any secret, regardless of umask.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(
            f"CQ_ENVIRONMENT={profile}\nCQ_DATABASE_URL=sqlite:///.local/{profile}.db\n"
        )
        if demo:
            stream.write("CQ_ORIGIN=http://127.0.0.1:8001\nCQ_PORT=8001\n")
        for key in ["SESSION_SECRET", "IP_SECRET", "ADMIN_TOKEN"]:
            stream.write(f"CQ_{key}={token_urlsafe(48)}\n")
    path.chmod(0o600)
    return path
