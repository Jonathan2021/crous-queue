import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from crous_queue.config import load_settings
from crous_queue.configuration import configure
from crous_queue.db import make_engine
from crous_queue.distribution import directory_snapshot, migration_configuration
from crous_queue.services.demo import seed_demo
from crous_queue.services.directory import DirectoryImporter, HTTPDirectoryProvider
from crous_queue.services.hours import MAPPINGS, HoursImporter, HTTPHoursProvider
from crous_queue.services.maintenance import backup_sqlite, purge, restore_sqlite


def main() -> None:
    parser = argparse.ArgumentParser(description="Crous Queue local operations")
    parser.add_argument(
        "command",
        choices=[
            "configure",
            "seed-demo",
            "migrate",
            "import-directory",
            "refresh-directory",
            "refresh-hours",
            "retain",
            "backup",
            "restore",
            "serve",
        ],
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Explicit local snapshot; default is the bundled CNOUS directory dated 2026-10-07",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--venue-id",
        action="append",
        help="Reviewed exact venue ID for refresh-hours; default: both Paris RUs",
    )
    args = parser.parse_args()
    try:
        if args.command == "configure":
            configure()
            print(
                "Development .env ready; existing secrets preserved. Run migrate, import-directory, then serve."
            )
            return
        if args.command == "seed-demo":
            profile = configure(demo=True)
            settings = load_settings(profile)
            if settings.environment != "demo":
                raise ValueError(
                    "Clear conflicting CQ_* overrides before seeding the separate demo profile."
                )
        else:
            settings = load_settings()
        url = make_url(settings.database_url)
        if url.drivername.startswith("sqlite") and url.database:
            folder = Path(url.database).parent
            if not folder.exists():
                folder.mkdir(parents=True, mode=0o700)
        if args.command in {"migrate", "seed-demo"}:
            with migration_configuration(settings.database_url) as config:
                command.upgrade(config, "head")
            if url.drivername.startswith("sqlite") and url.database:
                Path(url.database).chmod(0o600)
            if args.command == "seed-demo":
                with directory_snapshot(args.snapshot) as snapshot:
                    seed_demo(settings, snapshot, lambda: datetime.now(UTC))
                print(
                    "Synthetic demo ready. Start: uv run --env-file .local/demo.env crous-queue serve"
                )
        elif args.command == "import-directory":
            with directory_snapshot(args.snapshot) as snapshot:
                DirectoryImporter(
                    make_engine(settings.database_url), lambda: datetime.now(UTC)
                ).import_snapshot(snapshot)
            print(
                "Bundled retained directory dated 2026-10-07 imported; no wait reports created."
            )
        elif args.command == "refresh-directory":
            print(
                json.dumps(
                    DirectoryImporter(
                        make_engine(settings.database_url), lambda: datetime.now(UTC)
                    ).refresh(HTTPDirectoryProvider())
                )
            )
        elif args.command == "refresh-hours":
            result = HoursImporter(
                make_engine(settings.database_url), lambda: datetime.now(UTC)
            ).refresh(HTTPHoursProvider(), args.venue_id or list(MAPPINGS))
            print(json.dumps(result))
            if any(value != "good" for value in result.values()):
                parser.exit(
                    1,
                    "Hours refresh incomplete; last-known data retained. Inspect mapping/source and retry.\n",
                )
        elif args.command == "retain":
            print(
                json.dumps(purge(make_engine(settings.database_url), datetime.now(UTC)))
            )
        elif args.command == "backup":
            if args.output is None:
                parser.error("backup requires --output NEW_PATH")
            backup_sqlite(
                settings.database_url, args.output, environment=settings.environment
            )
            print(
                "Integrity-checked backup created, permissions 0600. Protect and rotate within 7 days."
            )
        elif args.command == "restore":
            if args.input is None or args.output is None:
                parser.error("restore requires --input BACKUP --output NEW_MARKED_PATH")
            restore_sqlite(args.input, args.output, environment=settings.environment)
            print(
                "Restored into new isolated path. Validate before changing database configuration."
            )
        else:
            import uvicorn

            logging.basicConfig(level=logging.INFO, format="%(message)s")
            uvicorn.run(
                "crous_queue.app:create_app",
                factory=True,
                host="127.0.0.1",
                port=settings.port,
                access_log=False,
                proxy_headers=False,
            )
    except (ValueError, OSError) as error:
        parser.error(str(error))
    except SQLAlchemyError:
        parser.error(
            "Database operation failed. Check migrations, permissions and available storage; parameters redacted."
        )


if __name__ == "__main__":
    main()
