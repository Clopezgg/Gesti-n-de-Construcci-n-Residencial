from __future__ import annotations

from unittest import TestCase

ACCESS_ROLES = frozenset(
	{
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
		"NEXORA Auditor",
		"NEXORA Project Viewer",
	}
)

OPERATOR_ROLES = frozenset(
	{
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
		"NEXORA Finance Operator",
	}
)

MANAGER_ROLES = frozenset(
	{
		"System Manager",
		"NEXORA Administrator",
		"NEXORA Finance Manager",
	}
)

ACTION_ROLES: dict[str, frozenset[str]] = {
	"preview": ACCESS_ROLES,
	"read_balances": ACCESS_ROLES,
	"read_entities": ACCESS_ROLES,
	"read_sensitive_entity": frozenset(
		{
			"System Manager",
			"NEXORA Administrator",
			"NEXORA Finance Manager",
			"NEXORA Auditor",
		}
	),
	"read_contracts": ACCESS_ROLES,
	"read_purchases": ACCESS_ROLES,
	"create_source": OPERATOR_ROLES,
	"execute": OPERATOR_ROLES,
	"upload_evidence": OPERATOR_ROLES,
	"create_entity": OPERATOR_ROLES,
	"create_contract": OPERATOR_ROLES,
	"create_supplier": OPERATOR_ROLES,
	"create_purchase_request": OPERATOR_ROLES,
	"submit_purchase_request": OPERATOR_ROLES,
	"update_entity": OPERATOR_ROLES,
	"approve": MANAGER_ROLES,
	"review_evidence": MANAGER_ROLES,
	"return": MANAGER_ROLES,
	"reclassify": MANAGER_ROLES,
	"manage_entity": MANAGER_ROLES,
	"manage_entity_role": MANAGER_ROLES,
	"manage_entity_compliance": MANAGER_ROLES,
	"consolidate_entity": MANAGER_ROLES,
	"manage_contract": MANAGER_ROLES,
	"execute_contract": MANAGER_ROLES,
	"manage_supplier": MANAGER_ROLES,
	"approve_purchase_request": MANAGER_ROLES,
	"manage_budget": MANAGER_ROLES,
}


class TestSecurityCore(TestCase):
	def test_action_roles_has_preview(self) -> None:
		self.assertIn("preview", ACTION_ROLES)

	def test_action_roles_has_approve(self) -> None:
		self.assertIn("approve", ACTION_ROLES)

	def test_action_roles_has_all_expected_actions(self) -> None:
		expected = {
			"preview",
			"read_balances",
			"read_entities",
			"read_sensitive_entity",
			"read_contracts",
			"read_purchases",
			"create_source",
			"execute",
			"upload_evidence",
			"create_entity",
			"create_contract",
			"create_supplier",
			"create_purchase_request",
			"submit_purchase_request",
			"update_entity",
			"approve",
			"review_evidence",
			"return",
			"reclassify",
			"manage_entity",
			"manage_entity_role",
			"manage_entity_compliance",
			"consolidate_entity",
			"manage_contract",
			"execute_contract",
			"manage_supplier",
			"approve_purchase_request",
			"manage_budget",
		}
		self.assertEqual(expected, set(ACTION_ROLES.keys()))

	def test_preview_allows_all_roles(self) -> None:
		self.assertEqual(ACCESS_ROLES, ACTION_ROLES["preview"])

	def test_approve_requires_manager(self) -> None:
		self.assertEqual(MANAGER_ROLES, ACTION_ROLES["approve"])

	def test_execute_requires_operator(self) -> None:
		self.assertEqual(OPERATOR_ROLES, ACTION_ROLES["execute"])

	def test_preview_includes_project_viewer(self) -> None:
		self.assertIn("NEXORA Project Viewer", ACTION_ROLES["preview"])

	def test_approve_excludes_operator(self) -> None:
		self.assertNotIn("NEXORA Finance Operator", ACTION_ROLES["approve"])

	def test_approve_excludes_auditor(self) -> None:
		self.assertNotIn("NEXORA Auditor", ACTION_ROLES["approve"])

	def test_approve_excludes_project_viewer(self) -> None:
		self.assertNotIn("NEXORA Project Viewer", ACTION_ROLES["approve"])

	def test_read_sensitive_entity_has_auditor(self) -> None:
		self.assertIn("NEXORA Auditor", ACTION_ROLES["read_sensitive_entity"])

	def test_manager_roles_are_correct(self) -> None:
		self.assertEqual({"System Manager", "NEXORA Administrator", "NEXORA Finance Manager"}, MANAGER_ROLES)

	def test_operator_roles_are_correct(self) -> None:
		self.assertEqual(
			{"System Manager", "NEXORA Administrator", "NEXORA Finance Manager", "NEXORA Finance Operator"},
			OPERATOR_ROLES,
		)

	def test_access_roles_are_comprehensive(self) -> None:
		self.assertEqual(
			{
				"System Manager",
				"NEXORA Administrator",
				"NEXORA Finance Manager",
				"NEXORA Finance Operator",
				"NEXORA Auditor",
				"NEXORA Project Viewer",
			},
			ACCESS_ROLES,
		)

	def test_create_source_is_operator(self) -> None:
		self.assertEqual(OPERATOR_ROLES, ACTION_ROLES["create_source"])

	def test_manage_entity_compliance_is_manager(self) -> None:
		self.assertEqual(MANAGER_ROLES, ACTION_ROLES["manage_entity_compliance"])
