# Crous Queue

Local MVP **0.2.1**: find a university restaurant and see or report a recent wait, with unknown/stale states that cannot be confused with zero waiting. French responsive PWA, national search, local favorites, anonymous signed sessions, estimates, own wait timer, moderation and private operations. Source-linked official hours, a nearby crowding map, independent meal/seating observations and moderated short comments now implement the root remarks. **No public deployment or real-user demand/accuracy validation.**

## Run locally

Prerequisites: Python 3.13, [uv 0.11.29](https://docs.astral.sh/uv/), `make`. From this repository or the local release archive:

```bash
make install
make migrate
uv run crous-queue import-directory
make serve
```

Open **http://127.0.0.1:8000**. `make install` creates independent random secrets in an ignored 0600 `.env`; it never overwrites an existing file. The development DB is ignored `.local/development.db`. Imports contain directory data only: 972 identities observed on 2026-10-07 across 26 regions. Every venue initially has unknown waiting time. Opening/access coverage is incomplete. Run `uv run --locked crous-queue refresh-hours` explicitly to refresh the two mapped official Paris pages (RU Cuvier and RU Châtelet); other venues use feed hours only when interpretable. Status becomes unknown after the local date changes or refresh fails. No page-view scraping. Search defaults to restaurant types; cafés, administrative and other venues are available in filters. No signup or location permission. The footer shows the directory observation date next to the Licence Ouverte attribution, and a banner appears once the directory is more than 30 days old.

At Cuvier select **Signaler une attente → 10 min → Confirmer**. Estimates expire at exactly 15 minutes; zero is a real contribution. Conflicting values show a range. Completed personal waits are separate observations. One contribution per device/venue per 2 minutes; retries reuse their original key and cannot add a vote. Corrupt/expired sessions require reloading.

**Abuse model, honestly:** a new cookie is a new "device", so the app cannot count people. At most two live estimates per coarse network (same Wi-Fi/NAT, IPv4 /24) count toward the displayed value; the page says "N appareils · K réseaux" and how many same-network reports were not counted. This limits repeats and bursts from one network, **not identities**: someone with several networks can still add several votes. Behind a reverse proxy set `CQ_TRUSTED_PROXIES`; by default forwarding headers are ignored. See [ADR-0009](docs/adr/0009-network-budget-and-trusted-proxy.md).

## Separate synthetic demo

```bash
make seed-demo
uv run --env-file .local/demo.env crous-queue serve
```

Open **http://127.0.0.1:8001/v/paris:r177**, or Châtelet `/v/paris:r175`. The demo uses `.local/demo.db` and a separate secret file, with a prominent **DÉMO** banner. Cuvier has synthetic 10/15-minute estimates plus an 8-minute completed timer; Châtelet has a synthetic zero. The Cuvier demo also has a vegetarian shortage, no seats and a safe comment awaiting approval in `/admin`. They expire normally. Re-running seed refreshes only synthetic providers and preserves the 2-minute throttle. The seed refuses every non-demo configuration and external database. Do not copy it to a real pilot or public host.

## Verify and operate

```bash
make check
uv run playwright install chromium
make test-browser
uv build
```

`check` runs Ruff, formatting, strict mypy and deterministic unit/integration tests. Tests always migrate isolated `test-*` databases and use injected clocks/retained or synthetic providers. Browser checks use actual Chromium clicks at 390px, clock advance, offline shell, lost-response retry, favorites and moderation. They create local ephemeral servers only. Set `CQ_EVIDENCE_PREFIX` to a new identifier to retain screenshots from a verification run.

Open `/admin` and enter the separate `CQ_ADMIN_TOKEN` from the local secret file; no token is stored in browser persistence. See [operations](docs/OPERATIONS.md) for privacy-safe logging, retention, backup/restore and actionable errors. See [pilot](docs/PILOT.md) for fixed freshness checks and returning-contributor diagnostics. [Deployment proposal](docs/DEPLOYMENT_PROPOSAL.md) and the exact [private-beta approval payload](deploy/PRIVATE_BETA_APPROVAL.md) are **NOT AUTHORIZED**; nothing is hosted.

The project owns its runtime and `uv.lock`; Foundry is optional coordination CLI tooling only. A developer needs no Foundry installation or store. The initial choice of FastAPI/Pydantic/SQLAlchemy follows the [FastAPI version guidance](https://fastapi.tiangolo.com/deployment/versions/) and [SQLite transaction documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html); tested exact versions are locked. Python is constrained to 3.13; public concurrency targets PostgreSQL, while verified local behavior uses SQLite. HTTP-only legacy official directory feeds are fetched server-side with no redirects, entity expansion, embedded-link fetches or executable HTML.

## Scope and evidence

[Decision](docs/mvp/DECISION.md), [roadmap](docs/mvp/ROADMAP.md), [architecture](docs/mvp/ARCHITECTURE.md) and [implementation log](docs/IMPLEMENTATION_LOG.md) retain the agreed product boundaries and exact checkpoint evidence. [Release evidence](docs/evidence/) distinguishes red current-package specification tests from green regressions. No skipped/xfail tests establish acceptance. The five-day voluntary lunch trial is a future adoption/physical-accuracy gate, not a synthetic test result.

No full menus, predictions, live Affluences import, names, photos or stored location traces. Meal/seating availability and <=280-character comments are observations; comments publish only after moderator review. Initial Q01–Q06 work stayed local. Q07 permits scoped private Git delivery and included-allowance Actions; real intake, public hosting, account creation, sends and paid services remain outside scope.

Q06 verification repaired release-cache and pilot-measurement defects, then rehearsed five synthetic lunch days. [Review matrix](docs/mvp/REVIEW_NEXT.md) and [blank operator schedule](docs/PILOT_OPERATOR_SCHEDULE.md) distinguish local build checks from the unapproved real trial. `scripts/rehearse_pilot.py` uses disposable stores only.

Current [release/artifact contract](docs/RELEASE.md), [French usage](docs/USER_GUIDE.md), [developer map](docs/DEVELOPMENT.md), [third-party attribution](docs/THIRD_PARTY_NOTICES.md) and [remarks delivery report](docs/mvp/REMARKS_DELIVERY.md) are the maintained entry points. Installed CLI now includes configuration, packaged migrations/snapshot and separate demo seeding; the older bare-wheel limitation is historical. Private Git/Actions delivery is explicitly authorized for this Q08–Q11 continuation; public publishing, real intake and deployment remain separate gates.

## Hours, map and availability

Venue cards/details separate “open today” from “open now”, show source links,
service intervals and last checks. Unknown, stale or conflicting sources remain
explicit. Website coverage starts with **two Paris RUs**, not national live hours.

Open **Carte** for matching venues and an accessible list. Light green means a
fresh 0-minute observation; dark red means >20 minutes. Unknown/expired/conflicting
is gray. Venues at one address share a segmented marker with one color per
venue; select it to choose each venue. “Autour de moi”
requests location only on click; city search and keyboard navigation work without
it. Optional OpenStreetMap tiles can fail without losing the venue list. Set
`CQ_MAP_TILES=none` to avoid external basemap requests.

On a venue, open **Signaler repas, places ou commentaire**. Grill, vegetarian,
standard meal and seats are independent; leave unobserved fields blank. Meals
expire at 10 minutes, seats at 5; later reports can clear shortages. A comment
awaits local moderator approval; no names/contact details/links. Neither this
feature nor synthetic demonstrations guarantee a meal or a seat.
