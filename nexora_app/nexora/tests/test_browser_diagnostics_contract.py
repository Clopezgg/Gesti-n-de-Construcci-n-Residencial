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

	def test_the_correction_dialog_survives_the_blur_of_its_own_button(self) -> None:
		"""Mismo defecto, otro sitio. Pulsar el botón del pie quita el foco al campo que se
		acababa de escribir, Frappe emite `change` por ese blur y la vista previa válida se
		anulaba justo en ese instante: el botón volvía a decir «Vista previa» y la pulsación
		con la que el usuario quería registrar se gastaba en repetir la validación. El
		recorrido real lo vio en iPhone —«la pantalla nunca pidió el registro definitivo de
		la corrección»—, que es donde se escribe el motivo y se pulsa a continuación sin
		tocar nada más."""
		flows = (APP_ROOT / "nexora/public/js/nexora_quick_flows.js").read_text(encoding="utf-8")
		self.assertIn("const invalidate = (fieldname) => {", flows)
		body = flows.split("const invalidate = (fieldname) => {", 1)[1].split("\n\t\t};", 1)[0]
		self.assertIn('const current = String(dialog.get_value(fieldname) ?? "");', body)
		self.assertIn(
			"if (seen.get(fieldname) === current) return;",
			body,
			"solo un valor distinto puede anular la vista previa",
		)
		# La salida temprana decide antes de tocar nada: al revés no protegería.
		self.assertLess(
			body.index("if (seen.get(fieldname) === current) return;"),
			body.index("state.preview = null;"),
		)
		# Sin línea base, el primer aviso de cada campo compara contra `undefined` y cuenta
		# como cambio aunque el valor sea el mismo: enfocar y desenfocar el comprobante sin
		# adjuntar nada bastaba para perder una vista previa válida.
		self.assertIn('const TRACKED = ["requester", "approved_by", "reason", "evidence"];', flows)
		self.assertIn("const remember = () => {", flows)
		opener = flows.split('dialog.set_primary_action(__("Vista previa"), preview);', 1)[1]
		self.assertIn("remember();", opener.split("\n\t}", 1)[0], "la línea base se toma al abrir")
		accepted = flows.split("state.preview = response.message;", 1)[1].split("\n\t\t\t}", 1)[0]
		self.assertIn("remember();", accepted, "y se renueva con cada vista previa aceptada")
		# Y ningún campo puede quedarse sin declarar cuál es: `onchange: invalidate` a secas
		# pasaría `undefined` y volvería a anular siempre. Se comprueba dentro del bloque de
		# cada campo: buscar las cuatro cadenas sueltas dejaría pasar dos callbacks
		# intercambiados, que anularían el campo equivocado.
		self.assertNotIn("onchange: invalidate,", flows)
		for fieldname in ("requester", "approved_by", "reason", "evidence"):
			with self.subTest(fieldname=fieldname):
				block = flows.split(f'fieldname: "{fieldname}",', 1)[1].split("\n\t\t\t\t},", 1)[0]
				self.assertIn(f'onchange: () => invalidate("{fieldname}"),', block)

	def test_the_operational_correction_dialog_survives_the_blur_of_its_own_button(self) -> None:
		"""Tercer sitio con el mismo defecto que el diálogo hermano de corrección rápida:
		nueve campos usaban `onchange: invalidate` a secas, sin línea base ni comparación,
		así que cualquier blur —incluido el que provoca pulsar el botón del pie del
		diálogo— anulaba la vista previa vigente. El recorrido real lo encontró en iPhone
		sobre la etapa `correccion`: «la pantalla nunca pidió la aplicación de la
		corrección de datos» en 120 s."""
		operational = (APP_ROOT / "nexora/public/js/nexora_operational_ui.js").read_text(encoding="utf-8")
		self.assertIn("const invalidate = (fieldname) => {", operational)
		body = operational.split("const invalidate = (fieldname) => {", 1)[1].split("\n\t\t};", 1)[0]
		self.assertIn('const current = String(dialog.get_value(fieldname) ?? "");', body)
		self.assertIn(
			"if (seen.get(fieldname) === current) return;",
			body,
			"solo un valor distinto puede anular la vista previa",
		)
		self.assertLess(
			body.index("if (seen.get(fieldname) === current) return;"),
			body.index("state.preview = null;"),
		)
		tracked_fields = (
			"source_name",
			"document_date",
			"currency",
			"original_amount",
			"exchange_rate",
			"channel",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
			"reason",
			"evidence",
		)
		self.assertIn("const TRACKED = [", operational)
		tracked_block = operational.split("const TRACKED = [", 1)[1].split("];", 1)[0]
		for fieldname in tracked_fields:
			with self.subTest(fieldname=fieldname):
				self.assertIn(f'"{fieldname}"', tracked_block)
		self.assertIn("const remember = () => {", operational)
		# La línea base se toma al terminar de cargar el documento —momento en el que los
		# campos quedan en un estado válido conocido— y se renueva con cada vista previa
		# aceptada.
		loaded = operational.split('dialog.set_primary_action(__("Vista previa"), previewCorrection);', 1)[1]
		self.assertIn(
			"remember();",
			loaded.split("\n\t\t\t} finally {", 1)[0],
			"la línea base se toma al cargar el documento",
		)
		accepted = operational.split("state.preview = response.message;", 1)[1].split(
			"\n\t\t\tdialog.fields_dict.preview_html", 1
		)[0]
		self.assertIn("remember();", accepted, "y se renueva con cada vista previa aceptada")
		# Ningún campo puede quedarse con `onchange: invalidate` a secas: pasaría
		# `undefined` como nombre de campo y compararía siempre contra el valor
		# equivocado. Se comprueba dentro del bloque de cada campo, no solo su ausencia
		# global, para no dejar pasar dos callbacks intercambiados.
		self.assertNotIn("onchange: invalidate,", operational)
		for fieldname in tracked_fields:
			with self.subTest(fieldname=fieldname):
				block = operational.split(f'fieldname: "{fieldname}",', 1)[1].split("\n\t\t\t\t},", 1)[0]
				self.assertIn(f'invalidate("{fieldname}")', block)

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
		# La fuente elegida sigue la misma regla: una sola invalidación, nombrada.
		# (Bloque 38: un gasto paga desde una sola fuente — el input de importe por
		# fuente se volvió un radio de selección, pero el invariante es el mismo.)
		listener = operations.split('body.on("change", ".nxr-source-radio"', 1)[1].split("\n\t});", 1)[0]
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
		# Y busca el informe donde el recorrido lo escribe. Con la ruta equivocada el paso
		# afirmaba «falló antes de arrancar» sobre un informe que sí existía: un
		# diagnóstico que miente es peor que no tenerlo.
		directory = browser.split("BROWSER_ARTIFACT_DIR=", 1)[1].split()[0]
		self.assertIn(
			f"report={directory}/nexora-browser-report.json",
			browser,
			"el paso final lee el informe en la carpeta que recibe el recorrido",
		)

	def test_no_guided_action_is_clicked_where_something_else_can_cover_it(self) -> None:
		"""El recorrido nombró dos interceptores sobre «Continuar»: el formulario de
		búsqueda de la barra fija, por arriba, y la lista de sugerencias de un campo Link
		—«Create a new Currency»—, por abajo. Ninguno es del producto: los dos se resuelven
		centrando el botón antes de pulsarlo y cerrando la lista al terminar de escribir."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function clickGuidedAction(page, selector)", smoke)
		helper = smoke.split("async function clickGuidedAction(page, selector) {", 1)[1].split("\n}", 1)[0]
		self.assertIn('scrollIntoView({ block: "center"', helper)
		# Centrar no bastó: el registro mostró el formulario de búsqueda y el «Create a
		# new Currency» interceptando el mismo clic ya centrado. Se cierra la lista y se
		# pulsa con el teclado, que ningún elemento dibujado encima puede interceptar.
		self.assertIn("document.activeElement?.blur?.()", helper)
		self.assertIn(".awesomplete > ul", helper)
		self.assertIn('await action.press("Enter");', helper)
		self.assertNotIn("await action.click();", helper)
		# Un clic espera a que el botón esté habilitado; `focus` + `Enter` no espera nada
		# y sobre un botón deshabilitado no hace nada en absoluto. Sin esta espera se
		# perdió una ejecución entera: el registro definitivo nunca se pidió y el fallo
		# apareció como un tiempo de espera en la llamada, no en el botón mudo.
		self.assertIn("!node.disabled", helper)
		self.assertIn("seguía deshabilitado", helper)

	def test_each_flow_names_its_own_call(self) -> None:
		"""Tres flujos piden el mismo método. «La pantalla nunca pidió el registro
		definitivo» no dice si fue el del ingreso, el del gasto o el de la corrección."""
		smoke = SMOKE.read_text(encoding="utf-8")
		for label in (
			"vista previa del ingreso",
			"registro definitivo del ingreso",
			"vista previa del gasto",
			"registro definitivo del gasto",
			"vista previa de la corrección",
			"registro definitivo de la corrección",
		):
			with self.subTest(label=label):
				self.assertIn(f'"{label}"', smoke)
		self.assertNotIn('"registro definitivo del movimiento"', smoke)
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
		# `setField` ya no pulsa Escape: la lista la cierra `clickGuidedAction` antes de
		# pulsar, y en un campo Link cerrar la lista con Escape impide seleccionar la
		# opción, así que Frappe descartaba al perder el foco lo que no se validó. El
		# recorrido lo mostró con `project` vacío justo antes de continuar.
		self.assertNotIn('await control.press("Escape");', field)
		self.assertIn('await control.press("Tab");', field)
		# Y el campo se comprueba en el momento: un dato que se pierde en silencio no se
		# descubre hasta que el asistente se niega a avanzar, y entonces ya no se sabe
		# quién lo vació.
		self.assertIn("no conservó lo que se escribió", field)
		# En móvil el asistente reordena los campos y un control repintado pierde lo
		# escrito. Se reescribe una vez —lo que hace cualquiera al ver el campo en
		# blanco— y queda constancia; rendirse al primer intento convertía un repintado
		# en un fallo del producto.
		self.assertIn("incluso tras reescribirlo", field)
		self.assertIn("se vació al escribirlo y hubo que reescribirlo", field)
		# Reescribir una vez, no en bucle: un campo que nunca se queda es un defecto real
		# y tiene que salir a la luz.
		self.assertEqual(1, field.count("rewritten = true;"))
		# La barra fija deja de tapar la acción también fuera del recorrido. Se busca la
		# declaración dentro de su regla, no la palabra: el comentario que la explica
		# también la contiene, y buscarla suelta haría una guarda que no puede fallar.
		css = (APP_ROOT / "nexora/public/css/nexora_guided_operations.css").read_text(encoding="utf-8")
		rule = css.split(".nxr-guided-stage-actions,", 1)[1].split("}", 1)[0]
		self.assertIn("scroll-margin-top:", rule)

	def test_no_assertion_demands_a_table_the_mobile_design_hides(self) -> None:
		"""Capítulo 37: en el ancho del teléfono las pantallas sustituyen la tabla por
		tarjetas y la ocultan. Exigir la fila visible hacía fallar el perfil de iPhone
		sobre un diseño correcto —la fila existía y estaba oculta—, primero en el panel y
		después en la búsqueda universal. Es el mismo defecto dos veces (Capítulo 36)."""
		smoke = SMOKE.read_text(encoding="utf-8")
		search = smoke.split("async function validateUniversalSearch(", 1)[1].split("\nasync function", 1)[0]
		self.assertIn(".nxr-mobile-cards article:visible", search)
		self.assertIn("tbody tr:visible", search)
		# El panel resolvió lo mismo antes: ninguna de las dos puede volver a exigir solo
		# la tabla.
		validators = VALIDATORS.read_text(encoding="utf-8")
		self.assertIn(".nxr-mobile-cards", validators)

	def test_every_api_wait_says_which_call_it_was_waiting_for(self) -> None:
		"""«Timeout … waiting for event "response"» no dice qué llamada se esperaba, y el
		recorrido tiene ocho. Un fallo así obliga a adivinar entre «la pantalla no pidió
		la vista previa» y «no pidió el detalle de la búsqueda» (Capítulo 51).

		`apiResponse` vive en `nexora_browser_support.mjs` (no en `nexora_browser_smoke.mjs`)
		desde la corrección del bug real de promesa huérfana que mataba el proceso
		completo de CI (`Target page, context or browser has been closed`, confirmado en
		dos ramas independientes): reubicarla permite importarla de forma aislada en
		`nexora_browser_support.test.mjs` sin arrastrar los efectos de nivel de módulo del
		script principal. El criterio de este test no cambia — cada espera de red sigue
		exigiendo pasar, con nombre, por el único ayudante — solo el archivo donde vive."""
		smoke = SMOKE.read_text(encoding="utf-8")
		support = SUPPORT.read_text(encoding="utf-8")
		self.assertIn("export function apiResponse(page, fragment, label)", support)
		self.assertIn("La pantalla nunca pidió", support)
		self.assertIn("apiResponse,", smoke, "el recorrido debe importar apiResponse del módulo compartido")
		# Ninguna espera puede quedarse sin nombre: `page.waitForResponse` sólo aparece
		# dentro del ayudante, nunca directamente en el recorrido.
		self.assertEqual(
			0,
			smoke.count("page\n    .waitForResponse(") + smoke.count("page.waitForResponse("),
			"el recorrido no debe llamar a waitForResponse directamente, solo vía apiResponse",
		)
		self.assertEqual(
			1,
			support.count("page\n    .waitForResponse(") + support.count("page.waitForResponse("),
			"todas las esperas pasan por `apiResponse`",
		)
		# El número de esperas crece con el recorrido —el Capítulo 53 pide ocho
		# operaciones—, así que fijarlo en una constante solo garantizaba tener que
		# actualizarla. Lo que no puede cambiar es que ninguna quede sin nombre.
		text = r'(?:"[^"]+"|`[^`]+`)'
		labelled = re.findall(rf"apiResponse\(\s*page,\s*{text},\s*{text}\s*\)", smoke, re.DOTALL)
		# Contar apariciones del texto incluiría comentarios y cadenas: un comentario que
		# escribiera `apiResponse(` haría fallar el test culpando a una espera sin nombre
		# que no existe, que es lo contrario del propósito de este archivo.
		callsites = len(re.findall(r"(?<!function )apiResponse\(\s*page\b", smoke))
		self.assertEqual(
			callsites,
			len(labelled),
			"cada espera de red pasa por `apiResponse` con su fragmento y su nombre",
		)
		# Un umbral numérico vuelve a acoplar el contrato a una cifra: una refactorización
		# legítima que funda dos esperas fallaría sin decir qué operación falta. Lo que hay
		# que exigir es que cada llamada del Capítulo 53 siga estando esperada por nombre.
		for endpoint in (
			"preview_operational_movement",
			"execute_operational_movement",
			"universal_search_consolidated",
			"get_search_result_detail",
			"get_operation_for_correction",
			"preview_operation_correction",
			"execute_operation_correction",
			"register_evidence",
			"review_evidence",
		):
			with self.subTest(endpoint=endpoint):
				self.assertRegex(
					smoke,
					rf'apiResponse\(\s*page,\s*"{endpoint}",\s*{text}\s*\)',
					"esta llamada dejó de esperarse con nombre",
				)

	def test_the_walk_checks_its_fields_again_right_before_advancing(self) -> None:
		"""Un campo puede conservar el valor al escribirlo y perderlo después: los Link de
		Frappe validan contra el servidor y descartan lo que no llegó a confirmarse.
		Comprobarlo al avanzar convierte «la etapa 2 nunca se abrió» en «el campo project
		se vació entre que se escribió y el momento de continuar»."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function assertWrittenFieldsHeld(page)", smoke)
		self.assertIn("se vaciaron entre que se escribieron", smoke)
		# Y se llama antes de cada «Continuar», no solo se define.
		for block in smoke.split("await clickGuidedAction(page, '[data-guided-next=\"2\"]');")[:-1]:
			with self.subTest(call=block[-120:]):
				self.assertTrue(
					block.rstrip().endswith("await assertWrittenFieldsHeld(page);"),
					"cada avance de etapa comprueba antes lo que se escribió",
				)

	def test_every_failure_says_which_profile_it_happened_in(self) -> None:
		"""«La pantalla nunca pidió la vista previa» no dice si fue en escritorio, en
		tableta o en el teléfono, y son tres correcciones distintas. El perfil se perdía
		al subir el error."""
		smoke = SMOKE.read_text(encoding="utf-8")
		catch = smoke.split('profile.status = "failed";', 1)[1].split("} finally {", 1)[0]
		self.assertIn("`[${name}] ${message}`", catch)
		self.assertNotIn("throw error;", catch, "relanzar tal cual pierde el perfil")

	def test_the_walk_reports_every_failure_instead_of_the_first(self) -> None:
		"""Abortar en la primera avería convertía cada ejecución de CI —ocho minutos— en un
		solo dato: se corregía un defecto y la siguiente ejecución revelaba el siguiente,
		escondido detrás. Nueve rondas seguidas se gastaron así."""
		smoke = SMOKE.read_text(encoding="utf-8")
		# Cada etapa se ejecuta y se registra por separado.
		self.assertIn("const step = async (id, fn, { needs = [] } = {})", smoke)
		registered = smoke.split("const step = async (id, fn, { needs = [] } = {})", 1)[1].split("\n  };", 1)[
			0
		]
		for status in ('status: "passed"', 'status: "failed"', 'status: "skipped"'):
			with self.subTest(status=status):
				self.assertIn(status, registered)
		# Las dependencias se declaran: lo que depende de otra etapa se salta diciendo por
		# qué, en vez de fallar por arrastre y ensuciar el diagnóstico. Se comprueba etapa
		# por etapa, no que la palabra aparezca en algún sitio.
		for dependent in ("busqueda", "correccion"):
			with self.subTest(stage=dependent):
				call = smoke.split(f'await step(\n      "{dependent}",', 1)
				self.assertEqual(2, len(call), f"la etapa {dependent} debe declararse con `step`")
				self.assertIn('{ needs: ["operaciones"] }', call[1].split(");", 1)[0])
		# Y al final se reportan todas juntas.
		self.assertIn("etapa(s) sin superar", smoke)
		# Los tres perfiles se recorren siempre: un perfil roto no puede esconder los otros.
		self.assertIn("const profileRuns = [", smoke)
		runner = smoke.split("const profileRuns = [", 1)[1]
		self.assertIn("failures.push(", runner)
		self.assertIn("failures.join(", runner)

	def test_the_dialog_button_is_waited_for_like_the_wizard_ones(self) -> None:
		"""Pulsar un botón deshabilitado no hace nada, y el fallo aparece 120 s después en
		la llamada que nunca se pidió, no en el botón mudo. Ya pasó con el registro
		definitivo del asistente; el diálogo de anulación tenía el mismo agujero
		(Capítulo 36)."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function clickDialogPrimary(dialog, page, label)", smoke)
		self.assertIn("seguía deshabilitado a los 60 s", smoke)
		# Ningún botón de diálogo se pulsa ya directamente.
		self.assertNotIn('.locator(".modal-footer .btn-primary").click();', smoke)

	def test_the_evidence_review_selector_tracks_the_screens_own_component_classes(self) -> None:
		"""El recorrido buscaba el botón «Validar»/«Rechazar» por sus clases de Bootstrap
		(`.btn-success`/`.btn-danger`). El Bloque D migró esas dos pantallas a
		`nxr-ds-btn--success`/`nxr-ds-btn--danger` y el recorrido dejó de encontrar el
		botón: no porque el producto se rompiera, sino porque el propio recorrido seguía
		mirando el nombre antiguo. La comprobación de una pantalla no puede sobrevivir a
		un cambio de vocabulario visual si sigue citando el vocabulario viejo."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("nxr-ds-btn--${", smoke)
		self.assertNotIn(".btn-${", smoke)
		self.assertNotIn(".nxr-review-fields .btn-", smoke)

	def test_full_page_captures_account_for_device_pixel_ratio(self) -> None:
		"""El límite del motor para una captura (32767 px) es en píxeles de *dispositivo*,
		no en píxeles CSS. Un umbral fijo en CSS solo es seguro a densidad 1x: el perfil
		`iphone-13-webkit` captura a 3x, así que una altura CSS de apenas 11 000 px ya
		produce un lienzo de más de 32767 píxeles reales, y un umbral de 30 000 pensado
		para escritorio nunca llegaba a activarse en el perfil que más lo necesitaba. El
		recorrido real lo mostró así: «page.screenshot: Cannot take screenshot larger
		than 32767 pixels» sustituyendo el resultado real de la etapa `operaciones`.

		`capture` vive en `nexora_browser_support.mjs`, no en el smoke test donde
		nació: la auditoría visual de los módulos prioritarios
		(`validateModuleGallery`, `nexora_browser_validators.mjs`) también necesita
		capturar pantalla, y el arnés de soporte es lo único que ambos archivos ya
		importan sin crear un ciclo entre ellos."""
		support = SUPPORT.read_text(encoding="utf-8")
		self.assertIn("export async function capture(page, profile, file) {", support)
		body = support.split("export async function capture(page, profile, file) {", 1)[1].split("\n}", 1)[0]
		self.assertIn("window.devicePixelRatio || 1", body)
		self.assertIn("Math.floor(32_767 / scale)", body)
		self.assertNotIn("height > 30_000", body)
		# Y la captura del panel usa la misma función guardada, no una llamada cruda que
		# no comprueba nada antes de pedir la página entera.
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertNotIn("fullPage: true,\n      });", smoke)

	def test_dashboard_capture_goes_through_the_guarded_helper(self) -> None:
		smoke = SMOKE.read_text(encoding="utf-8")
		panel = smoke.split('await step("panel", async () => {', 1)[1].split("\n    });", 1)[0]
		self.assertIn("await capture(", panel)
		self.assertNotIn("await page.screenshot(", panel)

	def test_a_stuck_export_toolbar_says_why_not_just_timeout(self) -> None:
		"""`nexora_tables.js` decide si la barra de exportación se ve mirando
		`table.getClientRects().length` (la misma lectura que un `Timeout` no puede
		distinguir de «la tabla nunca llegó a mejorarse»). El recorrido real lo mostró
		como `Timeout 60000ms exceeded` sobre `.nxr-table-export`, resuelto pero oculto
		124 veces seguidas, sin decir cuál de las dos causas era. Esta guarda exige que el
		fallo reproduzca la misma lectura que decide la visibilidad, no solo que exista."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function exportToolbarDiagnostics(page)", smoke)
		diagnostics = smoke.split("async function exportToolbarDiagnostics(page) {", 1)[1].split(
			"\nasync function validateExportSurfaces", 1
		)[0]
		self.assertIn("table.getClientRects().length", diagnostics)
		self.assertIn("bar.hidden", diagnostics)
		self.assertIn("nxrTableEnhanced", diagnostics)
		export_fn = smoke.split("async function validateExportSurfaces(page, context, profile, name) {", 1)[1]
		self.assertIn("exportToolbarDiagnostics(page)", export_fn)
		# El diagnóstico se pide dentro del manejador de error, no antes: pedirlo antes
		# describiría un estado que ya cambió para cuando el fallo se registra.
		self.assertLess(
			export_fn.index("} catch (error) {"),
			export_fn.index("exportToolbarDiagnostics(page)"),
		)

	def test_pwa_validation_runs_on_the_two_real_webkit_profiles_too(self) -> None:
		"""`validatePwa` (registro del service worker, caché offline, aviso sin conexión)
		solo se pedía en `desktop-chromium` (`{ pwa: true }`); `ipad-gen7-webkit` e
		`iphone-13-webkit` — los dos perfiles que corren sobre el motor WebKit real, el
		que importa para "PWA/iPhone" — nunca llegaban a `step("pwa", ...)`: solo pasaban
		por `validateManifest`, que ni registra ni comprueba el service worker. La
		afirmación "PWA segura en iPhone" nunca se había probado contra un motor WebKit
		real, solo contra Chromium de escritorio."""
		smoke = SMOKE.read_text(encoding="utf-8")
		runner = smoke.split("const profileRuns = [", 1)[1].split("\n];", 1)[0]
		rows = runner.split("\n  [")[1:]
		self.assertEqual(3, len(rows), "se esperan exactamente tres perfiles registrados")
		for profile_name in ("desktop-chromium", "ipad-gen7-webkit", "iphone-13-webkit"):
			with self.subTest(profile=profile_name):
				row = next(row for row in rows if f'"{profile_name}"' in row)
				self.assertIn(
					"{ pwa: true }",
					row,
					f"{profile_name} no pide validatePwa: el service worker y la caché "
					"offline nunca se comprueban en ese motor.",
				)

	def test_the_command_bar_shortcut_is_walked_for_real(self) -> None:
		"""NXR-UX-0008: la paleta de comandos (Ctrl+K/Cmd+K) no tenía ninguna etapa
		real de navegador que la abriera, filtrara y navegara — quedaría marcada
		NO DEMOSTRADO para siempre si nadie la ejercitara contra un sitio real."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn('await step("paleta", async () => {', smoke)
		step_body = smoke.split('await step("paleta", async () => {', 1)[1].split("\n    });", 1)[0]
		self.assertIn("validateCommandBar(page, profile)", step_body)
		self.assertIn('gotoRoute(page, context, profile, "nexora-dashboard")', step_body)
		validators = VALIDATORS.read_text(encoding="utf-8")
		self.assertIn("export async function validateCommandBar(page, profile) {", validators)
		body = validators.split("export async function validateCommandBar(page, profile) {", 1)[1].split(
			"\n}", 1
		)[0]
		self.assertIn("page.keyboard.press(`${modifier}+k`)", body)
		self.assertIn('input.fill("Reportes")', body)
		self.assertIn('page.keyboard.press("Enter")', body)
		self.assertIn('waitForRoute(page, "nexora-reports")', body)
		self.assertIn('page.keyboard.press("Escape")', body)

	def test_dialog_fields_are_checked_for_what_they_actually_kept(self) -> None:
		"""`fillDialogField` es lo único que rellena los diálogos genéricos de
		Frappe (`frappe.prompt`) — incluido el que conecta WhatsApp — y hasta
		ahora confiaba en que `fill()+Tab` se quedó, sin comprobarlo. Frappe
		valida los campos obligatorios de un `frappe.prompt` en el momento del
		clic sobre el botón principal: si uno quedó vacío por un repintado o
		una carrera de foco, el envío se bloquea sin ningún error de página, y
		el fallo aparece 120 s después como un timeout sin nombre en la
		petición que dependía de él (`whatsapp.connect_credential` es el caso
		real que lo mostró). Mismo patrón que `setField` ya prueba para
		`nexora-operations`, aplicado aquí al diálogo genérico."""
		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn("async function fillDialogField(dialog, fieldname, value) {", smoke)
		body = smoke.split("async function fillDialogField(dialog, fieldname, value) {", 1)[1].split(
			"\n}", 1
		)[0]
		self.assertIn("control.inputValue()", body, "debe releer lo que el control conservó")
		self.assertIn(
			"stored !== value",
			body,
			"debe comparar contra lo que se pidió escribir, no asumir que se quedó",
		)
		self.assertIn(
			"await control.fill(value)",
			body.split("stored !== value", 1)[1],
			"debe reintentar una vez si el valor no se quedó, igual que setField",
		)
		self.assertIn(
			"stored === value",
			body,
			"debe fallar de forma explícita, nombrando el campo, si ni reescribiendo se queda",
		)
		self.assertIn("fieldname", body.split("assert(", 1)[1].split(");", 1)[0])

	def test_the_module_gallery_captures_every_priority_screen(self) -> None:
		"""Fase de auditoría visual pedida por el propietario: Fondos, Entidades,
		Contratos, Compras (solicitudes, cotizaciones y proveedores son tres
		pantallas reales, no una) y Proyecto 360° no tenían ninguna captura real
		en el recorrido — Entidades y Proyecto 360° ni siquiera estaban en
		`routes`, así que nunca se comprobaba que abrieran. Sin esta etapa,
		cualquier rediseño de esas pantallas se haría sin evidencia visual real,
		exactamente lo que se pidió no hacer."""
		validators = VALIDATORS.read_text(encoding="utf-8")
		self.assertIn(
			"export async function validateModuleGallery(page, context, profile, name) {",
			validators,
		)
		body = validators.split(
			"export async function validateModuleGallery(page, context, profile, name) {", 1
		)[1].split("\n}", 1)[0]
		for route in (
			"nexora-finance",
			"nexora-entities",
			"nexora-contracts",
			"nexora-purchase-requests",
			"nexora-quotations",
			"nexora-suppliers",
			"nexora-project",
		):
			with self.subTest(route=route):
				self.assertIn(f'route: "{route}"', body)
		self.assertIn("capture(", body)
		# Espera por condición real entre navegar y capturar, no un tiempo fijo.
		self.assertIn("waitForLoadState(", body)
		self.assertIn('.waitFor({ state: "visible"', body)

		smoke = SMOKE.read_text(encoding="utf-8")
		self.assertIn('await step("galeria-modulos",', smoke)
		self.assertIn("validateModuleGallery(page, context, profile, name)", smoke)

	def test_the_reports_stage_also_captures_the_active_report(self) -> None:
		validators = VALIDATORS.read_text(encoding="utf-8")
		body = validators.split("export async function validateReports(page, context, profile, name) {", 1)[
			1
		].split("\nexport async function", 1)[0]
		self.assertIn("capture(", body)


if __name__ == "__main__":
	unittest.main()
