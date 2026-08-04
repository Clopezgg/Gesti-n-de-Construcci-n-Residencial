from __future__ import annotations

import pathlib
import unittest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
CONTEXT = PACKAGE / "public/js/nexora_report_actions.js"
PAGES = PACKAGE / "nexora/page"

# Pantallas de trabajo con selector de proyecto propio. Si una de ellas ignora el
# contexto activo, el usuario vuelve a elegir el proyecto en cada salto y la barra
# global puede quedar mostrando un proyecto distinto al de la pantalla.
CONTEXT_AWARE_PAGES = ("nexora_dashboard", "nexora_operations", "nexora_reports")


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

	def test_working_pages_publish_the_project_they_select(self) -> None:
		"""Sin esto la barra global y la pantalla quedan contradiciéndose."""
		for page in ("nexora_operations", "nexora_reports"):
			with self.subTest(page=page):
				self.assertIn("setActiveProject", source(page))
		self.assertIn("window.nexora.context?.update", source("nexora_dashboard"))

	def test_working_pages_release_their_context_subscription(self) -> None:
		"""Un listener que sobrevive al wrapper recarga pantallas ya cerradas."""
		for page in ("nexora_operations", "nexora_reports"):
			with self.subTest(page=page):
				code = source(page)
				self.assertIn("onContextChange", code)
				self.assertRegex(
					code, r'\$\(wrapper\)\.on\("remove", \(\) => release\?\.\(\)\)|releaseContext\?\.\(\)'
				)

	def test_context_synchronisation_cannot_loop(self) -> None:
		"""Aplicar el contexto no debe volver a publicarlo."""
		operations = source("nexora_operations")
		self.assertIn("state.syncingProject = true", operations)
		self.assertIn("if (!state.syncingProject)", operations)
		reports = source("nexora_reports")
		self.assertIn("suppressControlReload = true", reports)
		self.assertIn("if (suppressControlReload) return;", reports)


if __name__ == "__main__":
	unittest.main()
