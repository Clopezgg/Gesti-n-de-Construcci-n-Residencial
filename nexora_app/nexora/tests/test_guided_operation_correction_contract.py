from __future__ import annotations

import pathlib
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent
CORRECTIONS = APP_ROOT / "financial/corrections.py"
SERVICE = APP_ROOT / "financial/service.py"
UI = APP_ROOT / "public/js/nexora_operational_ui.js"
OPERATION = APP_ROOT / "nexora/doctype/nxr_operation/nxr_operation.py"
SOURCE = APP_ROOT / "nexora/doctype/nxr_fund_source/nxr_fund_source.py"
EFFECT = APP_ROOT / "nexora/doctype/nxr_operation_effect/nxr_operation_effect.py"


class TestGuidedOperationCorrectionContract(unittest.TestCase):
	def test_service_is_server_backed_and_exported(self) -> None:
		corrections = CORRECTIONS.read_text(encoding="utf-8")
		service = SERVICE.read_text(encoding="utf-8")
		for method in (
			"get_operation_for_correction",
			"preview_operation_correction",
			"execute_operation_correction",
		):
			self.assertIn(f"def {method}", corrections)
			self.assertIn(method, service)
		self.assertIn('action="reclassify"', corrections)
		self.assertIn("start_idempotency", corrections)
		self.assertIn("complete_idempotency", corrections)
		self.assertIn("operation_document_corrected", corrections)
		self.assertIn("before_json", corrections)
		self.assertIn("after_json", corrections)
		self.assertIn("rollback(point)", corrections)

	def test_evidence_is_optional_and_amount_change_is_guarded(self) -> None:
		text = CORRECTIONS.read_text(encoding="utf-8")
		self.assertIn('"evidence_required": False', text)
		self.assertIn("_amount_is_editable", text)
		self.assertIn("NXR Fund Allocation", text)
		self.assertIn("El importe y la tasa están bloqueados", text)
		self.assertIn("NXR Monthly Close", (APP_ROOT / "financial/operational_common.py").read_text())
		self.assertIn("_validate_open_period", text)

	def test_controlled_flags_do_not_open_free_form_edits(self) -> None:
		operation = OPERATION.read_text(encoding="utf-8")
		source = SOURCE.read_text(encoding="utf-8")
		effect = EFFECT.read_text(encoding="utf-8")
		self.assertIn("nexora_documentary_correction", operation)
		self.assertIn("GUIDED_CORRECTION_FIELDS", operation)
		self.assertIn("nexora_guided_correction", operation)
		self.assertIn("nexora_documentary_correction", source)
		self.assertIn("nexora_documentary_correction", effect)
		self.assertIn("Una operación ejecutada no puede eliminarse", operation)

	def test_ui_starts_with_document_number_and_loads_editable_data(self) -> None:
		ui = UI.read_text(encoding="utf-8")
		for marker in (
			"Corregir documento",
			"Número de documento",
			"Nombre de la remesa o fuente",
			"Fecha del documento",
			"Valor original",
			"Remitente u origen",
			"Banco o remesadora",
			"Comprobante opcional",
			"get_operation_for_correction",
			"preview_operation_correction",
			"execute_operation_correction",
		):
			self.assertIn(marker, ui)
		self.assertIn('data-code="304"', ui)
		self.assertIn("No es obligatorio para corregir fecha o datos", ui)

	def test_dashboard_header_and_rows_are_repaired_after_base_rerender(self) -> None:
		ui = UI.read_text(encoding="utf-8")
		self.assertIn("operationalTableIsSynchronized", ui)
		self.assertIn("headerCount === 11", ui)
		self.assertIn("row.children.length === 11", ui)
		self.assertIn("signature === dashboardSignature", ui)
		self.assertIn("renderRecent(rows)", ui)


if __name__ == "__main__":
	unittest.main()
