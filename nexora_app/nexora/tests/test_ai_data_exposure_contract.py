"""Bloque 20 — IA operacional: ninguna llamada al orquestador envía datos no
autorizados a un proveedor externo.

La auditoría de este bloque confirmó (por lectura exhaustiva, no inferencia) que
solo existen dos llamadores reales de ``nexora.intelligence.orchestrator.execute``
en todo el código de la app: ``conversation/nlu.py`` (Bloque 18 — envía únicamente
el texto del usuario, su propio historial de conversación y el catálogo estático de
intenciones, nunca datos financieros reales) y
``intelligence/service.py::run_orchestrated_request`` (el panel admin de "probar
conexión" — envía únicamente una cadena de prueba, nunca datos del negocio). Esta
prueba fija ambos hechos: si un futuro cambio agrega un tercer llamador, o si
``conversation/nlu.py`` empieza a incluir el resultado de una consulta real en el
payload que se manda al proveedor, esta prueba debe fallar.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


def _orchestrator_call_lines(path: Path) -> list[int]:
	"""Return call sites bound to the public orchestrator, regardless of aliases."""
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	execute_names: set[str] = set()
	module_names: set[str] = set()

	for node in ast.walk(tree):
		if isinstance(node, ast.ImportFrom):
			module = node.module or ""
			for imported in node.names:
				if module == "nexora.intelligence.orchestrator" and imported.name in {"execute", "*"}:
					execute_names.add(imported.asname or imported.name)
				if module == "nexora.intelligence" and imported.name == "orchestrator":
					module_names.add(imported.asname or imported.name)
		elif isinstance(node, ast.Import):
			for imported in node.names:
				if imported.name == "nexora.intelligence.orchestrator":
					module_names.add(imported.asname or "nexora")

	def dotted_name(expression: ast.AST) -> str | None:
		parts: list[str] = []
		while isinstance(expression, ast.Attribute):
			parts.append(expression.attr)
			expression = expression.value
		if isinstance(expression, ast.Name):
			parts.append(expression.id)
			return ".".join(reversed(parts))
		return None

	hits: list[int] = []
	for node in ast.walk(tree):
		if not isinstance(node, ast.Call):
			continue
		if isinstance(node.func, ast.Name) and node.func.id in execute_names:
			hits.append(node.lineno)
		elif isinstance(node.func, ast.Attribute) and node.func.attr == "execute":
			base = dotted_name(node.func.value)
			if base in module_names or base == "nexora.intelligence.orchestrator":
				hits.append(node.lineno)
	return hits


APP_ROOT = Path(__file__).resolve().parents[1]


def _all_python_sources() -> list[Path]:
	return [
		path
		for path in APP_ROOT.rglob("*.py")
		if "tests" not in path.parts and "__pycache__" not in path.parts
	]


class TestOnlyKnownCallersReachTheOrchestrator(unittest.TestCase):
	def test_exactly_two_real_callers_exist(self) -> None:
		hits: list[str] = []
		for path in _all_python_sources():
			for line in _orchestrator_call_lines(path):
				hits.append(f"{path.relative_to(APP_ROOT)}:{line}")
		self.assertEqual(
			sorted(hits),
			sorted(
				[
					"conversation/nlu.py:90",
					"intelligence/service.py:604",
				]
			),
			"un llamador nuevo del orquestador de IA debe auditarse antes de aceptarse "
			"(¿envía datos que el usuario no está autorizado a consultar?)",
		)


class TestConversationalNluPayloadNeverCarriesQueryResults(unittest.TestCase):
	"""El motor conversacional interpreta ANTES de consultar cualquier dato real
	(ver `dispatch.py`: `nlu.interpret()` corre antes de `_invoke_read`/
	`_run_write_preview`) — nunca al revés. Esta prueba fija esa separación:
	``interpret()`` solo puede construir su payload a partir del texto, el
	historial y el catálogo estático, nunca de un resultado de consulta."""

	def source(self) -> str:
		return (APP_ROOT / "conversation/nlu.py").read_text(encoding="utf-8")

	def test_interpret_only_sends_text_history_and_the_static_catalog(self) -> None:
		source = self.source()
		body = source[source.index("def interpret(") :]
		forbidden = (
			"_invoke_read",
			"_run_write",
			"preview_",
			"execute_",
			"list_source_balances",
			"get_contract",
		)
		for token in forbidden:
			self.assertNotIn(token, body, f"interpret() no debe conocer resultados de dominio ({token!r})")

	def test_payload_sent_to_the_provider_is_built_only_from_prompt_history_and_text(self) -> None:
		source = self.source()
		self.assertIn('payload = {\n\t\t"messages": messages,\n\t\t"prompt":', source)


if __name__ == "__main__":
	unittest.main()
