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

    def test_linters_require_exact_head_and_two_clean_all_files_passes(self):
        source = (WORKFLOWS / "linters.yml").read_text(encoding="utf-8")
        self.assertEqual(source.count("ref: ${{ github.event.pull_request.head.sha }}"), 2)
        self.assertEqual(source.count("pre-commit run --all-files"), 2)
        self.assertNotIn("pre-commit run --from-ref", source)
        self.assertIn("pre-commit-first.patch", source)
        self.assertIn("pre-commit-second.patch", source)
        self.assertIn("git-status-after-first.txt", source)
        self.assertIn("git-status-after-second.txt", source)
        self.assertEqual(source.count('test "$actual" = "$HEAD_SHA"'), 2)
        self.assertIn('test "$first_status" = "0"', source)
        self.assertIn('test "$second_status" = "0"', source)
        self.assertIn('test ! -s "$EVIDENCE_DIR/pre-commit-first.patch"', source)
        self.assertIn('test ! -s "$EVIDENCE_DIR/pre-commit-second.patch"', source)


if __name__ == "__main__":
    unittest.main()
