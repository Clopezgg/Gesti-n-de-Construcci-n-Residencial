from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"
HEAVY = (
    "server-tests-mariadb.yml",
    "construcontrol-runtime-receipt.yml",
    "construcontrol-container-receipt.yml",
    "forensic-audit-snapshot.yml",
)


class CertificationLaneContractTest(unittest.TestCase):
    def test_heavy_workflows_are_manual_gate_only(self):
        for filename in HEAVY:
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            trigger = text.split("permissions:", 1)[0]
            self.assertIn("workflow_dispatch:", trigger, filename)
            self.assertNotRegex(
                trigger,
                re.compile(r"^\s{2}(push|pull_request|schedule):", re.MULTILINE),
                filename,
            )
            for gate in ("A", "B", "C", "FINAL"):
                self.assertRegex(trigger, rf"(?m)^          - {gate}$", filename)
            self.assertNotIn("continue-on-error", text, filename)

    def test_fast_lanes_still_validate_pull_requests(self):
        for filename in ("construcontrol-verification-receipt.yml", "linters.yml"):
            text = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertIn("pull_request:", text, filename)


if __name__ == "__main__":
    unittest.main()
