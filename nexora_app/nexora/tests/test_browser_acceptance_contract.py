from __future__ import annotations

import pathlib
import unittest

import nexora

REPO_ROOT = pathlib.Path(nexora.__file__).resolve().parents[2]
BROWSER_FILES = (
	"nexora_browser_support.mjs",
	"nexora_browser_validators.mjs",
	"nexora_browser_smoke.mjs",
)


def _browser_code() -> str:
	return "\n".join(
		(REPO_ROOT / "scripts" / filename).read_text(encoding="utf-8") for filename in BROWSER_FILES
	)


class TestBrowserAcceptanceContract(unittest.TestCase):
	def test_browser_suite_covers_executive_surfaces(self) -> None:
		code = _browser_code()
		for marker in (
			'"nexora-dashboard"',
			'"nexora-reports"',
			'"nexora-closing"',
			'"desktop-chromium"',
			'"iphone-13-webkit"',
			"validateDashboard",
			"validateReports",
			"validateClosing",
			"validatePwa",
			"validateResponsiveLayout",
			"bounded_operational_queries",
			"nexora-analytics-v3",
		):
			self.assertIn(marker, code)

	def test_quick_actions_use_the_current_single_handler_contract(self) -> None:
		code = _browser_code()
		self.assertIn('[data-action="expense"]', code)
		self.assertIn('[data-action="income"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="expense"]', code)
		self.assertNotIn('[data-route="nexora-finance"][data-action="income"]', code)

	def test_the_navigation_is_built_once_and_updated_by_state(self) -> None:
		"""Antes eran doce enlaces reconstruidos con `innerHTML` y revinculados en seis
		instantes por cada cambio de ruta, porque no había forma de saber cuándo el marco
		terminaba de pintar. Ahora la carcasa se construye una vez y se actualiza por
		estado: repintar una navegación entera para marcar cuál está activa es tirar y
		rehacer manejadores que ya funcionaban."""
		base = (REPO_ROOT / "nexora_app/nexora/public/js/nexora.js").read_text(encoding="utf-8")
		self.assertNotIn("renderNavigation", base, "la tira de enlaces ya no existe")
		self.assertNotIn("[0, 50, 150, 300, 600, 1000]", base, "ni sus seis temporizadores")
		shell = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_shell.js").read_text(encoding="utf-8")
		# `build()` es el único que escribe la navegación; `sync` solo la monta si falta.
		self.assertEqual(1, shell.count("node.innerHTML = `"), "la navegación se escribe una vez")
		self.assertIn("if (!intact(shell)) {\n\t\t\tshell?.remove();\n\t\t\tshell = build();", shell)
		# El manejador de `Escape` vive en el documento y sobrevive a la carcasa: puede
		# llegar cuando ya no queda nada que abrir. Se comprueban las piezas, no la
		# referencia, que sigue viva aunque el marco haya vaciado sus hijos.
		drawer = shell.split("function openDrawer(open) {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("if (!intact(shell)) return;", drawer)
		self.assertIn("if (!scrim) return;", drawer)
		# NXR-UX-0014: dos disparadores abren el mismo cajón (la hamburguesa de
		# escritorio/tableta y "Más" de la barra inferior de teléfono) y los dos deben
		# reflejar el mismo estado — `querySelectorAll` nunca devuelve null, así que ya
		# no hace falta el guard `!trigger` que sí necesitaba el único botón de antes.
		self.assertIn('shell.querySelectorAll("[data-shell-drawer], [data-shell-tab-more]")', drawer)
		# Marcar el destino activo no puede repintar: se atribuye.
		paint = shell.split("function paintActive() {", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('link.setAttribute("aria-current", "page");', paint)
		self.assertNotIn("innerHTML", paint)

	def test_the_shell_never_relocates_the_frameworks_content(self) -> None:
		"""La primera versión reparentaba `#body` —donde el enrutador de Frappe construye
		cada pantalla— dentro de un marco de contenido propio, para envolverlo con la barra
		y la navegación. El recorrido real lo encontró en los tres perfiles:
		`#page-nexora-dashboard` dejaba de existir tras el primer arranque. Mover la raíz
		que el enrutador usa para montar sus páginas la desmonta; no la repinta, desaparece.

		La carcasa reserva su espacio con relleno en `<body>` (`nexora_shell.css`) y flota
		por encima; nunca vuelve a tocar el DOM del marco."""
		shell = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_shell.js").read_text(encoding="utf-8")
		for offender in (
			'getElementById("body")',
			"appendChild(container)",
			"function adopt(",
			"function release(",
		):
			with self.subTest(offender=offender):
				self.assertNotIn(offender, shell)
		css = (REPO_ROOT / "nexora_app/nexora/public/css/nexora_shell.css").read_text(encoding="utf-8")
		# La navegación y la barra flotan; el contenido se queda donde el marco lo puso y
		# solo se le reserva espacio con relleno.
		self.assertIn(".nxr-shell {", css)
		shell_rule = css.split(".nxr-shell {", 1)[1].split("}", 1)[0]
		self.assertIn("display: contents;", shell_rule)
		self.assertIn(".nxr-shell-active body {", css)
		body_rule = css.split(".nxr-shell-active body {", 1)[1].split("}", 1)[0]
		# `!important`: desk.bundle.css de Frappe trae `body { padding: 0 !important; }`
		# (núcleo del framework, no editable); sin igualar esa prioridad esta regla,
		# aunque más específica, pierde de todas formas (Bloque 35, hallazgo real de
		# auditoría visual).
		self.assertIn("padding-left: 264px !important;", body_rule)
		self.assertNotIn("nxr-shell__content", css)
		self.assertNotIn("nxr-shell__content", shell)

	def test_runtime_image_does_not_patch_application_source(self) -> None:
		dockerfile = (REPO_ROOT / "Dockerfile.nexora").read_text(encoding="utf-8")
		dashboard = (
			REPO_ROOT / "nexora_app/nexora/nexora/page/nexora_dashboard/nexora_dashboard.js"
		).read_text(encoding="utf-8")
		validators = (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text(encoding="utf-8")
		self.assertNotIn("sed -i", dockerfile)
		self.assertNotIn("RUN python3 -c", dockerfile)
		self.assertIn('loading="eager"', dashboard)
		self.assertIn("h2.nxr-project-name", validators)

	def test_route_wait_uses_rendered_state_and_publishes_diagnostics(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_support.mjs").read_text(encoding="utf-8")
		self.assertIn("did not reach a stable rendered state", code)
		self.assertIn("frappe_route", code)
		self.assertIn("page_visible", code)
		self.assertIn("routeSnapshot = await handle.jsonValue()", code)
		self.assertNotIn("page.locator(`#page-${route}`).innerText()", code)
		self.assertNotIn("locator(`#page-${route} .nxr-product-shell`)", code)

	def test_browser_network_calls_and_process_have_explicit_deadlines(self) -> None:
		support = (REPO_ROOT / "scripts/nexora_browser_support.mjs").read_text(encoding="utf-8")
		smoke = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		workflow = (REPO_ROOT / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		self.assertIn("NEXORA_BROWSER_REQUEST_TIMEOUT_MS", support)
		self.assertIn("const response = await page", support)
		self.assertIn(".context()\n    .request.fetch", support)
		self.assertIn("timeout: browserRequestTimeoutMs", support)
		self.assertNotIn("AbortController", support)
		self.assertIn("const response = await postArgs", smoke)
		self.assertNotIn(
			"return page.evaluate(", smoke.split("async function callFrappe", 1)[1].split("}", 1)[0]
		)
		self.assertIn("browserRequest(page, response.url()", smoke)
		self.assertIn("postArgs(", (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text())
		self.assertNotIn("window.frappe.call", _browser_code().split("async function callFrappe", 1)[0])
		self.assertNotIn(
			"window.frappe.call", (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text()
		)
		self.assertIn("kill-after=30s 10m", workflow)
		self.assertIn("kill-after=30s 20m", workflow)
		self.assertIn("timeout --signal=INT --kill-after=30s 50m", workflow)

	def test_global_context_observer_is_idempotent_and_frame_coalesced(self) -> None:
		code = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_report_actions.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"function setText(node, value)",
			"if (node.textContent === text) return;",
			"new MutationObserver(scheduleEnhancements)",
			"function scheduleEnhancements()",
			"if (observerFrame !== null) return;",
			"observerFrame = window.requestAnimationFrame",
		):
			self.assertIn(marker, code)
		self.assertNotIn(
			'querySelector("[data-nexora-context-user]").textContent =',
			code,
		)

	def test_guided_review_waits_for_stable_network_and_idempotent_rendering(self) -> None:
		smoke = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		guided = (REPO_ROOT / "nexora_app/nexora/public/js/nexora_guided_operations.js").read_text(
			encoding="utf-8"
		)
		for marker in (
			"waitForOperationalQuiescence",
			'page.waitForLoadState("networkidle"',
			"advanceValidatedGuidedReview",
			"__nexoraGuidedReviewProbe",
			"now - probe.since >= stableForMs",
		):
			self.assertIn(marker, smoke)
		for marker in (
			"target.dataset.accountSignature === signature",
			"if (review.innerHTML !== reviewHtml)",
			"if (node.hidden !== hidden)",
			# El repintado sigue siendo idempotente; lo que cambió es que compara contra
			# el estado utilizable —que ignora el parpadeo— y no contra el instantáneo.
			"if (next.disabled === usable)",
			"if (execute.disabled === usable)",
		):
			self.assertIn(marker, guided)
		self.assertNotIn("if (target) target.innerHTML = accountMarkup(state)", guided)

	def test_dashboard_gate_requires_context_actions_and_clean_console(self) -> None:
		code = (REPO_ROOT / "scripts/nexora_browser_validators.mjs").read_text(encoding="utf-8")
		for marker in (
			'.nxr-dashboard-shell[data-state="ready"]',
			".nxr-project-name",
			".nxr-dashboard-period",
			'[data-action="income"]',
			'[data-action="expense"]',
			"Dashboard bootstrap emitted page errors",
			"Dashboard bootstrap emitted console errors",
		):
			self.assertIn(marker, code)

	def test_browser_suite_calculates_but_does_not_persist_a_weekly_close(self) -> None:
		code = _browser_code()
		self.assertIn(".nxr-calculate", code)
		self.assertNotIn("save_weekly_close", code)
		self.assertNotIn("correct_weekly_close", code)

	def test_browser_suite_executes_search_correction_and_idempotent_replay(self) -> None:
		code = _browser_code()
		for marker in (
			"replayExecution",
			"universal_search_consolidated",
			"get_search_result_detail",
			"validateControlledCorrection",
			'"Anular operación"',
			'"nexora.operator@example.test"',
			'"nexora.manager@example.test"',
			'"Compensated"',
			"original_preserved: true",
		):
			self.assertIn(marker, code)

	def test_browser_suite_walks_the_eight_operations_of_chapter_53(self) -> None:
		"""Capítulo 53: «Como mínimo: crear, editar, consultar, aprobar, rechazar,
		anular, corregir y exportar. No se asume que funciona: se comprueba.»

		El recorrido cubría tres —crear, consultar y anular— y las otras cinco se daban
		por buenas sin recorrerlas. Aquí se comprueba que cada una tiene su etapa, su
		llamada al servidor y su afirmación, no solo su nombre en un comentario.
		"""
		smoke = (REPO_ROOT / "scripts/nexora_browser_smoke.mjs").read_text(encoding="utf-8")
		# Una etapa por operación, y todas dentro del corredor que no aborta en el primer
		# fallo: si «aprobar» se rompe, «exportar» sigue diciendo qué le pasa a él.
		for stage in ("anulacion", "correccion", "comprobantes", "exportacion"):
			with self.subTest(stage=stage):
				self.assertRegex(smoke, rf'step\(\s*"{stage}"')
		# Editar no existe sobre un documento contabilizado y el recorrido comprueba las
		# dos mitades: la negativa en sitio y la corrección auditada que sí cambia el dato.
		self.assertIn("No edite sus campos directamente", smoke)
		self.assertIn("refusal.save_disabled", smoke)
		self.assertIn("in_place_edit_refused: true", smoke)
		for endpoint in (
			"get_operation_for_correction",
			"preview_operation_correction",
			"execute_operation_correction",
			"register_evidence",
			"review_evidence",
			"upload_file",
		):
			with self.subTest(endpoint=endpoint):
				self.assertIn(endpoint, smoke)
		# Aprobar y rechazar son decisiones distintas sobre documentos distintos.
		self.assertIn('reviewEvidence(page, "Validated", "Validar")', smoke)
		self.assertIn('reviewEvidence(page, "Rejected", "Rechazar")', smoke)
		# Sustituir conserva el original: si desapareciera, el historial sería decorativo.
		self.assertIn('"Superseded"', smoke)
		# Exportar descarga de verdad, y el CSV se comprueba por contenido.
		self.assertIn('page.waitForEvent("download"', smoke)
		self.assertIn("await fs.readFile(file", smoke)
		# La exportación se salta donde la pantalla muestra tarjetas (Capítulo 37); que se
		# saltara en los tres perfiles sería una comprobación que no comprueba nada.
		self.assertIn("report.csv_export_profiles", smoke)
		self.assertIn(
			"Ningún perfil descargó el CSV",
			smoke,
			"sin esta exigencia la etapa de exportación puede pasar sin exportar",
		)
		# El informe nombra las ocho: leer el JSON debe bastar para saber qué se recorrió.
		self.assertIn(
			"profile.chapter_53 = {",
			smoke,
			"el informe debe nombrar las ocho operaciones en un solo bloque",
		)
		summary = smoke.split("profile.chapter_53 = {", 1)[1].split("};", 1)[0]
		for operation in (
			"crear",
			"editar",
			"consultar",
			"aprobar",
			"rechazar",
			"anular",
			"corregir",
			"exportar",
		):
			with self.subTest(operation=operation):
				self.assertIn(f"{operation}:", summary)


if __name__ == "__main__":
	unittest.main()
