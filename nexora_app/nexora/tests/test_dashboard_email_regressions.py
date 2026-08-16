from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

import nexora
from nexora.email_prompt_policy import (
	pending_emails_are_generic,
	remove_prompt_user,
	split_prompt_users,
)

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class FakePermissionError(Exception):
	pass


class FakeValidationError(Exception):
	pass


class FakeDefaults:
	def __init__(self, values: dict[str, str] | None = None):
		self.values = dict(values or {})

	def get_user_default(self, key: str):
		return self.values.get(key)

	def set_user_default(self, key: str, value: str) -> None:
		self.values[key] = value


def _load_boot_module(
	pending_email_ids: list[str],
	user: str = "Administrator",
	*,
	defaults: dict[str, str] | None = None,
	roles: list[str] | None = None,
):
	fake_frappe = types.ModuleType("frappe")
	fake_frappe._ = lambda value: value
	fake_frappe.PermissionError = FakePermissionError
	fake_frappe.ValidationError = FakeValidationError
	fake_frappe.session = types.SimpleNamespace(user=user)
	fake_frappe.get_all = Mock(return_value=pending_email_ids)
	fake_frappe.get_roles = Mock(return_value=roles or ["NEXORA Project Viewer"])
	fake_frappe.defaults = FakeDefaults(defaults)
	fake_frappe.utils = types.SimpleNamespace(today=lambda: "2026-07-28")
	fake_frappe.parse_json = json.loads
	fake_frappe.whitelist = lambda **_kwargs: lambda function: function
	fake_frappe.throw = lambda message, exception=FakeValidationError: (_ for _ in ()).throw(
		exception(message)
	)
	fake_frappe.db = types.SimpleNamespace(
		get_value=lambda doctype, name, fieldname: (
			"Proyecto Uno" if doctype == "Project" else "Usuario de Prueba"
		)
	)

	fake_permissions = types.ModuleType("nexora.permissions")
	fake_permissions.has_action = Mock(
		side_effect=lambda action, _user=None: action == "view_financial_details"
	)
	fake_permissions.require_action = Mock()
	fake_permissions.require_project_access = Mock()
	fake_permissions.canonical_project_name = lambda project: project or None

	module_path = APP_ROOT / "boot.py"
	spec = importlib.util.spec_from_file_location("nexora_boot_under_test", module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load {module_path}")
	module = importlib.util.module_from_spec(spec)
	with patch.dict(
		sys.modules,
		{"frappe": fake_frappe, "nexora.permissions": fake_permissions},
	):
		spec.loader.exec_module(module)
	return module, fake_frappe, fake_permissions


class TestDashboardFundsLayoutContract(unittest.TestCase):
	def test_funds_list_overrides_legacy_balance_grid(self) -> None:
		css = (APP_ROOT / "public/css/nexora_dashboard_fixes.css").read_text(encoding="utf-8")
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn("nexora_dashboard_fixes.css", hooks)
		self.assertIn(".nxr-funds-list.nxr-balance-row", css)
		self.assertIn("grid-template-columns: minmax(0, 1fr);", css)
		self.assertIn("grid-template-columns: minmax(0, 1fr) max-content;", css)
		self.assertIn("white-space: nowrap;", css)

	def test_funds_fix_does_not_hide_or_truncate_the_card(self) -> None:
		css = (APP_ROOT / "public/css/nexora_dashboard_fixes.css").read_text(encoding="utf-8")
		funds_rules = css.split(".nxr-global-context", 1)[0]
		self.assertNotIn("display: none", funds_rules)
		self.assertNotIn("visibility: hidden", funds_rules)
		self.assertIn("overflow-wrap: anywhere;", funds_rules)

	def test_global_context_and_decision_dashboard_are_connected(self) -> None:
		context_ui = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		dashboard = (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(
			encoding="utf-8"
		)
		css = (APP_ROOT / "public/css/nexora_dashboard_fixes.css").read_text(encoding="utf-8")
		for needle in (
			"nexora.boot.get_active_context",
			"nexora.boot.set_active_context",
			"nexora:context-changed",
			"Hay información sin guardar",
			"registerDirtySource",
		):
			self.assertIn(needle, context_ui)
		for needle in (
			"Saldo disponible",
			"Comprometido",
			"Pendiente de pagar",
			"from_date: activeContext?.from_date",
			"to_date: activeContext?.to_date",
		):
			self.assertIn(needle, dashboard)
		self.assertIn(".nxr-global-context", css)
		self.assertIn('type="month"', context_ui)


class TestGenericEmailPromptPolicy(unittest.TestCase):
	def test_generic_pending_email_removes_only_current_user(self) -> None:
		self.assertEqual(
			["Administrator", "finance@example.com"],
			split_prompt_users("Administrator, finance@example.com"),
		)
		self.assertTrue(pending_emails_are_generic(["ADMIN@NEXORA.COM"]))
		self.assertEqual(
			"finance@example.com",
			remove_prompt_user("Administrator,finance@example.com", "Administrator"),
		)

	def test_real_or_mixed_pending_email_is_never_suppressed(self) -> None:
		self.assertFalse(pending_emails_are_generic([]))
		self.assertFalse(pending_emails_are_generic(["finance@example.com"]))
		self.assertFalse(pending_emails_are_generic(["admin@nexora.com", "finance@example.com"]))

	def test_boot_hook_suppresses_only_known_generic_account(self) -> None:
		module, fake_frappe, _permissions = _load_boot_module(["admin@nexora.com"])
		bootinfo = {
			"sysdefaults": {
				"email_user_password": "Administrator,finance@example.com",
			}
		}
		module.suppress_generic_email_password_prompt(bootinfo)
		self.assertEqual(
			"finance@example.com",
			bootinfo["sysdefaults"]["email_user_password"],
		)
		fake_frappe.get_all.assert_called_once_with(
			"User Email",
			filters={
				"parent": "Administrator",
				"parenttype": "User",
				"parentfield": "user_emails",
				"awaiting_password": 1,
			},
			pluck="email_id",
		)

	def test_boot_hook_preserves_real_email_password_validation(self) -> None:
		module, _fake_frappe, _permissions = _load_boot_module(["finance@example.com"])
		bootinfo = {"sysdefaults": {"email_user_password": "Administrator"}}
		module.suppress_generic_email_password_prompt(bootinfo)
		self.assertEqual("Administrator", bootinfo["sysdefaults"]["email_user_password"])

	def test_boot_hook_changes_no_email_or_user_records(self) -> None:
		boot_code = (APP_ROOT / "boot.py").read_text(encoding="utf-8")
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertIn(
			'boot_session = ["nexora.boot.suppress_generic_email_password_prompt"]',
			hooks,
		)
		self.assertIn('"User Email"', boot_code)
		self.assertIn('"awaiting_password": 1', boot_code)
		for forbidden in ("set_value(", "delete_doc(", "db.delete(", "db.set_value("):
			self.assertNotIn(forbidden, boot_code)


class TestNexoraActiveContext(unittest.TestCase):
	def test_saved_project_period_user_and_role_are_returned(self) -> None:
		module, _frappe, permissions = _load_boot_module(
			[],
			user="viewer@example.com",
			defaults={
				"nexora_active_project": "PROJ-001",
				"nexora_active_period": "2026-07",
			},
			roles=["NEXORA Project Viewer"],
		)
		context = module.get_active_context()
		self.assertEqual("PROJ-001", context["project"])
		self.assertEqual("Proyecto Uno", context["project_label"])
		self.assertEqual("2026-07-01", context["from_date"])
		self.assertEqual("2026-07-31", context["to_date"])
		self.assertEqual("Consulta de proyecto", context["role_label"])
		self.assertTrue(context["can_view_financial_details"])
		permissions.require_action.assert_called_with("preview")
		permissions.require_project_access.assert_called_with(
			"PROJ-001", action="view_reports", user="viewer@example.com"
		)

	def test_context_change_persists_only_after_project_permission(self) -> None:
		module, fake_frappe, permissions = _load_boot_module(
			[],
			defaults={"nexora_active_period": "2026-07"},
		)
		result = module.set_active_context({"project": "PROJ-002", "period": "2026-08"})
		permissions.require_project_access.assert_any_call("PROJ-002", action="view_reports")
		self.assertEqual("PROJ-002", fake_frappe.defaults.values["nexora_active_project"])
		self.assertEqual("2026-08", fake_frappe.defaults.values["nexora_active_period"])
		self.assertEqual("2026-08-31", result["to_date"])

	def test_invalid_period_is_rejected_without_persisting(self) -> None:
		module, fake_frappe, _permissions = _load_boot_module([], defaults={})
		with self.assertRaisesRegex(FakeValidationError, "AAAA-MM"):
			module.set_active_context({"project": "PROJ-001", "period": "07/2026"})
		self.assertEqual({}, fake_frappe.defaults.values)

	def test_restricted_user_cannot_clear_required_project(self) -> None:
		module, fake_frappe, permissions = _load_boot_module([], defaults={})
		permissions.has_action.side_effect = lambda action, _user=None: action == "view_financial_details"
		with self.assertRaisesRegex(FakePermissionError, "Seleccione un proyecto"):
			module.set_active_context({"project": "", "period": "2026-07"})
		self.assertEqual({}, fake_frappe.defaults.values)


if __name__ == "__main__":
	unittest.main()
