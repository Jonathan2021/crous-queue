# Hosted private beta — approval payload (P4, 2026-10-09)

**Status: NOT AUTHORIZED.** Nothing has been provisioned, bought, registered or
sent. This document is the exact payload a human approves (or rejects) in R011
before the five-lunch coverage test (P6). Approval must name this file, its git
commit and the build checksum below. A general "go ahead" is not approval.

## 1. What would run

| Item | Exact value |
| --- | --- |
| Build | `crous_queue-0.2.1-py3-none-any.whl`, sha256 `bafceb5bcf06cf18c75d0348ca36126226d64b543a7664cbcfd90c81a679f4e3` (195 397 B), from Actions run [37970042546](https://github.com/Jonathan2021/crous-queue/actions/runs/37970042546) on commit `a4f048703ac7a98b68a44c583cb66ac6e35b977d`. Runtime set: `runtime-requirements.txt` sha256 `1a6286b0f13a1d688f05d45775fc13a3643d09f3487f5ce2f88a3885473ffd68`. The CI artifact expires 2026-10-16; after that, rebuild from the same commit and compare the wheel's contents rather than its hash. |
| Schema | Packaged Alembic head `0007` |
| Provider / region | Scaleway, zone `fr-par-1` (Paris). EU data residency, about 3 km from RU Cuvier. |
| Instance | One `DEV1-S` (2 vCPU, 2 GB RAM), Ubuntu 24.04 LTS image |
| Processes | `crous-queue serve` (uvicorn, loopback 127.0.0.1:8000) under systemd ([unit draft](crous-queue.service)); PostgreSQL 16 from Ubuntu packages on the same host, local socket only; Caddy 2 reverse proxy with automatic TLS on :443 ([Caddyfile draft](Caddyfile.example)) |
| Public surface | HTTPS only; port 22 limited to the operator's SSH key; 5432 and 8000 never exposed |
| Hostname | A subdomain of a domain the operator **already** controls (operator input). No domain purchase is part of this payload. |
| Configuration | [`production.env.example`](production.env.example) with `CQ_TRUSTED_PROXIES=127.0.0.1`, `CQ_FORWARDED_HEADER=x-forwarded-for`, `CQ_NETWORK_ESTIMATE_CAP=2`, `CQ_NETWORK_HOURLY_LIMIT=120`, `CQ_MAP_TILES=none` (no third-party tile requests from testers' phones) |
| Demo | Never on this host |

## 2. Cost ceiling

- List price read on 2026-10-09 from <https://www.scaleway.com/en/pricing/virtual-instances/> (PAR-1, before tax): DEV1-S **€0.00898/hour**. That is €6.56 for 730 h, or **€7.87/month incl. 20 % VAT**.
- The page excludes public IPv4 and storage from list prices and did not show their prices. **Unknown until read in the console at approval time.**
- **Ceiling: €25/month incl. VAT, all items.** If the console quote for instance + IPv4 + storage exceeds €20 incl. VAT, stop. Do not provision.
- Planned lifetime: **at most 21 days** (five ordinary lunch days, plus setup and slack). Expected compute is 504 h × €0.00898 = €4.53 before tax.
- Controls: set a billing alert at €15 if the console offers one, otherwise check consumption every Monday. Tear down on day 21, at the ceiling, or on a STOP decision, whichever comes first.
- No other paid service: no mail, SMS, paid API, CDN, managed database or map tiles.

## 3. Access: invite-only

- An invite link `https://<host>/invite/<random code>` sets an HttpOnly `cq_invite` cookie at the proxy. Every other request without that cookie gets 403 "Bêta privée sur invitation." The operator shows the link or a QR code to volunteers in person. The code exists only in the Caddyfile on the host, never in Git, Foundry or chat logs. Rotate it to revoke everyone.
- Proxy basic auth is deliberately **not** used. It would occupy the `Authorization` header that the app's admin API needs for `CQ_ADMIN_TOKEN`, and `/admin` would become unusable. This was found while drafting.
- `/admin*` returns 404 except from the operator's current public IP (`remote_ip`), and the app's bearer token is still required. If that IP changes (for example on mobile data), update one line and reload Caddy.
- Known limit, unverified: browsers fetch the web-app manifest without cookies, so "Add to home screen" may fail behind the invite gate. The site itself works in the browser.
- Testers are volunteers who already eat at Cuvier/Châtelet. No recruitment messages are part of this payload; any outreach text needs its own approval.

## 4. Data, retention and privacy

| Data | Retention | Enforced by |
| --- | --- | --- |
| Reports, timers, flags, moderation audits | deleted at 7 days | app retention loop every minute, plus an hourly `crous-queue retain` systemd timer |
| Per-report network key (ADR-0009), rate counters | at most 24 h | same jobs |
| Backups (`pg_dump --format=custom`, nightly, 0600, `/var/backups/crous-queue/`) | deleted after 7 days | backup timer deletes files with `-mtime +6` |
| Caddy access logs | **disabled** (no IPs, no query strings on disk) | Caddyfile has no `log` directive |
| systemd journal | app logs carry only request id, route template and status (OPERATIONS.md) | — |

The privacy page already says the operator must name themselves and a contact
before publication. **Operator name and privacy contact are required inputs**
(see §8). No raw IP is stored by the application.

## 5. Moderation duty

- The operator opens `/admin` at least once on each lunch day between 11:30 and 14:00, and at least once every 24 h during the beta.
- Comments stay pending until approved. Approve only plain observations; delete anything with names, contact details or links.
- For an evident burst, use **Masquer ce réseau (2 h)**. It also hides honest neighbours behind the same NAT, so record the reason.
- If the operator cannot keep this duty for 48 h, stop the service (§6). Do not leave it unmoderated.

## 6. Secrets, rollback and teardown

**Secrets.** On the host, generate `CQ_SESSION_SECRET`, `CQ_IP_SECRET`, `CQ_ADMIN_TOKEN` and the PostgreSQL password with `python3 -c 'import secrets;print(secrets.token_urlsafe(48))'`. Store them in `/etc/crous-queue/production.env` (root:crous-queue, 0640). None are in Git, Foundry, backups manifests or chat. Rotate all of them on teardown.

**Rollback** (failed deploy or bad migration):
1. `systemctl stop crous-queue`.
2. Keep the failed database for inspection. Restore the last pre-deploy dump into a **new** database: `createdb crous_queue_rollback && pg_restore --no-owner -d crous_queue_rollback /var/backups/crous-queue/<file>.dump`.
3. Reinstall the previously verified wheel into a fresh venv. Point `CQ_DATABASE_URL` at the restored database explicitly. Run `crous-queue migrate` then `crous-queue retain`. Start the service.
4. Never downgrade a live schema in place (RELEASE.md).

**Teardown** (day 21, ceiling reached, STOP, or human request). Commands are illustrative; verify each with `--help` at the time:
1. `systemctl stop crous-queue caddy`. Final `crous-queue retain`.
2. Export the anonymous measurement summary only (`scripts/check_pilot.py` outputs). Keep no raw reports.
3. Delete databases and backups on the host: `dropdb crous_queue_production; rm -rf /var/backups/crous-queue`.
4. `scw instance server terminate <server-id> with-ip=true with-block=true zone=fr-par-1`.
5. Remove the DNS record for the beta hostname.
6. Revoke the SSH key and the provider API key used for setup. Rotate the shared tester credential.
7. Confirm in the console that the server, IP and volumes list is empty and that the next invoice line stops. Record the confirmation in Foundry.

## 7. Dry-run checklist (no provisioning)

Run locally before asking for approval. Rows marked done were run on 2026-10-09.

- [x] Exact-SHA CI green for the build commit (run 37970042546). Artifact manifest checksums match the downloaded files.
- [x] PostgreSQL branch against a disposable local PostgreSQL 18.6 cluster: migration head→0006→head, 8 concurrent identical retries → 1 row, 8 concurrent throttle racers → 1 accepted / 7 `contribution_too_soon`, network budget (6 devices → count 2, excluded 4), concurrent admin hide → one success and one `moderation_conflict`, UTC round trip, 7-day retention, `pg_dump`/`pg_restore` row counts equal. Evidence: `docs/evidence/p4-20261009/postgresql-verify.txt`. **Production target is PostgreSQL 16**: rerun `scripts/verify_postgresql.py` against 16 before go-live.
- [x] `production.env.example` with dummy secrets passes the production settings validator (PostgreSQL, HTTPS, secure cookies, admin token, trusted proxy parse). Evidence: `docs/evidence/p4-20261009/config-dry-run.txt`.
- [x] Trusted-proxy behaviour is covered by `tests/integration/test_abuse.py` and `tests/unit/test_client_address.py`. A forged `X-Forwarded-For` from an untrusted peer is ignored.
- [ ] On the host after approval: `caddy validate --config /etc/caddy/Caddyfile` (Caddy is not installed locally, so the draft is unvalidated); a request without the invite cookie gets 403; `/admin` from another IP gets 404; two phones on different mobile networks appear as "2 réseaux"; `curl -H 'X-Forwarded-For: 1.2.3.4' http://<public-ip>:8000` is refused (port closed).
- [ ] On the host: stop the app, run `crous-queue retain`, confirm reports older than 7 days and network keys older than 24 h are gone (stopped-app recovery drill, OPERATIONS.md).
- [ ] Backup and restore drill on the host into a new database before inviting testers.

## 8. Human inputs required for approval (none inferred)

1. R011 answered: which queue, ordinary access at Cuvier/Châtelet.
2. Android incumbent check (Affluences, CrousRadar, Croustillapp) for live Cuvier/Châtelet data. If an incumbent already shows live Cuvier waits, STOP: do not approve this payload.
3. Operator legal name and privacy contact for the privacy page.
4. Hostname under an existing operator domain, or a decision to stop.
5. Scaleway account to use (existing or new). Creating it is the human's action.
6. Console quote for DEV1-S + IPv4 + storage in fr-par-1, at most €20 incl. VAT.
7. Operator's public IP for `/admin`, and a random invite code. Both stay on the host only.
8. Exact approval text naming this file, its commit and the wheel sha256.

Machine-readable summary: [`proposal.json`](proposal.json).
