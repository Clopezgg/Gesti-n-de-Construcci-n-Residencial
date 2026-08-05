from __future__ import annotations

import pathlib
import re
import unittest

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = APP_ROOT.parent / "scripts"
SMOKE = SCRIPTS / "nexora_browser_smoke.mjs"
SUPPORT = SCRIPTS / "nexora_browser_support.mjs"


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


if __name__ == "__main__":
	unittest.main()
