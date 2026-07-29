from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import unittest

import nexora

APP_ROOT = pathlib.Path(nexora.__file__).resolve().parent


class TestGuidedAccountProgressiveContract(unittest.TestCase):
	def test_assets_are_loaded_after_canonical_operation_engine(self) -> None:
		hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertLess(
			hooks.index("/assets/nexora/js/nexora_quick_flows.js"),
			hooks.index("/assets/nexora/js/nexora_guided_model.js"),
		)
		self.assertLess(
			hooks.index("/assets/nexora/js/nexora_guided_model.js"),
			hooks.index("/assets/nexora/js/nexora_guided_operations.js"),
		)
		self.assertIn("/assets/nexora/css/nexora_guided_operations.css", hooks)

	def test_human_account_choice_hides_internal_modes(self) -> None:
		code = (APP_ROOT / "public/js/nexora_guided_operations.js").read_text(encoding="utf-8")
		for label in (
			"Cuenta para esta operación",
			"Seleccionar una cuenta guardada",
			"Usar otros datos bancarios",
			"¿Desea guardar esta cuenta para utilizarla nuevamente?",
			"Sí, guardar para el futuro",
			"No, usar solo esta vez",
		):
			self.assertIn(label, code)
		for technical_label in (
			"Usar cuenta existente",
			"Crear cuenta nueva",
			"Datos manuales, no guardar",
		):
			self.assertNotIn(technical_label, code)
		self.assertIn('const technicalMode = field(root, "account_mode")', code)
		self.assertIn('const savedControl = field(root, "financial_account")', code)
		self.assertIn("technicalMode.hidden = true", code)
		self.assertIn("savedControl.hidden = true", code)

	def test_progressive_flow_uses_four_stages_and_same_canonical_buttons(self) -> None:
		code = (APP_ROOT / "public/js/nexora_guided_operations.js").read_text(encoding="utf-8")
		for marker in (
			'data-guided-stage="1"',
			'data-guided-stage="2"',
			'data-guided-stage="3"',
			'data-guided-stage="4"',
			"Datos principales",
			"Datos necesarios",
			"Revisión",
			"Registrar definitivamente",
			"Opciones avanzadas",
			".nxr-preview-movement",
			".nxr-execute-movement",
			"revealFirstError",
			"focus",
		):
			self.assertIn(marker, code)
		self.assertNotIn("execute_central_operation", code)
		self.assertNotIn("create_fund_source", code)

	def test_shared_account_component_requests_server_compatibility_filters(self) -> None:
		code = (APP_ROOT / "public/js/nexora_guided_operations.js").read_text(encoding="utf-8")
		for marker in (
			"nexora.financial.service.list_financial_accounts",
			"nexora.financial.service.get_financial_account",
			"movementDirection",
			"project: ctx.project",
			"currency: ctx.currency",
			"channel: ctx.channel",
			"counterparty: ctx.counterparty",
		):
			self.assertIn(marker, code)

	def test_model_rejects_incompatible_accounts_and_maps_human_choice(self) -> None:
		node = shutil.which("node")
		self.assertIsNotNone(node, "Node.js is required by the repository's JavaScript checks")
		model_path = APP_ROOT / "public/js/nexora_guided_model.js"
		script = f"""
			const model = require({json.dumps(str(model_path))});
			const base = {{
				name: 'A1', project: 'P1', direction: 'Origin', currency: 'USD',
				default_channel: 'Transfer', origin_or_sender: 'Ana'
			}};
			function ok(value, message) {{ if (!value) throw new Error(message); }}
			ok(model.accountCompatible(base, {{movementCode:'101', project:'P1', currency:'USD', channel:'Transfer', counterparty:'Ana'}}), 'valid account');
			ok(!model.accountCompatible(base, {{movementCode:'101', project:'P2', currency:'USD', channel:'Transfer', counterparty:'Ana'}}), 'other project');
			ok(!model.accountCompatible(base, {{movementCode:'101', project:'P1', currency:'HNL', channel:'Transfer', counterparty:'Ana'}}), 'currency mismatch');
			ok(!model.accountCompatible(base, {{movementCode:'101', project:'P1', currency:'USD', channel:'Cash', counterparty:'Ana'}}), 'channel mismatch');
			ok(!model.accountCompatible(base, {{movementCode:'102', project:'P1', currency:'USD', channel:'Transfer', counterparty:'Ana'}}), 'direction mismatch');
			const saved = model.canonicalAccountSelection({{movementCode:'101', choice:'saved', hasAccounts:true, selectedAccount:'A1'}});
			ok(saved.account_mode === 'Existing' && saved.financial_account === 'A1', 'saved mapping');
			const reusable = model.canonicalAccountSelection({{movementCode:'102', choice:'other', hasAccounts:false, saveForFuture:true, accountName:'Proveedor', counterparty:'Proveedor', paymentMethod:'Transfer', currency:'HNL'}});
			ok(reusable.account_mode === 'New' && reusable.direction === 'Destination', 'new destination mapping');
			const once = model.canonicalAccountSelection({{movementCode:'101', choice:'other', hasAccounts:false, saveForFuture:false}});
			ok(once.account_mode === 'Manual' && once.save_financial_account === 0, 'one-time mapping');
		"""
		result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=False)
		self.assertEqual(0, result.returncode, result.stderr)

	def test_responsive_and_accessibility_contract(self) -> None:
		css = (APP_ROOT / "public/css/nexora_guided_operations.css").read_text(encoding="utf-8")
		for marker in (
			"@media (max-width: 760px)",
			"env(safe-area-inset-bottom",
			"min-height: 44px",
			"touch-action: manipulation",
			"prefers-reduced-motion",
			"grid-template-columns: minmax(0, 1fr)",
		):
			self.assertIn(marker, css)


if __name__ == "__main__":
	unittest.main()
