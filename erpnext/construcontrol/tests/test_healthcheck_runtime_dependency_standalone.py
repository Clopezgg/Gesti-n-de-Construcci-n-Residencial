from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def validate_pgrep_dependency(dockerfile: str, compose: str) -> list[str]:
    failures: list[str] = []
    if "pgrep -f" in compose:
        if not re.search(
            r"apt-get\s+install\s+-y\s+--no-install-recommends\s+procps",
            dockerfile,
        ):
            failures.append("docker-compose uses pgrep but Dockerfile does not install procps")
        if "rm -rf /var/lib/apt/lists/*" not in dockerfile:
            failures.append("Dockerfile does not remove apt package indexes")
    return failures


class HealthcheckRuntimeDependencyTest(unittest.TestCase):
    def test_product_image_supplies_pgrep_required_by_healthchecks(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertEqual(validate_pgrep_dependency(dockerfile, compose), [])

    def test_missing_procps_is_rejected(self) -> None:
        failures = validate_pgrep_dependency(
            "FROM frappe/erpnext:v15\n",
            'healthcheck:\n  test: ["CMD-SHELL", "pgrep -f worker"]\n',
        )
        self.assertIn(
            "docker-compose uses pgrep but Dockerfile does not install procps",
            failures,
        )


if __name__ == "__main__":
    unittest.main()
