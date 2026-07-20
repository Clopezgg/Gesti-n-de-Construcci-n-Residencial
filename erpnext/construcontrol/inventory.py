from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

MOVEMENT_EFFECTS = {
	"receipt": 1,
	"return_in": 1,
	"adjustment_in": 1,
	"consumption": -1,
	"return_out": -1,
	"adjustment_out": -1,
	"transfer": 0,
}
INCOMING = {name for name, effect in MOVEMENT_EFFECTS.items() if effect > 0}
OUTGOING = {name for name, effect in MOVEMENT_EFFECTS.items() if effect < 0}
ADJUSTMENTS = {"adjustment_in", "adjustment_out"}


def _text(value: Any) -> str:
	value = unicodedata.normalize("NFKD", str(value or ""))
	return " ".join("".join(char for char in value if not unicodedata.combining(char)).casefold().split())


def normalize_movement(value: Any) -> str:
	aliases = {
		"entrada": "receipt",
		"recepcion": "receipt",
		"consumo": "consumption",
		"devolucion entrada": "return_in",
		"devolucion salida": "return_out",
		"transferencia": "transfer",
		"ajuste entrada": "adjustment_in",
		"ajuste salida": "adjustment_out",
	}
	raw = _text(value).replace("-", " ").replace("_", " ")
	movement = aliases.get(raw, raw.replace(" ", "_"))
	if movement not in MOVEMENT_EFFECTS:
		raise ValueError("Seleccione un tipo de movimiento de inventario válido.")
	return movement


def movement_fingerprint(values: Mapping[str, Any]) -> str:
	parts = (
		values.get("project"),
		values.get("material"),
		normalize_movement(values.get("movement_type")),
		values.get("movement_reference") or values.get("reference"),
		values.get("warehouse"),
		values.get("target_warehouse"),
		f"{float(values.get('quantity') or 0):.6f}",
	)
	return "|".join(_text(value) for value in parts)


def validate_movement_contract(
	values: Mapping[str, Any], *, available_quantity: Any, historical: bool = False
) -> dict[str, Any]:
	movement = normalize_movement(values.get("movement_type"))
	quantity = float(values.get("quantity") or 0)
	warehouse = str(values.get("warehouse") or "").strip()
	target = str(values.get("target_warehouse") or "").strip()
	reference = str(values.get("movement_reference") or values.get("reference") or "").strip()
	if not _text(values.get("project")) or not _text(values.get("material")):
		raise ValueError("Seleccione proyecto y material.")
	if quantity <= 0:
		raise ValueError("La cantidad debe ser mayor que cero.")
	if float(values.get("unit_cost_hnl") or 0) < 0:
		raise ValueError("El costo unitario no puede ser negativo.")
	if not historical and (not warehouse or not reference):
		raise ValueError("Seleccione bodega e indique una referencia única.")
	if movement == "transfer" and (not target or target == warehouse):
		raise ValueError("La bodega origen y destino deben ser diferentes.")
	if movement != "transfer" and target:
		raise ValueError("La bodega destino solo corresponde a transferencias.")
	if movement in ADJUSTMENTS and not historical and not str(values.get("justification") or "").strip():
		raise ValueError("Los ajustes de inventario requieren una justificación.")
	available = float(available_quantity or 0)
	if movement in OUTGOING | {"transfer"} and quantity > available + 1e-9:
		raise ValueError(f"La salida de {quantity:g} supera la existencia disponible de {available:g}.")
	return {"movement_type": movement, "quantity": quantity, "reference": reference}


def validate_procurement_contract(values: Mapping[str, Any]) -> dict[str, Any]:
	quantity = float(values.get("requested_quantity") or 0)
	quoted = float(values.get("quoted_amount_hnl") or 0)
	received = float(values.get("received_quantity") or 0)
	status = str(values.get("procurement_status") or "draft").strip().lower()
	allowed = {
		"draft",
		"requested",
		"quoted",
		"approved",
		"ordered",
		"partially_received",
		"received",
		"rejected",
		"cancelled",
	}
	if status not in allowed or quantity <= 0 or quoted < 0 or not 0 <= received <= quantity:
		raise ValueError("El estado, la cantidad o el monto MM02 son inválidos.")
	if status != "draft" and not _text(values.get("warehouse")):
		raise ValueError("Seleccione la bodega de recepción.")
	if status in {"quoted", "approved", "ordered", "partially_received", "received"} and (
		not _text(values.get("preferred_supplier")) or not _text(values.get("quote_reference")) or quoted <= 0
	):
		raise ValueError("La cotización requiere proveedor, referencia y monto positivo.")
	if status in {"ordered", "partially_received", "received"} and not _text(
		values.get("purchase_order_reference")
	):
		raise ValueError("Indique la orden de compra.")
	if status == "partially_received" and not 0 < received < quantity:
		raise ValueError("La recepción parcial debe coincidir con la cantidad recibida.")
	if status == "received" and received < quantity:
		raise ValueError("La solicitud no puede marcarse recibida con saldo pendiente.")
	if status == "rejected" and not _text(values.get("rejection_reason")):
		raise ValueError("Indique el motivo de rechazo.")
	return {
		"status": status,
		"requested_quantity": quantity,
		"quoted_amount_hnl": quoted,
		"received_quantity": received,
	}


def inventory_snapshot(
	initial_quantity: Any,
	initial_unit_cost: Any,
	movements: Iterable[Mapping[str, Any]],
	*,
	low_stock_threshold: Any = 0,
) -> dict[str, float | str]:
	quantity = float(initial_quantity or 0)
	value = quantity * float(initial_unit_cost or 0)
	threshold = float(low_stock_threshold or 0)
	if min(quantity, value, threshold) < 0:
		raise ValueError("Existencias, costos y umbrales no pueden ser negativos.")
	for row in movements:
		if row.get("is_logically_deleted"):
			continue
		movement = normalize_movement(row.get("movement_type"))
		moved = float(row.get("quantity") or 0)
		if moved <= 0:
			raise ValueError("La cantidad debe ser mayor que cero.")
		if movement == "transfer":
			continue
		if movement in INCOMING:
			cost = float(row.get("unit_cost_hnl") or (value / quantity if quantity else 0))
			if cost < 0:
				raise ValueError("El costo unitario no puede ser negativo.")
			quantity += moved
			value += moved * cost
		else:
			if moved > quantity + 1e-9:
				raise ValueError("El movimiento produciría inventario negativo.")
			average = value / quantity if quantity else 0
			quantity -= moved
			value = max(value - moved * average, 0)
	average = value / quantity if quantity else 0
	status = "depleted" if quantity <= 1e-9 else "low" if threshold and quantity <= threshold else "available"
	return {
		"current_qty": round(quantity, 6),
		"current_value_hnl": round(value, 2),
		"unit_cost_hnl": round(average, 6),
		"stock_status": status,
	}


def warehouse_balance(
	default_warehouse: Any,
	initial_quantity: Any,
	movements: Iterable[Mapping[str, Any]],
	warehouse: Any,
) -> float:
	selected = str(warehouse or "").strip()
	balance = float(initial_quantity or 0) if selected == str(default_warehouse or "").strip() else 0
	for row in movements:
		if row.get("is_logically_deleted"):
			continue
		movement = normalize_movement(row.get("movement_type"))
		quantity = float(row.get("quantity") or 0)
		source = str(row.get("warehouse") or "").strip()
		target = str(row.get("target_warehouse") or "").strip()
		if movement == "transfer":
			balance += quantity if target == selected else -quantity if source == selected else 0
		elif source == selected:
			balance += MOVEMENT_EFFECTS[movement] * quantity
		if balance < -1e-9:
			raise ValueError("El movimiento produciría inventario negativo en la bodega.")
	return round(balance, 6)


def _frappe():
	import frappe
	from frappe import _
	from frappe.utils import flt

	return frappe, _, flt


def ensure_inventory_schema() -> None:
	frappe, _, flt = _frappe()
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	fields = {
		"CC Material Ledger": [
			{
				"fieldname": "material_category",
				"label": "Categoría de material",
				"fieldtype": "Data",
				"insert_after": "material_name",
			},
			{
				"fieldname": "item",
				"label": "Artículo ERPNext",
				"fieldtype": "Link",
				"options": "Item",
				"insert_after": "material_category",
			},
			{
				"fieldname": "default_warehouse",
				"label": "Bodega predeterminada",
				"fieldtype": "Link",
				"options": "Warehouse",
				"insert_after": "item",
			},
			{
				"fieldname": "initial_unit_cost_hnl",
				"label": "Costo inicial (L)",
				"fieldtype": "Currency",
				"options": "HNL",
				"default": "0",
				"insert_after": "initial_qty",
			},
			{
				"fieldname": "current_value_hnl",
				"label": "Valor actual (L)",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "current_qty",
			},
		],
		"CC Inventory Movement": [
			{
				"fieldname": "warehouse",
				"label": "Bodega",
				"fieldtype": "Link",
				"options": "Warehouse",
				"insert_after": "material",
			},
			{
				"fieldname": "target_warehouse",
				"label": "Bodega destino",
				"fieldtype": "Link",
				"options": "Warehouse",
				"insert_after": "warehouse",
			},
			{
				"fieldname": "movement_reference",
				"label": "Referencia única",
				"fieldtype": "Data",
				"insert_after": "reference",
			},
			{
				"fieldname": "justification",
				"label": "Justificación",
				"fieldtype": "Small Text",
				"insert_after": "movement_reference",
			},
			{
				"fieldname": "unit_cost_hnl",
				"label": "Costo unitario (L)",
				"fieldtype": "Currency",
				"options": "HNL",
				"default": "0",
				"insert_after": "quantity",
			},
			{
				"fieldname": "total_cost_hnl",
				"label": "Costo total (L)",
				"fieldtype": "Currency",
				"options": "HNL",
				"read_only": 1,
				"insert_after": "unit_cost_hnl",
			},
			{
				"fieldname": "supplier",
				"label": "Proveedor",
				"fieldtype": "Link",
				"options": "Supplier",
				"insert_after": "total_cost_hnl",
			},
			{
				"fieldname": "procurement_request",
				"label": "Solicitud MM02",
				"fieldtype": "Link",
				"options": "CC Procurement Request",
				"insert_after": "supplier",
			},
			{
				"fieldname": "expense_control",
				"label": "Gasto FI02",
				"fieldtype": "Link",
				"options": "CC Expense Control",
				"insert_after": "procurement_request",
			},
		],
		"CC Procurement Request": [
			{
				"fieldname": "material",
				"label": "Material",
				"fieldtype": "Link",
				"options": "CC Material Ledger",
				"insert_after": "description",
			},
			{
				"fieldname": "requested_quantity",
				"label": "Cantidad solicitada",
				"fieldtype": "Float",
				"insert_after": "material",
			},
			{
				"fieldname": "unit",
				"label": "Unidad",
				"fieldtype": "Data",
				"insert_after": "requested_quantity",
			},
			{
				"fieldname": "required_by",
				"label": "Fecha requerida",
				"fieldtype": "Date",
				"insert_after": "unit",
			},
			{
				"fieldname": "warehouse",
				"label": "Bodega de recepción",
				"fieldtype": "Link",
				"options": "Warehouse",
				"insert_after": "required_by",
			},
			{
				"fieldname": "preferred_supplier",
				"label": "Proveedor",
				"fieldtype": "Link",
				"options": "Supplier",
				"insert_after": "warehouse",
			},
			{
				"fieldname": "quote_reference",
				"label": "Cotización",
				"fieldtype": "Data",
				"insert_after": "preferred_supplier",
			},
			{
				"fieldname": "quoted_amount_hnl",
				"label": "Monto cotizado (L)",
				"fieldtype": "Currency",
				"options": "HNL",
				"default": "0",
				"insert_after": "quote_reference",
			},
			{
				"fieldname": "purchase_order_reference",
				"label": "Orden de compra",
				"fieldtype": "Data",
				"insert_after": "quoted_amount_hnl",
			},
			{
				"fieldname": "expense_control",
				"label": "Gasto FI02",
				"fieldtype": "Link",
				"options": "CC Expense Control",
				"insert_after": "purchase_order_reference",
			},
			{
				"fieldname": "received_quantity",
				"label": "Cantidad recibida",
				"fieldtype": "Float",
				"read_only": 1,
				"insert_after": "expense_control",
			},
			{
				"fieldname": "procurement_status",
				"label": "Estado MM02",
				"fieldtype": "Select",
				"options": "draft\nrequested\nquoted\napproved\nordered\npartially_received\nreceived\nrejected\ncancelled",
				"default": "draft",
				"insert_after": "received_quantity",
			},
			{
				"fieldname": "rejection_reason",
				"label": "Motivo de rechazo",
				"fieldtype": "Small Text",
				"insert_after": "procurement_status",
			},
		],
	}
	for doctype, definitions in fields.items():
		standard = set(frappe.get_all("DocField", filters={"parent": doctype}, pluck="fieldname"))
		fields[doctype] = [field for field in definitions if field["fieldname"] not in standard]
	create_custom_fields(fields, update=True)
	movement_field = frappe.db.get_value(
		"DocField", {"parent": "CC Inventory Movement", "fieldname": "movement_type"}, "name"
	)
	if movement_field:
		frappe.db.set_value(
			"DocField", movement_field, "options", "\n".join(MOVEMENT_EFFECTS), update_modified=False
		)
	for doctype in fields:
		frappe.clear_cache(doctype=doctype)
	reconcile_inventory()


def _rows(material: str, exclude: str | None = None) -> list[dict[str, Any]]:
	frappe, _, flt = _frappe()
	rows = frappe.get_all(
		"CC Inventory Movement",
		filters={"material": material, "is_logically_deleted": 0},
		fields=["name", "movement_type", "quantity", "warehouse", "target_warehouse", "unit_cost_hnl"],
		order_by="posting_date asc, creation asc, name asc",
	)
	return [dict(row) for row in rows if row.name != exclude]


def _material(name: str) -> dict[str, Any]:
	frappe, _, flt = _frappe()
	return dict(
		frappe.db.get_value(
			"CC Material Ledger",
			name,
			[
				"project",
				"initial_qty",
				"initial_unit_cost_hnl",
				"unit_cost_hnl",
				"low_stock_threshold",
				"default_warehouse",
			],
			as_dict=True,
		)
		or {}
	)


def _snapshot(material: str, exclude: str | None = None) -> dict[str, float | str]:
	values = _material(material)
	return inventory_snapshot(
		values.get("initial_qty"),
		values.get("initial_unit_cost_hnl") or values.get("unit_cost_hnl"),
		_rows(material, exclude),
		low_stock_threshold=values.get("low_stock_threshold"),
	)


def validate_material_ledger(doc: Any, method: str | None = None) -> None:
	frappe, _, flt = _frappe()
	from erpnext.construcontrol.access import validate_document_project_access

	validate_document_project_access(doc)
	if flt(doc.get("initial_qty")) > 0 and not doc.get("default_warehouse") and not doc.get("source_id"):
		frappe.throw(_("Seleccione la bodega predeterminada para la existencia inicial."))
	if doc.get("default_warehouse") and not frappe.db.exists("Warehouse", doc.default_warehouse):
		frappe.throw(_("La bodega predeterminada no existe."))
	if frappe.db.exists(
		"CC Material Ledger",
		{
			"project": doc.get("project"),
			"material_name": doc.get("material_name"),
			"is_logically_deleted": 0,
			"name": ["!=", doc.name or ""],
		},
	):
		frappe.throw(_("Ya existe este material dentro del proyecto."))
	try:
		result = inventory_snapshot(
			doc.get("initial_qty"),
			doc.get("initial_unit_cost_hnl") or doc.get("unit_cost_hnl"),
			_rows(doc.name) if not doc.is_new() else [],
			low_stock_threshold=doc.get("low_stock_threshold"),
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	for fieldname in ("current_qty", "unit_cost_hnl", "current_value_hnl", "stock_status"):
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, result[fieldname])


def validate_inventory_movement(doc: Any, method: str | None = None) -> None:
	frappe, _, flt = _frappe()
	from erpnext.construcontrol.access import require_construcontrol_access, validate_document_project_access

	validate_document_project_access(doc)
	material = _material(doc.get("material"))
	if not material or material.get("project") != doc.get("project"):
		frappe.throw(_("El material no existe o pertenece a otro proyecto."))
	if doc.get("phase") and frappe.db.get_value("CC Construction Phase", doc.phase, "project") != doc.project:
		frappe.throw(_("La fase pertenece a otro proyecto."))
	historical = bool(doc.get("source_id") or doc.get("source_key"))
	movement = normalize_movement(doc.get("movement_type"))
	if movement in ADJUSTMENTS and not historical:
		require_construcontrol_access(manage=True)
	for fieldname in ("warehouse", "target_warehouse"):
		if doc.get(fieldname) and not frappe.db.exists("Warehouse", doc.get(fieldname)):
			frappe.throw(_("La bodega seleccionada no existe."))
	available = warehouse_balance(
		material.get("default_warehouse"),
		material.get("initial_qty"),
		_rows(doc.material, doc.name),
		doc.get("warehouse"),
	)
	try:
		contract = validate_movement_contract(
			doc.as_dict(), available_quantity=available, historical=historical
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	reference = contract["reference"]
	if reference and frappe.db.exists(
		"CC Inventory Movement",
		{
			"project": doc.project,
			"material": doc.material,
			"movement_type": movement,
			"movement_reference": reference,
			"warehouse": doc.get("warehouse"),
			"is_logically_deleted": 0,
			"name": ["!=", doc.name or ""],
		},
	):
		frappe.throw(_("Ya existe un movimiento con la misma referencia, material y bodega."))
	doc.movement_type = movement
	doc.movement_reference = reference
	cost = flt(doc.get("unit_cost_hnl")) or flt(material.get("unit_cost_hnl"))
	doc.unit_cost_hnl = cost
	doc.total_cost_hnl = flt(doc.get("quantity")) * cost
	if doc.meta.has_field("amount_hnl"):
		doc.amount_hnl = doc.total_cost_hnl
	if not doc.get("unit"):
		doc.unit = frappe.db.get_value("CC Material Ledger", doc.material, "unit")
	if doc.get("expense_control"):
		expense_project = frappe.db.get_value("CC Expense Control", doc.expense_control, "project")
		if expense_project != doc.project:
			frappe.throw(_("El gasto FI02 pertenece a otro proyecto."))
	if doc.get("procurement_request"):
		request = frappe.db.get_value(
			"CC Procurement Request", doc.procurement_request, ["project", "material"], as_dict=True
		)
		if not request or request.project != doc.project or request.material != doc.material:
			frappe.throw(_("La solicitud MM02 no corresponde al movimiento."))
		if movement not in {"receipt", "return_out"}:
			frappe.throw(_("MM02 solo admite recepciones o devoluciones al proveedor."))


def _refresh_material(name: str, exclude: str | None = None) -> None:
	frappe, _, flt = _frappe()
	if not name or not frappe.db.exists("CC Material Ledger", name):
		return
	result = _snapshot(name, exclude)
	frappe.db.set_value("CC Material Ledger", name, result, update_modified=False)


def _refresh_request(name: str) -> None:
	frappe, _, flt = _frappe()
	if not name or not frappe.db.exists("CC Procurement Request", name):
		return
	requested = flt(frappe.db.get_value("CC Procurement Request", name, "requested_quantity"))
	received = 0.0
	for row in frappe.get_all(
		"CC Inventory Movement",
		filters={"procurement_request": name, "is_logically_deleted": 0},
		fields=["movement_type", "quantity"],
	):
		received += flt(row.quantity) * (1 if normalize_movement(row.movement_type) == "receipt" else -1)
	received = max(received, 0)
	status = (
		"received" if requested and received >= requested else "partially_received" if received else "ordered"
	)
	frappe.db.set_value(
		"CC Procurement Request",
		name,
		{"received_quantity": received, "procurement_status": status},
		update_modified=False,
	)


def update_inventory_relations(doc: Any, method: str | None = None) -> None:
	previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	for material in {doc.get("material"), previous.get("material") if previous else None} - {None, ""}:
		_refresh_material(material)
	for request in {
		doc.get("procurement_request"),
		previous.get("procurement_request") if previous else None,
	} - {None, ""}:
		_refresh_request(request)


def remove_inventory_relations(doc: Any, method: str | None = None) -> None:
	from erpnext.construcontrol.access import require_construcontrol_access, validation_bypass_active

	if not validation_bypass_active():
		require_construcontrol_access(manage=True)
	_refresh_material(doc.get("material"), doc.name)
	_refresh_request(doc.get("procurement_request"))


def protect_material_delete(doc: Any, method: str | None = None) -> None:
	frappe, _, flt = _frappe()
	from erpnext.construcontrol.access import require_construcontrol_access, validation_bypass_active

	if validation_bypass_active():
		return
	require_construcontrol_access(manage=True)
	if frappe.db.exists("CC Inventory Movement", {"material": doc.name, "is_logically_deleted": 0}):
		frappe.throw(_("No puede eliminar un material con movimientos; anúlelo con trazabilidad."))


def validate_procurement_request(doc: Any, method: str | None = None) -> None:
	frappe, _, flt = _frappe()
	from erpnext.construcontrol.access import require_construcontrol_access, validate_document_project_access

	validate_document_project_access(doc)
	material = _material(doc.get("material"))
	if not material or material.get("project") != doc.get("project"):
		frappe.throw(_("El material solicitado pertenece a otro proyecto."))
	try:
		contract = validate_procurement_contract(doc.as_dict())
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	status = contract["status"]
	if status in {"approved", "ordered", "rejected", "cancelled"}:
		require_construcontrol_access(manage=True)
	if not doc.get("unit"):
		doc.unit = frappe.db.get_value("CC Material Ledger", doc.material, "unit")
	if doc.get("expense_control"):
		expense_project = frappe.db.get_value("CC Expense Control", doc.expense_control, "project")
		if expense_project != doc.project:
			frappe.throw(_("El gasto FI02 pertenece a otro proyecto."))
	order = str(doc.get("purchase_order_reference") or "").strip()
	if order and frappe.db.exists(
		"CC Procurement Request",
		{
			"project": doc.project,
			"purchase_order_reference": order,
			"is_logically_deleted": 0,
			"name": ["!=", doc.name or ""],
		},
	):
		frappe.throw(_("La orden de compra ya está vinculada a otra solicitud."))


def reconcile_inventory() -> dict[str, int]:
	frappe, _, flt = _frappe()
	materials = frappe.get_all("CC Material Ledger", filters={"is_logically_deleted": 0}, pluck="name")
	requests = frappe.get_all("CC Procurement Request", filters={"is_logically_deleted": 0}, pluck="name")
	for name in materials:
		_refresh_material(name)
	for name in requests:
		_refresh_request(name)
	return {"materials": len(materials), "procurement_requests": len(requests)}
