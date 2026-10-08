# Q07 release readiness — local MVP 0.1.2

Prepared 2026-10-08 for the explicitly authorized private `Jonathan2021/crous-queue`
delivery. The complete local MVP supports Linux/Python 3.13, SQLite and retained or
synthetic providers. Final delivery acceptance requires the **green workflow on
the final pushed commit**, with the artifact manifest's `source_commit` matching
that SHA. The final commit/run URLs and actual Foundry resolution receipt live in
the immutable Q07 result; they cannot be embedded in their own Git commit.

## Contract and acceptance evidence

Both `crous_queue-0.1.2-py3-none-any.whl` **with runtime dependencies** and
`crous-queue-0.1.2-local.tar.gz` **complete source kit** are supported. The wheel
contains templates/static assets, the three authoritative Alembic revisions and
the dated directory/provenance. It needs no caller `alembic.ini`, checkout fixtures,
Foundry or development scripts. The exact verified wheel dependency set is the
hash-exported `runtime-requirements.txt`; the source kit includes `uv.lock`.
[ADR-0005](../adr/0005-complete-installed-distribution.md) records the choice.

Paths below are relative to [Q07 evidence](../evidence/q07-20261008-e83a/).
Earlier failures remain evidence, never replacements for green acceptance.

| Q07 criterion | Executable check and evidence | Boundary |
| --- | --- | --- |
| Upgraded Foundry and ownership | `python3 tools/foundry_agent.py doctor`; `doctor.json`: bridge/contract 2026-10-07.2, canonical helper matches. Q07 claim and complete context `9e344b61-f53f-5c03-987e-34724095b2d2`; all 14 evidence records read, full map separately fetched | R011 and blocked investigations retained |
| Reproduce historical wheel failure before repair | `wheel-red.txt`, exit 1: 0.1.1 installed outside checkout fails migration; `resources-red.txt` is the red new specification | Source kit's earlier success remains valid |
| Standalone installed distribution | `scripts/verify_wheel.py`: fresh venv, hash-enforced runtime dependencies, empty cwd, non-overwriting 0600 configuration, migrate/import, separate demo, backup/restore/retain, localhost HTTP, Foundry absent; `wheel-verified.txt`/JSON | No checkout resources copied; no live feed or real report |
| Clean complete source distribution | `scripts/verify_release.py`: extracted kit install/migrate/import, `make check`, backup/restore/retain/demo and unknown-wait HTTP; `source-kit-verified.txt`, updated harness replay `source-kit-delivery.txt` | Disposable environment-marked stores only |
| Current code quality and acceptance | `make check`: Ruff/format, strict mypy, **25 core tests**; `core-verified.txt` and clean-candidate replay. Includes empty-cwd resources, actionable missing resources and locked-manifest drift with a successful unchanged control | No skips/xfails; SQLite coverage |
| Actual user/browser behavior | `uv run --locked pytest tests/browser`: **seven Chromium checks**; `browser-delivery.txt`, exit 0 | Mobile clicks, unknown/zero, exact expiry, retries, timer/favorites, moderation, asset update and offline read-only; strict CSP retained; no physical phone trial |
| Commit-matching private CI | [Pinned workflow](../../.github/workflows/ci.yml), [private Actions runs](https://github.com/Jonathan2021/crous-queue/actions/workflows/ci.yml): Python 3.13, `uv sync --locked`, core/browser, builds, both independent distribution replays, checksum inspection | Single Ubuntu job, 15-minute timeout, cancellation, read-only permissions, seven-day small artifacts; no publish/deploy/live provider |
| Current docs and attribution | [Developer map](../DEVELOPMENT.md), [French usage](../USER_GUIDE.md), [release/install/update guide](../RELEASE.md), [operations/recovery](../OPERATIONS.md), [notices](../THIRD_PARTY_NOTICES.md) | 972 source identities observed 2026-10-07, 26 regions; no current opening/menu/access/wait claim |
| Review and retained history | `before-hashes.json`, `preserved-evidence.json`: **131 existing evidence files checked, none changed**; `source-payload-delivery.json`, staged inventory and secret/data review | Q05/Q06 artifacts and local screenshots preserved |
| Dependency review | `runtime-advisories.json`, `advisories.exit` 0; pip-audit 2.10.1, **29 runtime packages, no known vulnerabilities returned** on 2026-10-08; `third-party-inventory.json` | Dated lookup, not an exhaustive audit; no new app license inferred |

The failed candidate lint/checksum outputs (`core-final.txt`, `source-kit-final.txt`,
`artifact-inspection.txt`) record a missing import in the new manifest script.
`build-verified.txt` records rejection of an unsupported `uv build --locked` flag.
Both were corrected before the clean candidate/CI gates; installation, export and
run use `--locked`, while the supported build command is `uv build`.

The first pushed commit's [CI run](https://github.com/Jonathan2021/crous-queue/actions/runs/37772085961)
passed core checks and six browser checks, then rejected the harness's eval-based
service-worker polling under Chromium 153's strict CSP. `ci-first-browser-red.txt`
retains that failure. The bounded native `controllerchange` wait now awaits actual
worker ownership, and the offline test explicitly checks that the response still
excludes `unsafe-eval`. No application CSP relaxation or browser bypass is used.
The final commit must pass all seven checks and the release/recovery gates.

## Exact build identity

Local tools: Python **3.13.5**, uv **0.11.29**, Ruff **0.16.10**, mypy **1.20.2**,
pytest **9.1.1**, Playwright **1.63.0**. CI pins uv 0.11.29 and Python 3.13; its logs
record the exact installed patch/browser on Ubuntu 24.04. Actions are pinned to
reviewed full commit SHAs; no repository write permission is required.

`uv.lock` SHA-256:
`7808d138e1c70e49cfa6abf57931692c19802ddbba7bc62cded7611409a47718`.
The final delivery source payload SHA-256 is
`ad12b15c45c2ff78c54dbd9464bf58c745bdb01b375e15ae47e73c81c4c452b4`;
`source-payload-delivery.json` defines its exact sorted per-file hash scope (runtime, tests,
scripts, fixtures, acceptance, workflow and configuration/build/lock files).
Documentation/self-referential evidence is outside that payload; Git's final
commit covers every staged file. Local reviewed wheel SHA-256:
`4de4f9432c31d227542d3a7b801d20759b752e0dfa80219683708444f01e880b`.
Earlier source payloads remain dated evidence of the initial reviewed candidate.

The authoritative final artifact hashes/sizes and SHA are generated **after the
checkout/build** in `release-manifest.json`, retained with the matching private
Actions artifact `crous-queue-<full commit SHA>`. `runtime-requirements.txt` and
`wheel-verification.json` accompany it. This avoids a self-referential checksum in
the source archive. A local companion manifest is retained in ignored `dist/`
and the operator's Foundry run records. No GitHub Release or package publication
is involved. After the seven-day retention expires, rebuild from the private
commit using [release instructions](../RELEASE.md).

## Deliberate exclusions and remaining gates

Excluded from Git/distributions: `.env`/demo secrets, `.local` databases/backups,
session/device/application data, `.venv`/caches, generated build outputs, local
Foundry manifest/store/context and feedback outbox/receipts. Historical generated
PNG evidence stays local; its original checksums/text evidence remain retained.
The source kit also omits coordination tools and historical evidence, which are
available in the private repository/operator record; the app does not need them.
The initial repository had no HEAD/staged files/remote. Existing operator files
and listeners were preserved; no other venture repository is changed.

Real lunch-day usefulness, physical queue accuracy, volunteer intake/eligibility,
operator/access arrangements and R011 remain unresolved. [Pilot](../PILOT.md) and
[blank schedule](../PILOT_OPERATOR_SCHEDULE.md) preserve the synthetic-versus-field
distinction. PostgreSQL concurrency/recovery, external retention monitoring,
HTTPS/public hosting and exact target/cost approval remain separate release gates
in the [unapproved deployment proposal](../DEPLOYMENT_PROPOSAL.md). Private Git
delivery and bounded included-allowance CI do not clear those gates.

## Tested startup

From a fresh checkout or extracted source kit:

```bash
make install
make migrate
uv run --locked crous-queue import-directory
make serve
```

Open `http://127.0.0.1:8000` for a fresh default profile. Existing `.env` is preserved;
use its configured port/origin. For installed-wheel setup from an empty directory,
follow the [wheel commands](../RELEASE.md#wheel-from-any-empty-working-directory).
Every imported venue starts with **unknown** waiting time.
