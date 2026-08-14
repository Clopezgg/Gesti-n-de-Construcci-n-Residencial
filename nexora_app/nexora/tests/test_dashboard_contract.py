from __future__ import annotations

import json
import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestDashboardContract(unittest.TestCase):
	@staticmethod
	def _dashboard_code() -> str:
		return (APP_ROOT / "nexora/page/nexora_dashboard/nexora_dashboard.js").read_text(encoding="utf-8")

	def test_dashboard_module_and_service_exist(self) -> None:
		self.assertTrue((APP_ROOT / "dashboard/__init__.py").is_file())
		self.assertTrue((APP_ROOT / "dashboard/service.py").is_file())

	def test_dashboard_and_search_pages_exist(self) -> None:
		for page_name in ("nexora-dashboard", "nexora-search"):
			# Frappe resolves page assets with frappe.scrub(name), so the folder and the
			# asset filenames use underscores even when the Page record uses hyphens.
			folder = page_name.replace("-", "_")
			root = APP_ROOT / f"nexora/page/{folder}"
			payload = json.loads((root / f"{folder}.json").read_text(encoding="utf-8"))
			self.assertEqual(page_name, payload["page_name"])
			self.assertIn("frappe.pages", (root / f"{folder}.js").read_text(encoding="utf-8"))

	def test_dashboard_keeps_project_control_reference(self) -> None:
		code = self._dashboard_code()
		self.assertIn("const projectControl = page.add_field", code)
		self.assertIn("projectControl.get_value()", code)
		self.assertNotIn("controls.project.get_value()", code)

	def test_dashboard_exposes_direct_income_and_expense_actions(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'data-action="income"',
			'data-action="expense"',
			"frappe.route_options",
			"nexora_action: action",
			"project: projectControl.get_value()",
		):
			self.assertIn(marker, code)

	def test_dashboard_uses_official_product_identity(self) -> None:
		code = self._dashboard_code()
		self.assertIn('title: __("NEXORA")', code)
		self.assertIn("Gestión Integral de Fondos, Proyectos y Operaciones", code)
		self.assertNotIn("NEXORA — Control de obras", code)

	def test_dashboard_translates_technical_operation_values(self) -> None:
		code = self._dashboard_code()
		for marker in (
			'Inflow: __("Ingreso")',
			'Outflow: __("Gasto")',
			'"Internal Transfer": __("Transferencia interna")',
			'"Real Return": __("Devolución real")',
			'Draft: __("Borrador")',
			'Executed: __("Registrado definitivamente")',
			'Posted: __("Registrado definitivamente")',
			'"Compensated Total": __("Corregido totalmente")',
		):
			self.assertIn(marker, code)

	def test_dashboard_handles_loading_failures_with_actionable_copy(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"try {",
			"catch (error)",
			'title: __("Resumen no disponible")',
			"Revise la conexión, el proyecto o sus permisos y vuelva a intentar.",
			'attr({ "data-state": "error", "aria-busy": "false" })',
		):
			self.assertIn(marker, code)

	def test_error_fallback_never_shows_two_dialogs(self) -> None:
		"""`showError` no devuelve valor. Encadenarlo con `||` ejecutaba el respaldo
		siempre y el usuario veía el mismo error dos veces, uno encima del otro. El
		respaldo existe solo para cuando el bundle compartido no cargó, así que la
		rama tiene que ser explícita."""
		shared = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		body = shared.split("function showError(", 1)[1].split("\n\t}", 1)[0]
		self.assertNotIn("return", body, "si showError devolviera algo, el contrato cambiaría")

		for relative in (
			"nexora/page/nexora_dashboard/nexora_dashboard.js",
			"nexora/page/nexora_operations/nexora_operations.js",
		):
			with self.subTest(surface=relative):
				code = (APP_ROOT / relative).read_text(encoding="utf-8")
				self.assertNotRegex(
					code,
					r"showError\??\.?\([^;]*\}\)\s*\|\|",
					"encadenar el respaldo con || duplica el diálogo",
				)
				self.assertIn("typeof window.nexora", code)
				self.assertIn("frappe.msgprint(", code)

	def test_dashboard_snapshot_uses_native_deadline_instead_of_frappe_thenable(self) -> None:
		code = self._dashboard_code()
		snapshot_request = code[
			code.index("function requestExecutiveSnapshot") : code.index("function renderIdentity")
		]
		load = code[code.index("async function load") : code.index("function render(data)")]
		for marker in (
			"return new Promise((resolve, reject) => {",
			"window.setTimeout(",
			"120000",
			"callback: (response) => finish(resolve, response?.message || {})",
			"error: (error) =>",
			"El resumen ejecutivo excedió 120 segundos.",
		):
			self.assertIn(marker, snapshot_request)
		self.assertIn(
			"const snapshot = await requestExecutiveSnapshot(snapshotPayload(), Boolean(freeze));",
			load,
		)
		self.assertNotIn("await frappe.call", load)
		self.assertIn("render(snapshot)", load)

	def test_dashboard_period_label_keeps_its_colon(self) -> None:
		"""Regresión real (Bloque 30): el PR #93 (`c513789d`, "make dashboard period
		selectable") sustituyó el texto plano `Período: <mes>` por un `<select>` y en
		el cambio perdió los dos puntos — `.nxr-dashboard-period` quedó como
		`Período<select>...` en vez de `Período: <select>...`. El recorrido real de
		Playwright (`nexora_browser_validators.mjs::validateDashboard`) exige que el
		texto visible empiece con `/^Período:/`; sin los dos puntos, la etapa `panel`
		fallaba en los tres perfiles en cada ejecución real desde ese PR — la causa
		raíz del defecto que los Bloques 24 a 29 documentaron como "preexistente y
		ajeno" sin diagnosticarlo."""
		code = self._dashboard_code()
		render_identity = code[code.index("function renderIdentity") : code.index("function periodKey")]
		self.assertIn('${__("Período")}: ${periodSelect(activePeriod)}', render_identity)

	def test_dashboard_integrates_complete_operational_summary(self) -> None:
		code = self._dashboard_code()
		for marker in (
			"finance.total_available_hnl",
			"finance.total_reserved_hnl",
			"executive.spent_hnl",
			"budgets.total_available_hnl",
			"pending_accounts",
			"progress.physical_percent",
			"nxr-evidence-gallery",
			"nxr-alert-rows",
			"nxr-contract-rows",
		):
			self.assertIn(marker, code)

	def test_dashboard_service_reconciles_against_canonical_effect_ledger(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"source_states",
			'"NXR Operation Effect"',
			'"Reserved"',
			'"Budget"',
			'{"Commitment Reserve", "Commitment Release"}',
			'"NXR Contract Estimate"',
			'"NXR Progress Record"',
			'"NXR Evidence"',
		):
			self.assertIn(marker, code)

	def test_service_has_whitelisted_permission_checked_functions(self) -> None:
		code = (APP_ROOT / "dashboard/service.py").read_text(encoding="utf-8")
		for marker in (
			"@frappe.whitelist",
			"def universal_search",
			"def get_dashboard_summary",
			"require_action",
		):
			self.assertIn(marker, code)

	def test_workspace_has_dashboard_and_search_shortcuts(self) -> None:
		payload = json.loads((APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		shortcuts = [shortcut["label"] for shortcut in payload.get("shortcuts", [])]
		self.assertIn("Panel principal", shortcuts)
		self.assertIn("Buscador universal", shortcuts)

	def test_global_navigation_uses_canonical_nexora_pages(self) -> None:
		"""La navegación se mudó de `nexora.js` —donde era una tira de enlaces inyectada en
		el cuerpo de la página— a la carcasa, que la agrupa por la pregunta que responde
		cada grupo en vez de listar doce destinos iguales en fila."""
		shell = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		for route in (
			"nexora-dashboard",
			"nexora-assistant",
			"nexora-operations",
			"nexora-search",
			"nexora-finance",
			"nexora-reports",
			"nexora-closing",
			"nexora-purchase-requests",
			"nexora-quotations",
			"nexora-suppliers",
			"nexora-contracts",
			"nexora-entities",
			"nexora-evidence",
			"nexora-progress",
			"nexora-conversation-channels",
			"nexora-ai-providers",
		):
			with self.subTest(route=route):
				self.assertIn(f'route: "{route}"', shell)
		# Los doce originales siguen estando en `SECTIONS`, el cajón lateral: la
		# reorganización no puede perder destinos por el camino. Se cuenta solo dentro
		# de ese arreglo, no en todo el archivo — NXR-UX-0014 agregó `TABBAR_ITEMS`, una
		# barra inferior de teléfono que referencia cuatro de estos mismos destinos (no
		# crea rutas nuevas), y contar el archivo completo los sumaría como distintos.
		# NXR-UX-0010 (Bloque 17) sumó un decimotercer destino real y nuevo
		# ("nexora-project"); NXR-CNV-0001 (Bloque 18) sumó un decimocuarto
		# ("nexora-assistant"); Bloque 25 (NXR-AVA-0006) sumó un decimoquinto
		# ("nexora-progress" — la página de avance que la matriz de requisitos daba
		# por implementada sin que existiera); el hallazgo de auditoría de este bloque
		# sumó un decimosexto y un decimoséptimo ("nexora-conversation-channels" y
		# "nexora-ai-providers" — páginas reales que habían quedado huérfanas de esta
		# misma navegación desde que reemplazó al workspace legado): 17 es el conteo
		# correcto ahora.
		sections_block = shell.split("const SECTIONS = [", 1)[1].split("\n\t];", 1)[0]
		self.assertEqual(17, sections_block.count('{ route: "'), "faltan o sobran destinos")
		self.assertIn('route: "nexora-project"', sections_block)
		self.assertIn('route: "nexora-assistant"', sections_block)
		self.assertIn('route: "nexora-progress"', sections_block)
		self.assertIn('route: "nexora-conversation-channels"', sections_block)
		self.assertIn('route: "nexora-ai-providers"', sections_block)
		self.assertEqual(5, shell.count("\t\t\tlabel: "), "cinco grupos, no doce iguales")
		self.assertIn('frappe.boot?.home_page === "nexora-dashboard"', shell)

	def test_the_dashboard_answers_what_to_do_today(self) -> None:
		"""El panel respondía «cómo va la empresa» con nueve tarjetas del mismo peso y
		dejaba sin responder la pregunta con la que alguien abre un sistema por la mañana.
		Los datos ya venían —vencimientos, conciliaciones, alertas—, repartidos entre
		tarjetas que el usuario tenía que recorrer y ordenar mentalmente."""
		code = self._dashboard_code()
		self.assertIn("function renderAgenda(data) {", code)
		self.assertIn('<section class="nxr-agenda"', code)
		# Va antes que las alertas: es lo primero que hay que leer.
		self.assertLess(code.index("renderAgenda(data);"), code.index("renderAlerts(sourceTotals)"))
		# Bloque Home #2: `renderAlerts` ya no repite aquí, en forma de tarjetas, lo que
		# `renderAgenda` acaba de mostrar arriba como lista priorizada (mismos vencimientos,
		# misma conciliación pendiente) — dos secciones consecutivas respondiendo la misma
		# pregunta. Ahora solo cubre una señal que la agenda no tiene: movimientos
		# corregidos o reversados en el período (auditoría, no urgencia).
		alerts = code.split("function renderAlerts(sourceTotals) {", 1)[1].split("\n\t}", 1)[0]
		self.assertNotIn("Ingresos sin conciliar", alerts)
		self.assertNotIn("Pago vencido", alerts)
		self.assertNotIn("Operación al día", alerts)
		agenda = code.split("function renderAgenda(data) {", 1)[1].split("\n\t}", 1)[0]
		# Ordena por lo que cuesta no atenderlo, no por el orden en que llegó.
		self.assertIn("items.sort((left, right) => left.weight - right.weight);", agenda)
		for source in ("pending.items", "analytics.unreconciled_count", "data.alerts"):
			with self.subTest(source=source):
				self.assertIn(source, agenda)
		# No pide nada nuevo al servidor: si lo hiciera, el panel tardaría más en abrirse.
		self.assertNotIn("frappe.call", agenda)
		# Y cuando no hay nada pendiente lo dice, en vez de dejar un hueco.
		self.assertIn("Todo al día", agenda)

	def test_dashboard_is_the_canonical_desk_home(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		install = (APP_ROOT / "install.py").read_text(encoding="utf-8")
		self.assertIn('"route": "/app/nexora-dashboard"', hooks)
		self.assertIn('NEXORA_HOME_PAGE = "nexora-dashboard"', install)
		self.assertIn('frappe.db.set_default("desktop:home_page", NEXORA_HOME_PAGE)', install)

	def test_dashboard_styles_cover_mobile_composition(self) -> None:
		css = (APP_ROOT / "public/css/nexora.css").read_text(encoding="utf-8")
		for selector in (
			".nxr-dashboard-shell",
			".nxr-dashboard-welcome",
			".nxr-section-heading",
			".nxr-dashboard-primary-actions",
			".nxr-balance-row",
			".nxr-evidence-gallery",
			".nxr-progress-track",
			".nxr-list-row",
		):
			self.assertIn(selector, css)

	def test_dashboard_context_is_consumed_by_related_pages(self) -> None:
		for relative_path in (
			"nexora/page/nexora_evidence/nexora_evidence.js",
			"nexora/page/nexora_reports/nexora_reports.js",
			"nexora/page/nexora_contracts/nexora_contracts.js",
			"nexora/page/nexora_purchase_requests/nexora_purchase_requests.js",
		):
			code = (APP_ROOT / relative_path).read_text(encoding="utf-8")
			self.assertIn("frappe.route_options", code)
			self.assertIn("launchOptions.project", code)

	def test_financial_report_sends_resolved_payload(self) -> None:
		code = (APP_ROOT / "nexora/page/nexora_reports/nexora_reports.js").read_text(encoding="utf-8")
		self.assertIn("args: { payload: payload() }", code)
		self.assertNotIn("args: { payload },", code)

	def test_search_result_detail_translates_dimension_and_effect_type(self) -> None:
		"""Hallazgo real de auditoría visual (captura real del recorrido de
		navegador, `desktop-chromium-universal-search.png`): la tabla «Efecto
		financiero» del consolidado de búsqueda pintaba `effect.dimension`/
		`effect.effect_type` sin traducir — el valor interno en inglés que
		`financial/db.py` escribe en `NXR Operation Effect` ("Funds", "Cost
		Recognized", "Budget Executed"…) aparecía tal cual junto a etiquetas en
		español en la misma fila. Único punto de la interfaz que muestra estos
		dos campos: se corrige aquí con el mismo registro de traducciones que ya
		usa el resto de la aplicación (`window.nexora.ui.label`), no con un
		diccionario nuevo y local."""
		search = (APP_ROOT / "nexora/page/nexora_search/nexora_search.js").read_text(encoding="utf-8")
		self.assertIn('ui.label("dimension", effect.dimension)', search)
		self.assertIn('ui.label("effectType", effect.effect_type)', search)
		self.assertNotIn("escape(effect.dimension)", search)
		self.assertNotIn("escape(effect.effect_type)", search)

		registry = (APP_ROOT / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		dimension_block = registry.split("dimension: Object.freeze({", 1)[1].split("}),", 1)[0]
		effect_type_block = registry.split("effectType: Object.freeze({", 1)[1].split("}),", 1)[0]
		# Conjunto real, tomado de los literales de financial/db.py,
		# operational_commands.py y corrections.py — no inventado.
		for value in ("Funds", "Reserved", "Cost", "Budget", "Savings", "Investment"):
			with self.subTest(dimension=value):
				self.assertIn(f"{value}:", dimension_block)
		for value in (
			"Executed",
			"Reserved",
			"Released",
			"Internal Transfer",
			"Real Return",
			"Analytic Adjustment",
			"Reclassification",
			"Received",
			"Reversed",
			"Cost Recognized",
			"Budget Reserved",
			"Budget Executed",
			"Savings Applied",
			"Investment Applied",
		):
			with self.subTest(effect_type=value):
				self.assertIn(value, effect_type_block)

	def test_the_executive_kpi_row_has_real_tokens_semantic_tone_and_a_hero_metric(self) -> None:
		"""Bloque Home #1 — primer incremento del rediseño pedido por el propietario
		        (auditoría visual: "jerarquía visual plana, KPIs sin semántica visual, demasiadas
		        tarjetas con igual importancia"). El KPI usaba `var(--fg-color, #fff)` /
		        `var(--border-color, #dfe3e8)` — las variables crudas del marco, no los tokens
		        propios que `nxr-ds-card` ya resuelve bien para el resto de tarjetas del panel
		        desde el Bloque C. Se corrige reutilizando ese mismo componente compartido
		        (Capítulo 34: nunca crear una segunda variante) y usando el `data-tone` que
		        `renderMetrics` ya calculaba para el color del texto, ahora también para el
		acento y el fondo de la tarjeta."""
		code = self._dashboard_code()
		self.assertIn('class="nxr-executive-metric nxr-ds-card"', code)

		css = (APP_ROOT / "public/css/nexora_executive.css").read_text(encoding="utf-8")
		metric_block = css.split(".nxr-executive-metric {", 1)[1].split("\n}", 1)[0]
		# Ya no debe depender de las variables crudas del marco para su propio fondo.
		self.assertNotIn("var(--fg-color", metric_block)
		self.assertNotIn("var(--border-color", metric_block)
		for tone in ("income", "balance", "warning", "voided"):
			with self.subTest(tone=tone):
				self.assertIn(f'.nxr-executive-metric[data-tone="{tone}"]', css)
		# Jerarquía real: la primera cifra (Saldo disponible) no compite en igualdad de
		# peso visual con las otras cinco.
		self.assertIn(".nxr-executive-metrics .nxr-executive-metric:first-child {", css)
		self.assertIn("grid-column: span 2", css)


if __name__ == "__main__":
	unittest.main()
