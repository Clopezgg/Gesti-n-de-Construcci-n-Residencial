from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

import frappe
from frappe import _

from nexora.budget.core import (
	OverspendError,
	assert_transition,
	compute_budget_totals,
	compute_line_balances,
	format_overspend_message,
	money,
	validate_line_amount,
	validate_no_overspend,
)
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash
from nexora.financial.db import (
	audit,
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	parse_payload,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.permissions import require_action, require_project_access


@frappe.whitelist(methods=["POST"])
def create_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	require_action("approve")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		lines = data.get("lines", [])
		if not lines:
			frappe.throw(_("El presupuesto debe tener al menos una línea."))
		for line in lines:
			validate_line_amount(line.get("approved_hnl", 0))
		totals = compute_budget_totals(lines)
		budget_number, budget_sequence = issue_document_number("NXR Budget", data["idempotency_key"])
		with service_write():
			budget = frappe.get_doc(
				{
					"doctype": "NXR Budget",
					"document_number": budget_number,
					"status": "Draft",
					"project": data["project"],
					"title": data.get("title") or f"Presupuesto {budget_number}",
					"version": data.get("version", 1),
					"effective_date": data.get("effective_date") or frappe.utils.today(),
					"amendment_deadline": data.get("amendment_deadline"),
					"total_approved_hnl": totals["total_approved_hnl"],
					"total_committed_hnl": totals["total_committed_hnl"],
					"total_executed_hnl": totals["total_executed_hnl"],
					"total_available_hnl": totals["total_available_hnl"],
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
					"lines": [
						{
							"economic_category": line.get("economic_category"),
							"cost_center": line.get("cost_center"),
							"description": line.get("description", ""),
							"approved_hnl": line["approved_hnl"],
							"committed_hnl": line.get("committed_hnl", 0),
							"executed_hnl": line.get("executed_hnl", 0),
							"available_hnl": compute_line_balances(
								line["approved_hnl"],
								line.get("committed_hnl", 0),
								line.get("executed_hnl", 0),
							)["available_hnl"],
						}
						for line in lines
					],
				}
			).insert(ignore_permissions=True)
		link_sequence(budget_sequence, budget.name)
		result = {
			"budget": budget.name,
			"document_number": budget_number,
			"totals": totals,
		}
		audit("budget_created", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Budget", budget.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def activate_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Active")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Active"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Active"}
		audit("budget_activated", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def amend_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	require_action("approve")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		budget_name = data["budget"]
		budget = frappe.get_doc("NXR Budget", budget_name)
		frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
		assert_transition(budget.status, "Amended")
		lines = data.get("lines", [])
		if not lines:
			frappe.throw(_("La enmienda debe tener al menos una línea."))
		for line in lines:
			validate_line_amount(line.get("approved_hnl", 0))
		totals = compute_budget_totals(lines)
		new_version = (budget.version or 1) + 1
		new_number, new_sequence = issue_document_number("NXR Budget", data["idempotency_key"])
		with service_write():
			budget.status = "Amended"
			budget.save(ignore_permissions=True)
			new_budget = frappe.get_doc(
				{
					"doctype": "NXR Budget",
					"document_number": new_number,
					"status": "Active",
					"project": budget.project,
					"title": data.get("title") or budget.title,
					"version": new_version,
					"effective_date": data.get("effective_date") or frappe.utils.today(),
					"amendment_deadline": data.get("amendment_deadline"),
					"total_approved_hnl": totals["total_approved_hnl"],
					"total_committed_hnl": totals["total_committed_hnl"],
					"total_executed_hnl": totals["total_executed_hnl"],
					"total_available_hnl": totals["total_available_hnl"],
					"idempotency_key": data["idempotency_key"],
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
					"lines": [
						{
							"economic_category": line.get("economic_category"),
							"cost_center": line.get("cost_center"),
							"description": line.get("description", ""),
							"approved_hnl": line["approved_hnl"],
							"committed_hnl": line.get("committed_hnl", 0),
							"executed_hnl": line.get("executed_hnl", 0),
							"available_hnl": compute_line_balances(
								line["approved_hnl"],
								line.get("committed_hnl", 0),
								line.get("executed_hnl", 0),
							)["available_hnl"],
						}
						for line in lines
					],
				}
			).insert(ignore_permissions=True)
		link_sequence(new_sequence, new_budget.name)
		result = {
			"previous_budget": budget.name,
			"new_budget": new_budget.name,
			"new_document_number": new_number,
			"version": new_version,
			"totals": totals,
		}
		audit("budget_amended", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Budget", new_budget.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def close_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Closed")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Closed"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Closed"}
		audit("budget_closed", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def cancel_budget(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	require_action("approve")
	budget_name = data["budget"]
	budget = frappe.get_doc("NXR Budget", budget_name)
	frappe.db.sql("SELECT name FROM `tabNXR Budget` WHERE name=%s FOR UPDATE", budget_name)
	assert_transition(budget.status, "Cancelled")
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		with service_write():
			budget.status = "Cancelled"
			budget.save(ignore_permissions=True)
		result = {"budget": budget.name, "status": "Cancelled"}
		audit("budget_cancelled", "NXR Budget", budget.name, fingerprint, correlation_id, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def check_budget_availability(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	project = data["project"]
	# NXR-SEC-0001 (Bloque 19): "preview" por sí solo es un rol amplio que incluye
	# "NEXORA Project Viewer"; sin este chequeo, un Project Viewer restringido a un
	# proyecto podía consultar la disponibilidad presupuestaria (existencia de
	# presupuesto activo, nombre interno, categorías económicas) de un proyecto ajeno.
	require_project_access(project, action="preview")
	cost_center = data.get("cost_center")
	economic_category = data.get("economic_category")
	amount = data["amount"]
	budget = _find_active_budget(project)
	if budget is None:
		return {"available": False, "reason": "No hay presupuesto activo para este proyecto"}
	# Mismo criterio de resolución que la reserva real al crear un compromiso
	# (`_find_active_budget_line`): primero centro de costo, luego categoría económica
	# si hace falta desambiguar. Antes de esta corrección esta vista previa solo
	# filtraba por categoría económica e ignoraba el centro de costo por completo,
	# pudiendo mostrar "disponible" para una línea de un centro de costo distinto al
	# que realmente se usará al crear el compromiso.
	candidates = budget.get("lines", [])
	if cost_center:
		candidates = [line for line in candidates if line.get("cost_center") == cost_center]
	if economic_category:
		matching_category = [line for line in candidates if line.get("economic_category") == economic_category]
		if matching_category:
			candidates = matching_category
	if not candidates:
		return {"available": False, "reason": "No hay línea de presupuesto para ese centro de costo/categoría"}
	for line in candidates:
		try:
			validate_no_overspend(
				line.get("approved_hnl", 0),
				line.get("committed_hnl", 0),
				line.get("executed_hnl", 0),
				amount,
			)
			return {"available": True, "budget": budget.name}
		except OverspendError:
			return {
				"available": False,
				"reason": f"Línea {line.get('economic_category', '?')} sin disponibilidad",
				"budget": budget.name,
			}
	return {"available": False, "reason": "Categoría económica no encontrada en presupuesto"}


def _find_active_budget(project: str) -> dict[str, Any] | None:
	budgets = frappe.get_all(
		"NXR Budget",
		filters={"project": project, "status": "Active"},
		fields=["name", "title", "total_approved_hnl", "total_available_hnl"],
		limit=1,
	)
	if not budgets:
		return None
	b = budgets[0]
	doc = frappe.get_doc("NXR Budget", b.name)
	return {
		"name": doc.name,
		"title": doc.title,
		"total_approved_hnl": doc.total_approved_hnl,
		"total_committed_hnl": doc.total_committed_hnl,
		"total_executed_hnl": doc.total_executed_hnl,
		"total_available_hnl": doc.total_available_hnl,
		"lines": [
			{
				"economic_category": line.economic_category,
				"cost_center": line.cost_center,
				"approved_hnl": line.approved_hnl,
				"committed_hnl": line.committed_hnl,
				"executed_hnl": line.executed_hnl,
				"available_hnl": line.available_hnl,
			}
			for line in doc.lines
		],
	}


# --- Enforcement transaccional presupuesto → compromiso (NXR-PRE-0008) --------------
#
# El presupuesto y el compromiso son conceptos distintos (Capítulo 49 de la misión):
# `NXR Budget Line` es la autorización (aprobado); `NXR Commitment` es la reserva
# contra esa autorización; `NXR Operation`/`NXR Operation Effect` (financial/) son el
# gasto/pago real contra el fondo. Este bloque conecta compromiso -> presupuesto sin
# tocar el modelo de fondos: `committed_hnl`/`executed_hnl` de la línea de presupuesto
# se mueven en el mismo sentido en que se mueve el compromiso, pero son un contador
# independiente del saldo del fondo (`NXR Fund Source`), que sigue gobernado
# exclusivamente por `financial/core.py`.
#
# Resolución de la línea aplicable: solo cuando el compromiso tiene `cost_center` y
# existe una única línea de presupuesto activa para ese proyecto+centro de costo (o
# una única línea de ese centro de costo que además coincide en `economic_category`
# cuando el compromiso la especifica). Si no se puede resolver una línea única, estas
# funciones devuelven `None` sin efecto: no es una excepción silenciosa a una regla que
# aplica, es que la regla no tiene todavía un presupuesto contra el cual aplicarse para
# ese centro de costo — el compromiso procede sin control presupuestario, igual que
# hoy. Documentado explícitamente en `docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md`.


def _find_active_budget_line(
	project: str, cost_center: str | None, economic_category: str | None
) -> tuple[str, str] | None:
	if not cost_center:
		return None
	budgets = frappe.get_all(
		"NXR Budget", filters={"project": project, "status": "Active"}, fields=["name"], limit=1
	)
	if not budgets:
		return None
	budget_name = budgets[0].name
	lines = frappe.get_all(
		"NXR Budget Line",
		filters={"parent": budget_name, "parenttype": "NXR Budget", "cost_center": cost_center},
		fields=["name", "economic_category"],
	)
	if not lines:
		return None
	if len(lines) == 1:
		return budget_name, lines[0].name
	if economic_category:
		matches = [line for line in lines if line.economic_category == economic_category]
		if len(matches) == 1:
			return budget_name, matches[0].name
	return None


def _lock_and_read_line(budget_line_name: str) -> dict[str, Any] | None:
	"""Bloquea y lee la línea en una sola consulta (evita leer con el ORM antes del
	lock, que podría devolver un valor obsoleto bajo concurrencia real)."""
	row = frappe.db.sql(
		"""SELECT parent, approved_hnl, committed_hnl, executed_hnl
		   FROM `tabNXR Budget Line` WHERE name=%s FOR UPDATE""",
		budget_line_name,
	)
	if not row:
		return None
	parent, approved, committed, executed = row[0]
	return {
		"parent": parent,
		"approved_hnl": approved,
		"committed_hnl": committed,
		"executed_hnl": executed,
	}


def _write_line_and_recompute_totals(
	budget_line_name: str,
	parent: str,
	committed_hnl: Decimal,
	executed_hnl: Decimal,
	available_hnl: Decimal,
) -> None:
	frappe.db.sql(
		"""UPDATE `tabNXR Budget Line`
		   SET committed_hnl=%s, executed_hnl=%s, available_hnl=%s
		   WHERE name=%s""",
		(str(committed_hnl), str(executed_hnl), str(available_hnl), budget_line_name),
	)
	budget = frappe.get_doc("NXR Budget", parent)
	totals = compute_budget_totals(
		[
			{
				"approved_hnl": line.approved_hnl,
				"committed_hnl": line.committed_hnl,
				"executed_hnl": line.executed_hnl,
			}
			for line in budget.lines
		]
	)
	with service_write():
		budget.total_approved_hnl = totals["total_approved_hnl"]
		budget.total_committed_hnl = totals["total_committed_hnl"]
		budget.total_executed_hnl = totals["total_executed_hnl"]
		budget.total_available_hnl = totals["total_available_hnl"]
		budget.save(ignore_permissions=True)


def reserve_budget_commitment(
	*, project: str, cost_center: str | None, economic_category: str | None, amount_hnl: Any
) -> dict[str, Any] | None:
	"""Reserva `amount_hnl` contra la línea de presupuesto aplicable, o falla.

	Lanza `OverspendError` (con el mensaje humano de `format_overspend_message`) cuando
	el compromiso excedería el disponible; en ese caso no escribe nada. Devuelve `None`
	sin efecto cuando no hay una línea de presupuesto aplicable que resolver (ver nota
	de alcance arriba). El bloqueo ocurre antes de cualquier mutación: la fila se lee
	con `FOR UPDATE` y se valida en Python antes de emitir el `UPDATE`.
	"""
	target = _find_active_budget_line(project, cost_center, economic_category)
	if target is None:
		return None
	budget_name, line_name = target
	locked = _lock_and_read_line(line_name)
	if locked is None:
		return None
	amount = money(amount_hnl)
	bal = compute_line_balances(locked["approved_hnl"], locked["committed_hnl"], locked["executed_hnl"])
	try:
		validate_no_overspend(locked["approved_hnl"], locked["committed_hnl"], locked["executed_hnl"], amount)
	except OverspendError:
		raise OverspendError(format_overspend_message(bal["available_hnl"], amount)) from None
	new_committed = money(bal["committed_hnl"] + amount)
	new_bal = compute_line_balances(locked["approved_hnl"], new_committed, locked["executed_hnl"])
	_write_line_and_recompute_totals(
		line_name, locked["parent"], new_committed, money(locked["executed_hnl"]), new_bal["available_hnl"]
	)
	return {
		"budget": budget_name,
		"budget_line": line_name,
		"committed_hnl": str(new_committed),
		"available_hnl": str(new_bal["available_hnl"]),
	}


def release_budget_reservation(
	*, budget: str | None, budget_line: str | None, amount_hnl: Any
) -> dict[str, Any] | None:
	"""Libera `amount_hnl` de comprometido en la línea exacta que lo reservó.

	Se dirige siempre a `budget`/`budget_line` guardados en el compromiso al crearse
	(no se re-resuelve por proyecto/centro de costo): si el presupuesto activo cambió
	desde entonces (p. ej. una enmienda creó una versión nueva), la liberación debe
	afectar la misma línea que reservó, no la que esté activa ahora.
	"""
	if not budget or not budget_line:
		return None
	locked = _lock_and_read_line(budget_line)
	if locked is None:
		return None
	amount = money(amount_hnl)
	new_committed = money(max(Decimal("0"), money(locked["committed_hnl"]) - amount))
	new_bal = compute_line_balances(locked["approved_hnl"], new_committed, locked["executed_hnl"])
	_write_line_and_recompute_totals(
		budget_line, locked["parent"], new_committed, money(locked["executed_hnl"]), new_bal["available_hnl"]
	)
	return {
		"budget": budget,
		"budget_line": budget_line,
		"committed_hnl": str(new_committed),
		"available_hnl": str(new_bal["available_hnl"]),
	}


def record_budget_execution(
	*, budget: str | None, budget_line: str | None, amount_hnl: Any
) -> dict[str, Any] | None:
	"""Mueve `amount_hnl` de comprometido a ejecutado en la línea exacta que lo reservó.

	El disponible no cambia por esta llamada (ya se descontó al reservar): comprometido
	baja y ejecutado sube en la misma cantidad. Mismo motivo que en
	`release_budget_reservation` para no re-resolver la línea por proyecto/centro.
	"""
	if not budget or not budget_line:
		return None
	locked = _lock_and_read_line(budget_line)
	if locked is None:
		return None
	amount = money(amount_hnl)
	new_committed = money(max(Decimal("0"), money(locked["committed_hnl"]) - amount))
	new_executed = money(money(locked["executed_hnl"]) + amount)
	new_bal = compute_line_balances(locked["approved_hnl"], new_committed, new_executed)
	_write_line_and_recompute_totals(budget_line, locked["parent"], new_committed, new_executed, new_bal["available_hnl"])
	return {
		"budget": budget,
		"budget_line": budget_line,
		"committed_hnl": str(new_committed),
		"executed_hnl": str(new_executed),
		"available_hnl": str(new_bal["available_hnl"]),
	}
