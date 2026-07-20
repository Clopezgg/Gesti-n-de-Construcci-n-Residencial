from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ENTRYPOINT = Path(__file__).resolve().parents[1] / "install_entrypoint.py"


class Flags(dict):
	def __getattr__(self, key: str):
		try:
			return self[key]
		except KeyError as exc:
			raise AttributeError(key) from exc

	def __setattr__(self, key: str, value) -> None:
		self[key] = value


@contextmanager
def fake_install_runtime(
	erpnext_install: Callable[[], None],
	construcontrol_install: Callable[[], None],
	*,
	flags: Flags | None = None,
	conf: Flags | None = None,
	is_setup_complete: Callable[[], bool] | None = None,
	setup_wizard_complete: Callable[[dict[str, object]], object] | None = None,
) -> Iterator[types.ModuleType]:
	names = (
		"frappe",
		"frappe.desk",
		"frappe.desk.page",
		"frappe.desk.page.setup_wizard",
		"frappe.desk.page.setup_wizard.setup_wizard",
		"erpnext",
		"erpnext.setup",
		"erpnext.setup.install",
		"erpnext.construcontrol",
		"erpnext.construcontrol.install",
	)
	previous = {name: sys.modules.get(name) for name in names}

	frappe = types.ModuleType("frappe")
	setattr(frappe, "flags", flags if flags is not None else Flags())
	setattr(frappe, "conf", conf if conf is not None else Flags())
	setattr(frappe, "is_setup_complete", is_setup_complete or (lambda: True))
	setattr(frappe, "clear_cache", lambda: None)

	frappe_desk = types.ModuleType("frappe.desk")
	frappe_desk.__path__ = []
	frappe_page = types.ModuleType("frappe.desk.page")
	frappe_page.__path__ = []
	frappe_setup_wizard = types.ModuleType("frappe.desk.page.setup_wizard")
	frappe_setup_wizard.__path__ = []
	frappe_setup_wizard_module = types.ModuleType("frappe.desk.page.setup_wizard.setup_wizard")
	frappe_setup_wizard_module.setup_complete = setup_wizard_complete or (
		lambda _args: {"status": "ok"}
	)

	erpnext = types.ModuleType("erpnext")
	erpnext.__path__ = []
	setup = types.ModuleType("erpnext.setup")
	setup.__path__ = []
	setup_install = types.ModuleType("erpnext.setup.install")
	setup_install.after_install = erpnext_install
	construcontrol = types.ModuleType("erpnext.construcontrol")
	construcontrol.__path__ = []
	construcontrol_install_module = types.ModuleType("erpnext.construcontrol.install")
	construcontrol_install_module.after_migrate = construcontrol_install

	replacements = {
		"frappe": frappe,
		"frappe.desk": frappe_desk,
		"frappe.desk.page": frappe_page,
		"frappe.desk.page.setup_wizard": frappe_setup_wizard,
		"frappe.desk.page.setup_wizard.setup_wizard": frappe_setup_wizard_module,
		"erpnext": erpnext,
		"erpnext.setup": setup,
		"erpnext.setup.install": setup_install,
		"erpnext.construcontrol": construcontrol,
		"erpnext.construcontrol.install": construcontrol_install_module,
	}
	sys.modules.update(replacements)
	try:
		spec = importlib.util.spec_from_file_location("cc_install_entrypoint_test", ENTRYPOINT)
		if spec is None or spec.loader is None:
			raise RuntimeError(f"Unable to load {ENTRYPOINT}")
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		yield module
	finally:
		for name, value in previous.items():
			if value is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = value


class InstallEntrypointContractTest(unittest.TestCase):
	def test_runs_erpnext_then_construcontrol_inside_migration_context(self) -> None:
		events: list[str] = []
		flags = Flags()

		def erpnext_install() -> None:
			events.append("erpnext")

		def construcontrol_install() -> None:
			self.assertIs(flags.in_migrate, True)
			events.append("construcontrol")

		with fake_install_runtime(
			erpnext_install,
			construcontrol_install,
			flags=flags,
		) as module:
			module.after_install()

		self.assertEqual(events, ["erpnext", "construcontrol"])
		self.assertNotIn("in_migrate", flags)

	def test_restores_existing_flag_when_construcontrol_install_fails(self) -> None:
		flags = Flags(in_migrate=False)

		def fail_install() -> None:
			self.assertIs(flags.in_migrate, True)
			raise RuntimeError("expected failure")

		with fake_install_runtime(lambda: None, fail_install, flags=flags) as module:
			with self.assertRaisesRegex(RuntimeError, "expected failure"):
				module.after_install()

		self.assertIn("in_migrate", flags)
		self.assertIs(flags.in_migrate, False)

	def test_completes_official_setup_synchronously_after_runtime_install(self) -> None:
		events: list[str] = []
		state = {"complete": False}
		conf = Flags(trigger_site_setup_in_background=True)

		def complete_setup(args: dict[str, object]) -> dict[str, str]:
			self.assertIs(conf.trigger_site_setup_in_background, False)
			self.assertEqual(args["company_name"], "Casa Controlada")
			self.assertEqual(args["company_abbr"], "HOG")
			self.assertEqual(args["country"], "Honduras")
			self.assertEqual(args["currency"], "HNL")
			self.assertEqual(args["timezone"], "America/Tegucigalpa")
			self.assertEqual(args["setup_demo"], 0)
			events.append("setup")
			state["complete"] = True
			return {"status": "ok"}

		with patch.dict(
			os.environ,
			{
				"CONSTRUCONTROL_COMPANY_NAME": "Casa Controlada",
				"CONSTRUCONTROL_COMPANY_ABBR": "hog",
				"CONSTRUCONTROL_COUNTRY": "Honduras",
				"CONSTRUCONTROL_CURRENCY": "hnl",
				"TZ": "America/Tegucigalpa",
			},
			clear=False,
		):
			with fake_install_runtime(
				lambda: events.append("erpnext"),
				lambda: events.append("construcontrol"),
				conf=conf,
				is_setup_complete=lambda: state["complete"],
				setup_wizard_complete=complete_setup,
			) as module:
				module.after_install()

		self.assertEqual(events, ["erpnext", "construcontrol", "setup"])
		self.assertIs(conf.trigger_site_setup_in_background, True)

	def test_setup_completion_fails_closed_when_wizard_does_not_finish(self) -> None:
		with fake_install_runtime(
			lambda: None,
			lambda: None,
			is_setup_complete=lambda: False,
			setup_wizard_complete=lambda _args: {"status": "ok"},
		) as module:
			with self.assertRaisesRegex(RuntimeError, "without completing the site"):
				module.ensure_setup_complete()

	def test_setup_arguments_reject_empty_required_values(self) -> None:
		with patch.dict(os.environ, {"CONSTRUCONTROL_COUNTRY": "   "}, clear=False):
			with fake_install_runtime(lambda: None, lambda: None) as module:
				with self.assertRaisesRegex(RuntimeError, "non-empty country"):
					module._setup_arguments()


if __name__ == "__main__":
	unittest.main()
