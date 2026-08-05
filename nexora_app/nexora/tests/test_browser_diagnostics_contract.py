from __future__ import annotations

import pathlib
import re
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = APP_ROOT.parent / "scripts"
SMOKE = SCRIPTS / "nexora_browser_smoke.mjs"
SUPPORT = SCRIPTS / "nexora_browser_support.mjs"
VALIDATORS = SCRIPTS / "nexora_browser_validators.mjs"


class TestBrowserDiagnosticsContract(unittest.TestCase):
	"""Un recorrido que falla debe decir por qué, no solo que falló.

	Tres ejecuciones de CI se gastaron leyendo `false !== true` sobre una vista
	previa rechazada por el servidor: el rojo señalaba el navegador cuando la
	causa estaba en una regla de negocio que nadie podía leer desde el log.
	"""

	def test_the_support_module_unpacks_the_server_reason(self) -> None:
		support = SUPPORT.read_text(encoding="utf-8")
		self.assertIn("export function serverReason(", support)
		self.assertIn("export async function assertResponseOk(", support)
		reason = support.split("export function serverReason(", 1)[1].split("\nexport ", 1)[0]
		# Frappe entrega el motivo en `_server_messages`, un JSON dentro de otro JSON.
		self.assertIn("_server_messages", reason)
		self.assertIn("exc_type", reason)
		helper = support.split("export async function assertResponseOk(", 1)[1].split("\nexport ", 1)[0]
		self.assertIn("status", helper, "el mensaje debe nombrar el estado HTTP")
		self.assertIn("serverReason(", helper)

	def test_no_response_check_hides_why_the_server_refused(self) -> None:
		"""`assert.equal(x.ok(), true, "algo falló")` descarta el cuerpo de la
		respuesta, que es justo donde viaja el motivo."""
		blind = re.compile(r"assert\.equal\(\s*\w+\.ok\(\)", re.MULTILINE)
		offenders: list[str] = []
		for script in sorted(SCRIPTS.glob("nexora_browser_*.mjs")):
			source = script.read_text(encoding="utf-8")
			for match in blind.finditer(source):
				line = source[: match.start()].count("\n") + 1
				offenders.append(f"{script.name}:{line}")
		self.assertEqual([], offenders, "use assertResponseOk para nombrar el motivo")

	def test_every_operational_request_is_checked_through_the_helper(self) -> None:
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("assertResponseOk,", smoke, "el helper debe importarse")
		for label in (
			"Income preview request",
			"Income execution request",
			"Expense preview request",
			"Expense execution request",
		):
			with self.subTest(request=label):
				self.assertRegex(smoke, rf'assertResponseOk\(\s*\w+,\s*"{label}"\s*\)')

	def test_waiting_for_the_guided_review_names_what_stayed_false(self) -> None:
		"""La espera resume cinco condiciones en un booleano. Cuando expira, «Timeout»
		no distingue «el servidor aprobó pero la consola no habilitó el botón» de «el
		asistente retrocedió de etapa»: son causas distintas con correcciones
		distintas, y una ejecución de CI se gastó sin poder elegir entre ellas."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function guidedReviewDiagnostics(page)", smoke)
		diagnostics = smoke.split("async function guidedReviewDiagnostics(page)", 1)[1]
		diagnostics = diagnostics.split("\n}", 1)[0]
		for signal in (
			"visible_stages",
			"review_stage_hidden",
			"continue_button_disabled",
			"console_execute_disabled",
			"preview_still_empty",
			# La consola escribe aquí el motivo cuando rechaza la vista previa: leerlo
			# evita confundir un rechazo de negocio con un fallo del navegador.
			"validation_summary",
			"action_status",
			# Y aquí, quién la anuló: el usuario editando o la pantalla refrescándose.
			"preview_invalidated_by",
		):
			with self.subTest(signal=signal):
				self.assertIn(signal, diagnostics)
		# Las dos esperas ciegas del recorrido guiado deben informar al expirar.
		for helper in (
			"async function waitForGuidedStage(page, stage, profile)",
			"async function advanceValidatedGuidedReview(page, label, profile)",
		):
			with self.subTest(helper=helper):
				body = smoke.split(helper, 1)[1].split("\n}", 1)[0]
				self.assertIn("guidedReviewDiagnostics(page)", body)
				self.assertIn("describeSignals(profile)", body)
		# Un llamante que omite `profile` recibe «the page reported no errors» aunque la
		# página estuviera gritando. Se coló uno dentro de la propia función corregida.
		anonymous = re.findall(r"await waitForGuidedStage\(page, \d+\)", smoke)
		self.assertEqual([], anonymous, "toda espera de etapa debe recibir el perfil")

	def test_the_page_errors_reach_the_log_and_not_only_the_artifact(self) -> None:
		"""`page_errors` y `console_errors` solo se comprueban al terminar el perfil,
		así que un fallo anterior los descarta sin mostrarlos. El informe JSON vive
		dentro del zip del artefacto, que no siempre puede descargarse: el log es el
		único canal garantizado."""
		support = SUPPORT.read_text(encoding="utf-8")
		self.assertIn("export function describeSignals(", support)
		described = support.split("export function describeSignals(", 1)[1].split("\nexport ", 1)[0]
		for bucket in ("page_errors", "console_errors", "server_errors", "auth_errors"):
			with self.subTest(bucket=bucket):
				self.assertIn(bucket, described)
		validators = VALIDATORS.read_text(encoding="utf-8")
		capture = validators.split("export async function captureFailure(", 1)[1].split("\n}", 1)[0]
		self.assertIn("console.error(", capture, "el fallo debe imprimirse en el log de CI")
		self.assertIn("describeSignals(profile)", capture)

	def test_the_console_records_who_invalidated_the_preview(self) -> None:
		"""La consola afirma «La información cambió» sin poder justificarlo. El recorrido
		mostró esa frase con el resumen de validación vacío —o sea, el servidor había
		aprobado— y sin forma de saber si la anuló el usuario o la propia pantalla al
		refrescarse. Cada llamante deja ahora su nombre."""
		operations = (
			APP_ROOT / "nexora/nexora/page/nexora_operations/nexora_operations.js"
		).read_text(encoding="utf-8")
		self.assertIn('function invalidatePreview(reason = "unknown")', operations)
		self.assertIn('attr("data-preview-invalidated-by", reason)', operations)
		# Ningún llamante puede quedarse anónimo: `unknown` no distinguiría nada.
		self.assertNotIn("invalidatePreview();", operations)
		for reason in (
			'invalidatePreview("allocation-amount")',
			"invalidatePreview(`field:${fieldname}`)",
			'invalidatePreview("server-refused-preview")',
			'invalidatePreview("after-execution")',
		):
			with self.subTest(reason=reason):
				self.assertIn(reason, operations)
		# Una vista previa aceptada limpia la marca: si no, el motivo anterior se lee
		# como si fuera el actual.
		success = operations.split("state.preview = response.message;", 1)[1].split("\n\t\t}", 1)[0]
		self.assertIn('removeAttr("data-preview-invalidated-by")', success)


if __name__ == "__main__":
	unittest.main()
