from __future__ import annotations

import json
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.construcontrol.audit import record_manual_event
from erpnext.construcontrol.tests.runtime_smoke import (
    run as run_construcontrol_runtime_smoke,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# The two inherited Pick List packed-item tests use RJ Warehouse but do not
# declare it as their own fixture. Running this module before the sharded suite
# makes that shared dependency explicit and independent from test ordering.
test_dependencies = ["Warehouse"]


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
            frappe.delete_doc(
                "CC Audit Log", event.name, ignore_permissions=True, force=True
            )
