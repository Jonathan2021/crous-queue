# Developer entry point — 0.1.2

Start from the source kit/private repository with Python 3.13, uv 0.11.29 and make. `make install` checks `uv.lock` against the manifest, installs dev dependencies and creates private configuration if absent. `make migrate`, `uv run --locked crous-queue import-directory`, `make serve` starts the independent loopback app. No Foundry installation is needed. `make check` runs Ruff/format/strict mypy/core acceptance; `uv run --locked playwright install --with-deps chromium` then `make test-browser` exercises real browser flows.

| Module/path | Responsibility and boundary |
| --- | --- |
| `app.py`, `api/` | App factory/retention lifecycle; HTTP validation, signed session, auth and delegation; no schema DDL on import |
| `config.py`, `configuration.py` | Explicit profile/secret validation; non-overwriting private development/demo files |
| `db.py`, `models.py`, `migrations/` | UTC persistence, SQLite transaction serialization, schema/model invariants and explicit versioned migrations |
| `distribution.py`, `resources/` | Installed migration/snapshot resolution; dated attributed directory, independently of caller cwd |
| `services/directory.py` | Replaceable provider protocol; bounded allowlist/XML parser/plain-text import; retain last-good failed region |
| `services/waits.py` | Injected UTC clock; idempotency, throttles, timer ownership and honest aggregation; DB authorization boundary |
| `services/moderation.py`, `maintenance.py` | Admin versioned hide audit/enum flags, scoped aggregate diagnostics, exact deletion and isolated recovery |
| `services/pilot*.py` | Aggregate provenance-bound scheduled measurements; fixed denominator, missingness, scoped repeat-device proxy and separate friction |
| `templates/`, `static/` | French server-rendered pages; small same-origin JS; local favorites/retries and content-versioned offline shell |
| `tests/unit`, `tests/integration`, `tests/browser` | Injected clocks/disposable stores; actual 390px/desktop clicks, transport failure and release/restart/offline replay |
| `scripts/verify_wheel.py`, `verify_release.py` | Actual installed wheel and source-kit setup/recovery from independent temporary working directories |

Venue identity is region plus source ID. Student Cuvier `paris:r177`, student Châtelet `paris:r175`, cafeteria `paris:r889` and staff administrative Jussieu `paris:r1149` never merge by coordinates. Selected student queues are declared source categories; physical eligibility remains R011. Other directory queues initially stay unspecified. Preserve raw source versus safe display fields.

Only visible latest per-device estimates younger than 15 minutes contribute; hiding a latest vote cannot revive that device's older vote. Zero is a real report, empty is unknown, one is unconfirmed, and ranges over 15 minutes are conflicting instead of a precise median. Effective freshness is the earlier of client observation/server receipt; future client time cannot extend validity. Own completed timers retain join/finish and stay separate past experiences. Pseudonymous cookies limit repeats, not Sybil attacks or unique people. Pilot reuse scopes to the two sites and counts distinct UTC days, not installs or public identities.

Read-time and elapsed-browser-time expiry keep states honest without cleanup dependence. Offline navigation gets an explanatory read-only shell; API data/writes are never cached or queued. Online static assets refresh before falling back to shell caches. Asset-content revisions trigger worker replacement; cleanup removes only this app's caches. Errors are redacted and actionable; failed imports retain data and label stale coverage.

Author new migration revisions under `src/crous_queue/migrations/versions`; preserve previous upgrade bodies and IDs. Use the same packaged configuration helper for tests/tools. Root `alembic.ini` points at the package; historical root revision copies are not active. No test targets an existing application DB; external live refresh is an explicit opt-in operator action, excluded from CI.

See [operations](OPERATIONS.md), [French first use](USER_GUIDE.md), [release contract](RELEASE.md) and [current readiness](mvp/RELEASE_READINESS.md). GitHub Actions provides commit-specific reproducibility; successful local tests alone do not claim remote CI or physical usefulness. Foundry bridge/outbox remain operator-local coordination, excluded from artifacts and runtime.
