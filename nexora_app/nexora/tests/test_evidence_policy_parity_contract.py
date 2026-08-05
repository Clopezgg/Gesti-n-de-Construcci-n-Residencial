from __future__ import annotations

import pathlib
import re
import unittest

from nexora.financial.evidence_core import (
	CASH_EVIDENCE_THRESHOLD_HNL,
	PAYMENT_EVIDENCE_METHODS,
	evaluate_evidence_policy,
)

PACKAGE = pathlib.Path(__file__).resolve().parents[1]
OPERATIONS = PACKAGE / "nexora/page/nexora_operations/nexora_operations.js"
SHARED = PACKAGE / "public/js/nexora.js"


class TestEvidencePolicyParityContract(unittest.TestCase):
	"""La pantalla debe pedir el comprobante exactamente cuando el servidor lo exige.

	`evaluate_evidence_policy` obliga a comprobante en depósitos y transferencias, y
	en efectivo por encima de L2,000. La consola operativa marcaba el comprobante
	como opcional para todo gasto: el usuario llenaba proyecto, beneficiario,
	importe, medio de pago, categoría, centro de costo y distribución, pulsaba vista
	previa y recién ahí el servidor lo rechazaba. Es trabajo perdido y un error
	inducido por la interfaz, no por el usuario.
	"""

	def source(self) -> str:
		return OPERATIONS.read_text(encoding="utf-8")

	def test_the_screen_mirrors_the_server_methods_and_threshold(self) -> None:
		code = SHARED.read_text(encoding="utf-8")
		methods = re.search(r"EVIDENCE_PAYMENT_METHODS: Object\.freeze\(\[([^\]]*)\]\)", code)
		self.assertIsNotNone(methods, "la pantalla debe declarar los medios que exigen comprobante")
		declared = {value.strip().strip('"') for value in methods.group(1).split(",") if value.strip()}
		self.assertEqual(set(PAYMENT_EVIDENCE_METHODS), declared)

		threshold = re.search(r"CASH_EVIDENCE_THRESHOLD_HNL: (\d+)", code)
		self.assertIsNotNone(threshold, "la pantalla debe declarar el umbral de efectivo")
		self.assertEqual(int(CASH_EVIDENCE_THRESHOLD_HNL), int(threshold.group(1)))

	def test_the_rule_lives_in_one_place_on_the_client(self) -> None:
		"""Una regla de negocio en dos archivos son dos reglas que se separarán."""
		shared = SHARED.read_text(encoding="utf-8")
		self.assertIn("window.nexora.rules = Object.freeze({", shared)
		self.assertIn("evidencePolicy(paymentMethod, amountHnl)", shared)
		# El gasto rápido nace en «Transferencia», que siempre exige comprobante.
		self.assertIn("applyExpenseEvidencePolicy(dialog)", shared)
		self.assertIn('set_df_property("evidence", "reqd"', shared)
		operations = self.source()
		self.assertNotIn("const EVIDENCE_PAYMENT_METHODS", operations)
		self.assertNotIn("const CASH_EVIDENCE_THRESHOLD_HNL", operations)

	def test_the_expense_blocks_the_preview_when_the_server_would_reject_it(self) -> None:
		code = self.source()
		self.assertIn("function evidenceRequirement()", code)
		self.assertIn("function applyEvidencePolicy()", code)
		# La consola consulta la regla compartida en vez de reimplementarla.
		self.assertIn("window.nexora.rules.evidencePolicy(", code)
		# La obligación se marca en el campo y además se valida antes de enviar: sin lo
		# segundo, el usuario todavía puede pulsar «Vista previa» y recibir el rechazo.
		validation = code.split('if (data.movement_code === "102")', 1)[1].split("\n\t\t}", 1)[0]
		self.assertIn("evidenceRequirement()", validation)
		self.assertIn('field: "evidence"', validation)

	def test_the_requirement_is_recomputed_when_its_inputs_change(self) -> None:
		"""El medio de pago y el importe deciden la obligación: si no se reevalúa al
		cambiarlos, el campo queda marcado según un estado anterior."""
		changed = self.source().split("async function fieldChanged(", 1)[1].split("\n\t}", 1)[0]
		self.assertIn('["payment_method", "amount_hnl"]', changed)
		self.assertIn("applyEvidencePolicy()", changed)

	def test_the_server_rule_still_behaves_as_the_screen_promises(self) -> None:
		"""Si la regla del servidor cambia, este caso falla junto con el espejo."""
		for method in sorted(PAYMENT_EVIDENCE_METHODS):
			with self.subTest(method=method):
				self.assertTrue(evaluate_evidence_policy(method, 1, "CONSTRUCTION_MATERIALS").required)
		self.assertFalse(evaluate_evidence_policy("Cash", 2000, "CONSTRUCTION_MATERIALS").required)
		self.assertTrue(evaluate_evidence_policy("Cash", 2000.01, "CONSTRUCTION_MATERIALS").required)


if __name__ == "__main__":
	unittest.main()
