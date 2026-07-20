from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

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
) -> Iterator[types.ModuleType]:
	names = (
		"frappe",
		"erpnext",
		"erpnext.setup",
		"erpnext.setup.install",
		"erpnext.construcontrol",
		"erpnext.construcontrol.install",
	)
	previous = {name: sys.modules.get(name) for name in names}

	frappe = types.ModuleType("frappe")
	setattr(frappe, "flags", flags if flags is not None else Flags())

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


if __name__ == "__main__":
	unittest.main()
