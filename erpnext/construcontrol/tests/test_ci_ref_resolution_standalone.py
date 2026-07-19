from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / ".github" / "helper" / "resolve-ci-refs.sh"


def resolve(repository_ref: str, **environment: str) -> tuple[str, str]:
    env = os.environ.copy()
    env.update(environment)
    completed = subprocess.run(
        ["bash", str(SCRIPT), repository_ref],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    lines = completed.stdout.strip().splitlines()
    if len(lines) != 2:
        raise AssertionError(f"Unexpected resolver output: {completed.stdout!r}")
    return lines[0], lines[1]


class CiReferenceResolutionTest(unittest.TestCase):
    def test_main_maps_to_pinned_frappe_and_version_15_payments(self) -> None:
        self.assertEqual(resolve("main"), ("v15.115.4", "version-15"))

    def test_upstream_version_branch_is_preserved(self) -> None:
        self.assertEqual(resolve("version-15"), ("version-15", "version-15"))

    def test_explicit_environment_overrides_are_honored(self) -> None:
        self.assertEqual(
            resolve("main", FRAPPE_BRANCH="develop", PAYMENTS_BRANCH="develop"),
            ("develop", "develop"),
        )


if __name__ == "__main__":
    unittest.main()
