# Q07 — Clarify distribution and deliver the local MVP

Prepared 2026-10-08 after the independent readiness audit. Read root/repository
`AGENTS.md`, `AGENT_HANDOFF.md`, `REVIEW_NEXT.md`, and current decision/architecture.
Continue accepted Q06; no new crowd-reporting feature or physical trial is required.

## Verified baseline

- Q06 result `ce2d0fb8-aa40-5c41-8a76-ab0b68bdd74d` is accepted with complete
  context. Doctor verifies bridge/contract `2026-10-07.2` and canonical helper hash.
- There are **no commits, configured remote or Actions workflow**. No matching
  repository was found under Jonathan2021. Prior handoffs prohibited commit/push;
  external delivery requires the explicit continuation prompt below this scope.
- Fresh Git-eligible source passes install/configuration, migration, retained
  directory import, separate synthetic demo seed, **22 core and seven browser
  tests**, Ruff/format/strict types, and builds.
- The versioned **source release kit works**: its existing verification harness
  independently installs, migrates/imports, tests, backs up/restores, runs retention,
  seeds its isolated demo and serves a fresh unknown-wait venue over localhost.
- **The wheel alone cannot bootstrap:** outside the checkout, with valid temporary
  configuration, `crous-queue migrate` exits 1 with `No 'script_location' key found
  in configuration.` The wheel contains no Alembic revisions; CLI migration reads
  cwd-relative `alembic.ini`, and directory import defaults to a repository fixture.
  README already directs users to source/the local archive, so this is an artifact
  support boundary to resolve explicitly, not a claim that its source quickstart fails.
- User/operations/pilot docs are substantial and checked entry-point links resolve.
  The architecture still contains initial build instructions; an actual developer
  map and an unambiguous release-artifact guide would improve maintenance.

Evidence: `docs/evidence/readiness-20261008/`; full coordinator report:
`/home/jonathan/startup_lab/foundry/docs/inquiry/readiness-review-2026-10-08-second/REPORT.md`.

## Foundry ownership

Ready Q07: `d608000e-df62-4005-a1fc-c74080e5f7e2`, workspace
`81ee3117-de70-411e-9856-07420859ffad`; unclaimed at handoff creation.

```bash
python3 tools/foundry_agent.py doctor
python3 tools/foundry_agent.py cli agent guide
python3 tools/foundry_agent.py resume
python3 tools/foundry_agent.py start --actor crous-release-YOUR_SESSION --work-id d608000e-df62-4005-a1fc-c74080e5f7e2 --budget-bytes 100000
```

Require `manifest_hash_matches: true` and bridge/contract `2026-10-07.2` or a later
reviewed upgrade. Current helper SHA-256:
`1e0be09cd1b537864e0b04bbc2358932b1efba7c7a5d4abb4c0b9aff0e91703f`.
Read saved context, full-map pointer and relevant arrivals; prepare fresh coverage
as needed. Keep existing blocked investigations and the R011 human gate unchanged.

## Required work

1. **Resolve the distribution contract first.** Prefer packaging the required
   migrations and resolving them independently of cwd; define the installed
   directory snapshot/import path and test it outside the checkout. Alternatively,
   explicitly designate the source release kit as the sole supported complete
   distribution, label the wheel as an incomplete component and remove standalone
   wheel claims from release guidance. Either choice must have exact executable
   setup instructions and honest artifact labels. Do not copy files into an audit
   smoke directory and then describe the wheel as self-contained. Retain a focused
   regression for the chosen contract and actionable missing-resource errors.
2. **Add GitHub Actions for actual local support.** On push/PR, use Python 3.13 and
   a lock-enforcing install that fails on manifest drift. Run Ruff/format/strict
   types, core tests and all seven Chromium checks with explicit prerequisites.
   Cover fresh configuration/migrate/import/demo separation, unknown versus zero,
   exact expiry, retries, moderation, online asset refresh and offline read-only
   behavior. Build and verify the supported release outside the checkout, including
   backup/restore/retention. Keep providers retained/synthetic; CI must not refresh
   live feeds or submit real wait reports. Bound jobs/concurrency/retention and use
   minimal permissions. PostgreSQL/public concurrency stays an explicit deferred
   gate unless support is newly claimed and meaningfully tested.
3. **Make code and usage docs current.** Add a release guide naming exact artifacts,
   prerequisites, install/config paths and update/rollback commands. Preserve the
   good French user quickstart, moderation guide and seven-day retention duties.
   Explain the module/provider/clock boundaries, aggregation and device/cohort
   semantics, stale/error behavior, queue identities, provenance separation and
   service-worker cache changes. Replace ambiguous scaffold instructions with an
   actual developer entry point; use targeted docstrings rather than cosmetic edits.
   Keep the 972-venue snapshot dated and attributed; it proves no current opening,
   campus eligibility, menu, seating or live reporting coverage.
4. **Prepare a reviewed source release.** Inventory untracked files, source/lock
   hashes, dependency advisories and third-party/directory attribution before
   staging. Exclude `.env`, databases, secrets, session/device data, environments
   and large generated outputs. Preserve original Q05/Q06 evidence. Regenerate
   checksums/manifests and any draft deployment artifact references for the chosen
   final build without implying deployment approval. Verify a clean candidate
   checkout and the actual intended distribution; no original data may be a fixture.

## Git delivery and completion

When explicitly authorized by the user's continuation prompt, create/use **private**
`Jonathan2021/crous-queue`, commit reviewed scoped files and push initial `main`.
Inspect unexpected existing remotes first. Do not force-push, change visibility,
deploy, publish a package or spend money. Actions must stay within the existing
included allowance; do not create public resources to bypass a private CI limit.

Wait for relevant Actions jobs on the **final pushed commit SHA**, repair failures,
and distinguish missing remote access/capacity from green CI. Finish independent
local work if delivery is blocked, then report the precise remaining gate.

Write `docs/mvp/RELEASE_READINESS.md`: criterion-to-evidence matrix, commands/tool
versions, source/artifact hashes, supported distribution contract, user/developer/
recovery links and remaining limits. Return branch/commit/CI links; retain final
self-referential IDs in the Foundry result if needed. Any final pushed change must
receive relevant CI. Account for deliberately excluded files.

Submit/preview/resolve the scoped result with exact saved-context pins and digest;
report observed Foundry feedback or explicitly none. Return the tested startup
command. Real lunch-day observation, volunteer intake, private access arrangements
and public hosting remain separately gated; no field results may be fabricated.
