# Crous Queue — user remarks implementation handoff

Prepared 2026-10-08. Execute Q08–Q11, in order, using Foundry **2026-10-08.1**.
This is an implementation continuation, not another readiness-only audit.

## Authority, baseline and working scope

Read root/repository `AGENTS.md`, the unchanged root `remarks`, this document,
`docs/mvp/RELEASE_READINESS.md`, and the existing decision/architecture/roadmap.
The user explicitly selected these remarks as new product scope. Where they
conflict with earlier MVP exclusions, record the updated decision and implement
the new behavior; do not use the old exclusions to discard these requests.
Preserve `remarks` verbatim and unrelated local work. Update current product
contracts/ADRs and roadmap; retain historical checkpoint documents as history.

The second run is accepted in Foundry. At handoff, local `main` and GitHub `main`
match `699eebf63f8a70eff02b961ae0d541cc2a271741`, with [successful exact-commit CI](https://github.com/Jonathan2021/crous-queue/actions/runs/37772856832).
Only `remarks` was untracked before this coordinator added the new bridge and
handoff. Recheck live Git state before editing; another agent may have advanced it.
Do not repeat the completed release package or mark human evidence gates passed.

First ready work: `e5d292f5-02cd-4d6a-a266-ac413b60e64f`.
Workspace: `81ee3117-de70-411e-9856-07420859ffad`.
Only the first package is ready. Record the later packages as conditional
roadmap nodes, then queue/claim the next one after actual acceptance. Continue
through the full sequence without asking the user to resend this prompt after
each package. Routine scoped local result review is delegated; no invented claims
or acceptance merely to clear a task.

## Required upgraded Foundry workflow

From `/home/jonathan/startup_lab/crous-queue`:

```bash
python3 tools/foundry_agent.py doctor
python3 tools/foundry_agent.py cli agent guide
python3 tools/foundry_agent.py resume
python3 tools/foundry_agent.py start --actor crous-queue-remarks-YOUR_UNIQUE_SESSION --work-id e5d292f5-02cd-4d6a-a266-ac413b60e64f --budget-bytes 100000
```

Doctor must report bridge/contract `2026-10-08.1` and a matching canonical helper
hash. The coordinator installed that helper and updated the local manifest.
Use the existing configured store. If a newer reviewed version is installed,
inspect its guide instead of downgrading it. Read saved context, all relevant
arrivals (page to `next_offset=null`) and the exact full map referenced by
`map_coverage`. Prepare fresh context with relevant evidence IDs before dependent
work; `context_complete` and full-map coverage are different claims. Reuse only
your own interrupted claim with `start --resume-owned`; never steal another one.

After each package use published result/resolution schemas, submit actual
findings/tests/limits, show, preview and resolve with the digest and saved context
map/work/review versions. Fresh evidence can require a fresh context and a
superseding result. Under this upgrade, `superseded` history links the accepted
replacement via `superseded_by`; it does not require repeating that old work.
Use final resolution receipts for new task IDs, not provisional preview IDs.
Report observed Foundry bugs/friction/positive behavior through the feedback
outbox and record the receipt; if none occurred, state that in the result.

## Delivery contract for this continuation

The existing user authorization for scoped commits/pushes to the **private**
`Jonathan2021/crous-queue` repository persists. Commit relevant code, migrations,
tests, bridge, handoff and documentation after review; inspect staged contents
explicitly. Keep credentials, local manifests/stores, environments, private traces,
large generated datasets and unrelated work out. No force-push. If `main` advanced,
reconcile safely. Verify GitHub Actions on the actual final delivered SHA, within
included/no-cost allowance. If allowance or another external dependency prevents
CI, retain a precise incomplete-delivery status and continue independent work.
Do not claim local checks are a substitute for an actual green Actions run.

Finish with a clean-checkout/installed-artifact rehearsal independent of Foundry:
install, migrate, synthetic seed, core browser flow, restart, backup/restore and
upgrade from the current release. Run relevant unit/integration tests, lint/types,
asset checks and browser checks without suppressing failures. Keep network-provider
fixtures deterministic; record bounded live probes separately. Update README,
usage guide, developer guide, environment example, release/version/artifact hashes,
architecture notes for non-obvious rules, and troubleshooting for the new flows.
Maintain the existing CI checks and extend them for meaningful new behavior.

The release report must name **canonical folder, delivery worktree (if any),
branch, local HEAD, remote branch/SHA, residual local changes, CI URL/head/conclusion,
and verified artifact hashes**. A separate worktree delivery is incomplete as a
user handoff unless the original folder is reconciled reversibly or its exact
remaining divergence/recovery path is stated. Preserve local data and dirty work;
never blindly overwrite it to make Git look clean. Distinguish implemented,
committed, pushed, merged, CI-passed and user-observed results.

Public hosting, paid APIs/resources, real invitations/messages and physical-use
or market-validation claims are outside this continuation. Those gates do not
block the authorized local product work. Do not modify OfferCheck, Volley Coach,
Coopain or Foundry runtime as a side effect; send Foundry feedback instead.

## Every remark and its acceptance target

| User request | Package | Visible completion |
| --- | --- | --- |
| Restaurant website connection, hours and open today inline | Q08 | Each venue card/detail shows source-linked hours and an honest local-date status. |
| Nearby map, dark red crowded and light green no wait | Q09 | Map and list share fresh queue observations, a readable legend and unknown/stale states. |
| Grill/vegetarian/standard options, no seats, other free text | Q10 | People can report each dimension independently, see its age, and submit bounded moderated text. |

## Q08 — Official hours and opening status

Reuse `services/directory.py`, `DirectoryRow`, the retained 972-venue directory
and per-venue provenance. The importer already retains `hours`, `opening` and
`closing`; inspect their semantics before adding another data pipeline. The old
weekly `010` fields are not sufficient evidence of exact opening times or today's
exceptional closure. Never equate “no wait reports” with “closed”.

Implement a replaceable official-hours provider and a bounded refresh/import
command. Start with Cuvier and Châtelet website mappings, and use existing feed
data nationally where supported. Preserve venue identity: RU Cuvier and Cafétéria
Cuvier can share coordinates but have different hours/services. Store official
URL, source timestamp if provided, retrieval time, raw schedule/provenance and
normalized schedule/exception interpretation. Missing coverage elsewhere must
remain explicit; do not invent national live-hours coverage from two parsers.

Show “ouvert aujourd'hui” separately from “ouvert maintenant”, today's service
interval(s), last checked date and official link. Use venue-local timezones,
including overseas regions; injected clock tests must cover boundary times,
weekends, exceptions, DST and unknown/unparseable schedules. A stale cached page
is historical evidence, not confirmation of today's status. Source conflict or
failed refresh should retain the last known data with a visible caveat.

Official sources checked during coordination:
- [RU Châtelet](https://www.crous-paris.fr/restaurant/ru-chatelet/)
- [RU Cuvier](https://www.crous-paris.fr/restaurant/ru-cuvier/)
- [Crous Paris directory/map](https://www.crous-paris.fr/se-restaurer/carte/)

Use allowlisted origins, bounded redirects/timeouts/response sizes and sanitized
parsing, with fixtures for source changes. Do not fetch arbitrary user URLs or
make every page view scrape the restaurant site. Document refresh cadence,
offline behavior, provenance/license and how an operator repairs a bad mapping.

## Q09 — Nearby map with honest crowding states

Add map/list views using a small supported map component and the existing venue
coordinates. Choose a documented, replaceable basemap source with attribution,
usage-policy compliance and an offline/failure fallback; no paid account needed.
Opening status and queue crowding are independent dimensions.

Use light green for a fresh zero-wait observation and dark red for the highest
crowding band, with documented intermediate bands drawn from the current wait
model. Always display text/minutes/age as well as color. Unknown and expired
reports are neutral/gray and must never become “no wait”. Preserve current queue
type distinctions and aggregation rules. Marker selection opens the correct
venue/report action; clustered/coincident markers must remain individually usable.

“Around me” requests browser location only when clicked. Denial/unavailability
must leave city/manual-center navigation usable. Use location transiently for
centering/distance; do not retain precise user coordinates or disclose them in
logs. Keep an accessible list and keyboard controls; verify map/list parity at
390px and desktop, empty coverage, stale data, failed tiles and geolocation denial.
Map labels and official hours must remain readable without the map provider.

## Q10 — Meal/seating availability and bounded free text

This explicitly expands the original MVP scope. Add independent report fields for
grill/grillade, vegetarian and standard meal availability, seating availability,
and a short optional comment. Keep “not offered here”, “temporarily unavailable”,
“available” and “unknown” distinct. A missing report proves nothing. Reports are
timestamped observations, never official stock inventories or guaranteed seats.

Extend the existing report/moderation services; choose and document per-dimension
expiry/aggregation/conflict rules and allow later positive reports to clear an
earlier shortage. Do not let a seating report overwrite queue time. Prevent
duplicate retry submissions and retain existing rate/abuse controls.

Implement free text now with a concrete bounded policy: a short length limit,
plain-text escaping, no link rendering, an instruction to avoid names/contact
details, and the existing moderator hide/review path. Prefer pending-by-default
publication of comments while structured reports remain usable immediately.
Show the author that a comment awaits moderation; provide a documented local
moderator workflow and demo fixture so the feature is actually usable. Do not
silently defer all free text or build a public unmoderated chat feed.

Tests: independent dimensions, conflict and expiry, valid zero wait, repeated
submission, abusive payloads/XSS, CSRF/rate limits, moderation authorization,
hide/delete/retention, and offline retry without stale claims. Add migrations and
upgrade/recovery checks against 0.1.2. Browser replay must submit a vegetarian
shortage, no seats, a safe comment, then show expiry/recovery without conflating
these with waiting time.

## Q11 — Review and deliver the evolved local MVP

Execute the delivery contract above. Specifically extend the standalone wheel and
source-kit checks so hours providers, map assets and migrations are packaged.
Preserve strict CSP and the repaired service-worker controller-change test.
Update `docs/USER_GUIDE.md`, `docs/DEVELOPMENT.md`, `docs/RELEASE.md` and operations
docs with source freshness, map legend, reporting/moderation and recovery.

Keep R011's real lunch/queue-type observations unmeasured until the user provides
them. Synthetic reports demonstrate software behavior, not current crowding at
actual restaurants. Final report must map all three remarks to evidence and
clearly state geographic hours coverage and any provider limitations.
