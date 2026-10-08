# ADR-0001 — Crous Queue bounded MVP

Status: accepted for implementation planning, 2026-10-07.

## Context

Find a university restaurant and see or report a recent wait in seconds, with unknown/stale states that cannot be confused with zero waiting.

## Decision

GO for a national-directory, crowd-reporting MVP. All 26 official feeds were fetched: 972 unique region-scoped venue IDs, including restaurants, cafeterias and other types. This is observed directory coverage, not proof every venue is open or every university restaurant is listed. Seed Cuvier/Châtelet for a local pilot without blocking the build on lunch observations.

Use the existing or specified modular monolith and replaceable domain/provider boundaries. Keep operational app data separate from Foundry coordination. Follow docs/mvp/ARCHITECTURE.md.

## Consequences

One executable private workflow is prioritized; later capabilities remain explicit. Deployment and market validation are separate gates. Repository can run and test without Foundry.

## Revisit

Five lunch days at Cuvier/Châtelet after a usable app exists: freshness coverage at fixed checks, estimate versus own completed wait (clearly different measures), contribution friction and repeat contributors. No mandatory interviews before implementation. National venue availability does not imply national live data. If reporting stays sparse, keep honest unknowns and test distribution rather than adding fictitious prediction.
