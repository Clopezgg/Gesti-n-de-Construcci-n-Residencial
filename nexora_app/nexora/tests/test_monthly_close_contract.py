from __future__ import annotations

import inspect
import json
import pathlib

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestMonthlyCloseContract:
	def test_monthly_close_has_historical_snapshot_fields(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_monthly_close/nxr_monthly_close.json"
		payload = json.loads(path.read_text(encoding="utf-8"))
		fields = {field["fieldname"] for field in payload["fields"]}
		assert {
			"period_key",
			"total_reserved_hnl",
			"total_committed_hnl",
			"total_available_hnl",
			"budget_available_hnl",
			"physical_progress",
			"snapshot_json",
			"snapshot_hash",
			"engine_version",
			"correction_of",
			"correction_reason",
		} <= fields

	def test_monthly_close_is_routed_to_canonical_service(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		assert "nexora.close.service.create_monthly_close" in hooks
		assert "nexora.close.monthly_canonical.create_monthly_close" in hooks
		assert "nexora.close.monthly_canonical.transition_monthly_close" in hooks

	def test_canonical_monthly_service_is_idempotent_and_historical(self) -> None:
		from nexora.close import monthly_canonical

		code = inspect.getsource(monthly_canonical.create_monthly_close)
		assert "start_idempotency" in code
		assert "issue_document_number" in code
		assert "get_executive_snapshot" in inspect.getsource(monthly_canonical._calculate)
		assert "snapshot_hash" in inspect.getsource(monthly_canonical._calculate)

	def test_monthly_correction_is_linked_not_overwritten(self) -> None:
		from nexora.close import monthly_canonical

		code = inspect.getsource(monthly_canonical.correct_monthly_close)
		assert "correction_of" in code
		assert "correction_reason" in code
		assert 'original.status != "Approved"' in code

	def test_all_public_functions_are_directly_whitelisted(self) -> None:
		"""Hallazgo real de CI (PR #206, sesión 2026-08-16): la redirección de
		`hooks.py::override_whitelisted_methods` no basta por sí sola — Frappe
		valida `is_whitelisted()` contra la función RESUELTA final (el destino
		de la redirección), no contra el nombre original que el cliente llamó.
		Las cuatro funciones públicas de este módulo no tenían `@frappe.whitelist`
		propio (a diferencia de `close/canonical_weekly.py`, su equivalente
		semanal, que sí lo tenía en las cuatro) porque nunca se habían ejercido
		con una llamada HTTP real hasta que esta sesión conectó el cierre
		mensual a una página real (Bloque 52) — CI real (navegador, no local)
		lo detectó como `frappe.exceptions.PermissionError: Function
		nexora.close.monthly_canonical.list_monthly_closes is not whitelisted`.
		`test_monthly_close_is_routed_to_canonical_service` solo verificaba el
		texto del hook, nunca que el destino fuera ejecutable — no repite ese
		error."""
		source = (APP_ROOT / "close/monthly_canonical.py").read_text(encoding="utf-8")
		for name in (
			"create_monthly_close",
			"transition_monthly_close",
			"correct_monthly_close",
			"list_monthly_closes",
		):
			marker = f'@frappe.whitelist(methods=["POST"])\ndef {name}('
			assert marker in source, f"{name} no está directamente whitelisted"

	def test_frontend_calls_the_canonical_monthly_close_service_methods(self) -> None:
		"""Hallazgo real de auditoría (sesión 2026-08-16, Bloque 52):
		`monthly_canonical` estaba completo y correctamente enrutado (ver
		`test_monthly_close_is_routed_to_canonical_service`), pero ninguna
		página NEXORA lo llamaba — el hermano semanal sí estaba conectado en
		`nexora_closing.js`. Se extendió esa misma página en vez de crear una
		paralela; este test fija que la extensión siga llamando los cuatro
		métodos `nexora.close.service.*` (los nombres que `hooks.py` redirige
		al módulo canónico), no una ruta distinta."""
		source = (APP_ROOT / "nexora/page/nexora_closing/nexora_closing.js").read_text(encoding="utf-8")
		for method in (
			"nexora.close.service.create_monthly_close",
			"nexora.close.service.transition_monthly_close",
			"nexora.close.service.correct_monthly_close",
			"nexora.close.service.list_monthly_closes",
		):
			assert method in source

	def test_transitioning_a_monthly_close_is_audited(self) -> None:
		"""Bloque 167 (Paso 5 del cierre maestro, formularios nativos): `create_monthly_close`
		ya llamaba `audit(...)`, pero la transición de estado —aprobar o anular un cierre
		mensual, ambos terminales— nunca dejó rastro en `NXR Audit Event`. Verificado con
		datos reales del código (no supuesto): `transition_monthly_close` es el destino real
		de la redirección de `hooks.py` que la página de Cierres ejecuta de verdad."""
		from nexora.close import monthly_canonical

		code = inspect.getsource(monthly_canonical.transition_monthly_close)
		assert "audit(" in code
