from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from erpnext.construcontrol.business_rules import normalize_expense_state

_ALLOWED_PAYMENT_STATES = {
    "draft",
    "pending_approval",
    "approved",
    "partially_paid",
    "paid",
    "overdue",
    "cancelled",
    "reimbursed",
}
_ALLOWED_APPROVAL_STATES = {"draft", "pending", "approved", "rejected"}
_INACTIVE_STATES = {"cancelled", "reimbursed"}


def _has_field(doc: Document, fieldname: str) -> bool:
    return bool(doc.meta.has_field(fieldname))


def _calculated_total(doc: Document) -> float:
    subtotal = flt(doc.get("subtotal_hnl") or doc.get("amount_hnl"))
    tax = flt(doc.get("tax_hnl"))
    withholding = flt(doc.get("withholding_hnl"))
    discount = flt(doc.get("discount_hnl"))
    for label, amount in (
        (_("Subtotal"), subtotal),
        (_("Impuestos"), tax),
        (_("Retenciones"), withholding),
        (_("Descuentos"), discount),
    ):
        if amount < 0:
            frappe.throw(_("{0} no puede ser negativo.").format(label))
    total = subtotal + tax - withholding - discount
    if total < 0:
        frappe.throw(_("Las retenciones y descuentos no pueden superar el subtotal más impuestos."))
    return total


def _validate_duplicate_invoice(doc: Document) -> None:
    invoice = str(doc.get("invoice_number") or "").strip()
    if not invoice:
        return
    supplier = doc.get("supplier")
    provider = str(doc.get("provider_name") or "").strip()
    filters: dict[str, Any] = {
        "invoice_number": invoice,
        "is_logically_deleted": 0,
        "name": ["!=", doc.name or ""],
    }
    if supplier:
        filters["supplier"] = supplier
    elif provider:
        filters["provider_name"] = provider
    duplicate = frappe.db.exists("CC Expense Control", filters)
    if duplicate:
        frappe.throw(
            _("La factura {0} ya está registrada para este proveedor en el gasto {1}.").format(
                frappe.bold(invoice), frappe.bold(duplicate)
            )
        )


def validate_professional_expense(doc: Document, method: str | None = None) -> None:
    if not _has_field(doc, "payment_status"):
        return

    total = _calculated_total(doc)
    paid = flt(doc.get("paid_amount_hnl"))
    if paid < 0:
        frappe.throw(_("El monto pagado no puede ser negativo."))
    if paid > total:
        frappe.throw(_("El monto pagado no puede superar el total del gasto."))

    payment_status = str(doc.get("payment_status") or "draft").strip().lower()
    approval_status = str(doc.get("professional_approval_status") or "draft").strip().lower()
    if payment_status not in _ALLOWED_PAYMENT_STATES:
        frappe.throw(_("Seleccione un estado de pago válido."))
    if approval_status not in _ALLOWED_APPROVAL_STATES:
        frappe.throw(_("Seleccione un estado de aprobación válido."))

    due_date = getdate(doc.get("due_date")) if doc.get("due_date") else None
    balance = total - paid
    if payment_status not in _INACTIVE_STATES:
        if balance <= 0 and total > 0:
            payment_status = "paid"
        elif paid > 0:
            payment_status = "partially_paid"
        elif due_date and due_date < getdate(today()) and approval_status == "approved":
            payment_status = "overdue"
        elif approval_status == "approved" and payment_status in {"draft", "pending_approval"}:
            payment_status = "approved"
        elif approval_status == "pending" and payment_status == "draft":
            payment_status = "pending_approval"

    if approval_status == "approved":
        if not doc.get("approved_by_user"):
            doc.approved_by_user = frappe.session.user
        if not doc.get("approved_at"):
            doc.approved_at = now_datetime()
        doc.approved_amount_hnl = total
    elif approval_status == "rejected":
        if not str(doc.get("rejection_reason") or "").strip():
            frappe.throw(_("Indique el motivo del rechazo."))
        doc.approved_amount_hnl = 0
    else:
        doc.approved_amount_hnl = 0
        doc.approved_by_user = None
        doc.approved_at = None

    if payment_status == "paid":
        if not doc.get("payment_date"):
            doc.payment_date = today()
        historical = bool(doc.get("source_id") or doc.get("source_key"))
        if not str(doc.get("payment_reference") or "").strip() and not historical:
            frappe.throw(_("Ingrese la referencia del pago."))

    doc.subtotal_hnl = flt(doc.get("subtotal_hnl") or total)
    doc.calculated_total_hnl = total
    doc.amount_hnl = total
    doc.paid_amount_hnl = paid
    doc.balance_due_hnl = balance
    doc.payment_status = payment_status
    doc.financial_status = {
        "draft": "pending",
        "pending_approval": "pending",
        "approved": "pending",
        "partially_paid": "paid",
        "paid": "paid",
        "overdue": "pending",
        "cancelled": "cancelled",
        "reimbursed": "reimbursed",
    }[payment_status]
    doc.status = "pending" if payment_status in {"draft", "pending_approval", "approved", "overdue"} else "active"
    _validate_duplicate_invoice(doc)


def _payable_status(doc: Document) -> str:
    status = str(doc.get("payment_status") or "draft")
    return {
        "partially_paid": "partial",
        "paid": "paid",
        "overdue": "overdue",
        "cancelled": "cancelled",
        "reimbursed": "reimbursed",
    }.get(status, "pending")


def sync_payable_from_expense(doc: Document, method: str | None = None) -> None:
    if not _has_field(doc, "balance_due_hnl") or doc.is_new():
        return
    source_key = f"expense-payable:{doc.name}"
    existing = frappe.db.get_value("CC Payable Control", {"source_key": source_key}, "name")
    payable = frappe.get_doc("CC Payable Control", existing) if existing else frappe.new_doc("CC Payable Control")
    values = {
        "source_key": source_key,
        "source_id": doc.name,
        "project": doc.get("project"),
        "code": doc.get("folio") or doc.name,
        "title": doc.get("description") or doc.get("provider_name") or doc.name,
        "status": _payable_status(doc),
        "posting_date": doc.get("posting_date"),
        "amount_hnl": flt(doc.get("balance_due_hnl")),
        "description": doc.get("notes"),
        "expense_control": doc.name,
        "supplier": doc.get("supplier"),
        "provider_name": doc.get("provider_name"),
        "invoice_number": doc.get("invoice_number"),
        "due_date": doc.get("due_date"),
        "original_amount_hnl": flt(doc.get("calculated_total_hnl") or doc.get("amount_hnl")),
        "paid_amount_hnl": flt(doc.get("paid_amount_hnl")),
        "balance_due_hnl": flt(doc.get("balance_due_hnl")),
        "payable_status": _payable_status(doc),
        "payload_json": frappe.as_json({"expense_control": doc.name}),
        "is_logically_deleted": 1 if doc.get("is_logically_deleted") or doc.get("payment_status") in _INACTIVE_STATES else 0,
    }
    for fieldname, value in values.items():
        if payable.meta.has_field(fieldname):
            payable.set(fieldname, value)
    if payable.is_new():
        payable.insert(ignore_permissions=True)
    else:
        payable.save(ignore_permissions=True)


def _explicit_legacy_state(doc: Document) -> str | None:
    """Map only explicit historical payment states; unknown data remains draft."""
    candidates: list[str] = []
    for fieldname in ("payment_status", "financial_status"):
        value = str(doc.get(fieldname) or "").strip().lower()
        if value:
            candidates.append(value)
    try:
        payload = frappe.parse_json(doc.get("payload_json") or "{}") or {}
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        for key in ("paymentStatus", "financialStatus"):
            value = str(payload.get(key) or "").strip().lower()
            if value:
                candidates.insert(0, value)

    for value in candidates:
        if value in {"paid", "partially_paid", "overdue", "cancelled", "reimbursed", "pending", "pending_approval", "approved"}:
            return value
    return None


def backfill_professional_expenses() -> dict[str, int]:
    """Reconcile already imported FI02 rows after professional fields are installed."""
    if not frappe.db.exists("DocType", "CC Expense Control"):
        return {"updated": 0, "payables": 0}

    updated = 0
    payables = 0
    names = frappe.get_all(
        "CC Expense Control",
        filters={"is_logically_deleted": 0},
        pluck="name",
    )
    previous_flag = getattr(frappe.flags, "in_construcontrol_migration", False)
    frappe.flags.in_construcontrol_migration = True
    try:
        for name in names:
            doc = frappe.get_doc("CC Expense Control", name)
            total = flt(doc.get("calculated_total_hnl") or doc.get("amount_hnl"))
            if total < 0:
                continue
            explicit = _explicit_legacy_state(doc)
            normalized = normalize_expense_state(explicit, total, doc.get("paid_amount_hnl"))
            state = str(normalized["payment_status"])
            approval = str(normalized["approval_status"])
            paid = flt(normalized["paid"])
            balance = flt(normalized["balance"])

            values = {
                "subtotal_hnl": flt(doc.get("subtotal_hnl")) or total,
                "calculated_total_hnl": total,
                "paid_amount_hnl": paid,
                "balance_due_hnl": balance,
                "payment_status": state,
                "professional_approval_status": approval,
                "approved_amount_hnl": total if approval == "approved" else 0.0,
            }
            changed = {
                key: value for key, value in values.items()
                if doc.meta.has_field(key) and doc.get(key) != value
            }
            if changed:
                frappe.db.set_value("CC Expense Control", name, changed, update_modified=False)
                updated += 1
                for key, value in changed.items():
                    doc.set(key, value)

            if explicit and state not in {"paid", "cancelled", "reimbursed", "draft"} and balance > 0:
                before = frappe.db.exists("CC Payable Control", {"source_key": f"expense-payable:{name}"})
                sync_payable_from_expense(doc)
                if not before:
                    payables += 1
    finally:
        frappe.flags.in_construcontrol_migration = previous_flag
    return {"updated": updated, "payables": payables}


def archive_payable_from_expense(doc: Document, method: str | None = None) -> None:
    name = frappe.db.get_value("CC Payable Control", {"expense_control": doc.name}, "name")
    if name:
        frappe.db.set_value(
            "CC Payable Control",
            name,
            {"is_logically_deleted": 1, "payable_status": "cancelled", "status": "cancelled"},
            update_modified=False,
        )


__all__ = ["archive_payable_from_expense", "backfill_professional_expenses", "sync_payable_from_expense", "validate_professional_expense"]
