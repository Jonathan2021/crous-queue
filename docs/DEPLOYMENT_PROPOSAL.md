# Deployment checkpoint — version 0.2.1

> Refreshed 2026-10-09 (P3): this text previously described 0.1.2 / schema 0003 and
> must not have been approved in that state. The exact hosted private-beta approval
> payload (host, region, cost ceiling, teardown, dry-run checklist) is
> [`deploy/PRIVATE_BETA_APPROVAL.md`](../deploy/PRIVATE_BETA_APPROVAL.md) (P4,
> 2026-10-09), also NOT AUTHORIZED. Where the two differ, that file is current.

Authorization: **NOT AUTHORIZED**. This is a concrete technical proposal for later exact approval, not a deployment instruction to execute now. No provider account, public hosting resource, domain, send or payment is authorized here. Q07 separately authorizes the private source repository and included-allowance Actions; that authorization does not approve this deployment.

Current approved payload: local source/release archive and wheel 0.2.1, Python 3.13, `uv.lock`, packaged schema head `0007` (`src/crous_queue/migrations/versions`), national retained directory dated 2026-10-07, **zero invented waits outside demo**, loopback app port 8000 and separate synthetic demo port 8001. Build checksums are recorded in the commit-specific `release-manifest.json` in the private CI artifact; prior 0.1.0/0.1.1 build evidence remains retained. Local incremental service cost: €0, using the existing computer; this excludes operator time/electricity.

Proposed first hosted payload: one EU-located operator-managed host, one app process running this exact build, one PostgreSQL database, a TLS reverse proxy, a private backup directory and independent hourly retention/health checks. Initial resource ceiling: 2 vCPU, 4 GiB RAM, 20 GiB storage; application request body <=4 KiB; one report per device/venue per 2 minutes, 30 contributions/device/hour and `CQ_NETWORK_HOURLY_LIMIT` (default 120) per coarse network/hour; at most `CQ_NETWORK_ESTIMATE_CAP` (default 2) live estimates counted per coarse network (ADR-0009). The app binds to loopback, so the TLS proxy runs on the same host and `CQ_TRUSTED_PROXIES=127.0.0.1` with `CQ_FORWARDED_HEADER=x-forwarded-for`; the proxy must set/append that header and the app port must not be reachable directly. Without that setting every user would share the proxy's single network bucket. No mail/SMS/paid API/map service. Keep demo off the public host. Hide `/admin` behind network access control as well as the independent bearer credential.

Configuration draft: `deploy/production.env.example`. The concrete public host/domain/provider, exact PostgreSQL version/image digest and provider quote are unresolved. Alternatives: (a) existing operator-owned EU host with no new bill; (b) a single modest EU VM within an explicit **€25/month maximum budget**, with alerts at €15 and service teardown at the approved ceiling. That ceiling is a planning constraint, not a verified provider price. Managed multi-service hosting is deferred. No expense is approved. Obtain a current written quote and choose the exact resource IDs, region, domain, build checksum and teardown payload before requesting approval.

Before that exact approval: validate the PostgreSQL branch against the selected version (simultaneous retry writes, throttle races, admin row version conflict, UTC behavior, migration, backup and restore). SQLite checks do not prove PostgreSQL concurrency. Name the operator and privacy contact, configure TLS/proxy trust exactly as above and verify a forged `X-Forwarded-For` sent past the proxy does not change the bucket, ensure infrastructure logs redact addresses/query strings, verify 7-day report/backup and <24-hour counter deletion with a stopped-app recovery drill. Verify physical mobile behavior and collect ordinary voluntary pilot evidence if available. Keep all missing decisions bounded in `docs/PILOT.md` and Foundry.

## Exact action to approve later

Fill and review `deploy/proposal.json`: build checksum, host/provider/account, region, public origin, PostgreSQL version/digest, maximum monthly cost, resource inventory, retention schedule, named operator/contact and the commands that provision/start/stop/delete only these resources. Approval must identify this complete filled payload. A general instruction to finish the MVP is not the exact authorization to spend or publish.

## Recovery and teardown

Before migration take a private checked backup. On failed rollout stop the app, keep the old private DB unchanged, validate an isolated restore, run migrations/retention, then change configuration explicitly. Never overwrite a live DB. Remove the public reverse-proxy route and app process; revoke this app's DB user/secrets; remove only the approved database/VM/volumes and DNS records after validating resource IDs. Remove retained reports and backups by their agreed deadlines. Confirm inventory is empty and ongoing billing is stopped. Preserve sanitized build/test receipts, never personal reports or credentials. Do not execute cloud teardown until the exact action is separately authorized.

Q06 completed local repairs and a disposable rehearsal only. Ordinary queue confirmation, willing participation, private access/intake and all external launch fields remain unapproved. The existing R011 follow-up records the next decision; synthetic measurements must not be used as usefulness evidence.
