# Crous Queue implementation instructions

Read `/home/jonathan/startup_lab/AGENTS.md`, then this file and `docs/mvp/AGENT_HANDOFF.md`. This is product implementation, not a learner slice.

- Product scope and constraints: `docs/mvp/DECISION.md` and `docs/mvp/ARCHITECTURE.md`; work order: `docs/mvp/ROADMAP.md`. Do not silently widen scope.
- Resume Foundry and claim only the next eligible package before editing. Never use live application data as a fixture. Keep immutable results and exact test evidence.
- Write current-package acceptance first; label red specification tests versus green regressions. Gates: `make check`, `make test-browser`; CI also builds and verifies both distributions (`docs/RELEASE.md`).
- Schema changes are new revisions in `src/crous_queue/migrations/versions`; never edit earlier ones. Root `alembic/` and `fixtures/venues-2026-10-07.json` are retained historical copies (ADR-0005), not the active schema or shipped snapshot.
- Keep this app independently runnable. Foundry is coordination tooling via CLI, never a runtime import. Do not change other venture repositories as a side effect.
- No real sends, payments, external provider account creation, public hosting, cloud provisioning, Git pushes or irreversible actions without exact authorization. Local fake providers and synthetic data are expected.
- No credentials, personal traces, databases or generated environments in Git. Preserve unrelated/staged changes. Do not commit/push unless asked.
- At each checkpoint report evidence/unknowns and Foundry friction using `tools/foundry_agent.py`. Do not wait for a perfect platform; retain feedback locally if Foundry is unavailable and continue independent work only when ownership is already established.
- If a needed decision is missing, record a bounded blocker with alternatives and continue independent accepted work. Never pretend synthetic tests validate demand or physical advice.

## Required Foundry workflow and feedback

Use Foundry to coordinate this repository's work. Read [docs/mvp/AGENT_HANDOFF.md](docs/mvp/AGENT_HANDOFF.md)
for the complete claim, context, result-review and recovery procedure. Run commands
from this repository; `.foundry/project.json` selects its venture/workspace, the
operator's store and the feedback destination.

Before starting an implementation package:

```bash
python3 tools/foundry_agent.py cli agent guide
python3 tools/foundry_agent.py resume
python3 tools/foundry_agent.py start --actor YOUR_AGENT_UNIQUE_SESSION
```

Read the saved context and relevant arrivals before editing. Claim only eligible
work in the assigned scope; do not steal a claim, silently pivot the venture or
create an empty replacement store. If the user's task differs from the reviewed
next package, reconcile the work scope rather than claiming an unrelated task.
Use `python3 tools/foundry_agent.py cli agent schema --name result` and the handoff
to submit checkpoint evidence, actual tests, limits and proposed next work. Preview
and resolve results only within your assigned review authority. A chat summary
alone does not update Foundry. No Codex-specific integration is required.

Report blocking Foundry defects immediately. At each package checkpoint, report
observed bugs, friction, improvement ideas or useful behavior; if none occurred,
say so in the checkpoint result rather than inventing feedback. To submit a report:

```bash
python3 tools/foundry_agent.py feedback-template > .foundry/feedback-input.json
# Fill descriptive fields; keep the generated UUID and venture/workspace IDs.
python3 tools/foundry_agent.py feedback --input .foundry/feedback-input.json
```

Use kind `bug`, `friction`, `idea` or `positive`. Include what you expected, what
happened, reproduction steps, impact, suggested improvement and sanitized evidence
paths. Keep secrets, personal data and confidential documents out of reports.

**Where it goes:** an immutable local outbox entry is saved as
`feedback/<UUID>.json`; successful delivery adds `feedback/<UUID>.receipt.json`.
The helper records it as evidence in **Foundry's own venture (`v-foundry`)**, using
`feedback_workspace_id` from the manifest, while retaining this source venture's
identity. It appears in Foundry's Now/unreviewed evidence for coordinator triage.
A receipt means recorded, not fixed. For failed delivery, retry the identical
outbox file with `feedback --input feedback/<UUID>.json`; use a new template/UUID
for a different report. Continue independent work during an outage only when its
ownership and scope are already established; reconcile on reconnection.
