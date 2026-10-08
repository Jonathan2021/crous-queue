# ADR-0008 — Independent expiring availability and moderated text

2026-10-08, Q10. Explicit user scope supersedes the initial no-seats/no-free-text
exclusions. Extend the existing report with optional grill, vegetarian, standard
meal and seating fields; keep wait kind/minutes independent. Availability-only
kind requires NULL minutes, enforced by schema and migration 0005. Estimate and
completed kinds still require 0–120 whole minutes. No fabricated zero for a seat
report. Fields distinguish absent, explicit unknown, not offered here,
temporarily unavailable and available. These are observations, not venue stock.

Per dimension, choose each device's latest observation (effective observed time,
then received time/ID for deterministic ties); a hidden latest observation is a
tombstone, never revival of its older report. Effective time is min(observed,
received). Meals expire exactly at 10 min; seating at 5 min, including “not offered”.
Within the latest 2-minute cohort, differing values give “avis divergents”. Later
same-device updates supersede that device; a new cohort more than 2 minutes after
old evidence can clear a shortage even from another device. Count/age and expiry
are visible. Explicit unknown counts as an uncertain observation; missing stays
unknown with count zero. No user reputation or inference from opening hours.

The existing signed device, CSRF checks, 4KB request limit, per-venue 2-minute
throttle and device/network hourly contribution counters cover the complete
submission. The existing device/idempotency key is shared for atomic retry.
Absent new fields and empty comments are excluded from payload digests so legacy
0.1.2 retries match. Retrying preserves original observed_at; old reports cannot
become current by reconnecting. No automatic offline queue or background send.

Comments are <=280 characters, plain text (control characters rejected), never
HTML or clickable URLs. Contributor instructions prohibit names/contact details
and discourage links. Content stays pending until moderator approval; structured
observations publish immediately. Public API omits pending/hidden/deleted text.
Author receives “awaits moderation”. Approved visible comments expire at 60 min.
Moderator explicitly checks relevance, private information, abuse and links;
automated moderation is not claimed. Existing separate bearer authentication,
CSRF and optimistic moderation version apply to approve/hide/delete. Hide comment
leaves structure usable. Delete clears text permanently in the active database;
report-hide suppresses all its dimensions/comments. Audits retain action/rationale,
not deleted text. Existing 7-day report/child retention removes all comments,
including pending ones; protected backups may retain bytes until rotated (7 days).

Migration preserves old reports, timers/flags/audits, unique retry keys and minute
bounds; foreign_key_check verifies SQLite links. Backup before upgrade; no lossy
in-place downgrade is supported. Restore a pre-upgrade backup with 0.1.2 to roll
back. Tests use synthetic schema/data only. Demo adds a pending safe comment and
shortage/no-seats fields to the existing synthetic report.

Revisit expiry/conflict thresholds using actual voluntary observations, not these
synthetic tests. R011 and real lunch usefulness remain unmeasured.
