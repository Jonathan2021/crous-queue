# ADR-0006 — Official hours and expanded remarks scope

2026-10-08, accepted for Q08. The user's unchanged root `remarks` and
`REMARKS_HANDOFF.md` authorize hours, map and independent availability/comments.
They supersede the original exclusions of seats and free text; Q09–Q11 remain
conditional until their predecessor is accepted. Historical checkpoints remain.

Hours use a replaceable `HoursProvider` and a separate cache keyed by venue ID.
Only RU Cuvier (`paris:r177`) and RU Châtelet (`paris:r175`) have reviewed website
mappings. A cafeteria at identical coordinates is not an alias. The existing
national feed `hours` text is interpreted by the same conservative normalizer.
Snapshot `opening` strings such as `010` and `closing` flags are retained source
fields, not clock times or proof of exceptional closure. The retained 972-row
snapshot has no usable hours text; importing it alone gives unknown statuses.

Website extraction reads the named venue's hours section, excludes nearby venues
and Izly desk hours, and verifies its title. Supported grammar: explicit French
weekday range and one or more daytime service intervals; explicit `Fermé le
DD/MM/YYYY` closures, and the venue’s own `Fermé aujourd’hui` badge bound to
the retrieval local date. Other exception/closure language or changed grammar gives
unknown. No inferred public-holiday calendar. Revisit with new reviewed fixtures
before expanding grammar or mapping, never silently guess.

Store sanitized raw schedule, normalized weekly schedule/dated exceptions, payload
hash, official URL, adapter version, optional Last-Modified, retrieval time and
last attempt/failure. Migration 0006 preserves rejected-attempt text/hash separately
so a newly unparseable page cannot erase the last good schedule. Response body is capped at 500 KB, timeout 10s, fixed HTTPS
mappings, zero redirects/proxies, at most 20 venues per command. Network happens
only in `refresh-hours`, never in page reads. An unsuccessful attempt retains
last-good data and marks status uncertain. Source conflict with fresh parseable
feed text is unknown. Retrieval is not publication time.

Opening today and opening now are separate schedule-based statements, always
qualified by the possibility of unannounced exceptions. A check must be on the
same venue-local date and less than 24h old; otherwise show historical intervals
and unknown current status. Read time and a one-minute browser refresh enforce
freshness. Intervals are start-inclusive/end-exclusive. UTC persistence with
IANA Europe/Paris, Indian/Reunion, America/Cayenne, America/Martinique and
America/Guadeloupe, and Indian/Mayotte when coordinates identify Mayotte. Overseas grouping uses bounded venue coordinate regions;
unrecognized geography has unknown timezone, never a guessed Paris offset.

No demand or physical-use conclusion follows. Feed text is Open Licence/fr-lo.
Website pages retain their source copyright; only factual hours and provenance
are extracted, with links. No website-wide reuse license is inferred.
