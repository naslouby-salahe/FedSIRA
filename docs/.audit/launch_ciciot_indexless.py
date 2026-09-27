from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = "indexless-20260925"
LOG = ROOT / "docs" / ".audit" / f"preprocess-cic-{ATTEMPT}.log"
PID_FILE = ROOT / "docs" / ".audit" / f"preprocess-cic-{ATTEMPT}.pid"
EXIT_FILE = ROOT / "docs" / ".audit" / f"preprocess-cic-{ATTEMPT}.exit"

command = (
    ".venv/bin/fedsira preprocess CICIoT2023; result=$?; "
    f"printf '%s\\n' \"$result\" > '{EXIT_FILE.as_posix()}'"
)
with LOG.open("w", encoding="utf-8") as output:
    process = subprocess.Popen(
        ["bash", "-lc", command],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=output,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
PID_FILE.write_text(f"{process.pid}\n", encoding="utf-8")
print(f"pid={process.pid} log={LOG.relative_to(ROOT)}")
