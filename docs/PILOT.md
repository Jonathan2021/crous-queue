# Private Cuvier / Châtelet pilot

Local build gate: implemented and synthetic browser replay verified. Real-user gate: **NOT MEASURED**. Public launch gate: **NOT AUTHORIZED**. No voluntary real reports were available during this implementation. Do not interpret synthetic demo reports as evidence of demand, accuracy or live national coverage.

Cuvier `paris:r177` and Châtelet `paris:r175` are the selected sites. Cuvier cafeteria `paris:r889` and administrative Jussieu `paris:r1149` remain separate. Verify actual eligibility and queue categories on an ordinary visit; don't observe strangers or record names/photos/location traces. Record unknown or unable if there is no voluntary visit.

After a usable app is privately available, choose five ordinary lunch days. At 11:45, 12:15, 12:45 and 13:15 Europe/Paris, run `uv run python scripts/check_pilot.py`. Evidence goes only to ignored an environment-specific ignored `.local/*-pilot-checks-v2.jsonl` file. Count fixed venue checks with at least one estimate younger than 15 minutes divided by all planned checks; missed checks stay missing, not zero. Report raw numerator/denominator by venue and day, along with single-report and conflicting-state counts. Do not combine demo and real environments.

Use `/admin/metrics` for the count of pseudonymous devices contributing on two or more distinct UTC days within the 7-day retention window. Treat it as a proxy for returning contributors, not unique people. Cookie clearing and shared devices limit interpretation; no credibility score follows from contribution frequency.

During a voluntary own wait, record the current estimate at joining, then start/finish the own timer. These are different measures: current joining estimate versus an experience ending later. Compare paired cases descriptively and retain timestamps only locally for <=7 days. Do not infer seat availability or walking-time savings. Time the three-tap contribution and note friction without collecting public free text or unsolicited contacts.

Review after five days: if reporting stays sparse, retain honest unknowns and try a bounded distribution experiment. No fictitious forecast, mandatory interviews, public publishing or invitations are authorized by this plan. Public hosting requires the exact checkpoint in `DEPLOYMENT_PROPOSAL.md`.

Q06 adds the [operator schedule](PILOT_OPERATOR_SCHEDULE.md), 40 blank local records, explicit planned/actual/missing denominators, provenance checks and a site-scoped returning-device count. See [dated verification](mvp/REVIEW_NEXT.md). The five synthetic rehearsal dates/attempts are not real pilot results.
