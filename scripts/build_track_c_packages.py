"""Build both Track C wheels with a frozen, reproducible ZIP timestamp."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Frozen before the first accepted build. Wheel ZIP timestamps otherwise inherit
# wall-clock/source mtimes and identical source can produce different hashes.
SOURCE_DATE_EPOCH = "1786558244"
PACKAGES = ("provider_contracts", "structured_output")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    output = args.outdir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    for package in PACKAGES:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                str(ROOT / "packages" / package),
                "--wheel",
                "--outdir",
                str(output),
            ],
            cwd=ROOT,
            env=environment,
            check=True,
        )
    for wheel in sorted(output.glob("proofgrid_*-0.1.0-py3-none-any.whl")):
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        print(f"{digest}  {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
