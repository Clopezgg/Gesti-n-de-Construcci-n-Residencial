from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestContext360ModuleContract(unittest.TestCase):
	"""Estructura mínima esperada del módulo `context360` (NXR-UX-0010/NXR-UX-0011):
	no duplica lógica de negocio, reutiliza `get_executive_snapshot` y cierra el
	acceso por proyecto antes de tocar cualquier doctype."""

	def test_module_files_exist(self) -> None:
		for relative in (
			"context360/__init__.py",
			"context360/core.py",
			"context360/service.py",
			"context360/timeline.py",
		):
			self.assertTrue((APP_ROOT / relative).is_file(), relative)

	def test_overview_reuses_the_real_executive_snapshot_not_the_legacy_one(self) -> None:
		code = (APP_ROOT / "context360/service.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.dashboard.executive import get_executive_snapshot", code)
		self.assertIn('get_executive_snapshot({"project": project})', code)
		# No debe recalcular fondos/presupuesto/contratos por su cuenta.
		self.assertNotIn("frappe.db.sql", code)

	def test_overview_and_timeline_gate_on_project_access_before_any_query(self) -> None:
		for relative in ("context360/service.py", "context360/timeline.py"):
			code = (APP_ROOT / relative).read_text(encoding="utf-8")
			self.assertIn("from nexora.permissions import require_project_access", code)
			self.assertIn('require_project_access(project, action="view_reports")', code)

	def test_timeline_uses_permission_aware_get_list_not_get_all(self) -> None:
		"""`frappe.get_all` ignora permisos de fila por diseño; la timeline cruza
		varios doctypes y debe respetar los permisos reales de cada uno."""
		code = (APP_ROOT / "context360/timeline.py").read_text(encoding="utf-8")
		self.assertIn("frappe.get_list(", code)
		self.assertNotIn("frappe.get_all(", code)

	def test_timeline_covers_the_seven_requested_categories(self) -> None:
		code = (APP_ROOT / "context360/core.py").read_text(encoding="utf-8")
		for category in ("financiero", "compras", "contratos", "inventario", "avance", "evidencia"):
			self.assertIn(f'"{category}"', code)

	def test_normalize_event_never_fabricates_a_missing_date(self) -> None:
		code = (APP_ROOT / "context360/core.py").read_text(encoding="utf-8")
		body = code.split("def normalize_event(", 1)[1]
		self.assertIn("if not date_value:\n\t\treturn None", body)


class TestDashboardSummaryProjectAccessFix(unittest.TestCase):
	"""Hallazgo de seguridad encontrado al inspeccionar qué reutilizar para
	NXR-UX-0010: `get_dashboard_summary` (legado, ya no lo usa `nexora_dashboard.js`
	— ver `get_executive_snapshot`) nunca llamaba a `require_project_access`, así
	que cualquier usuario con acción "preview" podía pedir el resumen ejecutivo de
	un proyecto ajeno. `require_project_access` ya existe y ya se usa para
	exactamente este caso (`snapshot_query.py`, `pending_query.py`); esto solo
	cierra la misma brecha en la función que faltaba."""

	def test_get_dashboard_summary_now_gates_on_project_access(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		self.assertIn("from nexora.permissions import require_action, require_project_access", code)
		body = code.split("def get_dashboard_summary(", 1)[1]
		self.assertIn('require_project_access(project, action="view_reports")', body)
