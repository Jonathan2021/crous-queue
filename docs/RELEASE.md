# Supported local release — 0.2.0

Complete distributions: `crous_queue-0.2.0-py3-none-any.whl` **with runtime dependencies**, and `crous-queue-0.2.0-local.tar.gz` **full source kit**. Linux/Python 3.13 is the tested support target. The older 0.1.1 bare wheel cannot bootstrap; its dated evidence remains unchanged. No GitHub Release/PyPI/public package or deployment is created.

## Source kit or private checkout

Install Python 3.13, uv 0.11.29 and make. Extract the source kit, enter its root, then:

```bash
make install
make migrate
uv run --locked crous-queue import-directory
make serve
```

Open `http://127.0.0.1:8000`. `CQ_PORT` and `CQ_ORIGIN` must agree if that port is occupied. Configuration is caller-local `.env` (0600), development data `.local/development.db`; no operator files ship. `make seed-demo` creates a separate `.local/demo.env` and `.local/demo.db`; `uv run --env-file .local/demo.env crous-queue serve` starts the conspicuously synthetic demo on 8001. No invented report enters development/production.

## Wheel from any empty working directory

With Python 3.13 and uv, obtain the wheel from the successful private Actions artifact or your reviewed build. Use an empty directory for operator configuration/data:

```bash
uv venv --python 3.13
uv pip install --python .venv/bin/python /absolute/path/crous_queue-0.2.0-py3-none-any.whl
.venv/bin/crous-queue configure
.venv/bin/crous-queue migrate
.venv/bin/crous-queue import-directory
.venv/bin/crous-queue serve
```

The wheel contains Jinja/static assets, all six schema revisions, official-hours/availability services and vendored Leaflet assets and the dated snapshot/provenance. It needs no `alembic.ini`, `fixtures/`, repository, Foundry or development scripts. `configure` preserves an existing file; copy `.env.example` only if configuring manually, and generate independent secrets. Set explicit `CQ_*` environment values if your service working directory differs. Installed `seed-demo`, `backup`, `restore`, `retain` and `serve` use the same CLI implementations as source. For a standalone demo, load the generated demo profile using `uv run --no-project --env-file .local/demo.env -- .venv/bin/crous-queue serve`.

A normal wheel install resolves compatible runtime dependencies. For the **exact verified dependency set**, obtain `runtime-requirements.txt` produced by `uv export --locked --no-dev --no-emit-project --output-file runtime-requirements.txt`, install it with `uv pip install --python .venv/bin/python --require-hashes -r runtime-requirements.txt`, then install the wheel with `--no-deps`. CI's wheel harness uses that hash-enforcing sequence; runtime requirements are also in the private CI artifact. The complete source kit carries `uv.lock` for maintenance and dev/browser verification.

## Verify, update and roll back

`make check`, explicit Chromium installation, `make test-browser`, `uv build`, `scripts/package_release.py`, `scripts/verify_wheel.py`, `scripts/verify_release.py` and `scripts/release_manifest.py` are the repeatable source/CI sequence. Installation/export/run enforce the lock with `--locked`; uv 0.11.29's build command has no `--locked` option. The wheel-only harness creates a fresh venv and empty working directory; it never copies checkout resources. The source-kit harness installs/migrates/imports/checks and rehearses backup/restore/retention/demo/HTTP from a separate extracted copy.

Before replacing an existing installation, stop your own app process and create an integrity-checked private backup with the existing version. Preserve its environment/checksum manifest and rotate/delete under seven days. Install the reviewed new wheel/locked runtime set, run explicit `migrate`, then `retain`, inspect a fresh unknown-wait venue and restart on loopback. Re-running migration/import is idempotent; migrations never run on import.

For rollback, stop the app, install the previously verified wheel/dependency set in a new environment, restore the matching old backup to a **new** environment-marked path, run appropriate migrations/retention, verify it, and switch configuration explicitly. Never downgrade a live schema or overwrite the original DB. See [operations](OPERATIONS.md) for exact backup/restore commands and error recovery.

`release-manifest.json` ties filenames, sizes and SHA-256 values to a build. The matching private Actions run and commit are recorded in [delivery report](mvp/REMARKS_DELIVERY.md)/Foundry. Artifact retention is seven days; builds can be reproduced from the private commit after expiry. This is local technical readiness, not real usefulness or PostgreSQL/public-concurrency validation.

## Evolved 0.2.0 behavior and upgrade from 0.1.2

This continuation adds source-linked opening status, nearby map/list and meal/seat
observations with pending-by-default comments. `CQ_MAP_TILES=osm|none` controls the
optional external basemap. `refresh-hours` explicitly checks the two reviewed Paris
RUs; fresh source coverage is not automatically national. Read USER_GUIDE and ADRs
0006–0008 before changing provider mappings, TTLs or moderation policy.

Upgrade 0.1.2 only after stopping the app and backing up with the old CLI. The new
`migrate` command preserves report IDs, old retry digests, timer links, flags and
audits; availability-only reports have no wait minutes. Verify `/map`, source links,
independent report fields and `/admin` before using the upgraded store. On error,
keep the failed store for inspection and restore to a new marked path. Returning
to 0.1.2 requires its old wheel and **pre-upgrade backup**; an in-place schema
downgrade would lose new observations and is refused.

To reproduce the separate real-old-artifact check (all application data synthetic):

```bash
uv run --locked python scripts/verify_upgrade.py \
  --old-wheel /absolute/path/crous_queue-0.1.2-py3-none-any.whl \
  --new-wheel dist/crous_queue-0.2.0-py3-none-any.whl \
  --requirements dist/runtime-requirements.txt
```

Both distribution harnesses now execute browser search, valid zero wait, vegetarian
shortage/no seats, pending comment, moderator approval and map identity checks.
The wheel rehearsal restarts and recovers the written store. Exact final SHA/CI and
artifact digests live in the final Foundry receipt plus private Actions manifest,
not an impossible self-referential hash inside its own archive.
