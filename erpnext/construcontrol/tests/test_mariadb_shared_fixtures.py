from __future__ import annotations

import json
import uuid
from typing import Any

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.construcontrol.audit import record_manual_event
from erpnext.construcontrol.construction import _calculate_project_control
from erpnext.construcontrol.tests.runtime_smoke import (
	_ensure_test_company,
)
from erpnext.construcontrol.tests.runtime_smoke import (
	run as run_construcontrol_runtime_smoke,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# The two inherited Pick List packed-item tests use RJ Warehouse but do not
# declare it as their own fixture. Running this module before the sharded suite
# makes that shared dependency explicit and independent from test ordering.
test_dependencies = ["Warehouse"]


def _insert_runtime_doc(doctype: str, values: dict[str, Any]) -> Any:
	doc = frappe.new_doc(doctype)
	for fieldname, value in values.items():
		if fieldname == "doctype" or doc.meta.has_field(fieldname):
			doc.set(fieldname, value)
	for field in doc.meta.fields:
		if not field.reqd or doc.get(field.fieldname):
			continue
		if field.fieldtype in {"Data", "Small Text", "Text", "Long Text"}:
			doc.set(field.fieldname, f"CI {doctype}")
		elif field.fieldtype in {"Date", "Datetime"}:
			doc.set(field.fieldname, today())
		elif field.fieldtype in {"Currency", "Float", "Int"}:
			doc.set(field.fieldname, 1)
		elif field.fieldtype == "Select":
			options = [option.strip() for option in str(field.options or "").splitlines() if option.strip()]
			if options:
				doc.set(field.fieldname, options[0])
	return doc.insert(ignore_permissions=True)


class TestMariaDBSharedFixtures(FrappeTestCase):
	def test_prepare_pick_list_warehouse(self) -> None:
		warehouse = create_warehouse("RJ Warehouse")
		self.assertEqual(warehouse, "RJ Warehouse - _TC")

	def test_construcontrol_finance_permissions_and_runtime_contract(self) -> None:
		result = run_construcontrol_runtime_smoke()
		self.assertTrue(result["ok"])
		self.assertEqual(result["funding_net_hnl"], 1000.0)
		self.assertEqual(result["expense_total_hnl"], 250.0)
		self.assertEqual(result["available_hnl"], 750.0)
		self.assertEqual(result["payable_status"], "paid")
		self.assertGreaterEqual(result["permission_denials"], 2)

	def test_audit_runtime_is_idempotent_immutable_and_secret_free(self) -> None:
		marker = f"AUDIT-CI-{uuid.uuid4().hex[:12]}"
		payload = {
			"amount_hnl": 250,
			"api_secret": "must-not-be-persisted",
			"nested": {"access_token": "must-not-be-persisted", "status": "approved"},
		}
		for _ in range(2):
			record_manual_event(
				module="AU01",
				action="UPDATE",
				record_type="CC Expense Control",
				record_id=marker,
				reason="Prueba runtime de auditoría",
				next_state=payload,
				origin="CI",
				correlation_id=marker,
			)

		rows = frappe.get_all(
			"CC Audit Log",
			filters={"record_type": "CC Expense Control", "record_id": marker},
			pluck="name",
		)
		self.assertEqual(len(rows), 1)
		event = frappe.get_doc("CC Audit Log", rows[0])
		self.assertEqual(event.action, "UPDATE")
		self.assertEqual(event.module, "AU01")
		self.assertEqual(event.origin, "CI")
		self.assertEqual(event.correlation_id, marker)
		self.assertEqual(len(event.fingerprint), 64)

		next_state = json.loads(event.next_state)
		self.assertEqual(next_state["amount_hnl"], 250)
		self.assertEqual(next_state["nested"]["status"], "approved")
		self.assertNotIn("api_secret", next_state)
		self.assertNotIn("access_token", next_state["nested"])
		self.assertNotIn("must-not-be-persisted", event.payload_json or "")

		event.description = "Mutación prohibida"
		with self.assertRaises(frappe.PermissionError):
			event.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("CC Audit Log", event.name, ignore_permissions=True, force=True)

	def test_inventory_quality_contract_and_project_runtime(self) -> None:
		marker = uuid.uuid4().hex[:12]
		frappe.set_user("Administrator")
		company = _ensure_test_company(marker)
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": f"ConstruControl Operations {marker}",
				"status": "Open",
				"is_active": "Yes",
				"company": company,
			}
		).insert(ignore_permissions=True)

		profile = _insert_runtime_doc(
			"CC Project Profile",
			{
				"source_id": f"PROFILE-{marker}",
				"project": project.name,
				"title": f"Perfil {marker}",
				"project_name": f"Proyecto {marker}",
				"original_budget_hnl": 2000,
				"updated_budget_hnl": 2000,
			},
		)
		phase = _insert_runtime_doc(
			"CC Construction Phase",
			{
				"source_id": f"PHASE-{marker}",
				"project": project.name,
				"title": f"Fase {marker}",
				"phase_name": f"Fase {marker}",
				"status": "active",
				"start_date": today(),
				"target_end_date": today(),
				"budget_hnl": 2000,
				"progress_percent": 25,
			},
		)
		_insert_runtime_doc(
			"CC Labor Contract",
			{
				"source_id": f"CONTRACT-{marker}",
				"project": project.name,
				"phase": phase.name,
				"title": f"Contrato {marker}",
				"contract_code": f"CI-{marker}",
				"contractor_name": "Contratista CI",
				"status": "active",
				"project_value_hnl": 1000,
				"labor_value_hnl": 1000,
			},
		)
		control = _calculate_project_control(project.name, persist=False)
		self.assertEqual(control["profile"], profile.name)
		self.assertEqual(control["updated_budget_hnl"], 2000.0)
		self.assertEqual(control["committed_hnl"], 1000.0)
		self.assertEqual(control["available_budget_hnl"], 1000.0)

		material = _insert_runtime_doc(
			"CC Material Ledger",
			{
				"source_id": f"MATERIAL-{marker}",
				"project": project.name,
				"title": f"Cemento {marker}",
				"material_name": f"Cemento {marker}",
				"unit": "SACO",
				"initial_qty": 10,
				"initial_unit_cost_hnl": 200,
				"unit_cost_hnl": 200,
			},
		)
		_insert_runtime_doc(
			"CC Inventory Movement",
			{
				"source_id": f"MOVE-{marker}",
				"project": project.name,
				"title": f"Consumo {marker}",
				"posting_date": today(),
				"material": material.name,
				"movement_type": "consumption",
				"quantity": 3,
				"unit_cost_hnl": 200,
			},
		)
		material.reload()
		self.assertEqual(float(material.current_qty or 0), 7.0)
		with self.assertRaises(frappe.ValidationError):
			_insert_runtime_doc(
				"CC Inventory Movement",
				{
					"source_id": f"NEGATIVE-{marker}",
					"project": project.name,
					"title": f"Salida inválida {marker}",
					"posting_date": today(),
					"material": material.name,
					"movement_type": "consumption",
					"quantity": 99,
				},
			)

		progress = _insert_runtime_doc(
			"CC Progress Update",
			{
				"source_id": f"PROGRESS-{marker}",
				"project": project.name,
				"phase": phase.name,
				"title": f"Avance {marker}",
				"posting_date": today(),
				"progress_percent": 25,
				"progress_status": "submitted",
				"quality_status": "failed",
				"observations": "Fisura detectada",
				"alert_level": "attention",
				"incident_status": "open",
				"corrective_action": "Reparar y reinspeccionar",
			},
		)
		self.assertEqual(progress.quality_status, "failed")
		self.assertEqual(progress.alert_level, "attention")
		with self.assertRaises(frappe.ValidationError):
			_insert_runtime_doc(
				"CC Progress Update",
				{
					"project": project.name,
					"phase": phase.name,
					"title": f"Avance inválido {marker}",
					"posting_date": today(),
					"responsible_user": "Administrator",
					"progress_percent": 30,
					"progress_status": "submitted",
					"quality_status": "failed",
					"alert_level": "normal",
				},
			)
