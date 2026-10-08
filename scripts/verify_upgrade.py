"""Optional actual old-wheel upgrade rehearsal; never uses an operator database."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-wheel", type=Path, required=True)
    parser.add_argument("--new-wheel", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    args = parser.parse_args()
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("CQ_") and k not in {"PYTHONPATH", "VIRTUAL_ENV"}
    }
    with tempfile.TemporaryDirectory(prefix="crous-old-wheel-upgrade-") as folder:
        root = Path(folder)
        python = str(root / "venv/bin/python")
        cli = str(root / "venv/bin/crous-queue")

        def run(argv):
            result = subprocess.run(
                argv, cwd=root, env=env, capture_output=True, text=True
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)

        run(["uv", "venv", "--python", "3.13", str(root / "venv")])
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--require-hashes",
                "-r",
                str(args.requirements.resolve()),
            ]
        )
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--no-deps",
                str(args.old_wheel.resolve()),
            ]
        )
        run(
            [
                python,
                "-c",
                "import crous_queue; assert crous_queue.__version__ == '0.1.2'",
            ]
        )
        for cmd in ["configure", "migrate", "import-directory", "seed-demo"]:
            run([cli, cmd])
        run(
            [
                python,
                "-c",
                "from crous_queue.config import load_settings; from crous_queue.db import make_engine; from crous_queue.services.waits import WaitService; from crous_queue.contracts import ReportInput; from crous_queue.security import Identity; from datetime import datetime,UTC; s=load_settings(); WaitService(make_engine(s.database_url),lambda:datetime.now(UTC)).submit(Identity('synthetic-upgrade-device','synthetic-network'),'paris:r177',ReportInput(kind='estimate',minutes=0,observed_at=datetime.now(UTC),queue_kind='student',idempotency_key='synthetic-old-wheel'))",
            ]
        )
        run([cli, "backup", "--output", ".local/development-before-upgrade.db"])
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--no-deps",
                "--reinstall",
                str(args.new_wheel.resolve()),
            ]
        )
        run([cli, "migrate"])
        # Both independently created old stores must migrate; preserve demo scope.
        demo_env = {
            **env,
            "CQ_ENVIRONMENT": "demo",
            "CQ_DATABASE_URL": "sqlite:///.local/demo.db",
        }
        result = subprocess.run(
            [cli, "migrate"], cwd=root, env=demo_env, capture_output=True, text=True
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        run(
            [
                python,
                "-c",
                "from crous_queue.config import load_settings; from crous_queue.db import make_engine; from crous_queue.services.waits import WaitService; from crous_queue.services.availability import AvailabilityService; from crous_queue.contracts import ReportInput; from crous_queue.security import Identity; from datetime import datetime,UTC; s=load_settings(); e=make_engine(s.database_url); w=WaitService(e,lambda:datetime.now(UTC)); assert w.state('paris:r177').minutes==0; r=w.submit(Identity('synthetic-new-device','synthetic-network'),'paris:r177',ReportInput(kind='availability',vegetarian='unavailable',seating='unavailable',comment='Synthetic upgrade check',observed_at=datetime.now(UTC),queue_kind='student',idempotency_key='synthetic-new-wheel')); assert r.comment_status=='pending'; assert AvailabilityService(e,lambda:datetime.now(UTC)).state('paris:r177','student').dimensions['seating'].state=='unavailable'",
            ]
        )
        run(
            [
                cli,
                "restore",
                "--input",
                ".local/development-before-upgrade.db",
                "--output",
                ".local/development-old-restored.db",
            ]
        )
        # Roll back by running the actual old wheel against the restored old store.
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--no-deps",
                "--reinstall",
                str(args.old_wheel.resolve()),
            ]
        )
        result = subprocess.run(
            [
                python,
                "-c",
                "from crous_queue.db import make_engine; from crous_queue.services.waits import WaitService; from datetime import datetime,UTC; assert WaitService(make_engine('sqlite:///.local/development-old-restored.db'),lambda:datetime.now(UTC)).state('paris:r177').minutes==0",
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
        print(
            json.dumps(
                dict(
                    old="0.1.2",
                    new="0.2.0",
                    old_artifact_install="passed",
                    upgrade="passed",
                    old_backup_restore_and_old_wheel_rollback="passed",
                    data="synthetic only",
                    foundry="absent",
                )
            )
        )


if __name__ == "__main__":
    main()
