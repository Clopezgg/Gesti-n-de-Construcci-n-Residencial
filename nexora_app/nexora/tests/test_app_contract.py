from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import re
import tempfile
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from nexora.financial.operational_dates import OperationalDateError, month_key

APP_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = APP_ROOT / "nexora"


def _load_register_module():
	module_path = APP_ROOT.parent / "scripts/register_nexora_app.py"
	spec = importlib.util.spec_from_file_location("register_nexora_app", module_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Unable to load {module_path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _called_names(function: ast.FunctionDef) -> set[str]:
	return {
		node.func.id
		for node in ast.walk(function)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
	}


class TestNexoraAppContract(unittest.TestCase):
	def test_required_scaffold_exists(self) -> None:
		required = [
			APP_ROOT / "pyproject.toml",
			PACKAGE / "hooks.py",
			PACKAGE / "modules.txt",
			PACKAGE / "install.py",
			PACKAGE / "permissions.py",
			PACKAGE / "directory/core.py",
			PACKAGE / "directory/service.py",
			PACKAGE / "contracts/service.py",
			PACKAGE / "purchases/core.py",
			PACKAGE / "purchases/service.py",
			PACKAGE / "purchases/request_core.py",
			PACKAGE / "purchases/request_service.py",
			PACKAGE / "nexora/workspace/nexora/nexora.json",
			PACKAGE / "nexora/page/nexora_entities/nexora_entities.json",
			PACKAGE / "nexora/page/nexora_entities/nexora_entities.js",
			PACKAGE / "nexora/page/nexora_contracts/nexora_contracts.json",
			PACKAGE / "nexora/page/nexora_contracts/nexora_contracts.js",
			PACKAGE / "nexora/page/nexora_suppliers/nexora_suppliers.json",
			PACKAGE / "nexora/page/nexora_suppliers/nexora_suppliers.js",
			PACKAGE / "fixtures/role.json",
		]
		self.assertEqual([], [str(path) for path in required if not path.is_file()])

	def test_month_key_accepts_date_datetime_and_iso_text(self) -> None:
		self.assertEqual("2026-07", month_key(date(2026, 7, 28)))
		self.assertEqual("2026-07", month_key(datetime(2026, 7, 28, 13, 45, tzinfo=timezone.utc)))
		self.assertEqual("2026-07", month_key("2026-07-28"))
		self.assertEqual("2026-07", month_key("2026-07-28 13:45:00"))

	def test_month_key_rejects_invalid_text_with_domain_error(self) -> None:
		with self.assertRaisesRegex(OperationalDateError, "no es válida"):
			month_key("28/07/2026")

	def test_doctype_package_and_module_declarations_are_installable(self) -> None:
		doctype_root = PACKAGE / "nexora/doctype"
		self.assertTrue((doctype_root / "__init__.py").is_file())
		definitions = sorted(doctype_root.glob("*/*.json"))
		self.assertEqual(59, len(definitions))
		for definition in definitions:
			payload = json.loads(definition.read_text(encoding="utf-8"))
			self.assertEqual("NEXORA", payload["module"], definition)
			self.assertTrue(definition.with_suffix(".py").is_file(), definition)
			# Frappe imports the controller as nexora.nexora.doctype.<scrub>.<scrub>; the
			# package marker keeps that import and the wheel layout explicit.
			self.assertTrue((definition.parent / "__init__.py").is_file(), definition.parent)

	def test_workspace_never_exposes_a_service_locked_doctype_as_a_raw_shortcut(self) -> None:
		"""Causa raíz real (reportada por el propietario): `NXR Entity` estaba
		como shortcut de tipo DocType en el workspace principal a la vez que ya
		existía la página NEXORA `nexora-entities` con un servicio real de
		creación — un usuario que pulsaba el shortcut técnico caía en el
		formulario genérico de Frappe y `require_service_write()` lo rechazaba
		con un error críptico. No es un caso aislado: cualquier DocType nuevo
		bloqueado a escritura por servicio que alguien vuelva a poner como
		shortcut técnico reproduce el mismo defecto. Esta prueba lo impide para
		siempre, no solo para los 10 casos ya corregidos."""
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		offenders: list[str] = []
		for shortcut in workspace.get("shortcuts", []):
			if shortcut.get("type") != "DocType":
				continue
			doctype = shortcut.get("link_to", "")
			scrubbed = doctype.lower().replace(" ", "_")
			controller = PACKAGE / "nexora/doctype" / scrubbed / f"{scrubbed}.py"
			if not controller.is_file():
				continue
			source = controller.read_text(encoding="utf-8")
			if "require_service_write()" in source:
				offenders.append(doctype)
		self.assertEqual(
			[],
			offenders,
			"estos DocTypes bloqueados a escritura por servicio no deben ser un shortcut "
			"técnico directo — deben tener su propia página NEXORA con un servicio real",
		)

	def test_route_changes_clear_stale_alerts_from_the_previous_screen(self) -> None:
		"""Hallazgo real de auditoría visual (capturas reales del recorrido de
		navegador contra Frappe/MariaDB reales): `frappe.show_alert` se
		autodescarta solo a los 7 s, pero nada limpiaba los avisos de una
		pantalla anterior al entrar a una nueva — un usuario real que encadena
		varias operaciones rápido podía seguir viendo, en la pantalla actual,
		confirmaciones de una pantalla que ya dejó atrás, tapando contenido
		real (incluido un diálogo abierto), confirmado en
		`desktop-chromium-whatsapp-admin.png` del recorrido real (8 avisos
		acumulados de etapas anteriores)."""
		source = (PACKAGE / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('frappe.router?.on?.("change", dismissStaleAlerts)', source)
		body = source[source.index("const dismissStaleAlerts = ") :]
		body = body[: body.index("\n\tfrappe.router")]
		self.assertIn("#alert-container .alert", body)
		self.assertIn('classList.add("out")', body)

	def test_shell_reserves_sidebar_space_against_frappes_own_important_reset(self) -> None:
		"""Causa raíz real (hallazgo de auditoría visual, confirmado con
		`getBoundingClientRect()` real contra Frappe/MariaDB reales): el propio
		`desk.bundle.css` de Frappe trae `body { padding: 0 !important; }` —
		ajeno a esta app, no editable. Sin igualar esa prioridad con
		`!important` en nuestra propia regla, ese reinicio del marco siempre
		gana pese a ser menos específico, `body` se queda con 0 de relleno
		real y todo el contenido de NEXORA arranca en el borde real del
		viewport en vez de a partir de los 264px que la navegación fija
		reserva — quedando parcialmente tapado por ella. Confirmado en
		capturas reales: encabezados y texto recortados en el borde
		izquierdo en el dashboard, operación guiada y avance."""
		css = (PACKAGE / "public/css/nexora_shell.css").read_text(encoding="utf-8")
		active = css[css.index(".nxr-shell-active body") :]
		active = active[: active.index("}")]
		self.assertIn("padding-left: 264px !important", active)
		collapsed = css[css.index('[data-nxr-shell-collapsed="true"] body') :]
		collapsed = collapsed[: collapsed.index("}")]
		self.assertIn("padding-left: 68px !important", collapsed)
		# El reinicio a cajón por debajo de 1024px tiene que igualar la misma prioridad:
		# `!important` ignora la cascada normal por selector/orden, así que sin esto la
		# reserva de escritorio (arriba) le ganaría también a este reinicio móvil.
		mobile = css[css.index("@media (max-width: 1024px)") :]
		mobile = mobile[: mobile.index("}\n\n\t.nxr-shell__bar")]
		self.assertIn("padding-left: 0 !important", mobile)

	def test_translation_calls_never_split_their_string(self) -> None:
		"""El extractor de traducciones de Frappe no lee concatenaciones dentro de
		__(), así que un mensaje partido con + queda sin traducir. Es la regla
		frappe-translation-js-splitting que semgrep aplica en CI."""
		pattern = re.compile(r'__\(\s*(?:"[^"]*"|\'[^\']*\')\s*\+', re.MULTILINE)
		offenders: list[str] = []
		for script in sorted(PACKAGE.rglob("*.js")):
			for match in pattern.finditer(script.read_text(encoding="utf-8")):
				line = script.read_text(encoding="utf-8")[: match.start()].count("\n") + 1
				offenders.append(f"{script.relative_to(PACKAGE)}:{line}")
		self.assertEqual([], offenders, "no concatene cadenas dentro de __()")

	def test_apps_registry_is_idempotent_without_trailing_newline(self) -> None:
		module = _load_register_module()
		with tempfile.TemporaryDirectory() as directory:
			apps_file = pathlib.Path(directory) / "apps.txt"
			apps_file.write_text("frappe\npayments", encoding="utf-8")
			module.register_app(apps_file)
			module.register_app(apps_file)
			self.assertEqual("frappe\npayments\nnexora\n", apps_file.read_text(encoding="utf-8"))

	def test_apps_registry_change_invalidates_frappe_module_cache(self) -> None:
		module = _load_register_module()
		with tempfile.TemporaryDirectory() as directory:
			bench = pathlib.Path(directory) / "frappe-bench"
			(bench / "apps").mkdir(parents=True)
			(bench / "sites").mkdir()
			apps_file = bench / "sites/apps.txt"
			apps_file.write_text("frappe\nerpnext\n", encoding="utf-8")
			with patch.object(module, "_run") as run:
				module.register_app(apps_file)
			run.assert_called_once_with("bench", "--site", "all", "clear-cache", cwd=bench)

	def test_catalog_seed_runs_only_after_doctype_sync(self) -> None:
		hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('after_migrate = "nexora.install.after_migrate"', hooks)
		tree = ast.parse((PACKAGE / "install.py").read_text(encoding="utf-8"))
		functions = {
			node.name: node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name in {"after_install", "after_migrate"}
		}
		self.assertEqual({"after_install", "after_migrate"}, set(functions))
		self.assertNotIn("seed_analytic_catalogs", _called_names(functions["after_install"]))
		self.assertIn("_ensure_sequence_counter", _called_names(functions["after_install"]))
		self.assertIn("seed_analytic_catalogs", _called_names(functions["after_migrate"]))
		self.assertNotIn("_ensure_sequence_counter", _called_names(functions["after_migrate"]))
		self.assertNotIn("create_sequence_counter", _called_names(functions["after_migrate"]))

	def test_identity_and_dependency_are_explicit(self) -> None:
		hooks = (PACKAGE / "hooks.py").read_text(encoding="utf-8")
		self.assertIn('app_name = "nexora"', hooks)
		self.assertIn('app_title = "NEXORA"', hooks)
		self.assertIn('required_apps = ["erpnext"]', hooks)

	def test_daily_income_and_expense_flows_are_simple_and_canonical(self) -> None:
		source = (PACKAGE / "public/js/nexora.js").read_text(encoding="utf-8")
		for label in (
			"Registrar ingreso",
			"Monto recibido",
			"Cómo se recibió",
			"Remitente u origen",
			"Registrar gasto",
			"Monto pagado",
			"Fondo que pagará",
			"Categoría del gasto",
			"Comprobante",
		):
			self.assertIn(label, source)
		self.assertIn("nexora.financial.service.create_fund_source", source)
		self.assertIn("nexora.financial.service.preview_central_operation", source)
		self.assertIn("nexora.financial.service.execute_central_operation", source)
		self.assertIn('operation_code: "CONSTRUCTION_PAYMENT"', source)
		self.assertIn("idempotency_key: uuid()", source)
		self.assertIn("preview_hash: preview.message.preview_hash", source)
		self.assertNotIn("Tipo oficial de operación", source)
		self.assertNotIn("Servicio canónico derivado", source)

	def test_visible_vocabulary_and_feedback_are_shared(self) -> None:
		ui_source = (PACKAGE / "public/js/nexora_report_actions.js").read_text(encoding="utf-8")
		for label in (
			"Cuenta guardada",
			"Tipo de movimiento",
			"Registrar definitivamente",
			"Documento que se corrige",
			"Distribución del pago",
			"Comprobante",
			"Historial financiero",
			"Registrado definitivamente",
		):
			self.assertIn(label, ui_source)
		for helper in ("selectOptions", "showSuccess", "showError", "formatMoney"):
			self.assertIn(helper, ui_source)
		for relative in (
			"nexora/page/nexora_search/nexora_search.js",
			"nexora/page/nexora_suppliers/nexora_suppliers.js",
			"nexora/page/nexora_evidence/nexora_evidence.js",
		):
			page_source = (PACKAGE / relative).read_text(encoding="utf-8")
			self.assertIn("window.nexora.ui", page_source, relative)
		self.assertNotIn(
			"Cumplimiento Supplier",
			(PACKAGE / "nexora/page/nexora_suppliers/nexora_suppliers.js").read_text(encoding="utf-8"),
		)
		css = (PACKAGE / "public/css/nexora_dashboard_fixes.css").read_text(encoding="utf-8")
		for rule in (
			":focus-visible",
			"prefers-reduced-motion",
			"min-height: 44px",
			'[aria-busy="true"]',
		):
			self.assertIn(rule, css)

	def test_new_app_has_no_legacy_import_or_visible_brand(self) -> None:
		findings: list[str] = []
		for path in APP_ROOT.rglob("*"):
			if path.is_file() and path.suffix in {".py", ".json", ".js", ".css", ".md", ".toml"}:
				text = path.read_text(encoding="utf-8")
				if re.search(r"(?:import|from)\s+erpnext\.construcontrol", text, re.IGNORECASE):
					findings.append(str(path))
		self.assertEqual([], findings)
		workspace = (PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertNotIn("ConstruControl", workspace)
		self.assertNotIn("ERPNext", workspace)

	def test_roles_and_workspace_are_consistent(self) -> None:
		roles = json.loads((PACKAGE / "fixtures/role.json").read_text(encoding="utf-8"))
		names = {row["name"] for row in roles}
		workspace = json.loads((PACKAGE / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		workspace_roles = {row["role"] for row in workspace["roles"]}
		self.assertEqual(names, workspace_roles)
		self.assertEqual("NEXORA", workspace["title"])


if __name__ == "__main__":
	unittest.main()
