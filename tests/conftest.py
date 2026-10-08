from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from crous_queue.app import create_app
from crous_queue.config import Settings
from crous_queue.db import make_engine
from crous_queue.services.directory import DirectoryImporter

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 7, 10, 0, tzinfo=UTC)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    url = f"sqlite:///{tmp_path / 'test-crous.db'}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return make_engine(url)


@pytest.fixture
def application(engine):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(
        ROOT / "fixtures/venues-2026-10-07.json"
    )
    current = [NOW]
    settings = Settings(
        environment="test",
        database_url=str(engine.url),
        session_secret="x" * 40,
        ip_secret="y" * 40,
        admin_token="z" * 40,
    )
    return create_app(settings, engine=engine, clock=lambda: current[0]), current
