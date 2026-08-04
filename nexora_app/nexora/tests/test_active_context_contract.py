from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
CONTEXT = PACKAGE / "public/js/nexora_report_actions.js"
PAGES = PACKAGE / "nexora/page"

# Pantallas de trabajo con selector de proyecto propio. Si una de ellas ignora el
# contexto activo, el usuario vuelve a elegir el proyecto en cada salto y la barra
# global puede quedar mostrando un proyecto distinto al de la pantalla.
CONTEXT_AWARE_PAGES = (
	"nexora_dashboard",
	"nexora_operations",
	"nexora_reports",
	"nexora_closing",
	"nexora_contracts",
	"nexora_purchase_requests",
	"nexora_evidence",
	"nexora_finance",
)

# Subconjunto añadido tras el bloque de fecha 2026-08-05: comparten el mismo patrón
# de guarda contra bucles (una bandera de sincronización local) en lugar del patrón
# original de nexora_operations/nexora_reports. Se listan con su bandera y su
# función de publicación para poder verificar el mismo contrato con nombres propios.
NEW_CONTEXT_AWARE_PAGES = {
	"nexora_closing": {"guard": "suppressReload", "publisher": "contextChanged"},
	"nexora_contracts": {"guard": "syncingProject", "publisher": "publishProject"},
	"nexora_purchase_requests": {"guard": "syncingProject", "publisher": "publishProject"},
	"nexora_evidence": {"guard": "syncingProject", "publisher": "contextChanged"},
	"nexora_finance": {"guard": "syncingProject", "publisher": "projectChanged"},
}

# Pantallas sin selector de proyecto propio: su dominio no está delimitado por
# proyecto (proveedores por entidad, cotizaciones por solicitud, directorio global
# de entidades, buscador universal por alcance). Forzar un filtro de proyecto ahí
# sería un campo sin uso real, no una propagación de contexto pendiente.
PROJECT_UNSCOPED_PAGES = ("nexora_suppliers", "nexora_quotations", "nexora_entities", "nexora_search")


def source(page: str) -> str:
	return (PAGES / page / f"{page}.js").read_text(encoding="utf-8")


class TestActiveContextContract(unittest.TestCase):
	def test_context_api_exposes_the_shared_project_helpers(self) -> None:
		code = CONTEXT.read_text(encoding="utf-8")
		published = code.split("window.nexora.context = Object.freeze({", 1)[1].split("});", 1)[0]
		for member in ("activeProject", "setActiveProject", "onContextChange"):
			with self.subTest(member=member):
				self.assertRegex(code, rf"\bfunction {member}\(")
				self.assertIn(f"{member},", published, "el helper debe publicarse en window.nexora.context")

	def test_set_active_project_does_not_reask_for_confirmation(self) -> None:
		"""El usuario ya actuó en la pantalla; volver a preguntar es fricción sin valor."""
		code = CONTEXT.read_text(encoding="utf-8")
		body = code.split("async function setActiveProject", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("skipConfirmation: true", body)
		self.assertIn("if (current === next) return", body, "no debe publicarse un cambio inexistente")

	def test_working_pages_inherit_the_active_project(self) -> None:
		for page in CONTEXT_AWARE_PAGES:
			with self.subTest(page=page):
				code = source(page)
				self.assertIn(
					"window.nexora.context",
					code,
					"la pantalla debe leer el contexto activo en lugar de pedir el proyecto otra vez",
				)
		# nexora_dashboard usa window.nexora.context.load()/.update() en vez de
		# activeProject()/setActiveProject(); el resto sigue el patrón compartido.
		for page in ("nexora_operations", "nexora_reports", *NEW_CONTEXT_AWARE_PAGES):
			with self.subTest(page=page):
				self.assertIn(
					"activeProject",
					source(page),
					"la pantalla debe heredar el proyecto activo al cargar, no solo publicarlo",
				)
		self.assertIn("window.nexora.context?.load?.(", source("nexora_dashboard"))

	def test_working_pages_publish_the_project_they_select(self) -> None:
		"""Sin esto la barra global y la pantalla quedan contradiciéndose."""
		for page in ("nexora_operations", "nexora_reports", *NEW_CONTEXT_AWARE_PAGES):
			with self.subTest(page=page):
				self.assertIn("setActiveProject", source(page))
		self.assertIn("window.nexora.context?.update", source("nexora_dashboard"))

	def test_working_pages_release_their_context_subscription(self) -> None:
		"""Un listener que sobrevive al wrapper recarga pantallas ya cerradas."""
		for page in ("nexora_operations", "nexora_reports", *NEW_CONTEXT_AWARE_PAGES):
			with self.subTest(page=page):
				code = source(page)
				self.assertIn("onContextChange", code)
				self.assertRegex(
					code, r'\$\(wrapper\)\.on\("remove", \(\) => release\?\.\(\)\)|releaseContext\?\.\(\)'
				)

	def test_context_handlers_cannot_leak_unhandled_rejections(self) -> None:
		"""Los suscriptores son asíncronos: un rechazo sin capturar aborta la
		sincronización y deja la pantalla a medio actualizar sin más rastro que un
		'unhandledrejection' en consola."""
		code = CONTEXT.read_text(encoding="utf-8")
		body = code.split("function onContextChange", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("Promise.resolve(handler(", body)
		self.assertIn(".catch(", body)
		self.assertIn("try {", body)
		for page, marker in (
			("nexora_reports", "startWithActiveProject().catch("),
			("nexora_operations", 'console.error("NEXORA operations failed to publish'),
			("nexora_closing", "initialize().catch("),
			("nexora_contracts", "initialize().catch("),
			("nexora_purchase_requests", "initialize().catch("),
			("nexora_evidence", "initialize().catch("),
			("nexora_finance", "loadCatalogs().catch("),
		):
			with self.subTest(page=page):
				self.assertIn(marker, source(page))

	def test_concurrent_writes_and_loads_discard_stale_results(self) -> None:
		"""Dos cambios rápidos de proyecto lanzan operaciones concurrentes. Sin un
		contador, la respuesta antigua pisa el contexto o mezcla las cuentas de un
		proyecto con el libro de otro."""
		context = CONTEXT.read_text(encoding="utf-8")
		body = context.split("async function setActiveProject", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("++contextState.writeSerial", body)
		self.assertIn("serial === contextState.writeSerial", body)

		operations = source("nexora_operations")
		load = operations.split("async function loadProjectData", 1)[1].split("\n\t}", 1)[0]
		self.assertIn("++state.projectSerial", load)
		self.assertIn("serial !== state.projectSerial", load)
		self.assertIn("controls.project.get_value() !== project", load)

	def test_operations_screen_survives_a_failed_initialisation(self) -> None:
		"""Si la carga inicial falla, la pantalla debe quedar utilizable en vez de
		congelarse en «cargando» sin explicación."""
		operations = source("nexora_operations")
		self.assertIn("initialize().catch(", operations)
		self.assertIn('attr("data-state", "ready")', operations)

	def test_context_synchronisation_cannot_loop(self) -> None:
		"""Aplicar el contexto no debe volver a publicarlo."""
		operations = source("nexora_operations")
		self.assertIn("state.syncingProject = true", operations)
		self.assertIn("if (!state.syncingProject)", operations)
		reports = source("nexora_reports")
		self.assertIn("suppressControlReload = true", reports)
		self.assertIn("if (suppressControlReload) return;", reports)

	def test_new_context_aware_pages_guard_their_programmatic_sync(self) -> None:
		"""Aplicar un cambio de contexto llegado de otra pantalla no debe volver a
		publicarlo: sin una bandera de sincronización, cada eco de la barra global
		dispararía otra escritura y un bucle de actualizaciones."""
		for page, spec in NEW_CONTEXT_AWARE_PAGES.items():
			with self.subTest(page=page):
				code = source(page)
				guard = spec["guard"]
				publisher = spec["publisher"]
				self.assertIn(
					f"{guard} = true",
					code,
					f"{page} debe activar una bandera antes de fijar el valor recibido del contexto",
				)
				self.assertIn(
					f"{guard} = false",
					code,
					f"{page} debe liberar la bandera de sincronización tras aplicar el valor",
				)
				self.assertRegex(
					code,
					rf"function {publisher}\(",
					f"{page} debe tener una función que publique el proyecto elegido por el usuario",
				)
				publisher_body = code.split(f"function {publisher}(", 1)[1].split("\n\t}", 1)[0]
				self.assertIn(
					f"if ({guard}) return",
					publisher_body,
					f"{page} no debe republicar un cambio que llegó del propio contexto activo",
				)
				self.assertIn("setActiveProject", publisher_body)

	def test_new_context_aware_pages_release_subscription_on_wrapper_remove(self) -> None:
		for page in NEW_CONTEXT_AWARE_PAGES:
			with self.subTest(page=page):
				code = source(page)
				self.assertIn('$(wrapper).on("remove", () => releaseContext?.());', code)

	def test_project_unscoped_pages_have_no_orphaned_project_filter(self) -> None:
		"""Estas pantallas no tienen selector de proyecto propio: no deben declarar
		un campo `project` a nivel de página que quede sin conectar al contexto
		activo ni a ningún filtro real."""
		for page in PROJECT_UNSCOPED_PAGES:
			with self.subTest(page=page):
				code = source(page)
				self.assertNotIn(
					'fieldname: "project"',
					code.split("on_page_load", 1)[-1].split("$(page.body).append", 1)[0],
					f"{page} no debería ganar un filtro de proyecto a nivel de página: "
					"su dominio no está delimitado por proyecto",
				)


if __name__ == "__main__":
	unittest.main()
