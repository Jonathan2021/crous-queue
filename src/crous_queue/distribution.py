"""Installed resources: no migration or snapshot lookup depends on caller cwd."""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path

from alembic.config import Config


@contextmanager
def migration_configuration(database_url: str) -> Iterator[Config]:
    root = files("crous_queue").joinpath("migrations")
    if (
        not root.is_dir()
        or not root.joinpath("env.py").is_file()
        or not root.joinpath("versions").is_dir()
    ):
        raise ValueError(
            "Packaged migrations are missing. Reinstall the complete Crous Queue wheel or source kit."
        )
    with as_file(root) as path:
        config = Config()
        config.set_main_option("script_location", str(path))
        config.set_main_option("path_separator", "os")
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        yield config


@contextmanager
def directory_snapshot(override: Path | None = None) -> Iterator[Path]:
    if override is not None:
        if not override.is_file():
            raise ValueError(
                "Directory snapshot file not found. Check --snapshot or omit it for the bundled dated directory."
            )
        yield override
        return
    resource = files("crous_queue").joinpath("resources", "venues-2026-10-07.json")
    if not resource.is_file():
        raise ValueError(
            "Packaged directory snapshot is missing. Reinstall the complete Crous Queue wheel or source kit."
        )
    with as_file(resource) as path:
        yield path
