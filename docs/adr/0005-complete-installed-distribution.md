# ADR-0005 — complete wheel and source-kit contract

Accepted for Q07 local distribution, 2026-10-08.

The 0.1.1 source kit bootstraps correctly, while an independently installed 0.1.1 wheel fails migration because it looks for cwd-relative Alembic configuration and omits revisions. The audit's source-kit result is preserved; its bare-wheel limitation is reproduced in Q07 evidence before repair.

Version 0.1.2 packages the authoritative migrations and dated CNOUS snapshot/provenance inside `crous_queue`. `distribution.py` resolves them using `importlib.resources`; CLI migration uses programmatic Alembic config without a caller ini file. Installed CLI adds non-overwriting private configuration and the same explicitly separated synthetic demo operation. Missing resources produce a reinstall/path message. Original root migration files and fixture snapshots remain retained for historical comparison; new migration revisions belong in the installed package.

Both the standalone wheel with runtime dependencies and the full source kit are complete supported local distributions on tested Linux/Python 3.13. The source kit additionally supplies the lock, tests, browser harness, developer/pilot scripts and documentation. The wheel itself is not a copy of the operator's data/config or a deployment artifact approved for public hosting. A fresh wheel-only environment installs runtime dependencies with exported lock hashes; no checkout migrations/fixtures are copied in.

CI uses Python 3.13 and `uv sync --locked`, which rejects manifest drift rather than silently relying on a stale frozen lock. One standard Linux job, 15-minute timeout, concurrency cancellation, read-only repository permissions, no live providers, no deployments/package publication and 7-day small artifact retention bound the authorized private verification. Explicit third-party Alembic import classification makes lint independent of a root directory shadowing its installed module.

Revisit only for a demonstrated installed-resource incompatibility or an explicitly authorized additional platform/public-concurrency target. Real intake, PostgreSQL/public concurrency, account/provider costs and field usefulness remain outside this release gate.
