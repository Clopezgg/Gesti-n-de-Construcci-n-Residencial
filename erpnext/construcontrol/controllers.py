from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.construcontrol.access import validate_document_project_access
from erpnext.construcontrol.business_rules import expense_amounts, funding_balances

INCOMING_MOVEMENTS = {"adjustment_in"}
OUTGOING_MOVEMENTS = {"consumption", "adjustment_out"}
ALLOWED_MOVEMENTS = INCOMING_MOVEMENTS | OUTGOING_MOVEMENTS


class ConstruControlDocument(Document):
	"""Base validation shared by operational ConstruControl records."""

	def validate(self) -> None:
		validate_document_project_access(self)
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


def _expense_amount_tuple(row: Any) -> tuple[float, float, float]:
	return expense_amounts(
		row.get("amount_hnl"),
		row.get("payment_status"),
		row.get("financial_status"),
		row.get("paid_amount_hnl"),
		row.get("balance_due_hnl"),
		row.get("professional_approval_status"),
	)


def _expense_totals(
	link_field: str,
	link_name: str,
	exclude_name: str | None = None,
) -> tuple[float, float, float]:
	rows = frappe.get_all(
		"CC Expense Control",
		filters={link_field: link_name, "is_logically_deleted": 0},
		fields=[
			"name",
			"amount_hnl",
			"financial_status",
			"payment_status",
			"paid_amount_hnl",
			"balance_due_hnl",
			"professional_approval_status",
		],
	)
	recognized = paid = pending = 0.0
	for row in rows:
		if exclude_name and row.name == exclude_name:
			continue
		row_recognized, row_paid, row_pending = _expense_amount_tuple(row)
		recognized += row_recognized
		paid += row_paid
		pending += row_pending
	return round(recognized, 2), round(paid, 2), round(pending, 2)


def recalculate_funding_source(name: str, exclude_name: str | None = None) -> None:
	if not name or not frappe.db.exists("CC Funding Source", name):
		return
	_recognized, paid, pending = _expense_totals("funding_source", name, exclude_name=exclude_name)
	values = frappe.db.get_value(
		"CC Funding Source",
		name,
		["net_amount_hnl", "amount_hnl", "status", "reconciliation_status"],
		as_dict=True,
	)
	try:
		balances = funding_balances(
			values.net_amount_hnl or values.amount_hnl,
			values.status,
			values.reconciliation_status,
			paid,
			pending,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	frappe.db.set_value(
		"CC Funding Source",
		name,
		{field: balances[field] for field in ("spent_hnl", "pending_hnl", "available_hnl", "projected_hnl")},
		update_modified=False,
	)


def recalculate_contract(name: str, exclude_name: str | None = None) -> None:
	if not name or not frappe.db.exists("CC Labor Contract", name):
		return
	_recognized, paid, _pending = _expense_totals("labor_contract", name, exclude_name=exclude_name)
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
	validate_document_project_access(doc)
	amount = flt(doc.get("net_amount_hnl") or doc.get("amount_hnl"))
	_recognized, paid, pending = (
		_expense_totals("funding_source", doc.name) if not doc.is_new() else (0.0, 0.0, 0.0)
	)
	try:
		balances = funding_balances(
			amount,
			doc.get("status"),
			doc.get("reconciliation_status"),
			paid,
			pending,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	doc.status = balances["status"]
	doc.reconciliation_status = balances["reconciliation_status"]
	doc.spent_hnl = balances["spent_hnl"]
	doc.pending_hnl = balances["pending_hnl"]
	doc.available_hnl = balances["available_hnl"]
	doc.projected_hnl = balances["projected_hnl"]


def validate_expense_control(doc: Document, method: str | None = None) -> None:
	validate_document_project_access(doc)
	amount = flt(doc.get("amount_hnl"))
	if amount < 0:
		frappe.throw(_("El monto no puede ser negativo."))
	if not doc.get("provider_name"):
		frappe.throw(_("Indique el proveedor o contratista."))

	if doc.get("funding_source"):
		fund_project = frappe.db.get_value("CC Funding Source", doc.funding_source, "project")
		if fund_project and doc.get("project") and fund_project != doc.project:
			frappe.throw(_("La fuente de fondos pertenece a otro proyecto."))

		_current_recognized, current_paid, current_pending = _expense_amount_tuple(doc)
		_other_recognized, other_paid, other_pending = _expense_totals(
			"funding_source",
			doc.funding_source,
			exclude_name=doc.name,
		)
		fund = frappe.db.get_value(
			"CC Funding Source",
			doc.funding_source,
			["net_amount_hnl", "amount_hnl", "status", "reconciliation_status"],
			as_dict=True,
		)
		try:
			funding_balances(
				fund.net_amount_hnl or fund.amount_hnl,
				fund.status,
				fund.reconciliation_status,
				other_paid + current_paid,
				other_pending + current_pending,
			)
		except ValueError as exc:
			frappe.throw(_(str(exc)))

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
	validate_document_project_access(doc)
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
	validate_document_project_access(doc)
	if flt(doc.get("initial_qty")) < 0:
		frappe.throw(_("La existencia inicial no puede ser negativa."))
	if not doc.is_new():
		movement_balance = get_material_balance(doc.name) - flt(
			frappe.db.get_value(doc.doctype, doc.name, "initial_qty")
		)
		resulting_balance = flt(doc.get("initial_qty")) + movement_balance
		if resulting_balance < 0:
			frappe.throw(_("La nueva existencia inicial produciría un inventario negativo."))


def validate_inventory_movement(doc: Document, method: str | None = None) -> None:
	validate_document_project_access(doc)
	if not doc.get("material"):
		frappe.throw(_("Seleccione un material."))
	material_project = frappe.db.get_value("CC Material Ledger", doc.material, "project")
	if material_project and doc.get("project") and material_project != doc.project:
		frappe.throw(_("El material seleccionado pertenece a otro proyecto."))
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
