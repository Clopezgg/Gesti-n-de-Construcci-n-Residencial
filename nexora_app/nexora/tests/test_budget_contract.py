from __future__ import annotations

import json
import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


def _function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


class TestBudgetContract(unittest.TestCase):
	def test_budget_module_exists(self) -> None:
		init = APP_ROOT / "budget/__init__.py"
		self.assertTrue(init.is_file())

	def test_budget_core_exists(self) -> None:
		core = APP_ROOT / "budget/core.py"
		self.assertTrue(core.is_file())

	def test_budget_service_exists(self) -> None:
		service = APP_ROOT / "budget/service.py"
		self.assertTrue(service.is_file())

	def test_budget_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget/nxr_budget.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Budget", payload["name"])

	def test_budget_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget/nxr_budget.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_budget_line_is_table(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget_line/nxr_budget_line.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Budget Line", payload["name"])
		self.assertEqual(1, payload["istable"])

	def test_budget_line_has_balance_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_budget_line/nxr_budget_line.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		field_names = {f["fieldname"] for f in payload["fields"]}
		for field in ("economic_category", "approved_hnl", "committed_hnl", "executed_hnl", "available_hnl"):
			self.assertIn(field, field_names)


class TestBudgetReadEndpoints(unittest.TestCase):
	"""Hallazgo real de auditoría (sesión 2026-08-16, Bloque 53): `budget/service.py`
	tenía create/activate/amend/close/cancel/check_budget_availability pero ningún
	`list`/`get` — a diferencia de compras/inventario/cierre, no había forma de
	consultar qué presupuestos existen o el estado de uno ya creado, así que
	tampoco podía construirse una página que solo envolviera lo ya existente
	(el mismo patrón que órdenes/inventario/cierre mensual). `get_budget`/
	`list_budgets` se agregaron en este bloque, mismo patrón de solo lectura que
	`purchases.order_service.get_order`/`list_orders`."""

	def test_get_and_list_budgets_are_whitelisted_get_endpoints(self) -> None:
		source = (APP_ROOT / "budget/service.py").read_text(encoding="utf-8")
		for name in ("get_budget", "list_budgets"):
			with self.subTest(function=name):
				self.assertIn(f'@frappe.whitelist(methods=["GET"])\ndef {name}(', source)

	def test_get_and_list_budgets_check_project_access(self) -> None:
		source = (APP_ROOT / "budget/service.py").read_text(encoding="utf-8")
		for name in ("get_budget", "list_budgets"):
			with self.subTest(function=name):
				body = _function_body(source, name)
				self.assertIn("require_project_access(", body)

	def test_neither_read_endpoint_mutates_state(self) -> None:
		source = (APP_ROOT / "budget/service.py").read_text(encoding="utf-8")
		for name in ("get_budget", "list_budgets"):
			with self.subTest(function=name):
				body = _function_body(source, name)
				self.assertNotIn("service_write", body)
				self.assertNotIn(".insert(", body)
				self.assertNotIn(".save(", body)
