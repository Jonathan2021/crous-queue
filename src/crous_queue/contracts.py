from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class VenueView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    region: str
    source_name: str
    source_type: str
    name: str
    venue_type: str
    address: str
    access: str
    hours: str
    zone: str
    source_closing: str
    source_opening: str
    source_timestamp: datetime | None
    last_seen_at: datetime
    source_url: str
    license: str


VenueType = Literal["restaurant", "cafeteria", "administrative", "other", "all"]


QueueKind = Literal["student", "staff", "unspecified"]


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["estimate", "completed"]
    minutes: Annotated[int, Field(strict=True, ge=0, le=120)]
    observed_at: AwareDatetime
    queue_kind: QueueKind
    idempotency_key: Annotated[
        str, Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    ]


class TimerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    venue_id: Annotated[str, Field(min_length=1, max_length=100)]
    queue_kind: QueueKind
    idempotency_key: Annotated[
        str, Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    ]


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    venue_id: str
    queue_kind: str
    kind: str
    minutes: int
    observed_at: datetime
    received_at: datetime
    source_window_start: datetime | None


class WaitState(BaseModel):
    state: Literal["unknown", "single", "recent", "conflicting"]
    minutes: float | None = None
    count: int = 0
    range: list[int] | None = None
    newest_at: datetime | None = None
    expires_at: datetime | None = None
    server_now: datetime
    completed: list[ReportView] = []
    estimates: list[ReportView] = []


class FlagInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal["suspected_false", "wrong_queue", "outdated"]


class HideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationale: Annotated[str, Field(min_length=8, max_length=500)]
    expected_version: Annotated[int, Field(strict=True, ge=0)]
