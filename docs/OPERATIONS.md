# Private local operations

The application uses Python 3.13 and `uv.lock`, independently of Foundry. Secrets are in ignored `.env` (mode 0600), databases/backups in ignored `.local/` (0700). Development binds to `127.0.0.1:8000`. Uvicorn proxy headers and access logs are disabled. Application request logs include generated request ID, method, route template and status only; no body, query, IP, device/session hash, authorization token or coordinates. SQL errors hide parameters.

## Migration and retention

Run `make install`, `make migrate`, then `uv run crous-queue import-directory`. Schema revisions 0001 (directory), 0002 (reports/timers/counters), 0003 (moderation) are explicit. App creation never creates tables. Back up before upgrading an existing database. Unknown schema/storage errors return redacted 503 with a recovery message. Installed `crous-queue migrate` resolves packaged revisions without a cwd ini file. In the source kit, `uv run --locked alembic current` uses the package pointer in `alembic.ini`; prefer the application CLI for validated profile selection.

Reports, timers, flags and audits are deleted at age >=7 days. Counter rows expire two hours after the start of their hour and are pruned each minute while the app runs; no raw IP is stored. `uv run crous-queue retain` executes the identical deletion job. For a hosted pilot, an independent hourly operator job and retention alert are required to keep deletion under 24h even after application interruption. Never claim the retention deadline is guaranteed when all jobs are stopped. Rotate/delete private backups under 7 days and purge immediately after restoring a historical backup.

## Administration

Open `/admin`, enter the separate `CQ_ADMIN_TOKEN` from your local secret file. The token stays only in that tab's JavaScript memory. Authenticated JSON endpoints require `Authorization: Bearer TOKEN`. Admin POSTs also require the anonymous session cookie, `X-CQ-Request: 1` and JSON, with same-origin validation. Requests never expose the token or device identities. Hiding requires a bounded rationale and the reviewed `expected_version`; stale actions return 409. A hidden latest vote never revives the same device's older contribution. Public flags accept only `suspected_false`, `wrong_queue`, `outdated`, one flag per device/report. This is limited moderation, not Sybil defense.

`/admin/metrics` returns counts only: raw reports retained, venue/queue combinations with a fresh estimate, and pseudonymous devices contributing on >=2 UTC days within 7 days. These counts are contribution diagnostics, not evidence of real demand or verified accuracy. The operator should set the DB connection's PostgreSQL time zone to UTC before public use.

## SQLite backup and restore

```bash
uv run crous-queue backup --output .local/development-backup.db
uv run crous-queue restore --input .local/development-backup.db --output .local/development-restored.db
```

The SQLite backup API creates a consistent WAL-aware snapshot with checksum, environment manifest and quick-check verification. Restore checks both checksum and environment, creates a new file, and never overwrites a live database. Validate the restored copy, migrate if needed, run retention, then explicitly change `CQ_DATABASE_URL` while the server is stopped. Revert that configuration to roll back. Keep the old database private until recovery is verified and its retention deadline reached. Backups are sensitive even when IDs are pseudonymous.

PostgreSQL is not provisioned. Before a public release: use a private connection/service file or protected environment (no password in argv); `pg_dump --format=custom --file=PRIVATE_PATH` with 0600 permissions, record checksum/environment, and test `pg_restore` into a new isolated database. Migrate, purge and verify before switching configuration. Validate simultaneous writes and row/advisory-lock behavior against the actual selected PostgreSQL version. The SQLite CLI refuses to pretend it backs up PostgreSQL.

## Recovering errors

422: check integer minutes 0–120, timezone-aware observation and allowed queue. 409: idempotency payload changed or moderation version changed; inspect the original/reload. 429: wait 2 minutes for venue contributions or for hourly throttle reset. 403: reload for a signed cookie and use the configured origin; expired/forged cookies cannot contribute. 503: verify migration head, disk space and DB permissions without copying SQL parameters into logs.

## Q06 shell and measurement recovery

Released shell assets use a content-derived worker revision and refresh online. Cached offline navigation still shows the explanatory read-only page, never cached API waits. A restart is required to load changed Python handlers; browser reload/update handles changed static assets.

Pilot logger v2 records bind environment, synthetic/real mode and storage identity. Never append demo, a different database, a restored-copy identity or old unversioned snapshots into an existing file. Retain the old file for review, choose a new matching plan/log, and never relabel it as observed real data. Blank records and schedule are in `PILOT_OPERATOR_SCHEDULE.md`; real intake/access remains unapproved.
