from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from crous_queue.network import parse_trusted_proxies


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CQ_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "demo", "production"] = "development"
    database_url: str = "sqlite:///.local/development.db"
    session_secret: str = ""
    ip_secret: str = ""
    admin_token: str = ""
    origin: str = "http://127.0.0.1:8000"
    secure_cookies: bool = False
    map_tiles: Literal["osm", "none"] = "osm"
    port: int = Field(default=8000, ge=1024, le=65535)
    # Reverse proxies whose forwarding header is believed; empty trusts none.
    trusted_proxies: str = ""
    forwarded_header: Literal["x-forwarded-for", "forwarded"] = "x-forwarded-for"
    # Live estimates/observations counted per coarse network per freshness window.
    network_estimate_cap: int = Field(default=2, ge=1, le=10)
    # Hard ceiling per coarse network per hour and action (NAT-tolerant).
    network_hourly_limit: int = Field(default=120, ge=10, le=10000)

    @model_validator(mode="after")
    def safe_configuration(self) -> "Settings":
        if min(len(self.session_secret), len(self.ip_secret)) < 32:
            raise ValueError(
                "Set CQ_SESSION_SECRET and CQ_IP_SECRET to independent random 32+ character values."
            )
        if self.session_secret == self.ip_secret or (
            self.admin_token
            and self.admin_token in {self.session_secret, self.ip_secret}
        ):
            raise ValueError("Session and IP secrets must differ.")
        try:
            parse_trusted_proxies(self.trusted_proxies)
        except ValueError:
            raise ValueError(
                "Set CQ_TRUSTED_PROXIES to comma-separated proxy IP addresses or CIDR networks, or leave it empty to trust none."
            ) from None
        parsed_url = make_url(self.database_url)
        if parsed_url.drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError(
                "Use sqlite:/// or postgresql+psycopg:// for the database URL."
            )
        database = Path(parsed_url.database or "").name
        if (
            self.environment in {"test", "demo", "development"}
            and self.environment not in database
        ):
            raise ValueError(
                f"Use a database explicitly named {self.environment}; refusing an unmarked database."
            )
        if self.environment == "production" and (
            parsed_url.drivername != "postgresql+psycopg"
            or not self.secure_cookies
            or not self.origin.startswith("https://")
            or len(self.admin_token) < 32
        ):
            raise ValueError(
                "Production requires PostgreSQL, HTTPS, secure cookies and a separate random admin token."
            )
        return self


def load_settings(env_file: Path = Path(".env")) -> Settings:
    # A per-call subclass keeps profile selection explicit without mutating global config.
    class ProfileSettings(Settings):
        model_config = SettingsConfigDict(
            env_prefix="CQ_", env_file=env_file, extra="ignore"
        )

    try:
        return ProfileSettings()
    except ValidationError as error:
        messages = [
            item["msg"]
            for item in error.errors(include_input=False, include_context=False)
        ]
        raise ValueError(
            "Invalid Crous Queue configuration: " + "; ".join(messages)
        ) from None
