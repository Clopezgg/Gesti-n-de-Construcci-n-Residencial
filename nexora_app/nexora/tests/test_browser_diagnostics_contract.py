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
		# La forma de propiedad (`replay.ok`) escapaba a la comprobación anterior y dejó
		# un «Idempotent replay failed with HTTP 417» sin decir por qué lo rechazó.
		# `assert.equal` no es la única forma de tirar el cuerpo: `assert(x.ok(), …)`,
		# `assert.ok(x.ok())` y `assert.strictEqual(x.ok(), true)` lo hacen igual.
		blind = re.compile(r"assert(?:\.\w+)?\(\s*\w+\.ok(?:\(\))?\s*(?:,|\))", re.MULTILINE)
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
		# Dos argumentos es la firma sin perfil, sea la etapa literal o una variable.
		anonymous = re.findall(r"await waitForGuidedStage\(\s*page\s*,\s*[^,)\n]+\s*\)", smoke)
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
		operations = (APP_ROOT / "nexora/nexora/page/nexora_operations/nexora_operations.js").read_text(
			encoding="utf-8"
		)
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

	def test_an_unchanged_field_never_destroys_a_valid_preview(self) -> None:
		"""El recorrido mostró `field:description` anulando un gasto que el servidor ya
		había aprobado, sobre un campo que el usuario no volvió a tocar: Frappe emite
		`change` también cuando la pantalla reescribe un control, cuando el asistente mueve
		el campo de contenedor o cuando el foco vuelve a él. «La información cambió» tiene
		que significar que cambió."""
		operations = (APP_ROOT / "nexora/nexora/page/nexora_operations/nexora_operations.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("fieldValues: {},", operations, "hace falta recordar el valor anterior")
		changed = operations.split("async function fieldChanged(fieldname) {", 1)[1]
		changed = changed.split("\n\t}", 1)[0]
		self.assertIn("state.fieldValues[fieldname] = current;", changed)
		self.assertIn(
			"if (previous !== current) invalidatePreview(`field:${fieldname}`);",
			changed,
			"solo un valor distinto puede anular la vista previa",
		)
		# Comprobar que la línea guardada existe no basta: añadir una invalidación
		# incondicional al lado la dejaría intacta y el defecto volvería. Dentro de
		# `fieldChanged` no puede haber más que una, y es la guardada.
		invalidations = [line.strip() for line in changed.splitlines() if "invalidatePreview(" in line]
		self.assertEqual(
			["if (previous !== current) invalidatePreview(`field:${fieldname}`);"],
			invalidations,
			"la única invalidación del manejador es la que compara el valor",
		)
		# Y `previous` se lee antes de sobrescribirlo: al revés siempre serían iguales y
		# la vista previa no se anularía nunca.
		self.assertLess(
			changed.index("const previous = state.fieldValues[fieldname];"),
			changed.index("state.fieldValues[fieldname] = current;"),
			"escribir antes de leer haría que `previous` fuese siempre `current`",
		)
		# El importe asignado sigue la misma regla: una sola invalidación, nombrada.
		listener = operations.split('body.on("input", ".nxr-source-amount"', 1)[1].split("\n\t});", 1)[0]
		self.assertEqual(
			1,
			listener.count("invalidatePreview("),
			"el importe asignado no puede anular la vista previa dos veces",
		)

	def test_a_wizard_that_refuses_to_advance_says_what_is_missing(self) -> None:
		"""«La etapa 2 nunca se abrió» no distingue un dato que el usuario no puso de un
		campo que la pantalla vació sola después de rellenarlo."""
		guided = (APP_ROOT / "nexora/public/js/nexora_guided_operations.js").read_text(encoding="utf-8")
		self.assertIn('state.wizard.dataset.guidedMissing = missing.join(",")', guided)
		# Se escribe siempre, también cuando no falta nada: un valor pegado de una
		# comprobación anterior sería peor que no tenerlo.
		primary = guided.split("function validatePrimary(root, state) {", 1)[1].split("\n\t}", 1)[0]
		self.assertLess(
			primary.index("dataset.guidedMissing"),
			primary.index("if (!missing.length) return true;"),
			"el diagnóstico se escribe antes de dar por buena la etapa",
		)
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("guided_missing:", smoke)
		self.assertIn("primary_values:", smoke)

	def test_the_screen_never_overwrites_itself_while_the_preview_is_built(self) -> None:
		"""Los manejadores de campo son asíncronos y escriben en otros controles. Si dos
		se solapan, el último en terminar pisa al anterior; si uno termina después de la
		vista previa, la anula recién nacida."""
		operations = (APP_ROOT / "nexora/nexora/page/nexora_operations/nexora_operations.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("pendingFieldWork: Promise.resolve(),", operations)
		# La cadena se mantiene: cada cambio se encola detrás del anterior.
		self.assertIn("state.pendingFieldWork = state.pendingFieldWork", operations)
		self.assertIn(".then(() => fieldChanged(definition.fieldname))", operations)
		# Y la vista previa espera a que la cadena termine antes de leer los valores.
		preview = operations.split("async function previewMovement() {", 1)[1].split(
			"const errors = validateBeforePreview();", 1
		)[0]
		self.assertIn("await state.pendingFieldWork", preview)

	def test_the_walk_covers_the_four_surfaces_the_constitution_demands(self) -> None:
		"""Capítulo 54: escritorio, tableta, móvil y PWA. La tableta no es un escritorio
		estrecho ni un teléfono grande: es el ancho donde las rejillas cambian de columnas
		y donde la aplicación decide entre tabla y tarjetas."""
		smoke = SMOKE.read_text(encoding="utf-8")
		for surface, marker in (
			("escritorio", "viewport: { width: 1440, height: 900 }"),
			("tableta", 'devices["iPad (gen 7)"]'),
			("móvil", 'devices["iPhone 13"]'),
			("pwa", "{ pwa: true }"),
		):
			with self.subTest(surface=surface):
				self.assertIn(marker, smoke)
		# El nombre del job debe decir lo que recorre: un usuario que lee «escritorio ·
		# iPhone» no sabe que la tableta también está cubierta.
		workflow = (APP_ROOT.parent / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		self.assertIn("escritorio · tableta · iPhone · PWA", workflow)
		# Y el mensaje de desbordamiento nombra el perfil real, no siempre «iPhone».
		validators = VALIDATORS.read_text(encoding="utf-8")
		self.assertIn("Desbordamiento horizontal en ${profile.name}", validators)
		self.assertNotIn("`iPhone overflow", validators)

	def test_the_cause_is_printed_last_so_the_log_tail_still_carries_it(self) -> None:
		"""La herramienta que lee el registro de CI devuelve solo la cola. Lanzando el
		error, Node imprimía la traza detrás del mensaje y el motivo —qué campo faltaba,
		quién anuló la vista previa— caía fuera de la ventana visible: hubo que leer el
		fallo dos veces sin poder nombrarlo. Un diagnóstico que no se puede leer no
		diagnostica (Capítulo 51)."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("[nexora] CAUSA DEL FALLO", smoke)
		self.assertIn("report.error_message", smoke)
		# Relanzar volvería a poner la traza al final: el proceso falla por código.
		# El `catch` de más abajo es el del recorrido completo; el de `runProfile` sí
		# relanza a propósito, para que el perfil marque su fallo antes de subir.
		runner = smoke.rsplit("} catch (error) {", 1)[1]
		self.assertNotIn("throw error;", runner, "relanzar entierra la causa bajo la traza")
		self.assertIn("process.exitCode = 1;", runner)
		# Y el motivo se imprime después del volcado, no antes.
		tail = smoke.split("if (!report.ok) {", 1)[1]
		self.assertLess(
			tail.index("${report.error}"),
			tail.index("[nexora] CAUSA DEL FALLO"),
			"la causa es lo último que se lee",
		)
		# Imprimirla al final del paso no basta: detrás vienen la subida del artefacto y
		# el apagado de los contenedores, cien líneas que la empujan fuera de la ventana
		# que devuelve el lector de registros. El trabajo la repite de último.
		workflow = (APP_ROOT.parent / ".github/workflows/nexora-app.yml").read_text(encoding="utf-8")
		browser = workflow.split("name: Frappe real · escritorio · tableta", 1)[1]
		steps = [
			line.split("- name:", 1)[1].strip()
			for line in browser.splitlines()
			if line.strip().startswith("- name:")
		]
		self.assertEqual(
			"Repetir la causa del fallo al final del registro",
			steps[-1],
			"el motivo se repite cuando ya no queda nada detrás",
		)
		self.assertIn("if: failure()", browser.rsplit("- name:", 1)[1])

	def test_no_guided_action_is_clicked_where_something_else_can_cover_it(self) -> None:
		"""El recorrido nombró dos interceptores sobre «Continuar»: el formulario de
		búsqueda de la barra fija, por arriba, y la lista de sugerencias de un campo Link
		—«Create a new Currency»—, por abajo. Ninguno es del producto: los dos se resuelven
		centrando el botón antes de pulsarlo y cerrando la lista al terminar de escribir."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function clickGuidedAction(page, selector)", smoke)
		helper = smoke.split("async function clickGuidedAction(page, selector) {", 1)[1].split("\n}", 1)[0]
		self.assertIn('scrollIntoView({ block: "center"', helper)
		# Ningún clic del asistente puede saltarse el ayudante.
		raw = [
			line.strip()
			for line in smoke.splitlines()
			if ".click();" in line
			and ("guided-next" in line or "nxr-guided-preview" in line or "nxr-guided-execute" in line)
		]
		self.assertEqual([], raw, "todo botón del asistente se pulsa por `clickGuidedAction`")
		# Y al escribir en un campo Link la lista de sugerencias se cierra de verdad.
		field = smoke.split("async function setField(page, name, value) {", 1)[1].split("\n}", 1)[0]
		self.assertIn('await control.press("Escape");', field)
		self.assertIn(".awesomplete > ul", field)
		# Escape va antes de tabular: después vuelve a enfocar el campo y le borra el
		# valor. El recorrido lo mostró con `original_amount` vacío tras rellenarlo.
		self.assertLess(
			field.index('await control.press("Escape");'),
			field.index('await control.press("Tab");'),
			"Escape se pulsa con el campo aún enfocado, no después de tabular",
		)
		# Y el campo se comprueba en el momento: un dato que se pierde en silencio no se
		# descubre hasta que el asistente se niega a avanzar, y entonces ya no se sabe
		# quién lo vació.
		self.assertIn("no conservó lo que se escribió", field)
		# La barra fija deja de tapar la acción también fuera del recorrido. Se busca la
		# declaración dentro de su regla, no la palabra: el comentario que la explica
		# también la contiene, y buscarla suelta haría una guarda que no puede fallar.
		css = (APP_ROOT / "nexora/public/css/nexora_guided_operations.css").read_text(encoding="utf-8")
		rule = css.split(".nxr-guided-stage-actions,", 1)[1].split("}", 1)[0]
		self.assertIn("scroll-margin-top:", rule)


if __name__ == "__main__":
	unittest.main()
