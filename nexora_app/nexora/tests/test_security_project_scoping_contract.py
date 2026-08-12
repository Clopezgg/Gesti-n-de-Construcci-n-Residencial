"""NXR-SEC-0001: cierre de la fuga cruzada entre proyectos (Bloque 19).

El Bloque 17 documentó, sin corregir, que `purchases.request_service.list_purchase_requests`/
`order_service.list_orders` solo exigían `require_action("read_purchases")` (rol
amplio) sin `require_project_access` (rol + proyecto) — un "NEXORA Project Viewer"
restringido a un proyecto podía leer datos de otro llamando la API directamente.
El Bloque 19 auditó exhaustivamente todas las funciones `@frappe.whitelist` que
aceptan o resuelven un `project`/documento project-scoped y corrigió cada hallazgo
real encontrado (nueve funciones en cinco módulos, más un IDOR más sutil en
`reports/service.py::get_contract_statement` donde el permiso se comprobaba contra
un `project` declarado por el cliente en vez del proyecto real del documento
consultado). Estas pruebas fijan cada corrección extrayendo el cuerpo exacto de la
función (no una búsqueda de substring en todo el archivo, que daría falsos positivos
si otra función cercana ya usa `require_project_access`) y comprobando que llama
`require_project_access`, no solo `require_action`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
	"""Extrae el cuerpo de `def name(...):` hasta la siguiente `def`/`@` de nivel
	superior (misma técnica ya usada por otras pruebas de contrato de este repo,
	p. ej. `test_shell_tabbar_contract.py`)."""

	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


class TestPurchaseModuleProjectScoping(unittest.TestCase):
	def test_quotation_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "purchases/quotation_service.py").read_text(encoding="utf-8")
		for name in ("get_quotation", "list_quotations", "compare_quotations"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)

	def test_receipt_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "purchases/receipt_service.py").read_text(encoding="utf-8")
		for name in ("get_receipt", "list_receipts"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)

	def test_order_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "purchases/order_service.py").read_text(encoding="utf-8")
		for name in ("get_order", "list_orders"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)

	def test_request_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "purchases/request_service.py").read_text(encoding="utf-8")
		for name in ("get_purchase_request", "list_purchase_requests"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)


class TestInventoryProjectScoping(unittest.TestCase):
	def test_stock_transaction_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "inventory/service.py").read_text(encoding="utf-8")
		for name in ("get_stock_transaction", "list_stock_transactions"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)


class TestContractProjectScoping(unittest.TestCase):
	def test_contract_functions_check_the_real_project(self) -> None:
		source = (APP_ROOT / "contracts/service.py").read_text(encoding="utf-8")
		for name in ("get_contract", "list_contracts"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)


class TestBudgetProjectScoping(unittest.TestCase):
	def test_check_budget_availability_checks_the_real_project(self) -> None:
		source = (APP_ROOT / "budget/service.py").read_text(encoding="utf-8")
		body = function_body(source, "check_budget_availability")
		self.assertIn("require_project_access", body)


class TestFinancialModuleProjectScoping(unittest.TestCase):
	"""Hallazgos ampliados más allá del alcance original de NXR-SEC-0001: la misma
	clase de fuga existía también en `financial/sources.py` y `financial/analytics.py`
	(consultas de solo lectura) y en `financial/operations.py` (vista previa, que
	revela saldos/efectos computados de fuentes de fondos sin poder ejecutarlos)."""

	def test_list_source_balances_checks_the_real_project(self) -> None:
		source = (APP_ROOT / "financial/sources.py").read_text(encoding="utf-8")
		body = function_body(source, "list_source_balances")
		self.assertIn("require_project_access", body)

	def test_advance_status_and_central_operations_list_check_the_real_project(self) -> None:
		source = (APP_ROOT / "financial/analytics.py").read_text(encoding="utf-8")
		for name in ("get_advance_status", "list_central_operations"):
			with self.subTest(function=name):
				body = function_body(source, name)
				self.assertIn("require_project_access", body)

	def test_central_operation_preview_and_execute_share_a_single_project_check(self) -> None:
		"""`prepare_central_payload` es el único punto que preparan tanto
		`preview_central_operation` como `execute_central_operation` — el chequeo
		vive ahí una sola vez, no duplicado en cada llamador."""
		source = (APP_ROOT / "financial/analytics.py").read_text(encoding="utf-8")
		body = function_body(source, "prepare_central_payload")
		self.assertIn("require_project_access", body)

	def test_preview_financial_operation_checks_the_real_project(self) -> None:
		source = (APP_ROOT / "financial/operations.py").read_text(encoding="utf-8")
		body = function_body(source, "preview_financial_operation")
		self.assertIn("require_project_access", body)

	def test_list_evidence_checks_the_real_project(self) -> None:
		source = (APP_ROOT / "financial/evidence.py").read_text(encoding="utf-8")
		body = function_body(source, "list_evidence")
		self.assertIn("require_project_access", body)


class TestCrossUserLeakInNotifications(unittest.TestCase):
	"""Hallazgo de una clase distinta al resto (no es entre proyectos, es entre
	usuarios): `list_notifications` permitía leer las notificaciones de CUALQUIER
	usuario enviando su `user`, sin que ningún llamador real del producto lo
	necesitara (sin referencias en el cliente)."""

	def test_list_notifications_only_lets_a_broad_role_read_another_users_notifications(self) -> None:
		source = (APP_ROOT / "notifications/service.py").read_text(encoding="utf-8")
		body = function_body(source, "list_notifications")
		self.assertIn("has_action", body)
		self.assertIn("frappe.session.user", body)


class TestIntegrationsProjectScoping(unittest.TestCase):
	def test_list_integrations_checks_the_real_project(self) -> None:
		source = (APP_ROOT / "integrations/service.py").read_text(encoding="utf-8")
		body = function_body(source, "list_integrations")
		self.assertIn("require_project_access", body)


class TestContractStatementIdorFix(unittest.TestCase):
	"""Hallazgo más sutil que los anteriores: `get_contract_statement` sí llamaba
	`require_project_access`, pero contra `data["project"]` (declarado por el
	cliente), no contra el proyecto real del `contract` consultado — un Project
	Viewer podía pasar su propio proyecto autorizado y el `contract` de otro."""

	def test_permission_is_checked_against_the_contracts_own_project_not_the_client_supplied_one(
		self,
	) -> None:
		source = (APP_ROOT / "reports/service.py").read_text(encoding="utf-8")
		body = function_body(source, "get_contract_statement")
		self.assertIn(
			'frappe.db.get_value("NXR Contract", contract, "project")',
			body,
			"debe resolver el proyecto desde el documento real, no confiar en el payload",
		)
		require_line = next(line for line in body.splitlines() if "require_project_access(" in line)
		self.assertNotIn('data.get("project")', require_line)
		self.assertNotIn("_project(data)", body)


class TestDirectoryIsCorrectlyGlobalNotAFalsePositive(unittest.TestCase):
	"""Confirma que el directorio de entidades NO necesita `require_project_access`:
	`NXR Entity` no tiene campo `project` — es un catálogo maestro compartido entre
	proyectos por diseño, no un hallazgo pendiente."""

	def test_nxr_entity_doctype_has_no_project_field(self) -> None:
		import json

		payload = json.loads(
			(APP_ROOT / "nexora/doctype/nxr_entity/nxr_entity.json").read_text(encoding="utf-8")
		)
		fieldnames = {field["fieldname"] for field in payload["fields"]}
		self.assertNotIn("project", fieldnames)


if __name__ == "__main__":
	unittest.main()
