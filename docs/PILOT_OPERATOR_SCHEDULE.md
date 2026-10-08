# Prepared five-lunch operator schedule — Q06

Status: blank local preparation; **NOT AUTHORIZED for real intake/access**. Dates and ordinary queue eligibility await existing R011. The rehearsal dates 12–16 October 2026 are synthetic examples, not booked visits.

| Lunch day | Date to assign after approval | Europe/Paris fixed checks | Selected sites |
| --- | --- | --- | --- |
| 1 | blank | 11:45, 12:15, 12:45, 13:15 | Cuvier `paris:r177`, Châtelet `paris:r175` |
| 2 | blank | same four times | same two separate venues |
| 3 | blank | same four times | same two separate venues |
| 4 | blank | same four times | same two separate venues |
| 5 | blank | same four times | same two separate venues |

Twenty paired slots mean **40 planned venue checks**. Student queue labels remain declared source categories, not field confirmation. Cafeteria `paris:r889` and staff Jussieu `paris:r1149` are excluded from this cohort. Do not enter a queue you cannot ordinarily access.

Prepared blank local records: `.local/q06-pilot-preparation-b7a2/fixed-checks.csv` (40 rows with dates/actual values blank) and `contribution-friction.csv` (header only). Regenerate into a new directory with `uv run python scripts/pilot_records.py prepare --output .local/NEW_DIRECTORY`. Existing filled records are never reset.

After exact private-access/intake approval, assign five dates and pin the environment/store with `scripts/pilot_records.py plan --days ISO_DAY1,ISO_DAY2,ISO_DAY3,ISO_DAY4,ISO_DAY5 --output .local/PLAN.json`. This reads configuration/storage identity only; the file itself grants no permission. At each paired slot use `scripts/check_pilot.py --plan .local/PLAN.json --slot-id d1-1145 --output .local/CHECKS.jsonl` (appropriate day/time suffix). The normal unscheduled logger now uses a per-environment `*-pilot-checks-v2.jsonl` file. Retained v1 logs stay untouched; they cannot silently become trusted scheduled checks.

Summarize matching records with `scripts/pilot_records.py summarize --plan .local/PLAN.json --records .local/CHECKS.jsonl`, adding `--friction .local/FRICTION.jsonl` only for measured typed friction observations. No free text, names, cookie hashes or location traces enter these records. Typed friction fields: matching plan/provenance, venue ID, outcome `completed|abandoned|error`, nullable measured duration/interactions. Unknown measurements stay null, not zero.

A performed empty check is **unknown**. A fresh zero-minute estimate is **single/recent**, and a disagreement is **conflicting**. A slot never performed has no snapshot: it stays **missing**, never unknown/zero. Actual timestamps remain UTC with Paris scheduling; captures >10 minutes away are counted separately as late. Fresh/actual and fresh/planned ratios describe recorded observations; late checks do not establish freshness at the exact planned time.

Record contribution attempts separately from venue freshness. The distinct-day reuse metric counts pseudonymous devices reporting at the two selected sites on at least two UTC days within 7 days; take the maximum observed diagnostic, never sum repeated snapshots. It is not unique people or proven retention. Synthetic rehearsal outputs have synthetic provenance and cannot be appended to real or different-store logs. Aggregate records still stay private and should be deleted under the 7-day pilot retention policy.

Missing-check example: omit day 3 at 12:15. The synthetic rehearsal returns **40 planned, 38 actual, 2 missing venue checks**, with **19 fresh / 38 actual** and **19 fresh / 40 planned**, **19 unknown**, **4 conflicting**, **15 single**, and **1 returning device**. Friction has three separately labeled fabricated attempts, not participant evidence.

Use a voluntary own completed timer only to compare a past personal experience with the estimate at joining; those remain different measures. Do not observe strangers, record seats/photos/identities, seed waits into a real feed, recruit, send invitations, deploy or spend under this preparation. The next decision is whether R011 and a concrete private access/intake payload can be satisfied, not another feature package.
