from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CQ_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "demo", "production"] = "development"
    database_url: str = "sqlite:///.local/development.db"
    session_secret: str = ""
    ip_secret: str = ""
    admin_token: str = ""
    origin: str = "http://127.0.0.1:8000"
    secure_cookies: bool = False
    port: int = Field(default=8000, ge=1024, le=65535)

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
