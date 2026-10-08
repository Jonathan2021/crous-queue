# Remarks continuation — local MVP 0.2.0

2026-10-08. Q08–Q10 are accepted sequentially in Foundry 2026-10-08.1; Q11 reviews
and delivers this candidate under the explicit private Git/no-cost CI authorization.
The final Q11 receipt is authoritative for final SHA/remote/CI/artifact identity.
A local green check alone is not CI acceptance. Q07's RELEASE_READINESS.md remains
historical 0.1.2 evidence. Root `remarks` is preserved verbatim.

## Remarks mapped to behavior and evidence

| Remark | Implemented behavior | Evidence |
| --- | --- | --- |
| Restaurant website, hours, open today inline | Replaceable bounded provider; exact RU identities, source/provenance, today versus now, local-date/DST/overseas semantics, explicit stale/unknown/conflict, last-good recovery | Q08 `core-final.txt` (30), `browser-first.txt` (8), dated `live-final.txt`; ADR-0006; Q11 review red/green regressions |
| Nearby map, dark red crowded/light green no wait | Bundled Leaflet, independent opening/waits, identical map/list aggregation, text/minutes/age, coincident venue actions, location only on click, manual search/keyboard and tile failure fallback | Q09 `core-final.txt` (31), `browser-final.txt` (10), `browser-verified.txt`; ADR-0007; current missing-coordinate regression |
| Grill/vegetarian/standard, no seats, other text | Independent fields, meal 10min/seats 5min, conflicts/recovery, 280-char pending comments with real moderator controls, shared abuse/retry protection | Q10 `core-final.txt` (36), `browser-final.txt` (12), actual browser/upgrade fixtures; ADR-0008 |

Q11 final local verification: `core-final.txt` passes Ruff/format/strict mypy and
**40 core tests**; `browser-final.txt` passes **14 Chromium tests**, including the
strict service-worker controller-change regression. `clean-export-rehearsal.txt`
records independent wheel/source install and recovery from the staged export.

Paths are under `docs/evidence/q08-20261008-b72e`, `q09-20261008-b72e`,
`q10-20261008-b72e` and `q11-20261008-b72e`. Initial red specification and interim
failed checks remain retained; only named successful final/verified exits establish
acceptance. New browser screenshot paths are unique; text evidence can be checked
from Git while PNGs remain local. Exact commands are in acceptance/q08–q11.md and
the test/harness source. None of these synthetic checks establishes demand,
restaurant stock, physical queue accuracy, access or guaranteed seats.

## Provider and interpretation limits

Official website mappings cover **RU Cuvier and RU Châtelet only**. Cafétéria
Cuvier and administrative Jussieu are separate identities, even at the same
coordinates. The dated 972-identity national snapshot supplies no interpreted
hours. A fresh national feed may supply supported explicit hours; `010` weekly
flags are never treated as clock times or a closure exception. Daily closed
badges are bound to retrieval date. Unknown grammar/source changes fail closed
with visible uncertainty. Refresh is explicit, bounded and separate from page
reads. A fresh interpretation still cannot guarantee an unannounced opening.

Q11 review found and repaired two source cases before release: unparseable new
hours now retain good historical schedule plus rejected-attempt provenance;
missing `0,0` coordinates get no false map marker or guessed overseas timezone.
Browser refresh updates status, service intervals and check time together. Moderators
can delete comment text even after hiding the whole report; reapproval stays blocked.
Known coordinate regions distinguish Réunion/Mayotte/Antilles/Guyane. OSM tiles
are optional/best-effort with attribution and no bulk/offline download. No account
or paid provider. R011/ordinary lunch observations remain **unmeasured**.

## Distribution and recovery contract

Version 0.2.0 supports Linux/Python 3.13 and SQLite. Wheel includes all six
migrations, dated directory, hours/availability providers, templates, map assets
and licenses; no checkout or Foundry resources are copied to make it run.
The complete source kit additionally contains locked development/browser tools.

Both harnesses install/migrate/import in disposable independent directories and
exercise browser search, 0-min wait, shortage/no seats, pending/approved comment
and map identity. Wheel rehearsal also restarts and restores the written store.
`old-wheel-upgrade.txt` records installation of the actual retained 0.1.2 wheel,
synthetic development/demo upgrades and old-wheel rollback against its restored
pre-upgrade backup. Its verified old wheel SHA-256 is
`4de4f9432c31d227542d3a7b801d20759b752e0dfa80219683708444f01e880b`.
Core tests also verify 0.1.2 schema/timer/flag/audit links and old retry compatibility.
No in-place lossy downgrade or operator data migration is performed.

Run/install/refresh/moderation/recovery steps are maintained in README,
USER_GUIDE, DEVELOPMENT, RELEASE and OPERATIONS; configuration is in .env.example.
The final artifact manifest is generated after checkout/build and retained in the
private exact-SHA Actions artifact and local `dist/verified-<SHA>/`. It records
wheel/source SHA-256/size and `source_commit`; the final delivery receipt checks
those bytes. Reproducible builds remain possible after seven-day artifact expiry.

## Git, CI and canonical folder

Canonical folder and delivery folder are both
`/home/jonathan/startup_lab/crous-queue`; branch `main`, no delivery worktree.
Baseline `699eebf63f8a70eff02b961ae0d541cc2a271741` was rechecked against private
`Jonathan2021/crous-queue` before editing. Scoped bridge/handoff, code/migrations,
tests/assets, docs and remarks are the authorized commit payload. Local manifests,
stores, secrets, environments, generated artifacts and application data are excluded.
No force push, public hosting/release, send, paid capacity or cloud resource.

Final **local HEAD, origin/main SHA, pushed/merged status, residual Git/ignored
state, CI URL/head/conclusion/timing and verified artifact hashes** are written to
`.foundry/runs/remarks-20261008/delivery-final.json` and the accepted Q11 result.
They cannot truthfully be embedded in their own Git commit. The workflow retains
one Ubuntu job, a 15-minute timeout, read-only repository permission and seven-day
small artifacts. Billing account usage is not readable with the existing OAuth
scope; no permission expansion or billing setting change is made. Per-run timing
is checked after CI; it is not account-wide billing evidence.

## Preservation exception and remaining gates

All historical text/checkpoint files and root remarks are unchanged. The old
browser harness used rolling `latest-*.png` defaults and overwrote three existing
local generated screenshots. Desktop was restored byte-for-byte from an identical
retained copy. Original rolling mobile/admin PNGs could not be recovered; their
pre-run hashes and a precise record remain in `prior-evidence-review.json`.
Current replay images are saved separately; harness defaults now use unique paths.
This is a disclosed preservation exception, not a claim of unchanged screenshots.
No operator DB/config or unrelated source work was changed.

Real lunch/demand/access/intake, R011 and PostgreSQL/public-operation validation
remain outside this local delivery. Comment publication depends on local moderator
review. The deployment proposal remains NOT AUTHORIZED. Synthetic results do not
clear any of these gates.
