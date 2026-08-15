from __future__ import annotations

import re
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
SEARCH_PAGE = APP_ROOT / "nexora/page/nexora_search/nexora_search.js"


class TestNaturalSearchContract(unittest.TestCase):
	def setUp(self) -> None:
		self.source = SEARCH_PAGE.read_text(encoding="utf-8")

	def test_natural_search_reuses_the_existing_conversation_dispatch(self) -> None:
		self.assertIn('method: "nexora.conversation.dispatch.send_message"', self.source)
		self.assertNotIn("orchestrator", self.source)
		natural_body = self.source.split("async function naturalSearch", 1)[1].split("async function search", 1)[0]
		self.assertNotIn("universal_search_consolidated", natural_body)

	def test_structured_search_remains_on_the_existing_canonical_endpoint(self) -> None:
		self.assertIn('method: "nexora.boot.universal_search_consolidated"', self.source)
		self.assertIn('method: "nexora.boot.get_search_result_detail"', self.source)

	def test_natural_search_has_human_error_and_empty_input_paths(self) -> None:
		body = self.source.split("async function naturalSearch", 1)[1]
		self.assertIn("Falta la consulta", body)
		self.assertIn("ui.showError", body)
		self.assertIn("No se modificó ningún dato", body)

	def test_natural_navigation_uses_server_directive_and_route_options(self) -> None:
		self.assertIn('result.data?.action === "navigate"', self.source)
		self.assertIn("result.data.route_options || {}", self.source)
		self.assertIn("frappe.set_route(result.data.route, result.data.route_options || {})", self.source)

	def test_no_second_search_catalog_or_permission_logic_is_created(self) -> None:
		self.assertNotRegex(self.source, r"(query_entity|query_operations|query_contract)\s*[:=]")
		self.assertNotIn("require_action", self.source)
		self.assertNotIn("require_project_access", self.source)


if __name__ == "__main__":
	unittest.main()
