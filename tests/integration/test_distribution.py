import pytest
from alembic import command
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crous_queue.db import make_engine
from crous_queue.distribution import directory_snapshot, migration_configuration
from crous_queue.models import Venue
from crous_queue.services.directory import DirectoryImporter
from tests.conftest import NOW


def test_packaged_resources_bootstrap_from_empty_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    url = f"sqlite:///{tmp_path / 'test-installed.db'}"
    with migration_configuration(url) as config:
        command.upgrade(config, "head")
    engine = make_engine(url)
    with directory_snapshot() as snapshot:
        DirectoryImporter(engine, lambda: NOW).import_snapshot(snapshot)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Venue)) == 972
    assert (
        not (tmp_path / "alembic.ini").exists() and not (tmp_path / "fixtures").exists()
    )


def test_missing_package_or_operator_resources_have_actionable_errors(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("crous_queue.distribution.files", lambda package: tmp_path)
    with pytest.raises(ValueError, match="Reinstall"):
        with migration_configuration("sqlite:///test-missing.db"):
            pass
    with pytest.raises(ValueError, match="Reinstall"):
        with directory_snapshot():
            pass
    with pytest.raises(ValueError, match="snapshot"):
        with directory_snapshot(tmp_path / "absent.json"):
            pass


def test_manifest_drift_fails_locked_install_without_network(tmp_path):
    import subprocess

    from tests.conftest import ROOT

    original = (ROOT / "pyproject.toml").read_text()
    (tmp_path / "pyproject.toml").write_text(original)
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    package = tmp_path / "src/crous_queue"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        '"""Minimal synthetic build target for lock-contract control."""\n'
    )
    # Positive control excludes unrelated missing-source/build failures.
    control = subprocess.run(
        ["uv", "sync", "--locked", "--offline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert control.returncode == 0, control.stderr
    project = original.replace('"pydantic-settings>=2.7,<3"', '"pydantic-settings<2.7"')
    assert project != original
    (tmp_path / "pyproject.toml").write_text(project)
    result = subprocess.run(
        ["uv", "sync", "--locked", "--offline"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (tmp_path / "uv.lock").read_bytes() == (ROOT / "uv.lock").read_bytes()
