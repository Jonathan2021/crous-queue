# Source and dependency attribution

Directory: CNOUS / regional CROUS, retained 2026-10-07 from the [official catalogue](https://www.data.gouv.fr/datasets/restaurants-brasseries-et-cafeterias-des-crous). Licence identifier `fr-lo` / Licence Ouverte as retained in `fixtures/directory-provenance.json` and the installed resource copy. No license-version or current-opening guarantee is inferred. All 972 rows preserve regional IDs and source provenance. Small hostile XML fixtures are synthetic. No external images/contact URLs or incumbent live queue data are copied/fetched by normal setup or CI.

Runtime uses FastAPI, Pydantic/Pydantic Settings, SQLAlchemy, Alembic, Jinja2/MarkupSafe, HTTPX, defusedxml, itsdangerous, Uvicorn and Psycopg plus locked transitives. These remain separately installed third-party dependencies with their upstream licenses, rather than vendored code in the app wheel. Psycopg binary has its own redistribution notices; consult the installed package/upstream license before repackaging dependencies. Exact version/license metadata and project URLs are in `docs/evidence/q07-20261008-e83a/third-party-inventory.json`; an absent metadata expression is not an invented license grant.

No new application license is selected by this private delivery. `static/icon.svg` and raster PWA exports are project-authored assets; no third-party logo, font file or media is bundled. Dev tooling includes pytest, Ruff, mypy and Playwright; Chromium is installed explicitly for synthetic browser verification, not redistributed inside the release kit.

pip-audit 2.10.1 queried the exact 29-package locked runtime set on 2026-10-08: no known advisories returned. Exact JSON/exit is retained in the Q07 evidence directory. This is a dated advisory lookup, not an exhaustive security audit, a promise of future safety or PostgreSQL/public-release clearance. Re-audit when dependencies change; never edit old findings into a later result.

## Leaflet and optional OpenStreetMap basemap

Leaflet 1.9.4 is vendored under `static/vendor/leaflet` with its BSD-2-Clause
LICENSE and exact download hashes in `provenance.json`. Stable release verified
at https://leafletjs.com/download.html on 2026-10-08. Runtime scripts are local.
Map data/tiles © OpenStreetMap contributors (ODbL),
https://www.openstreetmap.org/copyright . The public raster tile service is
best-effort under https://operations.osmfoundation.org/policies/tiles/ . No offline
bulk tile cache; browser HTTP caching is respected. See ADR-0007 for privacy,
provider replacement and `CQ_MAP_TILES=none`.
