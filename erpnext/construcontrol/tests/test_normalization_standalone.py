from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "normalization.py"
SPEC = importlib.util.spec_from_file_location("construcontrol_normalization_test", MODULE_PATH)
assert SPEC and SPEC.loader
normalization = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = normalization
SPEC.loader.exec_module(normalization)


class ConstruControlNormalizationTest(unittest.TestCase):
	def test_roles_are_presented_as_business_labels(self):
		self.assertEqual(normalization.normalize_role("administrator"), "admin")
		self.assertEqual(normalization.normalize_role("ConstruControl Manager"), "MANAGER")
		self.assertEqual(normalization.normalize_role("operador"), "OPERATOR")
		self.assertEqual(normalization.normalize_role("auditor"), "AUDITOR")
		self.assertEqual(normalization.normalize_role("viewer"), "VIEWER")

	def test_inventory_movement_aliases_have_correct_direction(self):
		for value in ("entry", "purchase", "receipt", "adjustment-in"):
			self.assertEqual(normalization.normalize_movement_type(value), "adjustment_in")
		for value in ("consumption", "use", "issue"):
			self.assertEqual(normalization.normalize_movement_type(value), "consumption")
		self.assertEqual(normalization.normalize_movement_type("adjustment-out"), "adjustment_out")

	def test_duplicate_email_uses_highest_authority_role(self):
		snapshots = [
			{
				"userAccounts": [
					{"id": "local", "email": "ADMIN@EJEMPLO.COM", "role": "auditor", "name": "Carlos"},
					{"id": "cloud", "email": "admin@ejemplo.com", "role": "admin", "name": "Carlos"},
				]
			}
		]
		directory = normalization.build_actor_directory(snapshots)
		self.assertEqual(directory["admin@ejemplo.com"]["role"], "admin")
		self.assertEqual(directory["local"]["role"], "AUDITOR")
		self.assertEqual(directory["cloud"]["role"], "admin")

	def test_audit_actor_separates_email_role_name_and_id(self):
		directory = normalization.build_actor_directory(
			[
				{
					"userAccounts": [
						{"id": "u-1", "email": "admin@ejemplo.com", "role": "admin", "name": "Carlos López"}
					]
				}
			]
		)
		identity = normalization.resolve_actor_identity({"actor": "admin@ejemplo.com"}, directory)
		self.assertEqual(identity["email"], "admin@ejemplo.com")
		self.assertEqual(identity["display_name"], "Carlos López")
		self.assertEqual(identity["role"], "admin")
		self.assertEqual(identity["user_id"], "u-1")


if __name__ == "__main__":
	unittest.main()
