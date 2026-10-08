from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from crous_queue.app import create_app
from crous_queue.config import Settings
from crous_queue.db import make_engine
from crous_queue.models import Venue
from crous_queue.services.demo import seed_demo
from crous_queue.services.directory import DirectoryImporter
from crous_queue.services.pilot import pilot_check
from crous_queue.services.waits import WaitService
from tests.conftest import NOW, ROOT


def test_every_directory_identity_starts_unknown(engine):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(
        ROOT / "fixtures/venues-2026-10-07.json"
    )
    with Session(engine) as db:
        ids = list(db.scalars(select(Venue.id)))
    assert len(ids) == 972
    service = WaitService(engine, lambda: NOW)
    assert all(service.state(venue).state == "unknown" for venue in ids)
    check = pilot_check(engine, lambda: NOW, environment="test")
    assert check["fresh_checks"] == 0 and check["total_checks"] == 2


def test_demo_isolated_guarded_idempotent_and_expiring(engine, tmp_path):
    path = tmp_path / "demo-crous.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")
    settings = Settings(
        environment="demo",
        database_url=f"sqlite:///{path}",
        session_secret="a" * 40,
        ip_secret="b" * 40,
    )
    seed_demo(settings, ROOT / "fixtures/venues-2026-10-07.json", lambda: NOW)
    seed_demo(settings, ROOT / "fixtures/venues-2026-10-07.json", lambda: NOW)
    service = WaitService(make_engine(settings.database_url), lambda: NOW)
    assert service.state("paris:r177").minutes == 12.5
    assert service.state("paris:r175").minutes == 0
    assert len(service.state("paris:r177").completed) == 1
    assert (
        WaitService(
            make_engine(settings.database_url), lambda: NOW + timedelta(minutes=15)
        )
        .state("paris:r177")
        .state
        == "unknown"
    )
    bad = Settings(
        environment="test",
        database_url=str(engine.url),
        session_secret="a" * 40,
        ip_secret="b" * 40,
    )
    with pytest.raises(ValueError, match="demo"):
        seed_demo(bad, ROOT / "fixtures/venues-2026-10-07.json", lambda: NOW)
    with TestClient(create_app(settings)) as c:
        assert "DÉMO" in c.get("/v/paris:r177").text


def test_release_gate_and_runtime_independence():
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text()
        assert "startup_foundry" not in text and "from learning" not in text
    release = (ROOT / "docs/DEPLOYMENT_PROPOSAL.md").read_text()
    assert "NOT AUTHORIZED" in release and "teardown" in release.lower()
    assert (ROOT / "scripts/seed_demo.py").is_file()
