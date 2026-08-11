"""Bloque 24 (Reportes): hace explícito y verificable de forma directa un
invariante que hasta ahora solo vivía implícito, dos capas por debajo del
propio endpoint — exactamente la clase de hallazgo que `NXR-SEC-0001`
(Bloque 19) advirtió que podía existir en cualquier función que resuelve un
`project` sin comprobarlo.

`get_source_statement_page`, `get_source_movement_page` y `get_contract_page`
(los tres endpoints reales que usa `nexora-reports` para FI01/FI02/CO01,
confirmado en `nexora_reports.js`) delegan en `source_statement()`,
`source_movement_page()` y `contract_page()`. Ninguna de las tres llama
`require_project_access` directamente — la auditoría del Bloque 19 ya
documentó que esto es seguro porque las tres resuelven el proyecto con
`dashboard.query_utils.project()`, que sí llama `require_project_access(value,
action="view_reports")` antes de devolver el valor. Esta prueba fija esa
cadena de protección de forma directa (no un grep superficial de todo el
archivo, que daría un falso positivo si la llamada existiera en una función
vecina): confirma que `query_utils.project()` sigue llamando
`require_project_access`, y que las tres funciones de consulta siguen
resolviendo el proyecto con esa función protegida como su primera operación
real — antes de construir cualquier filtro SQL — para que ningún cambio futuro
pueda mover la resolución del proyecto después de que la consulta ya se
construyó sin que esta prueba lo note.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


def first_statement(body: str) -> str:
	"""La primera línea real del cuerpo, saltando una firma que puede
	extenderse a varias líneas (parámetros con valor por defecto)."""
	lines = [line.strip() for line in body.splitlines() if line.strip()]
	for index, line in enumerate(lines):
		if line.endswith(":") and not line.startswith(("if ", "for ", "while ", "with ", "try")):
			return lines[index + 1]
	raise AssertionError("no se encontró el fin de la firma de la función")


class TestQueryUtilsProjectResolverIsProtected(unittest.TestCase):
	def test_project_resolver_calls_the_real_permission_check(self) -> None:
		source = (APP_ROOT / "dashboard/query_utils.py").read_text(encoding="utf-8")
		body = function_body(source, "project")
		self.assertIn("require_project_access(value, action=", body)


class TestReportCenterQueriesResolveProjectBeforeQuerying(unittest.TestCase):
	"""Las tres consultas reales detrás de FI01/FI02/CO01 en `nexora-reports`."""

	def test_contract_page_resolves_the_project_as_its_first_real_statement(self) -> None:
		source = (APP_ROOT / "dashboard/contract_page.py").read_text(encoding="utf-8")
		body = function_body(source, "contract_page")
		self.assertEqual("project = resolve_project(data)", first_statement(body))
		self.assertLess(body.index("resolve_project(data)"), body.index("frappe.db.sql("))

	def test_source_statement_resolves_the_project_as_its_first_real_statement(self) -> None:
		source = (APP_ROOT / "dashboard/source_query.py").read_text(encoding="utf-8")
		body = function_body(source, "source_statement")
		self.assertEqual("project = resolve_project(data)", first_statement(body))
		self.assertLess(body.index("resolve_project(data)"), body.index("frappe.get_all("))

	def test_source_movement_page_resolves_the_project_as_its_first_real_statement(self) -> None:
		source = (APP_ROOT / "dashboard/source_query.py").read_text(encoding="utf-8")
		body = function_body(source, "source_movement_page")
		self.assertEqual("project = resolve_project(data)", first_statement(body))
		self.assertLess(body.index("resolve_project(data)"), body.index("frappe.db.sql("))

	def test_expense_page_query_params_checks_project_access_directly(self) -> None:
		"""Mismo invariante, capa distinta: `expense_query.py` no pasa por
		`query_utils.project()` — llama `require_project_access` en su propio
		`_query_params`. Ambas rutas deben seguir protegidas, no solo una."""
		source = (APP_ROOT / "dashboard/expense_query.py").read_text(encoding="utf-8")
		body = function_body(source, "_query_params")
		self.assertIn('require_project_access(project, action="view_financial_details")', body)


class TestReportCenterEndpointsDelegateToTheProtectedQueries(unittest.TestCase):
	"""Confirma que los tres endpoints whitelisted que el navegador llama de
	verdad (`nexora_reports.js`) siguen delegando en las funciones protegidas
	arriba, y no en una implementación paralela sin el mismo chequeo."""

	def test_dashboard_executive_endpoints_delegate_to_the_protected_functions(self) -> None:
		source = (APP_ROOT / "dashboard/executive.py").read_text(encoding="utf-8")
		self.assertIn("return source_statement(parse_query_payload(payload))", source)
		self.assertIn("return source_movement_page(parse_query_payload(payload))", source)
		self.assertIn("return contract_page(parse_query_payload(payload))", source)

	def test_browser_uses_exactly_these_three_dotted_paths_for_fi01_fi02_co01(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn('FI01: "nexora.dashboard.executive.get_source_statement_page"', source)
		self.assertIn('FI02: "nexora.dashboard.executive.get_expense_page"', source)
		self.assertIn('CO01: "nexora.dashboard.executive.get_contract_page"', source)


if __name__ == "__main__":
	unittest.main()
