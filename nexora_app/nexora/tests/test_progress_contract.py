from __future__ import annotations

import json
import pathlib
import re
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


def function_body(source: str, name: str) -> str:
	match = re.search(rf"\ndef {re.escape(name)}\(.*?\n(?=\n@|\ndef |\Z)", source, flags=re.DOTALL)
	if not match:
		raise AssertionError(f"no se encontró la función {name!r}")
	return match.group(0)


class TestProgressContract(unittest.TestCase):
	def test_progress_module_exists(self) -> None:
		init = APP_ROOT / "progress/__init__.py"
		self.assertTrue(init.is_file())

	def test_progress_core_exists(self) -> None:
		core = APP_ROOT / "progress/core.py"
		self.assertTrue(core.is_file())

	def test_progress_service_exists(self) -> None:
		service = APP_ROOT / "progress/service.py"
		self.assertTrue(service.is_file())

	def test_progress_record_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_progress_record/nxr_progress_record.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Progress Record", payload["name"])

	def test_quality_check_doctype_is_defined(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_quality_check/nxr_quality_check.json"
		self.assertTrue(path.is_file())
		payload = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual("NXR Quality Check", payload["name"])

	def test_progress_record_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_progress_record/nxr_progress_record.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)

	def test_quality_check_controller_enforces_boundary(self) -> None:
		path = APP_ROOT / "nexora/doctype/nxr_quality_check/nxr_quality_check.py"
		code = path.read_text(encoding="utf-8")
		self.assertIn("require_service_write", code)
		self.assertIn("on_trash", code)


class TestListProgressRecords(unittest.TestCase):
	"""Bloque 25 (NXR-AVA-0006): antes no existía ninguna forma real de leer un
	registro de avance individual fuera del resumen agregado del panel
	ejecutivo. Mismo patrón de alcance por proyecto que
	`financial.evidence.list_evidence` — regresión directa de NXR-SEC-0001 si
	se relaja."""

	def source(self) -> str:
		return (APP_ROOT / "progress/service.py").read_text(encoding="utf-8")

	def test_list_progress_records_is_a_whitelisted_post_endpoint(self) -> None:
		source = self.source()
		self.assertRegex(source, r'@frappe\.whitelist\(methods=\["POST"\]\)\ndef list_progress_records\(')

	def test_list_progress_records_checks_project_access_not_a_broad_role_only(self) -> None:
		source = self.source()
		body = function_body(source, "list_progress_records")
		self.assertIn('require_project_access(project, action="preview")', body)


class TestProgressPageRegistration(unittest.TestCase):
	"""Bloque 25: la matriz de requisitos clasificaba NXR-AVA-0005/NXR-AVA-0006
	(cámara/galería y feed fotográfico de avance) como `IMPLEMENTADO Y
	VALIDADO`, pero ninguna página real los exponía — `progress/service.py`
	solo se llamaba desde `financial/seeds.py` (datos de siembra), nunca desde
	un cliente real. Esta clase fija que la página nueva existe y está
	realmente conectada, no solo declarada."""

	def test_page_files_exist(self) -> None:
		page_dir = APP_ROOT / "nexora/page/nexora_progress"
		self.assertTrue((page_dir / "nexora_progress.json").is_file())
		self.assertTrue((page_dir / "nexora_progress.js").is_file())
		self.assertTrue((page_dir / "__init__.py").is_file())

	def test_page_calls_the_real_service_functions_not_a_mock(self) -> None:
		script = (APP_ROOT / "nexora/page/nexora_progress/nexora_progress.js").read_text(encoding="utf-8")
		for method in (
			"nexora.progress.service.create_progress_record",
			"nexora.progress.service.transition_progress_record",
			"nexora.progress.service.list_progress_records",
		):
			self.assertIn(method, script)

	def test_registered_in_global_destinations(self) -> None:
		source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		self.assertIn('href: "/app/nexora-progress"', source)

	def test_registered_in_workspace_shortcuts_and_content(self) -> None:
		source = (APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		self.assertIn('"link_to": "nexora-progress"', source)
		self.assertIn("avance_nexora", source)

	def test_registered_in_shell_sections(self) -> None:
		source = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		self.assertIn('{ route: "nexora-progress"', source)

	def test_page_restricted_to_nexora_roles(self) -> None:
		payload = json.loads(
			(APP_ROOT / "nexora/page/nexora_progress/nexora_progress.json").read_text(encoding="utf-8")
		)
		roles = {row["role"] for row in payload["roles"]}
		self.assertTrue(roles)
		self.assertIn("NEXORA Administrator", roles)
