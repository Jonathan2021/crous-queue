from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("A timezone-aware UTC timestamp is required.")
            return value.astimezone(UTC)
        return value

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        return (
            value.replace(tzinfo=UTC)
            if value is not None and value.tzinfo is None
            else value.astimezone(UTC)
            if value is not None
            else None
        )


def make_engine(url: str) -> Engine:
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 20}
        if url.startswith("sqlite")
        else {},
        pool_pre_ping=True,
        hide_parameters=True,
    )
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def configure(dbapi: Any, record: Any) -> None:
            dbapi.isolation_level = None
            cursor = dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        @event.listens_for(engine, "begin")
        def begin(connection: Any) -> None:
            # Serialize local writers across processes, including throttle checks.
            connection.exec_driver_sql("BEGIN IMMEDIATE")

    return engine
