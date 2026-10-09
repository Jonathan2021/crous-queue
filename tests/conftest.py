from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine

from crous_queue.app import create_app
from crous_queue.config import Settings
from crous_queue.db import make_engine
from crous_queue.distribution import migration_configuration
from crous_queue.services.directory import DirectoryImporter

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)
SNAPSHOT = ROOT / "fixtures/venues-2026-10-07.json"
HEADERS = {"X-CQ-Request": "1"}
ADMIN_TOKEN = "z" * 40
ADMIN = {**HEADERS, "Authorization": "Bearer " + ADMIN_TOKEN}


def migrated(path: Path) -> str:
    """Upgrade a disposable SQLite store with the same packaged config as the CLI."""
    url = f"sqlite:///{path}"
    with migration_configuration(url) as config:
        command.upgrade(config, "head")
    return url


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return make_engine(migrated(tmp_path / "test-crous.db"))


@pytest.fixture
def application(engine):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(SNAPSHOT)
    current = [NOW]
    settings = Settings(
        environment="test",
        database_url=str(engine.url),
        session_secret="x" * 40,
        ip_secret="y" * 40,
        admin_token=ADMIN_TOKEN,
    )
    return create_app(settings, engine=engine, clock=lambda: current[0]), current
