from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / ".audit"
LOG = AUDIT / "preprocess-cic-local-staging-20260926.log"
PID_FILE = AUDIT / "preprocess-cic-local-staging-20260926.pid"
EXIT_FILE = AUDIT / "preprocess-cic-local-staging-20260926.exit"


def run_worker() -> None:
    environment = os.environ.copy()
    bounded_duckdb = str(AUDIT / "duckdb-limited")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (bounded_duckdb, environment.get("PYTHONPATH", "")) if part
    )
    with LOG.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [".venv/bin/fedsira", "preprocess", "CICIoT2023"],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
        )
    EXIT_FILE.write_text(f"{result.returncode}\n", encoding="utf-8")


def main() -> None:
    if sys.argv[1:] == ["worker"]:
        run_worker()
        return
    EXIT_FILE.unlink(missing_ok=True)
    worker = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "worker"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_FILE.write_text(f"{worker.pid}\n", encoding="utf-8")
    print(f"pid={worker.pid} log={LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
