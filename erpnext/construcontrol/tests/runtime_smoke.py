from __future__ import annotations

import json
import uuid

import frappe
from frappe.utils import today

_REQUIRED_PAGES = (
    "construcontrol-dashboard",
    "construcontrol-profile",
    "construcontrol-project-center",
    "construcontrol-users",
    "construcontrol-integrations",
    "construcontrol-reporting-center",
    "construcontrol-weekly-closing",
    "construcontrol-migration-console",
)

_REQUIRED_DOCTYPES = (
    "CC Funding Source",
    "CC Expense Control",
    "CC Payable Control",
    "CC Construction Phase",
    "CC Labor Contract",
    "CC Material Ledger",
    "CC Inventory Movement",
    "CC Progress Update",
    "CC Weekly Closing",
    "CC Audit Log",
    "CC Financial Institution",
    "CC Integration Registry",
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run() -> dict[str, object]:
    """Execute real CRUD and accounting relations inside one rolled-back transaction."""
    frappe.set_user("Administrator")
    marker = uuid.uuid4().hex[:12]
    try:
        for page in _REQUIRED_PAGES:
            _assert(bool(frappe.db.exists("Page", page)), f"Missing runtime page: {page}")
        for doctype in _REQUIRED_DOCTYPES:
            _assert(bool(frappe.db.exists("DocType", doctype)), f"Missing runtime DocType: {doctype}")

        project = frappe.get_doc(
            {
                "doctype": "Project",
                "project_name": f"ConstruControl CI {marker}",
                "status": "Open",
                "is_active": "Yes",
            }
        ).insert(ignore_permissions=True)

        fund = frappe.get_doc(
            {
                "doctype": "CC Funding Source",
                "project": project.name,
                "title": f"Ingreso CI {marker}",
                "income_type": "personal",
                "status": "received",
                "date_received": today(),
                "currency": "HNL",
                "original_amount": 1000,
                "exchange_rate": 1,
                "amount_hnl": 1000,
                "transaction_channel": "cash",
                "financial_institution": "CASH",
                "gross_amount": 1000,
                "fee_amount": 0,
                "original_currency": "HNL",
                "treasury_exchange_rate": 1,
                "reconciliation_status": "verified",
            }
        ).insert(ignore_permissions=True)
        _assert(float(fund.net_amount_hnl or 0) == 1000.0, "FI01 net amount was not calculated")

        expense = frappe.get_doc(
            {
                "doctype": "CC Expense Control",
                "project": project.name,
                "title": f"Gasto CI {marker}",
                "posting_date": today(),
                "category": "service",
                "provider_name": "Proveedor CI",
                "amount_hnl": 250,
                "subtotal_hnl": 250,
                "funding_source": fund.name,
                "professional_approval_status": "approved",
                "payment_status": "paid",
                "paid_amount_hnl": 250,
                "payment_reference": f"CI-PAY-{marker}",
            }
        ).insert(ignore_permissions=True)
        _assert(float(expense.calculated_total_hnl or 0) == 250.0, "FI02 total was not calculated")
        _assert(float(expense.balance_due_hnl or 0) == 0.0, "FI02 paid balance is inconsistent")

        payable = frappe.db.get_value(
            "CC Payable Control",
            {"source_key": f"expense-payable:{expense.name}"},
            ["name", "payable_status", "balance_due_hnl"],
            as_dict=True,
        )
        _assert(bool(payable), "FI03 payable was not synchronized")
        _assert(payable.payable_status == "paid", "FI03 payable status is inconsistent")
        _assert(float(payable.balance_due_hnl or 0) == 0.0, "FI03 balance is inconsistent")

        fund.reload()
        _assert(float(fund.spent_hnl or 0) == 250.0, "FI01 spent balance was not reconciled")
        _assert(float(fund.available_hnl or 0) == 750.0, "FI01 available balance was not reconciled")

        result = {
            "ok": True,
            "pages": len(_REQUIRED_PAGES),
            "doctypes": len(_REQUIRED_DOCTYPES),
            "funding_net_hnl": float(fund.net_amount_hnl or 0),
            "spent_hnl": float(fund.spent_hnl or 0),
            "available_hnl": float(fund.available_hnl or 0),
            "expense_total_hnl": float(expense.calculated_total_hnl or 0),
            "payable_status": payable.payable_status,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return result
    finally:
        frappe.db.rollback()


def create_persistence_marker(marker: str = "") -> str:
    frappe.set_user("Administrator")
    marker = str(marker or "").strip() or f"CONSTRUCONTROL-CI-{uuid.uuid4().hex}"
    existing = frappe.get_all("ToDo", filters={"description": marker}, pluck="name")
    for name in existing:
        frappe.delete_doc("ToDo", name, ignore_permissions=True, force=True)
    frappe.get_doc({"doctype": "ToDo", "description": marker, "status": "Open"}).insert(ignore_permissions=True)
    frappe.db.commit()
    print(marker)
    return marker


def verify_and_cleanup_persistence_marker(marker: str) -> dict[str, object]:
    frappe.set_user("Administrator")
    marker = str(marker or "").strip()
    name = frappe.db.get_value("ToDo", {"description": marker}, "name")
    _assert(bool(name), "Persistence marker disappeared after container restart")
    frappe.delete_doc("ToDo", name, ignore_permissions=True, force=True)
    frappe.db.commit()
    result = {"ok": True, "marker": marker, "persisted": True, "cleaned": True}
    print(json.dumps(result, sort_keys=True))
    return result
