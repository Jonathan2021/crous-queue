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

## Official hours refresh (Q08)

After `migrate` and `import-directory`, run `crous-queue refresh-hours` once each
local morning (and manually after a notice), or `--venue-id paris:r177` to repair
one of the two reviewed Paris mappings. No scheduler or live fetch is enabled by
installation. A failed/unknown refresh exits 1 with per-ID status; inspect the
source URL and schedule in `GET /venues/{id}/hours`. Repeating safely replaces the
cache. No credentials/account required. Runtime page views read local storage.

If a source moves, verify the venue identity, update `MAPPINGS` in
`services/hours.py`, add a sanitized synthetic shape fixture/test, review the
allowlist, then refresh. Redirects are deliberately refused. Never insert a user
URL. National feed `hours` text can supply a schedule only when the strict grammar
is supported; legacy flags cannot. A stale or unavailable source displays unknown
opening with historical intervals; there is no guarantee of exceptional opening.
See ADR-0006 for timezones, cadence, bounds and provenance/license limits.

## Availability/comment moderation (Q10)

Open `/admin` locally and enter the independent `CQ_ADMIN_TOKEN`. The token stays
in that tab's memory. Pending comments show alongside independent meal/seat
observations. Review for names/contact details, links, abuse and relevance. Enter
a short non-personal rationale, then “Approuver le commentaire” to publish,
“Masquer le commentaire” to remove its public text, or “Supprimer le texte” to
clear the stored comment. “Masquer” suppresses the entire report, including all
structured dimensions. A version conflict means reload before reviewing again.
Do not approve a comment merely to clear the queue. Hidden comments may be
reapproved after review; deleted text cannot. Seven-day retention covers every
state; rotate protected backups within seven days too.

`seed-demo` supplies a synthetic vegetarian shortage, no seats and a pending safe
comment in the isolated demo profile. Use the demo admin token to practice review,
then refresh the venue page. Nothing sends an invitation or publishes externally.
API: `POST /admin/reports/{id}/comment` with `action=approve|hide|delete`,
`expected_version`, `rationale`, existing bearer/X-CQ-Request/JSON/Origin checks.
Structured observations use the ordinary report endpoint and shared rate limit.

Before 0.1.2 → current upgrade: stop the local server, create an integrity-checked
backup, install the new artifact and run `migrate`. Check venue/report/comment
reads and `/admin`. On failure preserve the failed store and restore into a new
marked path. To return to 0.1.2, use the pre-upgrade backup and old artifact, never
run a lossy schema downgrade. See ADR-0008 and the distribution rehearsal.

A hidden whole report can still have its comment text deleted from the moderator
view. It cannot be approved or republished. Deletion keeps only the moderation
action and sanitized rationale, not the deleted comment.
