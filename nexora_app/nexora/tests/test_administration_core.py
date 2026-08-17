"""Pruebas de unidad reales de `nexora.administration.core` — sin Frappe, sin
red, sin base de datos. Ejecuta lógica real con entradas reales."""

from __future__ import annotations

import unittest

from nexora.administration.core import (
	ADMINISTRATOR_ROLE,
	ALLOWED_NEXORA_ROLES,
	AdministrationError,
	assert_manageable_role,
	assert_not_last_administrator,
	normalize_role_selection,
)


class TestAllowedRoles(unittest.TestCase):
	def test_the_five_nexora_roles_are_exactly_the_allowed_set(self) -> None:
		self.assertEqual(
			{
				"NEXORA Administrator",
				"NEXORA Finance Manager",
				"NEXORA Finance Operator",
				"NEXORA Auditor",
				"NEXORA Project Viewer",
			},
			set(ALLOWED_NEXORA_ROLES),
		)

	def test_administrator_role_constant_matches_the_allowed_set(self) -> None:
		self.assertIn(ADMINISTRATOR_ROLE, ALLOWED_NEXORA_ROLES)
		self.assertEqual("NEXORA Administrator", ADMINISTRATOR_ROLE)


class TestAssertManageableRole(unittest.TestCase):
	def test_every_nexora_role_is_manageable(self) -> None:
		for role in ALLOWED_NEXORA_ROLES:
			with self.subTest(role=role):
				assert_manageable_role(role)  # no debe lanzar

	def test_system_manager_is_never_manageable_from_this_screen(self) -> None:
		with self.assertRaises(AdministrationError):
			assert_manageable_role("System Manager")

	def test_an_arbitrary_frappe_technical_role_is_never_manageable(self) -> None:
		with self.assertRaises(AdministrationError):
			assert_manageable_role("Purchase Manager")

	def test_an_empty_role_is_never_manageable(self) -> None:
		with self.assertRaises(AdministrationError):
			assert_manageable_role("")


class TestAssertNotLastAdministrator(unittest.TestCase):
	def test_disabling_the_only_administrator_is_rejected(self) -> None:
		with self.assertRaises(AdministrationError):
			assert_not_last_administrator(
				active_administrators=["alice@example.com"],
				target_user="alice@example.com",
				target_will_remain_administrator=False,
			)

	def test_disabling_one_of_two_administrators_is_allowed(self) -> None:
		assert_not_last_administrator(
			active_administrators=["alice@example.com", "bob@example.com"],
			target_user="alice@example.com",
			target_will_remain_administrator=False,
		)  # no debe lanzar

	def test_a_user_that_keeps_the_administrator_role_never_triggers_the_check(self) -> None:
		assert_not_last_administrator(
			active_administrators=["alice@example.com"],
			target_user="alice@example.com",
			target_will_remain_administrator=True,
		)  # no debe lanzar

	def test_an_empty_administrator_list_is_rejected_for_any_target(self) -> None:
		with self.assertRaises(AdministrationError):
			assert_not_last_administrator(
				active_administrators=[],
				target_user="new_user@example.com",
				target_will_remain_administrator=False,
			)


class TestNormalizeRoleSelection(unittest.TestCase):
	def test_deduplicates_and_strips_whitespace(self) -> None:
		result = normalize_role_selection([" NEXORA Auditor ", "NEXORA Auditor", "NEXORA Finance Manager"])
		self.assertEqual({"NEXORA Auditor", "NEXORA Finance Manager"}, result)

	def test_drops_blank_entries(self) -> None:
		result = normalize_role_selection(["NEXORA Auditor", "", "   "])
		self.assertEqual({"NEXORA Auditor"}, result)

	def test_rejects_a_non_nexora_role_anywhere_in_the_list(self) -> None:
		with self.assertRaises(AdministrationError):
			normalize_role_selection(["NEXORA Auditor", "System Manager"])

	def test_rejects_a_non_list_payload(self) -> None:
		for bad_value in (None, "NEXORA Auditor", {"role": "NEXORA Auditor"}):
			with self.subTest(bad_value=bad_value), self.assertRaises(AdministrationError):
				normalize_role_selection(bad_value)

	def test_an_empty_list_is_a_valid_selection_meaning_no_nexora_roles(self) -> None:
		self.assertEqual(set(), normalize_role_selection([]))


if __name__ == "__main__":
	unittest.main()
