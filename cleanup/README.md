# Notes for the next cleanup pass

## Records, not junk

- `docs/evidence/`, `acceptance/`, `docs/IMPLEMENTATION_LOG.md`, `docs/adr/`,
  `docs/mvp/` (including the dated `*HANDOFF*.md`, `FIRST_TASK.md`, `spec.json`),
  `remarks` and `feedback/README.md` are package history. Do not trim or delete.
- `deploy/` is a tracked NOT AUTHORIZED draft (`docs/DEPLOYMENT_PROPOSAL.md`);
  `deploy/proposal.json` was refreshed on 2026-10-09 (P3/P4) to 0.2.1 / schema 0007
  with the exact approval payload in `deploy/PRIVATE_BETA_APPROVAL.md`; approving
  it remains a human call.

## Looks dead, kept on purpose

- Root `alembic/` (revisions 0001-0003) and `fixtures/venues-2026-10-07.json`
  duplicate packaged files; ADR-0005 retains them for history. Active migrations
  live in `src/crous_queue/migrations/versions`; tests use the fixture, the wheel
  ships `src/crous_queue/resources/` (a test pins them byte-identical).
- `tools/foundry_agent.py` is vendored byte-for-byte from Foundry. Never edit here.
- `httpx2` (dev) is what `starlette.testclient` imports; `psycopg[binary]` backs
  the `postgresql+psycopg` URLs that production settings require.

## Full CI-equivalent locally

```bash
uv sync --locked && make check
uv run --locked playwright install chromium && make test-browser
mkdir -p dist && uv export --locked --no-dev --no-emit-project --output-file dist/runtime-requirements.txt
uv build && uv run --locked python scripts/package_release.py
uv run --locked python scripts/verify_wheel.py --output wheel-verification.json
uv run --locked python scripts/verify_release.py
uv run --locked python scripts/release_manifest.py --output dist/release-manifest.json
```

`verify_release.py` runs `make install`/`make check` in an extracted kit: it
needs ~600 MB free in `TMPDIR` and must not inherit `UV_PROJECT_ENVIRONMENT`.
Browser screenshots land in ignored `docs/evidence/<CQ_EVIDENCE_PREFIX>-*.png`.

## Coverage gaps left deliberately

`scripts/verify_*.py`, `package_release.py`, `release_manifest.py` and
`artifact_browser.py` are exercised by the CI release steps, not pytest. The
PostgreSQL advisory-lock branch in `services/waits.py` has no PostgreSQL in CI.
