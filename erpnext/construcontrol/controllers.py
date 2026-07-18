from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

INCOMING_MOVEMENTS = {"adjustment_in"}
OUTGOING_MOVEMENTS = {"consumption", "adjustment_out"}
ALLOWED_MOVEMENTS = INCOMING_MOVEMENTS | OUTGOING_MOVEMENTS
INACTIVE_FINANCIAL_STATES = {"cancelled", "reimbursed"}


class ConstruControlDocument(Document):
    """Base validation shared by operational ConstruControl records."""

    def validate(self) -> None:
        if self.meta.has_field("amount_hnl") and flt(self.get("amount_hnl")) < 0:
            frappe.throw(_("El monto no puede ser negativo."))
        if self.meta.has_field("quantity") and flt(self.get("quantity")) < 0:
            frappe.throw(_("La cantidad no puede ser negativa."))


class CCFundingSource(ConstruControlDocument):
    def validate(self) -> None:
        super().validate()
        validate_funding_source(self)


class CCExpenseControl(ConstruControlDocument):
    def validate(self) -> None:
        super().validate()
        validate_expense_control(self)

    def on_update(self) -> None:
        update_expense_relations(self)

    def on_trash(self) -> None:
        remove_expense_relations(self)


class CCLaborContract(ConstruControlDocument):
    def validate(self) -> None:
        super().validate()
        validate_labor_contract(self)


class CCMaterialLedger(ConstruControlDocument):
    def validate(self) -> None:
        super().validate()
        validate_material_ledger(self)


class CCInventoryMovement(ConstruControlDocument):
    def validate(self) -> None:
        super().validate()
        validate_inventory_movement(self)

    def on_update(self) -> None:
        update_inventory_balance(self)

    def on_trash(self) -> None:
        remove_inventory_balance(self)


def _expense_is_active(row: Any) -> bool:
    return not bool(row.get("is_logically_deleted")) and row.get("financial_status") not in INACTIVE_FINANCIAL_STATES


def _expense_totals(funding_source: str, exclude_name: str | None = None) -> tuple[float, float]:
    rows = frappe.get_all(
        "CC Expense Control",
        filters={"funding_source": funding_source, "is_logically_deleted": 0},
        fields=["name", "amount_hnl", "financial_status", "status", "is_logically_deleted"],
    )
    spent = 0.0
    pending = 0.0
    for row in rows:
        if exclude_name and row.name == exclude_name:
            continue
        if not _expense_is_active(row):
            continue
        amount = flt(row.amount_hnl)
        if row.status == "pending" or row.financial_status == "pending":
            pending += amount
        else:
            spent += amount
    return spent, pending


def recalculate_funding_source(name: str, exclude_name: str | None = None) -> None:
    if not name or not frappe.db.exists("CC Funding Source", name):
        return
    spent, pending = _expense_totals(name, exclude_name=exclude_name)
    amount = flt(frappe.db.get_value("CC Funding Source", name, "amount_hnl"))
    frappe.db.set_value(
        "CC Funding Source",
        name,
        {
            "spent_hnl": spent,
            "pending_hnl": pending,
            "available_hnl": amount - spent,
            "projected_hnl": amount - spent - pending,
        },
        update_modified=False,
    )


def recalculate_contract(name: str, exclude_name: str | None = None) -> None:
    if not name or not frappe.db.exists("CC Labor Contract", name):
        return
    rows = frappe.get_all(
        "CC Expense Control",
        filters={"labor_contract": name, "is_logically_deleted": 0},
        fields=["name", "amount_hnl", "financial_status", "is_logically_deleted"],
    )
    paid = sum(
        flt(row.amount_hnl)
        for row in rows
        if row.name != exclude_name and _expense_is_active(row) and row.financial_status != "pending"
    )
    value = flt(
        frappe.db.get_value("CC Labor Contract", name, "project_value_hnl")
        or frappe.db.get_value("CC Labor Contract", name, "labor_value_hnl")
    )
    frappe.db.set_value(
        "CC Labor Contract",
        name,
        {"paid_hnl": paid, "balance_hnl": value - paid},
        update_modified=False,
    )


def _movement_effect(movement_type: str, quantity: float) -> float:
    if movement_type in INCOMING_MOVEMENTS:
        return flt(quantity)
    if movement_type in OUTGOING_MOVEMENTS:
        return -flt(quantity)
    frappe.throw(_("Tipo de movimiento de inventario no permitido: {0}").format(movement_type or "vacío"))
    return 0.0


def get_material_balance(material: str, exclude_name: str | None = None) -> float:
    initial = flt(frappe.db.get_value("CC Material Ledger", material, "initial_qty"))
    rows = frappe.get_all(
        "CC Inventory Movement",
        filters={"material": material, "is_logically_deleted": 0},
        fields=["name", "movement_type", "quantity"],
    )
    balance = initial
    for row in rows:
        if exclude_name and row.name == exclude_name:
            continue
        balance += _movement_effect(str(row.movement_type or ""), flt(row.quantity))
    return balance


def refresh_material_balance(material: str, exclude_name: str | None = None) -> None:
    if not material or not frappe.db.exists("CC Material Ledger", material):
        return
    balance = get_material_balance(material, exclude_name=exclude_name)
    threshold = flt(frappe.db.get_value("CC Material Ledger", material, "low_stock_threshold") or 0)
    status = "depleted" if balance <= 0 else "low" if threshold and balance <= threshold else "available"
    frappe.db.set_value(
        "CC Material Ledger",
        material,
        {"current_qty": balance, "stock_status": status},
        update_modified=False,
    )


# Runtime-created operational DocTypes use document event hooks because custom
# DocTypes do not load controller classes directly from this filesystem.
def validate_funding_source(doc: Document, method: str | None = None) -> None:
    amount = flt(doc.get("amount_hnl"))
    if amount < 0:
        frappe.throw(_("El monto recibido no puede ser negativo."))

    spent, pending = _expense_totals(doc.name, exclude_name=None) if not doc.is_new() else (0.0, 0.0)
    if amount < spent:
        frappe.throw(
            _("El ingreso no puede reducirse por debajo del gasto ejecutado de {0}.").format(
                frappe.format_value(spent, {"fieldtype": "Currency", "options": "HNL"})
            )
        )
    doc.spent_hnl = spent
    doc.pending_hnl = pending
    doc.available_hnl = amount - spent
    doc.projected_hnl = amount - spent - pending


def validate_expense_control(doc: Document, method: str | None = None) -> None:
    amount = flt(doc.get("amount_hnl"))
    if amount < 0:
        frappe.throw(_("El monto no puede ser negativo."))
    if not doc.get("provider_name"):
        frappe.throw(_("Indique el proveedor o contratista."))

    if doc.get("funding_source"):
        fund_project = frappe.db.get_value("CC Funding Source", doc.funding_source, "project")
        if fund_project and doc.get("project") and fund_project != doc.project:
            frappe.throw(_("La fuente de fondos pertenece a otro proyecto."))

        if not doc.get("is_logically_deleted") and doc.get("financial_status") not in INACTIVE_FINANCIAL_STATES:
            spent, pending = _expense_totals(doc.funding_source, exclude_name=doc.name)
            fund_amount = flt(frappe.db.get_value("CC Funding Source", doc.funding_source, "amount_hnl"))
            projected = fund_amount - spent - pending - amount
            if projected < 0:
                frappe.throw(
                    _("El gasto supera el saldo disponible y pendiente de la fuente FI01 por {0}.").format(
                        frappe.format_value(abs(projected), {"fieldtype": "Currency", "options": "HNL"})
                    )
                )

    if doc.get("labor_contract"):
        contract_project = frappe.db.get_value("CC Labor Contract", doc.labor_contract, "project")
        if contract_project and doc.get("project") and contract_project != doc.project:
            frappe.throw(_("El contrato pertenece a otro proyecto."))


def _old_value(doc: Document, fieldname: str) -> Any:
    previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
    return previous.get(fieldname) if previous else None


def update_expense_relations(doc: Document, method: str | None = None) -> None:
    funds = {value for value in (doc.get("funding_source"), _old_value(doc, "funding_source")) if value}
    contracts = {value for value in (doc.get("labor_contract"), _old_value(doc, "labor_contract")) if value}
    for name in funds:
        recalculate_funding_source(name)
    for name in contracts:
        recalculate_contract(name)


def remove_expense_relations(doc: Document, method: str | None = None) -> None:
    if doc.get("funding_source"):
        recalculate_funding_source(doc.funding_source, exclude_name=doc.name)
    if doc.get("labor_contract"):
        recalculate_contract(doc.labor_contract, exclude_name=doc.name)


def validate_labor_contract(doc: Document, method: str | None = None) -> None:
    project_value = flt(doc.get("project_value_hnl"))
    labor_value = flt(doc.get("labor_value_hnl"))
    paid = flt(doc.get("paid_hnl"))
    if project_value < 0 or labor_value < 0:
        frappe.throw(_("Los valores contractuales no pueden ser negativos."))
    value = project_value or labor_value
    if value < paid:
        frappe.throw(_("El valor contractual no puede ser menor que el monto ya pagado."))
    doc.balance_hnl = value - paid


def validate_material_ledger(doc: Document, method: str | None = None) -> None:
    if flt(doc.get("initial_qty")) < 0:
        frappe.throw(_("La existencia inicial no puede ser negativa."))
    if not doc.is_new():
        movement_balance = get_material_balance(doc.name) - flt(frappe.db.get_value(doc.doctype, doc.name, "initial_qty"))
        resulting_balance = flt(doc.get("initial_qty")) + movement_balance
        if resulting_balance < 0:
            frappe.throw(_("La nueva existencia inicial produciría un inventario negativo."))


def validate_inventory_movement(doc: Document, method: str | None = None) -> None:
    if not doc.get("material"):
        frappe.throw(_("Seleccione un material."))
    if doc.get("movement_type") not in ALLOWED_MOVEMENTS:
        frappe.throw(_("Seleccione un tipo de movimiento válido."))
    quantity = flt(doc.get("quantity"))
    if quantity <= 0:
        frappe.throw(_("La cantidad debe ser mayor que cero."))
    if doc.get("movement_type") in OUTGOING_MOVEMENTS:
        available = get_material_balance(doc.material, exclude_name=doc.name)
        if quantity > available:
            frappe.throw(
                _("La salida de {0} supera la existencia disponible de {1}.").format(
                    frappe.bold(quantity), frappe.bold(available)
                )
            )


def update_inventory_balance(doc: Document, method: str | None = None) -> None:
    materials = {value for value in (doc.get("material"), _old_value(doc, "material")) if value}
    for material in materials:
        refresh_material_balance(material)


def remove_inventory_balance(doc: Document, method: str | None = None) -> None:
    if doc.get("material"):
        refresh_material_balance(doc.material, exclude_name=doc.name)
