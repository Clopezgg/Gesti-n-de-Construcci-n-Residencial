from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[3] / ".github" / "helper" / "documentation.py"
SPEC = importlib.util.spec_from_file_location("documentation_check", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
	raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DocumentationCheckTest(unittest.TestCase):
	def test_non_feature_pull_request_is_skipped(self) -> None:
		result = MODULE.evaluate_pull_request(
			{"title": "Reconstrucción controlada", "body": "", "head": {"sha": "abc"}}
		)
		self.assertEqual(result[0], 0)

	def test_feature_requires_documentation_link(self) -> None:
		missing = MODULE.evaluate_pull_request({"title": "feat: module", "body": "", "head": {"sha": "abc"}})
		present = MODULE.evaluate_pull_request(
			{
				"title": "feat: module",
				"body": "See https://docs.frappe.io/framework/user/en/api",
				"head": {"sha": "abc"},
			}
		)
		self.assertEqual(missing[0], 1)
		self.assertEqual(present[0], 0)

	def test_reads_current_pull_request_from_event_payload(self) -> None:
		event = {
			"repository": {"full_name": "Clopezgg/Gesti-n-de-Construcci-n-Residencial"},
			"pull_request": {"title": "docs: audit", "body": "", "head": {"sha": "abc"}},
		}
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "event.json"
			path.write_text(json.dumps(event), encoding="utf-8")
			payload = MODULE.payload_from_event(str(path))
		self.assertEqual(payload, event["pull_request"])

	def test_github_documentation_link_with_deeper_path_is_valid(self) -> None:
		self.assertTrue(
			MODULE.is_documentation_link("https://github.com/frappe/frappe_io/blob/main/docs/example.md")
		)


if __name__ == "__main__":
	unittest.main()
