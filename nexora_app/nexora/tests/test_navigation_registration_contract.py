"""Contrato de registro de navegación para páginas nuevas de esta sesión.

Este repositorio tiene un defecto recurrente y ya documentado dos veces
(Bloque 21: `nexora-conversation-channels`/`nexora-ai-providers`; esta
sesión: `nexora-administracion` no existía en absoluto, y
`nexora.purchases.order_service` no tenía ninguna página): una página nueva
se construye con servicio real detrás, pero queda huérfana de una o más de
las tres superficies de navegación reales de NEXORA — el shell
(`nexora_shell.js`, lo que ve un usuario real), el workspace legado
(`nexora/workspace/nexora/nexora.json`) y la lista de destinos de la PWA
(`public/js/nexora.js`). `test_whatsapp_channel_contract.py` ya fija este
patrón para el canal de WhatsApp; este archivo lo repite para las dos
páginas nuevas de esta sesión en vez de dejarlas sin esa misma protección.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

PAGES_TO_CHECK = (
	{
		"route": "nexora-purchase-orders",
		"page_dir": "nexora_purchase_orders",
		"workspace_content_id": "órdenes_de_compra",
	},
	{
		"route": "nexora-administracion",
		"page_dir": "nexora_administracion",
		"workspace_content_id": "administración",
	},
	{
		"route": "nexora-inventory",
		"page_dir": "nexora_inventory",
		"workspace_content_id": "movimientos_de_inventario",
	},
	{
		"route": "nexora-budget",
		"page_dir": "nexora_budget",
		"workspace_content_id": "presupuesto_nexora",
	},
	{
		"route": "nexora-quality",
		"page_dir": "nexora_quality",
		"workspace_content_id": "calidad_nexora",
	},
	{
		"route": "nexora-receipts",
		"page_dir": "nexora_receipts",
		"workspace_content_id": "recepciones",
	},
	{
		"route": "nexora-integrations",
		"page_dir": "nexora_integrations",
		"workspace_content_id": "integraciones_nexora",
	},
	{
		"route": "nexora-notifications",
		"page_dir": "nexora_notifications",
		"workspace_content_id": "notificaciones_nexora",
	},
)


class TestEveryNewPageIsRegisteredOnAllThreeNavigationSurfaces(unittest.TestCase):
	def test_page_files_exist(self) -> None:
		for entry in PAGES_TO_CHECK:
			with self.subTest(route=entry["route"]):
				page_dir = APP_ROOT / "nexora/page" / entry["page_dir"]
				self.assertTrue((page_dir / f"{entry['page_dir']}.json").is_file())
				self.assertTrue((page_dir / f"{entry['page_dir']}.js").is_file())
				self.assertTrue((page_dir / "__init__.py").is_file())

	def test_registered_in_shell_navigation(self) -> None:
		source = (APP_ROOT / "public/js/nexora_shell.js").read_text(encoding="utf-8")
		for entry in PAGES_TO_CHECK:
			with self.subTest(route=entry["route"]):
				self.assertIn(f'route: "{entry["route"]}"', source)

	def test_registered_in_workspace_shortcuts(self) -> None:
		source = (APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8")
		for entry in PAGES_TO_CHECK:
			with self.subTest(route=entry["route"]):
				self.assertIn(f'"link_to": "{entry["route"]}"', source)

	def test_registered_in_workspace_content_blocks(self) -> None:
		payload = json.loads((APP_ROOT / "nexora/workspace/nexora/nexora.json").read_text(encoding="utf-8"))
		content_ids = {block["id"] for block in json.loads(payload["content"])}
		for entry in PAGES_TO_CHECK:
			with self.subTest(route=entry["route"]):
				self.assertIn(entry["workspace_content_id"], content_ids)

	def test_registered_in_pwa_global_destinations(self) -> None:
		source = (APP_ROOT / "public/js/nexora.js").read_text(encoding="utf-8")
		for entry in PAGES_TO_CHECK:
			with self.subTest(route=entry["route"]):
				self.assertIn(f'href: "/app/{entry["route"]}"', source)


class TestPurchaseOrderDeskFormNoLongerDuplicatesTheNexoraPage(unittest.TestCase):
	"""El botón de pago vivía en un client script de Desk puro
	(`frappe.ui.form.on`); se migró a `nexora-purchase-orders` para no dejar
	dos lugares con la misma acción divergiendo con el tiempo (Constitución
	Cap. 36: "el mismo problema se resuelve igual en todo el sistema")."""

	def test_the_old_desk_client_script_file_was_removed(self) -> None:
		self.assertFalse((APP_ROOT / "public/js/nxr_purchase_order.js").exists())

	def test_hooks_no_longer_registers_a_doctype_js_for_purchase_order(self) -> None:
		source = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
		self.assertNotIn("nxr_purchase_order.js", source)

	def test_the_payment_action_exists_in_the_new_nexora_page(self) -> None:
		source = (APP_ROOT / "nexora/page/nexora_purchase_orders/nexora_purchase_orders.js").read_text(
			encoding="utf-8"
		)
		self.assertIn("nexora.purchases.financial_bridge.pay_purchase_order", source)


if __name__ == "__main__":
	unittest.main()
