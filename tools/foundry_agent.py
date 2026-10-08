#!/usr/bin/env python3
"""Standalone repository-side CLI bridge. No Foundry Python imports or model calls."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

BRIDGE_VERSION = "2026-10-08.1"


def write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")


def cli_argv(config: dict[str, Any], *, require_store: bool = True) -> list[str]:
    """Validate operator configuration before the CLI can initialize a store."""
    argv = config["cli"]
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(x, str) for x in argv)
    ):
        raise ValueError("project.json cli must be a nonempty argv array")
    argv = list(argv)
    for index, value in enumerate(argv):
        if value == "--store":
            if index + 1 == len(argv):
                raise ValueError("Configured --store needs an existing database path")
            path = argv[index + 1]
        elif value.startswith("--store="):
            path = value.split("=", 1)[1]
        else:
            continue
        resolved = Path(path).expanduser().resolve()
        if not path or (require_store and not resolved.is_file()):
            raise ValueError(
                "Configured Foundry store is missing; restore it or correct "
                "project.json. Refusing to create an empty operator database."
            )
        # Pass the exact checked path, including expansion; subprocess has no shell.
        if value == "--store":
            argv[index + 1] = str(resolved)
        else:
            argv[index] = "--store=" + str(resolved)
    return argv


def command_timeout(config: dict[str, Any]) -> int:
    value = config.get("timeout_seconds", 60)
    if type(value) is not int or not 1 <= value <= 600:
        raise ValueError("timeout_seconds must be an integer from 1 to 600")
    return value


def run_command(
    config: dict[str, Any], args: tuple[str, ...], *, capture: bool
) -> subprocess.CompletedProcess[str]:
    timeout = command_timeout(config)
    static = args[:2] in {("agent", "guide"), ("agent", "schema")}
    try:
        return subprocess.run(
            [*cli_argv(config, require_store=not static), *args],
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Foundry exceeded {timeout}s. A mutation outcome may be unknown; "
            "inspect resume/result show and saved context before retrying. "
            "No automatic retry was performed. Keep the same request key/payload "
            "for an idempotent retry. Use --timeout-seconds 120 for a bounded "
            "read retry; never reset the store or steal a claim."
        ) from exc


def invoke(config: dict[str, Any], *args: str) -> dict[str, Any]:
    completed = run_command(config, args, capture=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip()[-2000:] or "Foundry command failed")
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise ValueError("Foundry returned an unexpected response")
    return value


def submit(
    config: dict[str, Any], payload: dict[str, Any], *args: str
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="foundry-input-") as folder:
        path = Path(folder) / "input.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return invoke(config, *args, "--input", str(path))


def start_work(
    config: dict[str, Any],
    actor: str,
    work_id: str | None,
    budget: int,
    *,
    resume_owned: bool = False,
) -> dict[str, Any]:
    workspace = config["workspace_id"]
    state = invoke(
        config, "agent", "resume", "--workspace-id", workspace, "--format", "json"
    )
    review = state.get("current_review") or {}
    selected = work_id or review.get("next_work_item_id")
    work = next((w for w in state["work"] if w["id"] == selected), None)
    if work is None:
        raise ValueError(
            "No current next work; completed MVPs need an explicitly reviewed "
            "continuation via venture-work create, then start --work-id. "
            "Do not reclaim completed work or invent an unrelated task."
        )
    if not state["map_revision_id"]:
        raise ValueError("Create and review a decision map before starting work")
    if resume_owned:
        if work["status"] != "in_progress" or work["owner"] != actor:
            raise ValueError(
                "Recovery requires in_progress work with this exact owner; "
                "use normal start for ready work and never take another owner's claim"
            )
        # No claim mutation and no release on failure: interrupted work stays owned.
        return submit(
            config,
            {
                "work_id": work["id"],
                "expected_work_version": work["version_id"],
                "expected_head": state["map_revision_id"],
                "request_key": "recover:" + str(uuid4()),
                "actor": actor,
                "budget_bytes": budget,
            },
            "handoff",
            "prepare",
            "--workspace-id",
            workspace,
        )
    claimed = submit(
        config,
        {"expected_version": work["version_id"], "actor": actor},
        "handoff",
        "claim",
        "--workspace-id",
        workspace,
        "--work-id",
        work["id"],
    )
    try:
        return submit(
            config,
            {
                "work_id": work["id"],
                "expected_work_version": claimed["version_id"],
                "expected_head": state["map_revision_id"],
                "request_key": "start:" + str(uuid4()),
                "actor": actor,
                "budget_bytes": budget,
            },
            "handoff",
            "prepare",
            "--workspace-id",
            workspace,
        )
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        # Preparation has no work effects. Release only our exact, unchanged claim.
        submit(
            config,
            {
                "expected_version": claimed["version_id"],
                "actor": actor,
                "rationale": "Context preparation failed; release this exact claim",
            },
            "handoff",
            "release",
            "--workspace-id",
            workspace,
            "--work-id",
            work["id"],
        )
        raise


def send_feedback(config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    required = {
        "id",
        "venture_id",
        "workspace_id",
        "actor",
        "kind",
        "summary",
        "expected",
        "actual",
        "reproduction",
        "impact",
        "suggestion",
        "sources",
    }
    if not required <= report.keys():
        raise ValueError(
            "Feedback is missing: " + ", ".join(sorted(required - report.keys()))
        )
    if (
        report["venture_id"] != config["venture_id"]
        or report["workspace_id"] != config["workspace_id"]
    ):
        raise ValueError("Feedback belongs to another project; use its configuration")
    if report["kind"] not in {"bug", "friction", "idea", "positive"}:
        raise ValueError("Feedback kind must be bug, friction, idea or positive")
    if not all(
        isinstance(report[k], str) and report[k].strip() for k in required - {"sources"}
    ):
        raise ValueError("Feedback text fields must be nonempty strings")
    if not isinstance(report["sources"], list) or not all(
        isinstance(s, str) for s in report["sources"]
    ):
        raise ValueError("sources must be a list of source locators")
    payload = {
        "request_key": "dogfood:" + report["id"],
        "actor": report["actor"],
        "summary": "[Dogfood/" + report["kind"] + "] " + report["summary"],
        "details": json.dumps(report, ensure_ascii=False, sort_keys=True),
        "epistemic_status": "inference" if report["kind"] == "idea" else "observation",
        "sources": ["document: feedback/" + report["id"] + ".json"],
        "confidence": "low",
    }
    with tempfile.TemporaryDirectory(prefix="foundry-feedback-") as folder:
        path = Path(folder) / "input.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return invoke(
            config,
            "change",
            "record",
            "--workspace-id",
            config["feedback_workspace_id"],
            "--input",
            str(path),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=".foundry/project.json")
    parser.add_argument(
        "--timeout-seconds", type=int, help="Bound each CLI call (1–600s)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("resume")
    commands.add_parser(
        "doctor", help="Check bridge, public contract and store configuration"
    )
    command = commands.add_parser(
        "cli", help="Use the configured public CLI; start with: cli agent guide"
    )
    command.add_argument("arguments", nargs=argparse.REMAINDER)
    start = commands.add_parser("start", help="Claim current work and prepare context")
    start.add_argument("--actor", required=True)
    start.add_argument("--work-id")
    start.add_argument("--budget-bytes", type=int, default=24000)
    start.add_argument("--resume-owned", action="store_true")
    commands.add_parser("feedback-template")
    feedback = commands.add_parser(
        "feedback", help="Retain and send one sanitized feedback report"
    )
    feedback.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        config_path = Path(args.config).resolve()
        config = json.loads(config_path.read_text())
        if args.timeout_seconds is not None:
            config["timeout_seconds"] = args.timeout_seconds
        command_timeout(config)
        if args.command == "cli":
            # Pass argv, never a shell string. This trusted-local convenience is
            # not an authorization boundary or workspace-limited credential.
            return run_command(
                config, tuple(args.arguments or ["--help"]), capture=False
            ).returncode
        if args.command == "doctor":
            argv = cli_argv(config)
            schema = invoke(config, "agent", "schema", "--name", "result")
            kit_hash = sha256(Path(__file__).read_bytes()).hexdigest()
            result = {
                "bridge_version": BRIDGE_VERSION,
                "agent_contract_version": schema.get(
                    "x-foundry-agent-contract", "legacy"
                ),
                "kit_sha256": kit_hash,
                "manifest_hash_matches": config.get("kit_sha256") == kit_hash,
                "workspace_id": config["workspace_id"],
                "venture_id": config["venture_id"],
                "configured_cli": argv,
                "timeout_seconds": command_timeout(config),
                "store_file_checked": any(
                    arg == "--store" or arg.startswith("--store=") for arg in argv
                ),
                "database_opened": False,
                "next_check": "Run resume to verify workspace records; "
                "doctor checks configuration only",
            }
        elif args.command == "resume":
            result = invoke(
                config,
                "agent",
                "resume",
                "--workspace-id",
                config["workspace_id"],
                "--format",
                "json",
            )
        elif args.command == "start":
            result = start_work(
                config,
                args.actor,
                args.work_id,
                args.budget_bytes,
                resume_owned=args.resume_owned,
            )
            path = config_path.parent / "runs" / (result["id"] + ".json")
            write_new(path, result)
            result = {"saved_context": str(path), **result}
        elif args.command == "feedback-template":
            result = {
                key: "Describe " + key
                for key in [
                    "actor",
                    "summary",
                    "expected",
                    "actual",
                    "reproduction",
                    "impact",
                    "suggestion",
                ]
            }
            result.update(
                id=str(uuid4()),
                venture_id=config["venture_id"],
                workspace_id=config["workspace_id"],
                kind="friction",
                sources=[],
            )
        else:
            report = json.loads(Path(args.input).read_text())
            # Durable outbox first; sync retry uses the same request key and bytes.
            identity = report.get("id", "")
            from uuid import UUID

            UUID(identity)
            destination = config_path.parent.parent / "feedback" / (identity + ".json")
            if destination.exists():
                if json.loads(destination.read_text()) != report:
                    raise ValueError(
                        "An existing feedback ID has different content; issue a new ID"
                    )
            else:
                write_new(destination, report)
            result = send_feedback(config, report)
            receipt = destination.with_suffix(".receipt.json")
            if not receipt.exists():
                write_new(receipt, result)
            result = {"feedback_file": str(destination), "receipt": result}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(
            "Foundry bridge: "
            + str(exc)
            + "\nRetained feedback without a receipt can be retried "
            "with the same --input. Do not bypass claims or edit the database.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
