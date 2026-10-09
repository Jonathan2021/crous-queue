"""Installed CLI operations in a disposable working directory; no network."""

import json
import os
import stat
import sys

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue import cli
from crous_queue.db import make_engine
from crous_queue.models import Venue
from crous_queue.services.directory import FixtureProvider
from crous_queue.services.hours import FixtureHoursProvider
from tests.conftest import ROOT
from tests.integration.test_hours import HTML


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for key in [k for k in os.environ if k.startswith("CQ_")]:
        monkeypatch.delenv(key)

    def invoke(*argv):
        monkeypatch.setattr(sys, "argv", ["crous-queue", *argv])
        cli.main()
        return capsys.readouterr().out

    return invoke


def test_bootstrap_operate_and_recover_from_empty_directory(run, tmp_path, capsys):
    with pytest.raises(SystemExit) as missing:
        run("migrate")
    assert missing.value.code == 2
    assert "Invalid Crous Queue configuration" in capsys.readouterr().err
    assert "ready" in run("configure")
    run("migrate")
    database = tmp_path / ".local/development.db"
    assert stat.S_IMODE(database.stat().st_mode) == 0o600
    assert "no wait reports created" in run("import-directory")
    with Session(make_engine(f"sqlite:///{database}")) as db:
        assert db.scalar(select(func.count()).select_from(Venue)) == 972
    assert set(json.loads(run("retain"))) == {
        "timers",
        "reports",
        "flags",
        "audits",
        "rate_buckets",
    }
    for argv, message in [
        (["backup"], "backup requires --output"),
        (["restore", "--input", "x.db"], "restore requires --input"),
    ]:
        with pytest.raises(SystemExit) as usage:
            run(*argv)
        assert usage.value.code == 2 and message in capsys.readouterr().err
    run("backup", "--output", ".local/development-backup.db")
    run(
        "restore",
        "--input",
        ".local/development-backup.db",
        "--output",
        ".local/development-restored.db",
    )
    with pytest.raises(SystemExit) as overwrite:
        run("backup", "--output", ".local/development-backup.db")
    assert overwrite.value.code == 2 and "no files are overwritten" in (
        capsys.readouterr().err
    )


def test_refresh_commands_report_per_source_and_flag_incomplete_hours(
    run, monkeypatch, capsys
):
    run("configure")
    run("migrate")
    run("import-directory")
    feed = (ROOT / "fixtures/xml/paris.xml").read_bytes()
    monkeypatch.setattr(
        cli, "HTTPDirectoryProvider", lambda: FixtureProvider({"paris": feed})
    )
    regions = json.loads(run("refresh-directory"))
    assert regions["paris"] == "good" and len(regions) == 26
    assert {state for region, state in regions.items() if region != "paris"} == {
        "stale"
    }
    monkeypatch.setattr(
        cli,
        "HTTPHoursProvider",
        lambda: FixtureHoursProvider({"paris:r177": HTML}),
    )
    assert json.loads(run("refresh-hours", "--venue-id", "paris:r177")) == {
        "paris:r177": "good"
    }
    with pytest.raises(SystemExit) as incomplete:
        run("refresh-hours")
    assert incomplete.value.code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"paris:r177": "good", "paris:r175": "failed"}
    assert "last-known data retained" in captured.err


def test_demo_seed_refuses_overrides_and_serve_stays_on_loopback(
    run, monkeypatch, capsys
):
    # A valid exported profile must not silently redirect synthetic data.
    monkeypatch.setenv("CQ_ENVIRONMENT", "test")
    monkeypatch.setenv("CQ_DATABASE_URL", "sqlite:///.local/test.db")
    with pytest.raises(SystemExit) as conflict:
        run("seed-demo")
    assert conflict.value.code == 2
    assert "Clear conflicting CQ_*" in capsys.readouterr().err
    monkeypatch.delenv("CQ_ENVIRONMENT")
    monkeypatch.delenv("CQ_DATABASE_URL")
    assert "Synthetic demo ready" in run("seed-demo")
    run("configure")
    calls = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: calls.append(kwargs))
    run("serve")
    assert calls == [
        dict(
            factory=True,
            host="127.0.0.1",
            port=8000,
            access_log=False,
            proxy_headers=False,
        )
    ]
