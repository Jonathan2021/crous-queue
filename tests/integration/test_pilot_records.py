import argparse
import csv
import os
import subprocess
import sys

import pytest

from crous_queue.config import Settings
from crous_queue.services.demo import seed_demo
from crous_queue.services.directory import DirectoryImporter
from tests.conftest import NOW, ROOT, SNAPSHOT, migrated


def test_pilot_logger_cannot_mix_demo_and_other_store(engine, tmp_path):
    DirectoryImporter(engine, lambda: NOW).import_snapshot(SNAPSHOT)
    demo = tmp_path / "demo-pilot.db"
    settings = Settings(
        environment="demo",
        database_url=migrated(demo),
        session_secret="a" * 40,
        ip_secret="b" * 40,
    )
    seed_demo(settings, SNAPSHOT, lambda: NOW)
    output = tmp_path / ".local/checks.jsonl"

    def run(environment, url):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_pilot.py"),
                "--output",
                str(output),
            ],
            cwd=tmp_path,
            env={
                **os.environ,
                "CQ_ENVIRONMENT": environment,
                "CQ_DATABASE_URL": url,
                "CQ_SESSION_SECRET": "a" * 40,
                "CQ_IP_SECRET": "b" * 40,
            },
            capture_output=True,
            text=True,
        )

    first = run("demo", settings.database_url)
    assert first.returncode == 0, first.stderr
    original = output.read_bytes()
    second = run("test", str(engine.url))
    assert second.returncode != 0, (
        "Logger accepted mixed demo/test measurements into one file"
    )
    assert output.read_bytes() == original


def test_only_selected_sites_count_as_returning_devices(engine):
    from datetime import timedelta

    from crous_queue.contracts import ReportInput
    from crous_queue.security import Identity
    from crous_queue.services.pilot import pilot_check
    from crous_queue.services.waits import WaitService

    DirectoryImporter(engine, lambda: NOW).import_snapshot(SNAPSHOT)
    current = [NOW]
    for day in range(2):
        current[0] = NOW + timedelta(days=day)
        for device, venue, queue in [
            ("pilot", "paris:r177", "student"),
            ("elsewhere", "lyon:r352", "unspecified"),
        ]:
            # Pick an actual other region identity from the retained snapshot below.
            if device == "elsewhere":
                from sqlalchemy import select
                from sqlalchemy.orm import Session

                from crous_queue.models import Venue

                with Session(engine) as db:
                    venue = db.scalar(
                        select(Venue.id).where(Venue.region == "lyon").limit(1)
                    )
            WaitService(engine, lambda: current[0]).submit(
                Identity(device, "network"),
                venue,
                ReportInput(
                    kind="estimate",
                    minutes=0,
                    observed_at=current[0],
                    queue_kind=queue,
                    idempotency_key=f"{device}_day_{day}",
                ),
            )
    assert (
        pilot_check(engine, lambda: current[0], environment="test")[
            "returning_devices_7d"
        ]
        == 1
    )


def test_disposable_five_lunch_rehearsal_and_demo_recovery():
    from scripts.rehearse_pilot import rehearse

    result = rehearse()
    assert result["kind"] == "synthetic_rehearsal_not_real_usefulness"
    assert result["summary"]["missing_slots"] == ["d3-1215"]
    assert result["summary"]["fresh_estimate_contributions"] == 23
    assert result["summary"]["friction"]["recorded_attempts"] == 3
    assert result["summary"]["friction"]["timed_attempts"] == 2
    assert (
        result["demo_restore_and_exact_expiry"] == "passed"
        and result["other_store_reports"] == 0
    )


def test_blank_pilot_sheets_stay_local_and_are_never_reset(tmp_path, monkeypatch):
    from scripts.pilot_records import local_path, prepare_blanks

    monkeypatch.chdir(tmp_path)
    for outside in ["records.jsonl", ".local/../records.jsonl", "/tmp/records"]:
        with pytest.raises(argparse.ArgumentTypeError):
            local_path(outside)
    folder = local_path(".local/pilot-blank")
    prepare_blanks(folder)
    with (folder / "fixed-checks.csv").open() as stream:
        header, *rows = list(csv.reader(stream))
    assert len(rows) == 40  # 5 days x 4 fixed times x 2 selected sites
    assert len({(row[2], row[4]) for row in rows}) == 40
    # Nothing is pre-filled: an unperformed check must stay visibly missing.
    assert all(row[1] == "" and row[6:] == [""] * 5 for row in rows)
    original = {path.name: path.read_bytes() for path in folder.iterdir()}
    with pytest.raises(FileExistsError):
        prepare_blanks(folder)
    assert {path.name: path.read_bytes() for path in folder.iterdir()} == original
