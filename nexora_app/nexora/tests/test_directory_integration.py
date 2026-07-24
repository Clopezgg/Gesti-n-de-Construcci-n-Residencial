from __future__ import annotations

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.file_manager import save_file

from nexora.directory.api import (
	assign_entity_role,
	consolidate_entities,
	create_entity,
	create_entity_compliance,
	detect_entity_duplicates,
	get_entity,
	resolve_canonical_entity,
	search_entities,
	transition_entity,
	transition_entity_compliance,
	transition_entity_role,
)
from nexora.financial.evidence import register_evidence, review_evidence


def _key(prefix: str) -> str:
	return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


def _ensure_project() -> str:
	name = frappe.db.get_value("Project", {"project_name": "_Test NEXORA Directory"}, "name")
	if name:
		return str(name)
	return str(
		frappe.get_doc({"doctype": "Project", "project_name": "_Test NEXORA Directory", "status": "Open"})
		.insert(ignore_permissions=True)
		.name
	)


class TestDirectoryMariaDB(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.project = _ensure_project()
		cls.operator = _ensure_user("nxr-directory-operator@example.test", "NEXORA Finance Operator")
		cls.manager = _ensure_user("nxr-directory-manager@example.test", "NEXORA Finance Manager")
		cls.viewer = _ensure_user("nxr-directory-viewer@example.test", "NEXORA Project Viewer")
		cls.auditor = _ensure_user("nxr-directory-auditor@example.test", "NEXORA Auditor")

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		super().tearDown()

	def _create(
		self,
		*,
		name: str,
		entity_type: str = "Individual",
		identifier_type: str = "Passport",
		identifier_value: str | None = None,
		contact_type: str = "Email",
		contact_value: str | None = None,
		linked_user: str | None = None,
		idempotency_key: str | None = None,
	) -> tuple[dict[str, object], dict[str, object]]:
		marker = uuid.uuid4().hex[:10]
		payload: dict[str, object] = {
			"entity_type": entity_type,
			"display_name": name,
			"legal_name": f"{name} Legal" if entity_type == "Organization" else None,
			"country": "Honduras",
			"linked_user": linked_user,
			"identifiers": [
				{
					"identifier_type": identifier_type,
					"identifier_value": identifier_value or f"P-{marker}",
					"is_primary": 1,
				}
			],
			"contacts": [
				{
					"contact_type": contact_type,
					"contact_value": contact_value or f"{marker}@example.test",
					"is_primary": 1,
					"is_verified": 1,
				}
			],
			"idempotency_key": idempotency_key or _key("entity-create"),
		}
		frappe.set_user(self.operator)
		return create_entity(payload), payload

	def _activate(self, entity: str) -> dict[str, object]:
		frappe.set_user(self.manager)
		return transition_entity(entity, "Active", _key("entity-activate"))

	def _validated_evidence(self, suffix: str) -> str:
		frappe.set_user(self.operator)
		file_doc = save_file(
			f"directory-{suffix}-{uuid.uuid4().hex}.txt",
			f"Evidencia de cumplimiento {suffix}".encode(),
			"Project",
			self.project,
			is_private=1,
		)
		registered = register_evidence(
			{
				"project": self.project,
				"evidence_kind": "Other",
				"channel": "Other",
				"file_url": file_doc.file_url,
				"external_reference": f"DIR-{suffix}-{uuid.uuid4().hex[:8]}",
				"idempotency_key": _key("directory-evidence"),
			}
		)
		frappe.set_user(self.manager)
		review_evidence(str(registered["evidence"]), "Validated", _key("directory-review"))
		return str(registered["evidence"])

	def test_people_companies_identifiers_contacts_search_idempotency_and_sensitive_permissions(self) -> None:
		linked_user = _ensure_user(f"nxr-person-{uuid.uuid4().hex}@example.test", "NEXORA Project Viewer")
		key = _key("person-idempotent")
		person, payload = self._create(
			name="José López",
			identifier_type="Passport",
			identifier_value=f"HN-{uuid.uuid4().hex[:10]}",
			contact_type="Email",
			contact_value=f"jose-{uuid.uuid4().hex[:8]}@example.test",
			linked_user=linked_user,
			idempotency_key=key,
		)
		self.assertEqual(person, create_entity(payload))
		self.assertEqual(1, frappe.db.count("NXR Entity", {"idempotency_key": key}))
		self._activate(str(person["name"]))

		rtn = f"0801-{uuid.uuid4().int % 10**10:010d}"
		whatsapp = f"+5049{uuid.uuid4().int % 10**7:07d}"
		company, _ = self._create(
			name="Constructora Ágil S.A.",
			entity_type="Organization",
			identifier_type="RTN",
			identifier_value=rtn,
			contact_type="WhatsApp",
			contact_value=whatsapp,
		)
		self._activate(str(company["name"]))

		for query, expected in (
			("Constructora Agil", company["name"]),
			(str(company["document_number"]), company["name"]),
			(rtn, company["name"]),
			(whatsapp, company["name"]),
		):
			frappe.set_user(self.viewer)
			matches = search_entities(query=query)
			self.assertIn(expected, {row["name"] for row in matches}, query)

		frappe.set_user(self.viewer)
		masked = get_entity(str(person["name"]), include_sensitive=0)
		self.assertNotIn("legal_name", masked)
		self.assertNotIn("identifier_value", masked["identifiers"][0])
		self.assertNotIn("normalized_hash", masked["identifiers"][0])
		self.assertNotIn("contact_value", masked["contacts"][0])
		with self.assertRaises(frappe.PermissionError):
			get_entity(str(person["name"]), include_sensitive=1)

		frappe.set_user(self.auditor)
		sensitive = get_entity(str(person["name"]), include_sensitive=1)
		self.assertEqual(
			payload["identifiers"][0]["identifier_value"], sensitive["identifiers"][0]["identifier_value"]
		)
		self.assertEqual(payload["contacts"][0]["contact_value"], sensitive["contacts"][0]["contact_value"])
		self.assertEqual(linked_user, sensitive["linked_user"])

	def test_multiple_roles_vigency_overlap_and_server_permissions(self) -> None:
		entity, _ = self._create(name=f"Proveedor múltiple {uuid.uuid4().hex[:8]}")
		self._activate(str(entity["name"]))
		frappe.set_user(self.manager)
		contractor = assign_entity_role(
			{
				"entity": entity["name"],
				"role_type": "Contractor",
				"project": self.project,
				"valid_from": "2026-01-01",
				"valid_until": "2026-06-30",
				"idempotency_key": _key("role-contractor"),
			}
		)
		supplier = assign_entity_role(
			{
				"entity": entity["name"],
				"role_type": "Supplier",
				"project": self.project,
				"valid_from": "2026-01-01",
				"idempotency_key": _key("role-supplier"),
			}
		)
		transition_entity_role(str(contractor["role"]), "Active", _key("role-activate"))
		transition_entity_role(str(supplier["role"]), "Active", _key("role-activate"))
		self.assertEqual(
			2, frappe.db.count("NXR Entity Role", {"entity": entity["name"], "status": "Active"})
		)
		with self.assertRaisesRegex(frappe.ValidationError, "superpuesto"):
			assign_entity_role(
				{
					"entity": entity["name"],
					"role_type": "Contractor",
					"project": self.project,
					"valid_from": "2026-06-30",
					"valid_until": "2026-12-31",
					"idempotency_key": _key("role-overlap"),
				}
			)
		future = assign_entity_role(
			{
				"entity": entity["name"],
				"role_type": "Contractor",
				"project": self.project,
				"valid_from": "2026-07-01",
				"valid_until": "2026-12-31",
				"idempotency_key": _key("role-future"),
			}
		)
		self.assertEqual("Proposed", future["status"])
		frappe.set_user(self.viewer)
		with self.assertRaises(frappe.PermissionError):
			assign_entity_role(
				{
					"entity": entity["name"],
					"role_type": "Owner",
					"valid_from": "2026-01-01",
					"idempotency_key": _key("role-denied"),
				}
			)

	def test_duplicate_prevention_detection_and_linked_user_uniqueness(self) -> None:
		identifier = f"DUP-{uuid.uuid4().hex[:12]}"
		contact = f"duplicate-{uuid.uuid4().hex[:8]}@example.test"
		linked_user = _ensure_user(f"nxr-duplicate-{uuid.uuid4().hex}@example.test", "NEXORA Project Viewer")
		original, _ = self._create(
			name="Entidad Duplicada",
			identifier_type="Passport",
			identifier_value=identifier,
			contact_value=contact,
			linked_user=linked_user,
		)
		frappe.set_user(self.operator)
		with self.assertRaisesRegex(frappe.ValidationError, "ya pertenece"):
			create_entity(
				{
					"entity_type": "Individual",
					"display_name": "Otra entidad",
					"identifiers": [{"identifier_type": "Passport", "identifier_value": identifier}],
					"contacts": [
						{"contact_type": "Email", "contact_value": f"other-{uuid.uuid4().hex}@example.test"}
					],
					"idempotency_key": _key("duplicate-exact"),
				}
			)
		with self.assertRaisesRegex(frappe.ValidationError, "usuario ya está vinculado"):
			create_entity(
				{
					"entity_type": "Individual",
					"display_name": "Usuario repetido",
					"linked_user": linked_user,
					"idempotency_key": _key("duplicate-user"),
				}
			)
		candidates = detect_entity_duplicates(
			{
				"display_name": "Entidad Duplicada",
				"contacts": [{"contact_type": "Email", "contact_value": contact}],
			}
		)
		match = next(row for row in candidates if row["entity"] == original["name"])
		self.assertGreaterEqual(match["score"], 55)
		self.assertIn("contacto coincidente", match["reasons"])
		self.assertIn("nombre normalizado coincidente", match["reasons"])

	def test_compliance_requires_validated_evidence_and_creates_audit(self) -> None:
		entity, _ = self._create(name=f"Entidad cumplimiento {uuid.uuid4().hex[:8]}")
		self._activate(str(entity["name"]))
		frappe.set_user(self.manager)
		compliance = create_entity_compliance(
			{
				"entity": entity["name"],
				"compliance_type": "Tax",
				"valid_from": "2026-01-01",
				"valid_until": "2026-12-31",
				"idempotency_key": _key("compliance-create"),
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "evidencia validada"):
			transition_entity_compliance(
				str(compliance["compliance"]),
				"Current",
				_key("compliance-without-evidence"),
			)
		evidence = self._validated_evidence("tax")
		frappe.set_user(self.manager)
		current = transition_entity_compliance(
			str(compliance["compliance"]),
			"Current",
			_key("compliance-current"),
			notes="RTN revisado.",
			evidence=evidence,
		)
		self.assertEqual("Current", current["status"])
		self.assertEqual(
			evidence, frappe.db.get_value("NXR Entity Compliance", compliance["compliance"], "evidence")
		)
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Entity Compliance", "reference_name": compliance["compliance"]},
			)
		)

	def test_consolidation_preserves_references_and_redirects_to_canonical_entity(self) -> None:
		source, _ = self._create(name=f"Entidad origen {uuid.uuid4().hex[:8]}")
		target, _ = self._create(name=f"Entidad destino {uuid.uuid4().hex[:8]}")
		self._activate(str(source["name"]))
		self._activate(str(target["name"]))
		frappe.set_user(self.manager)
		role = assign_entity_role(
			{
				"entity": source["name"],
				"role_type": "Supplier",
				"valid_from": "2026-01-01",
				"idempotency_key": _key("source-role"),
			}
		)
		compliance = create_entity_compliance(
			{
				"entity": source["name"],
				"compliance_type": "Identity",
				"idempotency_key": _key("source-compliance"),
			}
		)
		before = {
			"identifiers": frappe.db.count("NXR Entity Identifier", {"parent": source["name"]}),
			"contacts": frappe.db.count("NXR Entity Contact", {"parent": source["name"]}),
			"roles": frappe.db.count("NXR Entity Role", {"entity": source["name"]}),
			"compliance": frappe.db.count("NXR Entity Compliance", {"entity": source["name"]}),
		}
		result = consolidate_entities(
			str(source["name"]),
			str(target["name"]),
			"Duplicado confirmado mediante revisión humana.",
			_key("entity-consolidation"),
		)
		self.assertEqual(before, result["preserved_references"])
		self.assertTrue(frappe.db.exists("NXR Entity", source["name"]))
		self.assertEqual("Consolidated", frappe.db.get_value("NXR Entity", source["name"], "status"))
		self.assertEqual(target["name"], frappe.db.get_value("NXR Entity", source["name"], "merged_into"))
		self.assertEqual(source["name"], frappe.db.get_value("NXR Entity Role", role["role"], "entity"))
		self.assertEqual(
			source["name"], frappe.db.get_value("NXR Entity Compliance", compliance["compliance"], "entity")
		)
		resolved = resolve_canonical_entity(str(source["name"]))
		self.assertEqual(target["name"], resolved["canonical"])
		self.assertEqual([source["name"], target["name"]], resolved["chain"])
		frappe.set_user(self.viewer)
		redirected = get_entity(str(source["name"]))
		self.assertEqual(target["name"], redirected["canonical_entity"])
		self.assertEqual(1, redirected["redirected"])
		matches = search_entities(query=str(source["display_name"]))
		source_row = next(row for row in matches if row["name"] == source["name"])
		self.assertEqual(target["name"], source_row["canonical_entity"])
		self.assertTrue(
			frappe.db.exists(
				"NXR Audit Event",
				{"reference_doctype": "NXR Entity Consolidation", "reference_name": result["consolidation"]},
			)
		)


if __name__ == "__main__":
	import unittest

	unittest.main()
