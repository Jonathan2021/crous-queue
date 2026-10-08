# Crous Queue — implementation contract

Python FastAPI/SQLAlchemy/Alembic modular monolith; responsive server-rendered PWA shell, SQLite local and PostgreSQL for public concurrency. App owns no precise location-history table. DirectoryImporter interface: fixed catalog/resource allowlist, timeout, payload/row limits, XML parser with external entities disabled, reject nonfinite/out-of-range coordinates, normalize HTML to safe plain text, never fetch embedded image/contact URLs. Store source timestamp and fetched_at separately; catalog updated_at is not proof venue hours are current.

Venue key is region + ':' + original_id, unique. Store source name/type/coordinates, cautiously normalized address/access/hours text, active/closed flags as source data, last_seen_at, source_url, license. Partial feed failure retains last-good region data and flags stale coverage; missing in one refresh is not deletion. Keep administrative/restaurant/cafeteria identities separate even at identical coordinates. Import all listed venues, default to restaurant type in UI and expose other types explicitly.

WaitReport(id, venue_id, queue_kind, kind=estimate|completed, minutes, observed_at, received_at, source_window_start, device_hash, idempotency_key, visibility). Use server received time; client observation time cannot be >2min future or >60min old. Estimate: “how much longer do you think someone joining now would wait?” integer 0–120. Completed timer: measured own wait, preserve join and finish; label as completed experience ending X minutes ago and do not silently mix it with current estimates. Only estimate reports enter initial live median. A completed report remains a separate recent observation because its queue state may have changed while waiting.

Aggregation v1: only visible estimates with age <15min, latest per device+venue+queue; zero is a real report, no observations is unknown. One report is labeled unconfirmed single report. Two+ reports use median, show range/count and newest age; range >15min displays conflicting range instead of a precise aggregate. Timestamp expiry enforced on server reads and client timer, not only scheduled cleanup. Start with separate queues only where real queue classes are known; never pool staff/student reports.

Abuse: signed random device cookie, one contribution per venue per 2min; report replaces that device's aggregate contribution; coarse salted IP rate limiting with short retention, aggregate counters, admin hide with audit. This limits repeats, not Sybil attacks. No device fingerprinting. Raw reports default 7-day retention, rate-limit identifiers <=24h; document any change. Moderation endpoint requires separate admin authentication. No blanket credibility score from number of reports.

## Interface contract

GET /venues?q=&region=&type=restaurant; GET /venues/{id}; GET /venues/{id}/waits; POST /venues/{id}/reports {kind, minutes, observed_at, queue_kind, idempotency_key}; POST /timers/start and /timers/{id}/finish bound to device; POST /reports/{id}/flags with enum reason; admin POST /reports/{id}/hide with rationale. Device/IP rate limits and payload validation apply before writes. No endpoint lists raw device identities.

## User flow

Home: search university/city/restaurant and favorites. Venue: name, type/access, recent wait state, timestamp and report count, large “Report a wait” button, quick values 0/5/10/15/20/30 plus numeric input. Ask whether this is an estimate now or a completed wait. Empty state says “No recent report”, never “0 min”. Confirmation is one tap after value selection; show new aggregate and expiry. Cuvier cafeteria/admin rows are clearly distinguished in search. FR first, installable browser app, no app-store prerequisite.

## Common release requirements

Explicit configuration and secrets outside Git; UTC persistence with correct local rendering; schema migrations and backup/restore; structured redacted errors; authorization and idempotency on writes; deterministic tests and a real browser replay; local fixture providers. Bind development to loopback. Before public release prepare cost limits, resource inventory and teardown plus the exact deployment payload for approval. No runtime import from Foundry, learning or another venture.


## Current implementation and developer entry point

The modular monolith is implemented under `src/crous_queue/`. Read [the actual module/clock/provider map](../DEVELOPMENT.md), [the installed distribution contract](../RELEASE.md), [operations](../OPERATIONS.md) and [current release readiness](RELEASE_READINESS.md). Python 3.13 and `uv.lock` govern source/CI setup; no Foundry/learning runtime imports exist.

Installed CLI resolves authoritative package migrations and the dated snapshot independently of cwd. Wheel and full source kit are complete supported local distributions with separate configuration/data. Explicit migration remains required; app creation performs no DDL. Disposable core/browser and artifact harnesses establish the documented local behavior; external providers are retained/synthetic in routine verification. PostgreSQL/public concurrency and physical usefulness remain distinct unpassed gates.

Initial Q01–Q05 build order and dated acceptance are preserved in `ROADMAP.md`, decision/ADRs and `IMPLEMENTATION_LOG.md`. Subsequent Q06/Q07 reviews retain observed failures and exact current checks rather than treating synthetic or prior green outputs as demand/field evidence. The current maintenance entry point is `DEVELOPMENT.md`; no pending scaffold instructions or unrelated venture-specific bundle apply.

## Remarks continuation (2026-10-08)

`services/hours.py` owns the replaceable `HoursProvider`, bounded website refresh,
conservative website/feed interpretation and injected-clock local status. Migration
0004 adds `official_hours` without altering the directory or wait data. See
ADR-0006 for freshness, exceptions, timezone and source-priority rules. Opening
status never consumes crowd reports. The user has authorized availability and
moderated comments as a later independent dimension (Q10).

Q09 adds `api/map.py` plus a self-hosted Leaflet adapter in `static/map.js`.
The map and visible list share one dataset/clock and the existing wait aggregation.
Venue coordinates only go to the public-data API. ADR-0007 specifies provider
policy, queue palette, coincident identities, transient location and offline fallback.

Q10 extends `ReportInput` and `WaitReport` via migration 0005 with nullable
independent observations and bounded pending comments. `services/availability.py`
owns per-dimension expiry/cohort rules; wait aggregation ignores availability-only
reports. Existing moderation service adds versioned comment actions. ADR-0008
defines public/private text boundaries, retry compatibility and migration recovery.
