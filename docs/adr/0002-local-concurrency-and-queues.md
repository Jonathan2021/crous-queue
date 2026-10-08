# ADR-0002 — local write serialization and queue meaning

Accepted for private MVP, 2026-10-07.

SQLite uses explicit `BEGIN IMMEDIATE` transactions, foreign keys and WAL; contribution throttles and idempotency checks run inside that transaction. PostgreSQL uses sorted transaction advisory locks on already salted device/network keys plus database uniqueness. SQLite is for the local single-instance pilot. PostgreSQL concurrency requires its own executable integration check before public deployment; local tests do not establish it.

Cuvier/Châtelet/Cuvier cafeteria expose a declared student queue based on retained Paris evidence; administrative venues expose staff queues; other venues initially expose an unspecified queue. The UI labels that uncertainty. No pooling of staff/student observations, no inference that another queue exists, and no eligibility promise. Revisit with verified venue-specific queue classes.

Aggregation uses the earlier of observed/server-received time for freshness so future client clocks never extend validity. Latest per-device estimate is selected before visibility filtering; hiding the latest vote cannot resurrect an earlier vote from that device. Completed timers are server measured, rounded up to integer minutes, and never enter the live median. Raw join/end timestamps are preserved.

Reports and timer-start retries are immutable per device/idempotency key. Same key with a different payload is 409. A retry after seven-day retention cannot recover a purged receipt and is bounded by observation-time validation. No synthetic wait is written to production.
