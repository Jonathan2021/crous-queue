# Q06 verification and continuation — 2026-10-08

Run `q06-20261008-b7a2`. Scope: reproduce local MVP acceptance, repair demonstrated defects, rehearse five lunch days using only disposable synthetic data. Hypotheses frozen before checks: existing gates stay green; a released browser shell must receive changed assets after reload/restart; the existing pilot logger must preserve planned denominator, absent checks and environment separation. No real data intake, refresh, trial or deployment.

Foundry doctor confirmed bridge/contract `2026-10-07.2` and manifest hash `1e0be09cd1b537864e0b04bbc2358932b1efba7c7a5d4abb4c0b9aff0e91703f`. Work `781199db-adde-4600-9a4d-4c56eed14fdc`, actor `reviewer-crous-queue-20261008-q06-b7a2`; initial context `b0665223-270b-52c5-a741-bc1a5b12245b` was incomplete. All 11 relevant arrivals were fetched; fresh context `d08bcdc6-f1af-5f1a-ab81-44733549ea75` includes them and reports complete evidence coverage. Full retained map revision `c0e2fb20-b25a-5517-b1a2-98ec6c546c1b` read separately (8 nodes, context selects 2). Source/status hashes frozen in `docs/evidence/q06-20261008-b7a2/`.

| Criterion | Current evidence (under `docs/evidence/q06-20261008-b7a2/`) | Verdict |
| --- | --- | --- |
| 972 retained identities; separate Cuvier/Châtelet/cafeteria/admin; last-good malformed region | `verified-check.txt`, 22 tests, directory tests | PASS, exit 0; dated snapshot only |
| Unknown/zero/conflict; exact 15-min expiry; latest device; completed separation | `verified-check.txt`, aggregation/report tests | PASS |
| Mobile 3-tap form; lost-response retry; favorites/timer; moderation | `final-browser.txt`, 7 actual Chromium tests at 390px | PASS, exit 0 |
| Retention/concurrent writes/auth/restart; redacted logs | `verified-check.txt`, safeguard and report tests | PASS |
| Changed release assets after server restart; offline read-only shell | `cache-red.txt` then `cache-green.txt`; final browser test | FAIL before repair / PASS after repair |
| Planned/actual/fresh/unknown/conflicting/missing denominators | `rehearsal.json` + `measurement-green.txt` + full verification | PASS: 40 planned, 38 actual, 2 missing; 19/38 fresh actual and 19/40 fresh planned |
| Pilot device reuse limited to selected sites; separate nullable friction | `pilot-cohort-red.txt`, `rehearsal.json`, final cohort/summary tests | FAIL before repair / PASS after repair; 1 synthetic returning device; 3 fabricated friction attempts |
| Environment/store/plan separation, duplicate and legacy guards | `measurement-isolation-red.txt`, `measurement-green.txt`, full verification | FAIL before repair / PASS after repair |
| Demo backup/restore, exact expiry; non-demo seed refusal | `rehearsal.json`, `verified-check.txt`, `clean-release.txt` | PASS; disposable stores only |
| Runnable versioned source/wheel; clean setup without Foundry | `build.txt`, `clean-release.txt`, `artifact-inspection.json` | PASS, version 0.1.1; old artifacts/evidence preserved |
| Operator schedule and blank local records | `blank-preparation.txt`, `docs/PILOT_OPERATOR_SCHEDULE.md` | PASS: 40 blank rows; dates/access unassigned |
| Concrete unapproved deployment payload | `deploy/proposal.json`, `docs/DEPLOYMENT_PROPOSAL.md`; current wheel checksum pinned | PASS as draft only; authorization absent |
| Five physical lunch days, field-confirmed queues/usefulness, private intake/access, public/PostgreSQL release | existing R011 follow-up; unavailable ordinary observations/approval | NOT RUN — no real intake or external actions authorized |

Defects were recorded here before repair. Historical release outputs and existing databases stay unchanged. No synthetic result establishes adoption.

## Demonstrated defects before repair

D1: Released CSS remains cached after an online reload and server restart. `cache-red.txt` (exit 1) observes `first` after deploying `second`; the constant `cq-shell-v1` key plus cache-first static fetch keeps the previous assets. Fix must refresh online assets, version the shell by content and preserve the offline read-only fallback.

D2: The logger accepts demo and test-store snapshots into one output file. `measurement-isolation-red.txt` (exit 1) reproduces two successful appends into the same disposable file with different environments. This would permit demo/real contamination because the default path is shared; reject mixed/legacy provenance without rewriting retained evidence.

D3 (measurement gap): `pilot_check` reports 2 actual venue checks per invocation but has no planned slots, missingness or cumulative denominator. A missed invocation disappears entirely. Q06 will add only a fixed five-day schedule, provenance-bound records, separate contribution-friction observations and a summary with explicit denominators. No real dates/access are inferred.

D4: Pilot returning-device count was national rather than scoped to the two selected sites. `pilot-cohort-red.txt` (exit 1) creates one repeat pilot device and one repeat unrelated-venue device: logger reports 2 instead of 1. The existing national admin metric remains valid; pilot output must explicitly restrict its cohort.

## Final assessment and next decision

Local technical gate **PASS** after three reproduced defects and one measurement gap were addressed. Initial `make check` passed 17 tests and baseline browser passed 6. Three new red reproductions are retained with exit 1. A candidate final check stopped at two packaging-script import lint errors (exit 2); `verified-check.txt` then passed lint/format/mypy and 22 tests. The final browser check passed 7. No skip/xfail or prior-green result substituted for modified-source verification.

All rehearsal outputs are synthetic: no real reporting coverage, returning contributors, queue eligibility or physical estimate accuracy was observed. R011's original inline response blocks remain unchanged. The explicit [R011 readiness follow-up](../../../foundry/requests/2026-10-08-crous-R011-pilot-readiness.md) is linked in Foundry's INBOX. The justified next decision is to review an exact private access/intake payload if ordinary eligibility and voluntary participation are available; otherwise defer physical validation. No Q07 feature expansion, sends, spend, accounts, remote/public hosting, commits or pushes.

The upgraded Foundry coverage workflow worked without new friction: doctor matched, 11 arrivals fetched, full retained map read separately, complete context prepared. Positive feedback and final result/resolution IDs are recorded below once their actual receipts are returned.

## Accepted checkpoint

- Foundry work: `781199db-adde-4600-9a4d-4c56eed14fdc` (complete).
- Complete saved context: `d08bcdc6-f1af-5f1a-ab81-44733549ea75`.
- Accepted result: `ce2d0fb8-aa40-5c41-8a76-ab0b68bdd74d`.
- Final resolution receipt: `.foundry/runs/q06-b7a2-final-receipt.json`, request digest `9f563ff80324eac471957823ea5828774fd94c65783172ef28bbef68de375c91`.
- Actual final review ID: `b9a08a35-2243-452c-a129-c024eff4196c`; decision ID: `22fb650f-9f54-404d-acbd-10e2c8365d13`; retained map: `89c44237-62c3-5a37-8aff-a008c04c2d7b`.
- Feedback UUID: `ac4d1719-f4e9-4db2-bb1d-ed44be079eb7`, recorded for triage; no new Foundry friction.

Final resume confirms no ready build continuation and preserves both previous blocked investigations, including human-owned R011. Created IDs above come from the final receipt, not provisional preview effects. Runtime/test/source hashes were checked again after the user's “continue”: no drift since current verification. Final mobile render was visually inspected. Existing databases and previous evidence remain untouched.
