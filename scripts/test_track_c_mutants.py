"""Prove the Track C contract suites reject construction-known source defects."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "packages" / "provider_contracts"
STRUCTURED = ROOT / "packages" / "structured_output"


@dataclass(frozen=True)
class Mutation:
    name: str
    package: str
    old: str
    new: str
    test: str


MUTATIONS = (
    Mutation(
        "instance-cache-ignored",
        "provider_contracts",
        'return self.cache_dir / key[:2] / f"{key}.json"',
        'return DEFAULT_CACHE_DIR / key[:2] / f"{key}.json"',
        "test_replay_uses_instance_directory_and_never_falls_through",
    ),
    Mutation(
        "replay-miss-falls-through",
        "provider_contracts",
        "if self.record_with is None:\n            raise NotRecorded(",
        "if False and self.record_with is None:\n            raise NotRecorded(",
        "test_replay_uses_instance_directory_and_never_falls_through",
    ),
    Mutation(
        "rate-limit-misclassified",
        "provider_contracts",
        "if exc.code == 429:\n                raise RateLimited",
        "if False:\n                raise RateLimited",
        "test_rate_limit_is_distinct_from_other_http_failures",
    ),
    Mutation(
        "raw-url-error-leaks",
        "provider_contracts",
        "except (urllib.error.URLError, TimeoutError, OSError) as exc:",
        "except TimeoutError as exc:",
        "test_url_failure_is_normalized",
    ),
    Mutation(
        "empty-content-accepted",
        "provider_contracts",
        'if not isinstance(text, str) or not text.strip():\n            raise InvalidResponse("provider response content must be a non-empty string")',
        'if False:\n            raise InvalidResponse("provider response content must be a non-empty string")',
        "test_malformed_success_envelope_is_rejected",
    ),
    Mutation(
        "trailing-prose-swallowed",
        "structured_output",
        "return stripped[start : index + 1]",
        "return stripped[start:]",
        "test_construction_known_response_shapes",
    ),
    Mutation(
        "schema-validation-bypassed",
        "structured_output",
        "errors = validate(value, schema)",
        "errors = []",
        "test_relay_shaped_defects_are_refused",
    ),
    Mutation(
        "parse-labelled-extract",
        "structured_output",
        'return None, "parse", f"invalid JSON: {exc}"',
        'return None, "extract", f"invalid JSON: {exc}"',
        "test_construction_known_response_shapes",
    ),
)


def run_test(package: str, source_root: Path, test: str) -> subprocess.CompletedProcess[str]:
    package_root = PROVIDER if package == "provider_contracts" else STRUCTURED
    test_file = (
        package_root / "tests" / "test_provider_contracts.py"
        if package == "provider_contracts"
        else package_root / "tests" / "test_structured_output.py"
    )
    env = os.environ.copy()
    paths = [str(source_root)]
    if package == "structured_output":
        paths.append(str(PROVIDER / "src"))
    existing = env.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", f"{test_file}::{test}"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    baseline_failures: list[str] = []
    for package in ("provider_contracts", "structured_output"):
        source = (PROVIDER if package == "provider_contracts" else STRUCTURED) / "src"
        result = run_test(
            package,
            source,
            (
                "test_replay_uses_instance_directory_and_never_falls_through"
                if package == "provider_contracts"
                else "test_construction_known_response_shapes"
            ),
        )
        if result.returncode:
            baseline_failures.append(package)
    if baseline_failures:
        print("FAIL clean control: " + ", ".join(baseline_failures))
        return 1

    survivors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="proofgrid-track-c-mutants-") as directory:
        temp = Path(directory)
        for mutation in MUTATIONS:
            package_root = PROVIDER if mutation.package == "provider_contracts" else STRUCTURED
            source = package_root / "src"
            mutated_source = temp / mutation.name / "src"
            shutil.copytree(source, mutated_source)
            module = next(mutated_source.rglob("core.py"))
            original = module.read_text(encoding="utf-8")
            if original.count(mutation.old) != 1:
                print(f"FAIL {mutation.name}: mutation anchor count is {original.count(mutation.old)}")
                return 1
            module.write_text(original.replace(mutation.old, mutation.new), encoding="utf-8")
            result = run_test(mutation.package, mutated_source, mutation.test)
            killed = result.returncode != 0
            print(f"{'KILLED' if killed else 'SURVIVED'} {mutation.name}")
            if not killed:
                survivors.append(mutation.name)

    if survivors:
        print("FAIL surviving mutants: " + ", ".join(survivors))
        return 1
    print(f"PASS clean controls and {len(MUTATIONS)}/{len(MUTATIONS)} mutants killed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
