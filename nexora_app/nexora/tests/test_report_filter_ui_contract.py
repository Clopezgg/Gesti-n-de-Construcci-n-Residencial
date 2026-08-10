from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestReportFilterUIContract(unittest.TestCase):
	def test_report_center_exposes_financial_and_contract_filters(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		for marker in (
			'fieldname: "project"',
			'fieldname: "from_date"',
			'fieldname: "to_date"',
			'fieldname: "source"',
			'fieldname: "economic_category"',
			'fieldname: "cost_center"',
			'fieldname: "entity"',
			'fieldname: "payment_method"',
			'fieldname: "contractor"',
			'fieldname: "contract_status"',
		):
			self.assertIn(marker, code)

	def test_all_filters_are_sent_to_preview_detail_export_and_saved_reports(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		for marker in (
			"cost_center: controls.cost_center.get_value() || null",
			"payment_method: controls.payment_method.get_value() || null",
			"contract_status: controls.contract_status.get_value() || null",
			"args: { payload: payload() }",
			"const exportPayload = { ...payload(), report_code: activeView, format }",
			"filters: businessFilters()",
			"Object.entries(saved.filters || {})",
		):
			self.assertIn(marker, code)

	def test_interface_discloses_active_filter_count(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("snapshot.filter_context?.active", code)
		self.assertIn("filtro(s) activo(s)", code)

	def test_saved_report_definitions_exclude_pagination_state(self) -> None:
		"""`page`/`page_size` son estado de navegación de la tabla, no un filtro de
		negocio: no deben quedar grabados en la definición de un reporte guardado.
		`businessFilters()` es la única fuente para lo que se persiste; `payload()`
		(que sí lleva `page`/`page_size`, para consultar) delega en ella y las agrega
		encima solo para la llamada en vivo."""
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		business_start = code.index("function businessFilters()")
		business_end = code.index("\n\tfunction payload()", business_start)
		business_body = code[business_start:business_end]
		self.assertNotIn("page", business_body)
		self.assertNotIn("page_size", business_body)
		payload_start = code.index("function payload()")
		payload_end = code.index("\n\n", payload_start)
		payload_body = code[payload_start:payload_end]
		self.assertIn("...businessFilters()", payload_body)
		self.assertIn("page: currentPage", payload_body)
		self.assertIn("page_size: 25", payload_body)
		save_call = code[code.index("async function saveReport()") : code.index("async function loadSavedReports()")]
		self.assertIn("filters: businessFilters()", save_call)
		self.assertNotIn("filters: payload()", save_call)

	def test_report_center_inherits_the_date_range_from_navigation(self) -> None:
		"""El dashboard (`routeContext()`) y la barra de contexto global
		(`contextRouteOptions()`) escriben `from_date`/`to_date`/`nexora_period` en
		`route_options` para que el centro de reportes herede el mismo período que el
		usuario venía viendo. Antes de esta corrección nadie los leía: el rango se
		perdía en silencio al navegar desde el dashboard hacia un reporte."""
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("launchOptions.from_date || launchOptions.to_date", code)
		self.assertIn("setDateRangeSilently(launchOptions.from_date, launchOptions.to_date)", code)
		self.assertIn("async function setDateRangeSilently(fromDate, toDate)", code)
		self.assertIn("controls.from_date.set_value(fromDate || \"\")", code)
		self.assertIn("controls.to_date.set_value(toDate || \"\")", code)

	def test_report_center_resyncs_its_date_range_when_the_active_context_changes(self) -> None:
		"""Si el usuario cambia el período activo en la barra global mientras el centro
		de reportes está abierto, el rango aplicado debe seguir a ese cambio -- igual
		que ya ocurre con el proyecto -- en vez de quedar con fechas obsoletas."""
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		on_change = code[
			code.index("window.nexora.context?.onContextChange?.(async (context) => {") : code.index(
				"$(wrapper).on(\"remove\", () => release?.());"
			)
		]
		self.assertIn("rangeChanged", on_change)
		self.assertIn("controls.from_date.get_value()", on_change)
		self.assertIn("controls.to_date.get_value()", on_change)
		self.assertIn("setDateRangeSilently(context?.from_date, context?.to_date)", on_change)

	def test_report_errors_surface_the_real_backend_reason(self) -> None:
		"""Un rango invertido o inválido ya lo rechaza el servidor
		(`normalize_period`), pero un `frappe.msgprint` genérico ocultaba el motivo real
		("La fecha final no puede ser anterior a la fecha inicial."). El centro de
		reportes debe usar el mismo helper compartido que el resto del producto
		(`window.nexora.ui.showError`), que muestra `error.message` cuando el servidor
		lo entrega."""
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn(
			'window.nexora.ui.showError(error, { title: __("Reportes no disponibles"), '
			'fallback: __("Revise los filtros, el proyecto o sus permisos.") });',
			code,
		)


if __name__ == "__main__":
	unittest.main()
