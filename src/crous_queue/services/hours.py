"""Conservative official schedule interpretation; never infer hours from waits."""

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from crous_queue.models import OfficialHours, Venue
from crous_queue.services.directory import REGIONS, folded, plain_text

MAPPINGS = {
    "paris:r177": ("https://www.crous-paris.fr/restaurant/ru-cuvier/", "RU Cuvier"),
    "paris:r175": ("https://www.crous-paris.fr/restaurant/ru-chatelet/", "RU Châtelet"),
}
MAX_BYTES = 500_000
TTL = timedelta(hours=24)
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
TIME = r"(\d{1,2})[h:](\d{2})?"
SPAN = TIME + r"\s*(?:a|[-–])\s*" + TIME


class Schedule(BaseModel):
    weekly: dict[str, list[tuple[str, str]]]
    exceptions: dict[str, list[tuple[str, str]]] = Field(default_factory=dict)


def parse_schedule(raw: str) -> Schedule | None:
    """Only explicit weekday time ranges and dated closures are supported.

    Unknown exception language invalidates interpretation, not the retained text.
    Non-hours prose (access/Izly) must be separated by the website adapter.
    """
    text = folded(plain_text(raw))
    exceptions: dict[str, list[tuple[str, str]]] = {}
    for closure in re.finditer(r"ferme le (\d{2}/\d{2}/\d{4})", text):
        try:
            day = datetime.strptime(closure[1], "%d/%m/%Y").date().isoformat()
        except ValueError:
            return None
        exceptions[day] = []
    text = re.sub(r"ferme le \d{2}/\d{2}/\d{4}", "", text)
    if re.search(r"ferm|sauf|exception|vacanc|ferie|travaux", text):
        return None
    match = re.fullmatch(
        r"\s*du ("
        + "|".join(DAYS)
        + r") au ("
        + "|".join(DAYS)
        + r") (?:de )?("
        + SPAN
        + r"(?:\s*(?:et|,)\s*(?:de )?"
        + SPAN
        + r")*)[.\s]*",
        text,
    )
    if not match:
        return None
    first, last = DAYS.index(match[1]), DAYS.index(match[2])
    if last < first:
        return None
    intervals: list[tuple[str, str]] = []
    for m in re.finditer(SPAN, match[3]):
        h1, m1, h2, m2 = int(m[1]), int(m[2] or 0), int(m[3]), int(m[4] or 0)
        if max(h1, h2) > 23 or max(m1, m2) > 59 or (h1, m1) >= (h2, m2):
            return None
        intervals.append((f"{h1:02}:{m1:02}", f"{h2:02}:{m2:02}"))
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:], strict=False)):
        return None
    return Schedule(
        weekly={str(i): intervals if first <= i <= last else [] for i in range(7)},
        exceptions=exceptions,
    )


def timezone_for(venue: Venue) -> str | None:
    if venue.region == "reunion":
        if -22 <= venue.latitude <= -20 and 55 <= venue.longitude <= 56:
            return "Indian/Reunion"
        if -14 <= venue.latitude <= -12 and 44 <= venue.longitude <= 46:
            return "Indian/Mayotte"
        return None
    if venue.region == "antilles.guyane":
        if 2 <= venue.latitude <= 6 and -55 <= venue.longitude <= -51:
            return "America/Cayenne"
        if 14 <= venue.latitude <= 15 and -62 <= venue.longitude <= -60:
            return "America/Martinique"
        if 15 <= venue.latitude <= 19 and -64 <= venue.longitude <= -60:
            return "America/Guadeloupe"
        return None
    return "Europe/Paris" if venue.region in REGIONS else None


@dataclass(frozen=True)
class HoursDocument:
    payload: bytes
    source_timestamp: datetime | None = None


class HoursProvider(Protocol):
    def fetch(self, venue_id: str) -> HoursDocument: ...


class FixtureHoursProvider:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads

    def fetch(self, venue_id: str) -> HoursDocument:
        return HoursDocument(self.payloads[venue_id])


class HTTPHoursProvider:
    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self.transport = transport

    def fetch(self, venue_id: str) -> HoursDocument:
        if venue_id not in MAPPINGS:
            raise ValueError("No reviewed official website mapping for this venue ID.")
        url = MAPPINGS[venue_id][0]
        # Redirect bound is zero; an operator must review any moved mapping.
        with httpx.Client(
            timeout=10,
            follow_redirects=False,
            trust_env=False,
            transport=self.transport,
        ) as client:
            with client.stream(
                "GET", url, headers={"User-Agent": "CrousQueue/official-hours-local"}
            ) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError(
                            "Official page exceeds 500 KB; last-good schedule retained."
                        )
                modified = response.headers.get("last-modified")
                try:
                    timestamp = parsedate_to_datetime(modified) if modified else None
                    if timestamp and timestamp.tzinfo is None:
                        timestamp = None
                except ValueError:
                    timestamp = None
                return HoursDocument(bytes(body), timestamp)


def website_schedule(
    venue_id: str, payload: bytes, local_date: str | None = None
) -> tuple[str, Schedule | None]:
    if len(payload) > MAX_BYTES:
        raise ValueError("Official page exceeds 500 KB.")
    html = payload.decode("utf-8", errors="strict")
    # Inspect the venue's own section, excluding nearby venue hours/badges.
    own = re.split(r"Restaurants\s*/\s*Caf", html, maxsplit=1, flags=re.I)[0]
    title = re.search(r"<h1\b[^>]*>(.*?)</h1>", own, re.S | re.I)
    if not title or folded(MAPPINGS[venue_id][1]) not in folded(plain_text(title[1])):
        raise ValueError("Official page identity changed; inspect the mapping.")
    sections = re.split(r"<h[23]\b[^>]*>(.*?)</h[23]>", own, flags=re.S | re.I)
    raw = ""
    for index in range(1, len(sections) - 1, 2):
        if folded(plain_text(sections[index])) == "horaires":
            # Keep raw sanitized source; don't mistake an Izly desk for meal service.
            raw = plain_text(sections[index + 1])
            schedule_text = re.split(r"accessible|un guichet", folded(raw), maxsplit=1)[
                0
            ].strip()
            schedule = parse_schedule(schedule_text)
            # Any closure notice outside the parsed schedule makes this uncertain.
            main_text = folded(plain_text(own[title.start() :]))
            daily_closed = (
                "ferme aujourd'hui" in main_text or "ferme aujourd’hui" in main_text
            )
            if daily_closed and schedule and local_date:
                schedule.exceptions[local_date] = []
                main_text = main_text.replace("ferme aujourd'hui", "").replace(
                    "ferme aujourd’hui", ""
                )
            notices = re.findall(
                r"(?:ferm\w*|exception\w*|vacanc\w*|ferie\w*)[^.]{0,140}", main_text
            )
            if any(notice not in folded(schedule_text) for notice in notices):
                schedule = None
            return raw, schedule
    raise ValueError("Official hours section missing; source layout may have changed.")


class HoursImporter:
    def __init__(self, engine: Engine, clock: Callable[[], datetime]) -> None:
        self.engine, self.clock = engine, clock

    def refresh(
        self, provider: HoursProvider, venue_ids: Sequence[str] = tuple(MAPPINGS)
    ) -> dict[str, str]:
        if len(venue_ids) > 20 or any(v not in MAPPINGS for v in venue_ids):
            raise ValueError(
                "Refresh requires at most 20 reviewed venue IDs; edit MAPPINGS after identity review."
            )
        results: dict[str, str] = {}
        for venue_id in venue_ids:
            now = self.clock()
            with Session(self.engine) as db, db.begin():
                if db.get(Venue, venue_id) is None:
                    raise ValueError(
                        "Import the directory before refreshing official hours."
                    )
                cached = db.get(OfficialHours, venue_id) or OfficialHours(
                    venue_id=venue_id,
                    official_url=MAPPINGS[venue_id][0],
                    provider="crous-paris-html-v1",
                    raw_schedule="",
                    normalized="null",
                    payload_sha256="",
                    error="",
                )
                cached.attempted_at = now
                try:
                    document = provider.fetch(venue_id)
                    raw, schedule = website_schedule(
                        venue_id,
                        document.payload,
                        now.astimezone(ZoneInfo("Europe/Paris")).date().isoformat(),
                    )
                    cached.last_attempt_raw = raw
                    cached.last_attempt_sha256 = sha256(document.payload).hexdigest()
                    if schedule is None:
                        cached.error = "schedule_unparseable"
                        results[venue_id] = "unknown"
                        db.add(cached)
                        continue
                    cached.official_url = MAPPINGS[venue_id][0]
                    cached.retrieved_at, cached.source_timestamp = (
                        now,
                        document.source_timestamp,
                    )
                    cached.raw_schedule = raw
                    cached.normalized = (
                        schedule.model_dump_json() if schedule else "null"
                    )
                    cached.payload_sha256 = sha256(document.payload).hexdigest()
                    cached.error = "" if schedule else "schedule_unparseable"
                    results[venue_id] = "good" if schedule else "unknown"
                except (ValueError, KeyError, httpx.HTTPError):
                    cached.error = "refresh_failed_check_mapping_or_source"
                    results[venue_id] = "failed"
                db.add(cached)
        return results


class HoursState(BaseModel):
    today: Literal["open", "closed", "unknown"] = "unknown"
    now: Literal["open", "closed", "unknown"] = "unknown"
    freshness: str = "unknown"
    timezone: str | None
    local_date: str
    intervals: list[str] = Field(default_factory=list)
    checked_at: datetime | None = None
    source_timestamp: datetime | None = None
    official_url: str
    raw_schedule: str = ""
    caveat: str = "Horaires inconnus. Vérifiez auprès du CROUS."
    expires_at: datetime | None = None


def hours_state(db: Session, venue: Venue, now: datetime) -> HoursState:
    zone = timezone_for(venue)
    local = now.astimezone(ZoneInfo(zone)) if zone else now
    cached = db.get(OfficialHours, venue.id)
    s = HoursState(
        timezone=zone,
        local_date=local.date().isoformat(),
        official_url=MAPPINGS.get(venue.id, (venue.source_url, ""))[0],
    )
    schedule = parse_schedule(venue.hours)
    s.raw_schedule, s.checked_at, s.source_timestamp = (
        venue.hours,
        venue.last_seen_at,
        venue.source_timestamp,
    )
    error = ""
    if cached:
        schedule = (
            Schedule.model_validate(json.loads(cached.normalized))
            if cached.normalized != "null"
            else None
        )
        s.raw_schedule, s.checked_at, s.source_timestamp = (
            cached.raw_schedule,
            cached.retrieved_at,
            cached.source_timestamp,
        )
        s.official_url, error = cached.official_url, cached.error
    if not zone or not schedule or not s.checked_at:
        if error:
            s.caveat = "Source indisponible ou horaires non interprétables. Dernières données conservées."
        return s
    intervals = schedule.exceptions.get(
        s.local_date, schedule.weekly.get(str(local.weekday()), [])
    )
    s.intervals = [f"{start}–{end}" for start, end in intervals]
    midnight = (local + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    s.expires_at = min(s.checked_at + TTL, midnight)
    if (
        error
        or now - s.checked_at >= TTL
        or s.checked_at.astimezone(ZoneInfo(zone)).date() != local.date()
    ):
        s.freshness = "stale"
        s.caveat = "Horaires anciens ou actualisation échouée : ouverture aujourd’hui non vérifiée."
        return s
    feed_schedule = parse_schedule(venue.hours)
    if (
        cached
        and feed_schedule
        and now - venue.last_seen_at < TTL
        and feed_schedule != schedule
    ):
        s.freshness = "conflict"
        s.caveat = "Sources officielles divergentes : vérifiez le site du CROUS."
        return s
    s.freshness = "fresh"
    s.today = "open" if intervals else "closed"
    clock = local.strftime("%H:%M")
    s.now = (
        "open" if any(start <= clock < end for start, end in intervals) else "closed"
    )
    s.caveat = "Selon les horaires publiés ; une fermeture exceptionnelle non annoncée reste possible."
    return s
