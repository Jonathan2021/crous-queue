# Crous Queue verification and continuation handoff

Prepared 2026-10-07 for the existing implementation agent. Objective: verify the
MVP honestly, repair demonstrated defects, then execute Q06 as bounded
below using the upgraded Foundry workflow.

## Independent review baseline

Q01–Q05 are accepted in Foundry. Fresh make check passed lint, formatting, types and 17 backend tests; all 6 actual browser tests passed. The app delivers the national directory and recent-report workflow. This is a directory-backed local MVP, with no evidence yet of live reporting coverage or returning contributors.

Last accepted result at review: `bd9fff84-b0be-5054-aee4-e243153c0dc2`. Full coordinator evidence:
`/home/jonathan/startup_lab/foundry/docs/inquiry/mvp-review-2026-10-07/REPORT.md`.
Start with docs/IMPLEMENTATION_LOG.md, docs/OPERATIONS.md, docs/PILOT.md, docs/DEPLOYMENT_PROPOSAL.md, scripts/check_pilot.py and ../../foundry/requests/2026-10-06-crous.md.

## Foundry checkpoint requirements

Read root and repository AGENTS.md, the original docs/mvp/AGENT_HANDOFF.md and the
current decision/architecture/roadmap. This handoff is the user's later authorized
continuation; it does not erase original acceptance or historical release limits.
The audit is a dated baseline, not permission to skip inspecting current changes.

From this repository, verify the installed local upgrade before work:

```bash
python3 tools/foundry_agent.py doctor
python3 tools/foundry_agent.py cli agent guide
python3 tools/foundry_agent.py resume
```

Require doctor to report bridge_version and agent_contract_version `2026-10-07.2`
and manifest_hash_matches true. The canonical helper hash is
`1e0be09cd1b537864e0b04bbc2358932b1efba7c7a5d4abb4c0b9aff0e91703f`.
The existing configured executable/store are authoritative. Never install a new
empty store or add Foundry imports to the application. Doctor checks configuration;
resume verifies current records. If a newer reviewed upgrade exists, inspect its
release notes instead of downgrading it.

Read the newly saved context, its map_coverage and all relevant arrivals. The map
in a context is selected for the task; follow map_coverage.full_map_command to
read the exact retained full revision. context_complete is a separate evidence
coverage indicator. Fetch arrivals and prepare a fresh context including relevant
evidence_ids; reading files alone does not mark context coverage complete.

Use the public result/resolution schemas. Submit source-backed findings, commands,
exit codes, actual failures, changed-file hashes, screenshots, limits, feedback
UUIDs and proposed next work. Preview then resolve only routine local changes
within this assigned scope. Pin the digest and versions from the saved context;
if stale, reconcile through a new context and superseding result. Use created IDs
from the final resolution receipt and resume, not provisional preview IDs.
Conditional may_lead_to map edges need both condition and outcome.

For a slow read, a bounded retry is available as
`python3 tools/foundry_agent.py --timeout-seconds 120 resume`. A timed-out mutation
may have committed: inspect state before retrying the identical request/payload.
Do not steal claims, silently reset work, or release another actor's ownership.
Report genuine Foundry friction with the feedback template/outbox; a receipt means
recorded, not fixed. If none occurred, state that in the checkpoint.

## Completion and boundaries

First produce docs/mvp/REVIEW_NEXT.md with a criterion-to-evidence matrix and a
clear pass/fail/not-run verdict. Record any real defect before fixing it and add
only meaningful regression tests. Continue the bounded next local work below;
do not stop at a plan or repeat the whole original build. Preserve unrelated
changes, old evidence, existing databases, and package dependency order.

At the next checkpoint, deliver the runnable result, exact verification evidence,
Foundry result and final receipt IDs, current limitations and one justified next
decision. Distinguish local build, real usefulness and external release. Stop
expansion when the next material gate depends on unavailable real evidence; create
an actionable request under foundry/requests/ and link it from INBOX.md without
overwriting inline replies. Reuse existing request IDs where applicable. Complete
independent local preparation before asking for inputs.

No commits/pushes, public or remote deployment, paid services, account creation,
real sends, real data intake or other consequential external actions are granted
by this handoff. A requested external step must have an exact reviewable payload
and the required explicit approval. Learning remains paused. Do not fabricate
adoption, customer data, qualified review or a passed physical-use gate.

## Start or recover your package

The coordinator created ready work `781199db-adde-4600-9a4d-4c56eed14fdc` for this handoff,
depending on accepted release result `bd9fff84-b0be-5054-aee4-e243153c0dc2`. This does not authorize any
real pilot or deployment. Use a unique actor for this new package:

```bash
python3 tools/foundry_agent.py start --actor reviewer-crous-queue-YOUR_SESSION --work-id 781199db-adde-4600-9a4d-4c56eed14fdc
```

Refresh resume first. If another agent owns it or a later result replaces it,
follow the current reviewed state. Never reclaim O01/V01/Q01/C01 or the completed
release just because the old handoff still names it.

## Part one Verify and repair

Run make check and CQ_EVIDENCE_PREFIX=next-review-UNIQUE uv run pytest tests/browser. Verify the 972-row retained snapshot, separate Cuvier/Châtelet/cafeteria IDs, malformed-region last-good data, unknown versus zero versus conflicting waits, exact 15-minute expiry, same-device replacement, offline lost-response retry, moderation and retention. Review service-worker/cache behavior after a release and restart. Treat source observations as dated; do not claim the directory is current without a new permitted read-only refresh.

Coordinator-reproduced commands or starting diagnostic command:

```bash
make check
CQ_EVIDENCE_PREFIX=next-review-UNIQUE uv run pytest tests/browser
```

Use isolated synthetic data and new evidence filenames. Do not overwrite retained
screenshots/logs or use application databases as fixtures. A prior green run is
relevant regression evidence, not proof of code modified afterwards.

## Part two Execute the next bounded work

**Q06: Audit honest wait states and rehearse a five-lunch pilot**

Rehearse the existing five-lunch measurement workflow against a disposable synthetic store. Add only missing measurement/diagnostic support actually revealed by the rehearsal. Produce an operator schedule and blank local records for fixed checks at the two selected sites; count planned checks, actual checks, fresh estimates, unknown/conflicting states, distinct-day device reuse and contribution friction separately. Include a missing-check example that stays missing. Confirm queue categories through the existing R011 request when an ordinary voluntary visit is available; preserve user replies.

Acceptance: Full checks and mobile/offline/moderation flows pass; measurement output includes explicit numerator/denominator and missingness; synthetic and real environments cannot be mixed; demo backup/restore and expiry remain correct; no synthetic waits enter a real feed; release proposal remains a concrete unapproved payload.

## Decision after this package

Next real gate: five ordinary lunch days with voluntary own observations at Cuvier/Châtelet and an approved private access arrangement. No strangers’ identities/photos/traces. If fresh contributions remain sparse, test a bounded distribution approach after approval; do not add fictitious wait prediction. National venue coverage does not imply national live data.
