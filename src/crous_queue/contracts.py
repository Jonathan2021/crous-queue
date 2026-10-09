from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


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


AvailabilityValue = Literal["available", "unavailable", "not_offered", "unknown"]


class ReportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["estimate", "completed", "availability"]
    minutes: Annotated[int, Field(strict=True, ge=0, le=120)] | None = None
    observed_at: AwareDatetime
    queue_kind: QueueKind
    idempotency_key: Annotated[
        str, Field(min_length=8, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    ]

    grill: AvailabilityValue | None = None
    vegetarian: AvailabilityValue | None = None
    standard: AvailabilityValue | None = None
    seating: AvailabilityValue | None = None
    comment: Annotated[str, Field(max_length=280)] = ""

    @model_validator(mode="after")
    def independent_dimensions(self) -> "ReportInput":
        self.comment = self.comment.strip()
        if any(ord(c) < 32 and c not in "\n\t" for c in self.comment):
            raise ValueError("Comment must be plain text without control characters.")
        if (self.kind == "availability") != (self.minutes is None):
            raise ValueError(
                "Wait reports need minutes; availability-only reports must omit them."
            )
        if (
            self.kind == "availability"
            and not self.comment
            and all(
                v is None
                for v in (self.grill, self.vegetarian, self.standard, self.seating)
            )
        ):
            raise ValueError(
                "Choose at least one observation or write a short comment."
            )
        return self


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
    minutes: int | None
    comment_status: str | None = None
    observed_at: datetime
    received_at: datetime
    source_window_start: datetime | None
    # Per-response ordinal of the coarse network ("s1", "s2"); never a hash.
    source: str | None = None


class WaitState(BaseModel):
    state: Literal["unknown", "single", "recent", "conflicting"]
    minutes: float | None = None
    # Counted devices, distinct coarse networks among them, and fresh
    # estimates left out because their network exceeded its budget.
    count: int = 0
    sources: int = 0
    excluded: int = 0
    # Freshness times of excluded estimates so clients can expire the notice.
    excluded_observed: list[datetime] = []
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


class NetworkHideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationale: Annotated[str, Field(min_length=8, max_length=500)]


class CommentModerationInput(HideInput):
    action: Literal["approve", "hide", "delete"]
