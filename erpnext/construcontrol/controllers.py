from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ConstruControlDocument(Document):
	"""Base validation shared by the operational ConstruControl records."""

	def validate(self) -> None:
		if self.meta.has_field("amount_hnl") and flt(self.get("amount_hnl")) < 0:
			frappe.throw(_("El monto no puede ser negativo."))
		if self.meta.has_field("quantity") and flt(self.get("quantity")) < 0:
			frappe.throw(_("La cantidad no puede ser negativa."))


class CCFundingSource(ConstruControlDocument):
	def validate(self) -> None:
		super().validate()
		if flt(self.amount_hnl) < 0:
			frappe.throw(_("El monto recibido no puede ser negativo."))
		self.available_hnl = flt(self.amount_hnl) - flt(self.spent_hnl)
		self.projected_hnl = flt(self.available_hnl) - flt(self.pending_hnl)


class CCExpenseControl(ConstruControlDocument):
	def validate(self) -> None:
		super().validate()
		if not self.provider_name:
			frappe.throw(_("Indique el proveedor o contratista."))
		if self.funding_source:
			fund_project = frappe.db.get_value("CC Funding Source", self.funding_source, "project")
			if fund_project and self.project and fund_project != self.project:
				frappe.throw(_("La fuente de fondos pertenece a otro proyecto."))
		if self.labor_contract:
			contract_project = frappe.db.get_value("CC Labor Contract", self.labor_contract, "project")
			if contract_project and self.project and contract_project != self.project:
				frappe.throw(_("El contrato pertenece a otro proyecto."))

	def on_update(self) -> None:
		if self.funding_source:
			recalculate_funding_source(self.funding_source)
		if self.labor_contract:
			recalculate_contract(self.labor_contract)

	def on_trash(self) -> None:
		if self.funding_source:
			recalculate_funding_source(self.funding_source, exclude_name=self.name)
		if self.labor_contract:
			recalculate_contract(self.labor_contract, exclude_name=self.name)


class CCLaborContract(ConstruControlDocument):
	def validate(self) -> None:
		super().validate()
		if flt(self.project_value_hnl) < 0 or flt(self.labor_value_hnl) < 0:
			frappe.throw(_("Los valores contractuales no pueden ser negativos."))
		self.balance_hnl = flt(self.project_value_hnl or self.labor_value_hnl) - flt(self.paid_hnl)


class CCMaterialLedger(ConstruControlDocument):
	def validate(self) -> None:
		super().validate()
		if flt(self.initial_qty) < 0:
			frappe.throw(_("La existencia inicial no puede ser negativa."))


class CCInventoryMovement(ConstruControlDocument):
	def validate(self) -> None:
		super().validate()
		if not self.material:
			frappe.throw(_("Seleccione un material."))
		if flt(self.quantity) <= 0:
			frappe.throw(_("La cantidad debe ser mayor que cero."))
		if self.movement_type in {"consumption", "adjustment_out"}:
			available = get_material_balance(self.material, exclude_name=self.name)
			if flt(self.quantity) > available:
				frappe.throw(
					_("La salida de {0} supera la existencia disponible de {1}.").format(
						frappe.bold(self.quantity), frappe.bold(available)
					)
				)

	def on_update(self) -> None:
		refresh_material_balance(self.material)

	def on_trash(self) -> None:
		refresh_material_balance(self.material, exclude_name=self.name)


def recalculate_funding_source(name: str, exclude_name: str | None = None) -> None:
	filters = {"funding_source": name, "is_logically_deleted": 0}
	rows = frappe.get_all(
		"CC Expense Control",
		filters=filters,
		fields=["name", "amount_hnl", "financial_status", "status"],
	)
	spent = 0.0
	pending = 0.0
	for row in rows:
		if exclude_name and row.name == exclude_name:
			continue
		amount = flt(row.amount_hnl)
		if row.financial_status in {"cancelled", "reimbursed"}:
			continue
		if row.status == "pending" or row.financial_status == "pending":
			pending += amount
		else:
			spent += amount
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
	rows = frappe.get_all(
		"CC Expense Control",
		filters={"labor_contract": name, "is_logically_deleted": 0},
		fields=["name", "amount_hnl", "financial_status"],
	)
	paid = sum(
		flt(row.amount_hnl)
		for row in rows
		if row.name != exclude_name and row.financial_status not in {"pending", "cancelled", "reimbursed"}
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
		qty = flt(row.quantity)
		balance += qty if row.movement_type == "adjustment_in" else -qty
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


# Runtime-created operational DocTypes use these hooks because custom DocTypes
# do not load a Python controller class from the filesystem.
def validate_funding_source(doc: Document, method: str | None = None) -> None:
	if flt(doc.get("amount_hnl")) < 0:
		frappe.throw(_("El monto recibido no puede ser negativo."))
	doc.available_hnl = flt(doc.get("amount_hnl")) - flt(doc.get("spent_hnl"))
	doc.projected_hnl = flt(doc.get("available_hnl")) - flt(doc.get("pending_hnl"))


def validate_expense_control(doc: Document, method: str | None = None) -> None:
	if flt(doc.get("amount_hnl")) < 0:
		frappe.throw(_("El monto no puede ser negativo."))
	if not doc.get("provider_name"):
		frappe.throw(_("Indique el proveedor o contratista."))
	if doc.get("funding_source"):
		fund_project = frappe.db.get_value("CC Funding Source", doc.funding_source, "project")
		if fund_project and doc.get("project") and fund_project != doc.project:
			frappe.throw(_("La fuente de fondos pertenece a otro proyecto."))
	if doc.get("labor_contract"):
		contract_project = frappe.db.get_value("CC Labor Contract", doc.labor_contract, "project")
		if contract_project and doc.get("project") and contract_project != doc.project:
			frappe.throw(_("El contrato pertenece a otro proyecto."))


def update_expense_relations(doc: Document, method: str | None = None) -> None:
	if doc.get("funding_source"):
		recalculate_funding_source(doc.funding_source)
	if doc.get("labor_contract"):
		recalculate_contract(doc.labor_contract)


def remove_expense_relations(doc: Document, method: str | None = None) -> None:
	if doc.get("funding_source"):
		recalculate_funding_source(doc.funding_source, exclude_name=doc.name)
	if doc.get("labor_contract"):
		recalculate_contract(doc.labor_contract, exclude_name=doc.name)


def validate_labor_contract(doc: Document, method: str | None = None) -> None:
	if flt(doc.get("project_value_hnl")) < 0 or flt(doc.get("labor_value_hnl")) < 0:
		frappe.throw(_("Los valores contractuales no pueden ser negativos."))
	doc.balance_hnl = flt(doc.get("project_value_hnl") or doc.get("labor_value_hnl")) - flt(doc.get("paid_hnl"))


def validate_material_ledger(doc: Document, method: str | None = None) -> None:
	if flt(doc.get("initial_qty")) < 0:
		frappe.throw(_("La existencia inicial no puede ser negativa."))


def validate_inventory_movement(doc: Document, method: str | None = None) -> None:
	if not doc.get("material"):
		frappe.throw(_("Seleccione un material."))
	if flt(doc.get("quantity")) <= 0:
		frappe.throw(_("La cantidad debe ser mayor que cero."))
	if doc.get("movement_type") in {"consumption", "adjustment_out"}:
		available = get_material_balance(doc.material, exclude_name=doc.name)
		if flt(doc.quantity) > available:
			frappe.throw(
				_("La salida de {0} supera la existencia disponible de {1}.").format(
					frappe.bold(doc.quantity), frappe.bold(available)
				)
			)


def update_inventory_balance(doc: Document, method: str | None = None) -> None:
	if doc.get("material"):
		refresh_material_balance(doc.material)


def remove_inventory_balance(doc: Document, method: str | None = None) -> None:
	if doc.get("material"):
		refresh_material_balance(doc.material, exclude_name=doc.name)
