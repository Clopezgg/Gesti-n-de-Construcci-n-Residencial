from __future__ import annotations

import importlib.util
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


def _load_boot_module(pending_email_ids: list[str], user: str = "Administrator"):
	fake_frappe = types.ModuleType("frappe")
	fake_frappe.session = types.SimpleNamespace(user=user)
	fake_frappe.get_all = Mock(return_value=pending_email_ids)
	module_path = APP_ROOT / "boot.py"
	spec = importlib.util.spec_from_file_location("nexora_boot_under_test", module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load {module_path}")
	module = importlib.util.module_from_spec(spec)
	with patch.dict(sys.modules, {"frappe": fake_frappe}):
		spec.loader.exec_module(module)
	return module, fake_frappe


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
		self.assertNotIn("display: none", css)
		self.assertNotIn("visibility: hidden", css)
		self.assertIn("overflow-wrap: anywhere;", css)


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
		module, fake_frappe = _load_boot_module(["admin@nexora.com"])
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
		module, _fake_frappe = _load_boot_module(["finance@example.com"])
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


if __name__ == "__main__":
	unittest.main()
