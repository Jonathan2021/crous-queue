# Crous Queue — MVP decision

2026-10-07. GO for a national-directory, crowd-reporting MVP. All 26 official feeds were fetched: 972 unique region-scoped venue IDs, including restaurants, cafeterias and other types. This is observed directory coverage, not proof every venue is open or every university restaurant is listed. Seed Cuvier/Châtelet for a local pilot without blocking the build on lunch observations.

## Job

Find a university restaurant and see or report a recent wait in seconds, with unknown/stale states that cannot be confused with zero waiting.

## Evidence and limits

CNOUS feed license is fr-lo (Open Licence); all 26 current resource URLs returned parseable XML. Paris has separate RU Cuvier paris:r177, RU Châtelet paris:r175, Cuvier cafeteria paris:r889 and administrative Jussieu paris:r1149. Never merge these by coordinates. HTTPS on the legacy Paris feed returned 404 while the catalog-declared HTTP feed succeeded; import server-side with strict bounds and plain-text normalization. Existing Affluences and CrousRadar establish strong overlap; adoption remains an experiment.

## MVP boundary

National searchable directory; restaurant/cafeteria filters; manual city/search selection with optional one-time approximate geolocation; favorite venues stored locally; recent crowd-reported wait; report current estimated remaining wait or start/finish an own wait timer; freshness, report count and disagreement; report-abuse action and small admin moderation view. No signup to view or contribute in initial MVP; signed pseudonymous device session and strict throttles.

Do not infer seats, menus, queue length, future wait or walking-time savings. Do not import Affluences live data without an authorized feed. Menus and predictions are later options. Keep private/staff-only venues visibly identified when source access information is available. Public reports contain no names, free text, photos or location traces.

## Build versus adoption

Five lunch days at Cuvier/Châtelet after a usable app exists: freshness coverage at fixed checks, estimate versus own completed wait (clearly different measures), contribution friction and repeat contributors. No mandatory interviews before implementation. National venue availability does not imply national live data. If reporting stays sparse, keep honest unknowns and test distribution rather than adding fictitious prediction.

These are implementation-ready plans, not a delivered application. Technical probes are explicitly scoped. Demand, launch and paid services are not assumed.
