"""Bounded, allowlisted directory import. Source documents are untrusted data."""

import json
import math
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

import httpx
from defusedxml import ElementTree
from sqlalchemy import Engine, Select, select
from sqlalchemy.orm import Session

from crous_queue.models import Coverage, Venue

REGIONS = (
    "versailles",
    "toulouse",
    "strasbourg",
    "normandie",
    "reunion",
    "rennes",
    "reims",
    "poitiers",
    "paris",
    "orleans.tours",
    "nice",
    "nantes",
    "nancy.metz",
    "montpellier",
    "lyon",
    "limoges",
    "lille",
    "grenoble",
    "bfc",
    "creteil",
    "corte",
    "clermont.ferrand",
    "bordeaux",
    "antilles.guyane",
    "amiens",
    "aix.marseille",
)
ALLOWLIST = {
    region: f"http://webservices-v2.crous-mobile.fr/feed/{region}/externe/resto.xml"
    for region in REGIONS
}
MAX_BYTES = 2_000_000
MAX_ROWS = 2000


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "iframe", "object"}:
            self.blocked += 1
        if tag in {"p", "br", "div", "li"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "iframe", "object"} and self.blocked:
            self.blocked -= 1
        self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.blocked:
            self.parts.append(data)


def plain_text(value: str) -> str:
    parser = TextParser()
    parser.feed(value[:20000])
    return " ".join("".join(parser.parts).split())[:4000]


def folded(value: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(c)
    )


def venue_query(
    q: str = "", region: str = "", venue_type: str = "all"
) -> Select[tuple[Venue]]:
    """Shared directory search: folded literal substring, exact region, type unless "all"."""
    query = select(Venue)
    if q:
        query = query.where(Venue.search_text.contains(folded(q), autoescape=True))
    if region:
        query = query.where(Venue.region == region)
    if venue_type != "all":
        query = query.where(Venue.venue_type == venue_type)
    return query


@dataclass(frozen=True)
class DirectoryRow:
    original_id: str
    source_name: str
    source_type: str
    latitude: float
    longitude: float
    zone: str = ""
    address: str = ""
    access: str = ""
    hours: str = ""
    closing: str = ""
    opening: str = ""
    source_timestamp: datetime | None = None

    @property
    def name(self) -> str:
        return plain_text(self.source_name)

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", self.original_id)
            or len(self.original_id) > 60
            or ":" in self.original_id
            or not self.name
        ):
            raise ValueError("Feed row needs a bounded original ID and nonempty name.")
        if (
            not math.isfinite(self.latitude)
            or not -90 <= self.latitude <= 90
            or not math.isfinite(self.longitude)
            or not -180 <= self.longitude <= 180
        ):
            raise ValueError("Feed coordinate is nonfinite or out of range.")


def info_section(value: str, label: str) -> str:
    sections = re.split(r"<h2[^>]*>(.*?)</h2>", value[:20000], flags=re.I | re.S)
    for index in range(1, len(sections) - 1, 2):
        if folded(plain_text(sections[index])) == label:
            return plain_text(sections[index + 1])
    return ""


def parse_feed(region: str, payload: bytes) -> list[DirectoryRow]:
    if region not in ALLOWLIST or len(payload) > MAX_BYTES:
        raise ValueError("Unknown region or payload exceeds 2 MB.")
    try:
        root = ElementTree.fromstring(
            payload, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
        nodes = root.findall(".//resto")
        if not nodes or len(nodes) > MAX_ROWS:
            raise ValueError(
                "Feed is empty or exceeds the row limit; last-good data retained."
            )
        rows = []
        for node in nodes:

            def field(name: str, node: Any = node) -> str:
                return str(node.get(name) or node.findtext(name, default="") or "")

            rows.append(
                DirectoryRow(
                    original_id=node.get("id", "") or field("id"),
                    source_name=field("title") or field("nom"),
                    source_type=field("type"),
                    latitude=float(field("lat")),
                    longitude=float(field("lon")),
                    zone=plain_text(field("zone")),
                    address=plain_text(
                        field("adresse")
                        or re.sub(
                            r"<h2[^>]*>.*?</h2>",
                            "",
                            field("contact"),
                            flags=re.I | re.S,
                        )
                    ),
                    access=plain_text(
                        field("acces") or info_section(field("infos"), "pratique")
                    ),
                    hours=plain_text(
                        field("horaires") or info_section(field("infos"), "horaires")
                    ),
                    closing=field("closing")[:100],
                    opening=field("opening")[:300],
                )
            )
        if len({row.original_id for row in rows}) != len(rows):
            raise ValueError("Duplicate original IDs within feed.")
        return rows
    except Exception as error:
        raise ValueError("Invalid regional XML; last-good data retained.") from error


class DirectoryProvider(Protocol):
    def fetch(self, region: str) -> bytes: ...


class FixtureProvider:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads

    def fetch(self, region: str) -> bytes:
        return self.payloads[region]


class HTTPDirectoryProvider:
    def fetch(self, region: str) -> bytes:
        url = ALLOWLIST[region]
        # No redirects, environment proxies or embedded links; fixed public host only.
        with httpx.Client(
            timeout=10, follow_redirects=False, trust_env=False
        ) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError("Regional feed exceeds 2 MB.")
                return bytes(body)


class DirectoryImporter:
    def __init__(self, engine: Engine, clock: Callable[[], datetime]) -> None:
        self.engine = engine
        self.clock = clock

    def save_region(
        self, region: str, rows: list[DirectoryRow], digest: str, fetched: datetime
    ) -> None:
        with Session(self.engine) as db, db.begin():
            for row in rows:
                venue_id = f"{region}:{row.original_id}"
                venue = db.get(Venue, venue_id) or Venue(id=venue_id)
                source_type = folded(row.source_type)
                if "administrati" in folded(row.name + row.source_type):
                    venue_type = "administrative"
                elif "restaurant" in source_type or source_type in {
                    "libre-service",
                    "brasserie",
                }:
                    venue_type = "restaurant"
                elif "cafeteria" in source_type:
                    venue_type = "cafeteria"
                else:
                    venue_type = "other"
                values: dict[str, Any] = dict(
                    region=region,
                    source_id=row.original_id,
                    source_name=row.source_name,
                    source_type=row.source_type,
                    name=row.name,
                    venue_type=venue_type,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    zone=row.zone,
                    address=row.address,
                    access=row.access,
                    hours=row.hours,
                    source_closing=row.closing,
                    source_opening=row.opening,
                    source_timestamp=row.source_timestamp,
                    last_seen_at=fetched,
                    source_url=ALLOWLIST[region],
                    license="fr-lo",
                    search_text=folded(
                        " ".join([row.name, row.zone, row.address, region, row.access])
                    ),
                )
                for key, value in values.items():
                    setattr(venue, key, value)
                db.add(venue)
            coverage = db.get(Coverage, region) or Coverage(region=region)
            coverage.status, coverage.fetched_at, coverage.last_good_at = (
                "good",
                fetched,
                fetched,
            )
            coverage.payload_sha256, coverage.error = digest, ""
            db.add(coverage)

    def import_snapshot(self, path: Path) -> None:
        payload = path.read_bytes()
        records = json.loads(payload)
        grouped: dict[str, list[DirectoryRow]] = {}
        if len(records) > len(REGIONS) * MAX_ROWS:
            raise ValueError("Snapshot row limit exceeded.")
        for value in records:
            region = value["region"]
            if (
                region not in ALLOWLIST
                or value["source_url"] != ALLOWLIST[region]
                or value["id"] != f"{region}:{value['source_id']}"
            ):
                raise ValueError(
                    "Snapshot provenance does not match the declared allowlist."
                )
            grouped.setdefault(region, []).append(
                DirectoryRow(
                    original_id=value["source_id"],
                    source_name=value["name"],
                    source_type=value["type"],
                    latitude=float(value["lat"]),
                    longitude=float(value["lon"]),
                    zone=plain_text(value["zone"]),
                    closing=value["closing"],
                    opening=value["opening"],
                )
            )
        fetched = datetime(
            2026, 10, 7, tzinfo=UTC
        )  # Retained snapshot date, not a live refresh.
        for region, rows in grouped.items():
            if len({r.original_id for r in rows}) != len(rows):
                raise ValueError("Snapshot contains duplicate regional IDs.")
            self.save_region(region, rows, sha256(payload).hexdigest(), fetched)

    def refresh(
        self, provider: DirectoryProvider, *, regions: Sequence[str] = REGIONS
    ) -> dict[str, str]:
        result = {}
        for region in regions:
            if region not in ALLOWLIST:
                raise ValueError(
                    "Unknown region; only catalog-declared feeds are allowed."
                )
            fetched = self.clock()
            try:
                payload = provider.fetch(region)
                self.save_region(
                    region,
                    parse_feed(region, payload),
                    sha256(payload).hexdigest(),
                    fetched,
                )
                result[region] = "good"
            except (ValueError, KeyError, httpx.HTTPError):
                with Session(self.engine) as db, db.begin():
                    coverage = db.get(Coverage, region) or Coverage(
                        region=region, last_good_at=None, payload_sha256=""
                    )
                    coverage.status, coverage.fetched_at, coverage.error = (
                        "stale",
                        fetched,
                        "regional_feed_unavailable_or_invalid",
                    )
                    db.add(coverage)
                result[region] = "stale"
        return result
