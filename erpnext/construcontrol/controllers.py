"""Legacy controller facade for persisted Frappe controller references.

New hooks and services must import the owning FI01, FI02, CO01 or MIGO module.
This facade can be removed after a migration proves that no installed DocType,
hook, Server Script or queued job refers to ``erpnext.construcontrol.controllers``.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.construcontrol.access import validate_document_project_access
from erpnext.construcontrol.construction import recalculate_contract, validate_labor_contract
from erpnext.construcontrol.expenses import (
	remove_expense_relations,
	update_expense_relations,
	validate_expense_control,
)
from erpnext.construcontrol.finance import recalculate_funding_source, validate_funding_source
from erpnext.construcontrol.inventory import (
	INCOMING as INCOMING_MOVEMENTS,
)
from erpnext.construcontrol.inventory import (
	OUTGOING as OUTGOING_MOVEMENTS,
)
from erpnext.construcontrol.inventory import (
	get_material_balance,
	refresh_material_balance,
	remove_inventory_relations,
	update_inventory_relations,
	validate_inventory_movement,
	validate_material_ledger,
)

ALLOWED_MOVEMENTS = INCOMING_MOVEMENTS | OUTGOING_MOVEMENTS | {"transfer"}
CONTROLLER_COMPATIBILITY_REMOVAL_CONDITION = (
	"remove after an installed-site reference audit and migration show zero persisted controller references"
)


class ConstruControlDocument(Document):
	"""Compatibility base for old custom DocType controller assignments."""

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
		update_inventory_relations(self)

	def on_trash(self) -> None:
		remove_inventory_relations(self)


update_inventory_balance = update_inventory_relations
remove_inventory_balance = remove_inventory_relations

__all__ = [
	"ALLOWED_MOVEMENTS",
	"CCExpenseControl",
	"CCFundingSource",
	"CCInventoryMovement",
	"CCLaborContract",
	"CCMaterialLedger",
	"CONTROLLER_COMPATIBILITY_REMOVAL_CONDITION",
	"ConstruControlDocument",
	"get_material_balance",
	"recalculate_contract",
	"recalculate_funding_source",
	"refresh_material_balance",
	"remove_expense_relations",
	"remove_inventory_balance",
	"update_expense_relations",
	"update_inventory_balance",
	"validate_expense_control",
	"validate_funding_source",
	"validate_inventory_movement",
	"validate_labor_contract",
	"validate_material_ledger",
]
