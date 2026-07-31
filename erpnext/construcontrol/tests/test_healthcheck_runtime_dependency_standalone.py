from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_SERVICES = ("queue-short", "queue-long", "scheduler")
CHILD_LIVENESS_CHECK = "pgrep -P 1 >/dev/null"


def _service_block(compose: str, service: str) -> str:
	match = re.search(
		rf"(?ms)^  {re.escape(service)}:\s*$\n(?P<body>.*?)(?=^  [a-z0-9][a-z0-9-]*:\s*$|\Z)",
		compose,
	)
	return match.group("body") if match else ""


def validate_runtime_healthchecks(dockerfile: str, compose: str) -> list[str]:
	failures: list[str] = []
	if "pgrep" in compose:
		if not re.search(
			r"apt-get\s+install\s+-y\s+--no-install-recommends\s+procps",
			dockerfile,
		):
			failures.append("docker-compose uses pgrep but Dockerfile does not install procps")
		if "rm -rf /var/lib/apt/lists/*" not in dockerfile:
			failures.append("Dockerfile does not remove apt package indexes")
	if "init: true" not in compose:
		failures.append("runtime healthchecks require init: true so PID 1 supervises the service child")
	for service in RUNTIME_SERVICES:
		block = _service_block(compose, service)
		if not block:
			failures.append(f"missing service block: {service}")
			continue
		if CHILD_LIVENESS_CHECK not in block:
			failures.append(f"{service} does not verify the live child supervised by PID 1")
		if "pgrep -f '[b]ench" in block:
			failures.append(f"{service} uses a brittle bench command-line healthcheck")
	return failures


class HealthcheckRuntimeDependencyTest(unittest.TestCase):
	def test_product_image_and_compose_supply_stable_runtime_healthchecks(self) -> None:
		dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
		compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
		self.assertEqual(validate_runtime_healthchecks(dockerfile, compose), [])

	def test_missing_procps_is_rejected(self) -> None:
		failures = validate_runtime_healthchecks(
			"FROM frappe/erpnext:v15\n",
			"init: true\n"
			"  queue-short:\n    healthcheck: pgrep -P 1 >/dev/null\n"
			"  queue-long:\n    healthcheck: pgrep -P 1 >/dev/null\n"
			"  scheduler:\n    healthcheck: pgrep -P 1 >/dev/null\n",
		)
		self.assertIn(
			"docker-compose uses pgrep but Dockerfile does not install procps",
			failures,
		)

	def test_title_based_worker_and_scheduler_checks_are_rejected(self) -> None:
		dockerfile = (
			"RUN apt-get install -y --no-install-recommends procps " "&& rm -rf /var/lib/apt/lists/*\n"
		)
		compose = (
			"init: true\n"
			"  queue-short:\n    healthcheck: pgrep -f '[b]ench worker.*short,default'\n"
			"  queue-long:\n    healthcheck: pgrep -f '[b]ench worker.*long,default,short'\n"
			"  scheduler:\n    healthcheck: pgrep -f '[b]ench schedule'\n"
		)
		failures = validate_runtime_healthchecks(dockerfile, compose)
		self.assertTrue(any("brittle bench command-line" in item for item in failures))

	def test_missing_child_liveness_check_is_rejected(self) -> None:
		dockerfile = (
			"RUN apt-get install -y --no-install-recommends procps " "&& rm -rf /var/lib/apt/lists/*\n"
		)
		compose = (
			"init: true\n"
			"  queue-short:\n    healthcheck: true\n"
			"  queue-long:\n    healthcheck: true\n"
			"  scheduler:\n    healthcheck: true\n"
		)
		failures = validate_runtime_healthchecks(dockerfile, compose)
		self.assertEqual(
			sum("does not verify the live child" in item for item in failures),
			len(RUNTIME_SERVICES),
		)


if __name__ == "__main__":
	unittest.main()
