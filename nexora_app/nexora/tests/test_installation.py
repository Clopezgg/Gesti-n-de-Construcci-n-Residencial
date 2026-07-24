from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from nexora.financial.seeds import seed_demo_data
from nexora.install import BASE_ROLES

CONTRACT_DOCTYPES = (
	"NXR Contractor Profile",
	"NXR Contract",
	"NXR Contract Line",
	"NXR Contract Evidence",
	"NXR Contract Amendment",
	"NXR Contract Estimate",
	"NXR Contract Estimate Line",
	"NXR Contract Transaction",
)

DIRECTORY_DOCTYPES = (
	"NXR Entity",
	"NXR Entity Identifier",
	"NXR Entity Contact",
	"NXR Entity Role",
	"NXR Entity Compliance",
	"NXR Entity Consolidation",
)

PURCHASE_DOCTYPES = ("NXR Supplier Profile",)


class TestNexoraInstallation(FrappeTestCase):
	def test_app_and_minimum_fixtures_are_installed(self) -> None:
		self.assertIn("nexora", frappe.get_installed_apps())
		self.assertIn("erpnext", frappe.get_installed_apps())
		for role_name in BASE_ROLES:
			self.assertTrue(frappe.db.exists("Role", role_name))
		self.assertTrue(frappe.db.exists("Workspace", "NEXORA"))
		self.assertTrue(frappe.db.exists("Page", "nexora-evidence"))
		self.assertTrue(frappe.db.exists("Page", "nexora-entities"))
		self.assertTrue(frappe.db.exists("Page", "nexora-contracts"))
		self.assertTrue(frappe.db.exists("Page", "nexora-suppliers"))
		self.assertTrue(frappe.db.exists("Print Format", "NEXORA Contract"))
		self.assertEqual("NXR Contract", frappe.db.get_value("Print Format", "NEXORA Contract", "doc_type"))
		self.assertTrue(frappe.db.exists("DocType", "NXR Evidence"))
		for doctype in (*DIRECTORY_DOCTYPES, *CONTRACT_DOCTYPES, *PURCHASE_DOCTYPES):
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)
		self.assertTrue(frappe.db.exists("Currency", "HNL"))
		self.assertTrue(frappe.db.exists("Country", "Honduras"))
		self.assertTrue(frappe.db.exists("NXR Operation Type", "MAXIMUM_ACCOUNT"))
		self.assertTrue(frappe.db.exists("NXR Economic Category", "MAXIMUM_ACCOUNT"))

	def test_workspace_contains_only_nexora_identity(self) -> None:
		workspace = frappe.get_doc("Workspace", "NEXORA")
		serialized = workspace.as_json()
		self.assertIn("NEXORA", serialized)
		self.assertNotIn("ConstruControl", serialized)

	def test_workspace_exposes_certified_financial_evidence_directory_contract_and_supplier_surfaces(
		self,
	) -> None:
		workspace = frappe.get_doc("Workspace", "NEXORA")
		shortcuts = {(row.label, row.type, row.link_to) for row in workspace.shortcuts}
		self.assertIn(("Núcleo de Fondos", "Page", "nexora-finance"), shortcuts)
		self.assertIn(("Fuentes de fondos", "DocType", "NXR Fund Source"), shortcuts)
		self.assertIn(("Libro Central", "DocType", "NXR Operation"), shortcuts)
		self.assertIn(("Directorio de entidades", "Page", "nexora-entities"), shortcuts)
		self.assertIn(("Entidades", "DocType", "NXR Entity"), shortcuts)
		self.assertIn(("Evidencias", "Page", "nexora-evidence"), shortcuts)
		self.assertIn(("Gestión contractual", "Page", "nexora-contracts"), shortcuts)
		self.assertIn(("Contratos", "DocType", "NXR Contract"), shortcuts)
		self.assertIn(("Perfiles de contratista", "DocType", "NXR Contractor Profile"), shortcuts)
		self.assertIn(("Gestión de proveedores", "Page", "nexora-suppliers"), shortcuts)
		self.assertIn(("Perfiles de proveedor", "DocType", "NXR Supplier Profile"), shortcuts)
		self.assertIn(("Expedientes de evidencia", "DocType", "NXR Evidence"), shortcuts)
		self.assertIn(("Tipos de operación", "DocType", "NXR Operation Type"), shortcuts)
		self.assertIn(("Clasificación económica", "DocType", "NXR Economic Category"), shortcuts)

	def test_demo_seed_rejects_sites_without_explicit_staging_flag(self) -> None:
		previous = frappe.conf.get("nexora_staging")
		frappe.conf.nexora_staging = 0
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "nexora_staging=1"):
				seed_demo_data()
		finally:
			if previous is None:
				frappe.conf.pop("nexora_staging", None)
			else:
				frappe.conf.nexora_staging = previous
