from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today

from erpnext.construcontrol.access import validate_document_project_access, validation_bypass_active
from erpnext.construcontrol.business_rules import expense_amounts, funding_balances, normalize_expense_state

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
_APPROVER_ROLES = {"System Manager", "ConstruControl Manager"}
_APPROVAL_FIELD_MAP = {
	"draft": "draft",
	"pending": "pending_approval",
	"approved": "approved",
	"rejected": "rejected",
}
_PROTECTED_APPROVED_FIELDS = {
	"project",
	"phase",
	"title",
	"posting_date",
	"category",
	"subcategory",
	"commercial_source",
	"unit",
	"quantity",
	"description",
	"provider_name",
	"supplier",
	"invoice_number",
	"invoice_date",
	"due_date",
	"purchase_order_reference",
	"cost_center",
	"subtotal_hnl",
	"tax_hnl",
	"withholding_hnl",
	"discount_hnl",
	"amount_hnl",
	"funding_source",
	"labor_contract",
	"labor_payment_type",
}


def _has_field(doc: Document, fieldname: str) -> bool:
	return bool(doc.meta.has_field(fieldname))


def _clean_text(value: Any) -> str:
	return " ".join(str(value or "").strip().split())


def _calculated_total(doc: Document) -> float:
	raw_subtotal = doc.get("subtotal_hnl")
	subtotal = flt(raw_subtotal if raw_subtotal not in (None, "") else doc.get("amount_hnl"))
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
	historical = bool(doc.get("source_id") or doc.get("source_key"))
	if total <= 0 and not historical and not doc.get("is_logically_deleted"):
		frappe.throw(_("El total del gasto debe ser mayor que cero."))
	return round(total, 2)


def _canonical_approval(value: Any) -> str:
	state = str(value or "draft").strip().lower()
	if state == "pending_approval":
		return "pending"
	return state


def _approval_state(doc: Document) -> str:
	professional = doc.get("professional_approval_status")
	standard = doc.get("approval_status")
	return _canonical_approval(professional if professional not in (None, "") else standard)


def _set_approval_fields(doc: Document, approval_status: str) -> None:
	if _has_field(doc, "professional_approval_status"):
		doc.professional_approval_status = approval_status
	if _has_field(doc, "approval_status"):
		doc.approval_status = _APPROVAL_FIELD_MAP[approval_status]


def _previous_doc(doc: Document) -> Document | None:
	return doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None


def _previous_approval(doc: Document) -> str:
	previous = _previous_doc(doc)
	return _approval_state(previous) if previous else "draft"


def _has_approver_role() -> bool:
	return bool(_APPROVER_ROLES & set(frappe.get_roles()))


def _require_approver_for_approval_change(doc: Document, approval_status: str) -> None:
	if validation_bypass_active():
		return
	previous_status = _previous_approval(doc)
	changed = previous_status != approval_status
	protected_transition = approval_status in {"approved", "rejected"} or previous_status in {
		"approved",
		"rejected",
	}
	if changed and protected_transition and not _has_approver_role():
		frappe.throw(
			_("Solo un administrador o gerente puede aprobar, rechazar o reabrir gastos."),
			frappe.PermissionError,
		)


def _normalize_supplier(doc: Document) -> None:
	supplier = doc.get("supplier")
	provider = _clean_text(doc.get("provider_name"))
	if supplier:
		supplier_name = _clean_text(frappe.db.get_value("Supplier", supplier, "supplier_name"))
		if supplier_name:
			provider = supplier_name
	if not provider:
		frappe.throw(_("Indique el proveedor o contratista."))
	doc.provider_name = provider


def _normalize_invoice(doc: Document) -> str:
	invoice = _clean_text(doc.get("invoice_number")).upper()
	if invoice:
		doc.invoice_number = invoice
	return invoice


def _validate_duplicate_invoice(doc: Document) -> None:
	invoice = _normalize_invoice(doc)
	if not invoice:
		return
	supplier = doc.get("supplier")
	provider = _clean_text(doc.get("provider_name"))
	filters: dict[str, Any] = {
		"invoice_number": invoice,
		"is_logically_deleted": 0,
		"name": ["!=", doc.name or ""],
	}
	if supplier:
		filters["supplier"] = supplier
	else:
		filters["provider_name"] = provider
	duplicate = frappe.db.exists("CC Expense Control", filters)
	if duplicate:
		frappe.throw(
			_("La factura {0} ya está registrada para este proveedor en el gasto {1}.").format(
				frappe.bold(invoice), frappe.bold(duplicate)
			)
		)


def _validate_duplicate_payment_reference(doc: Document, paid: float) -> None:
	reference = _clean_text(doc.get("payment_reference")).upper()
	if reference:
		doc.payment_reference = reference
	if paid <= 0 or not reference:
		return
	duplicate = frappe.db.exists(
		"CC Expense Control",
		{
			"payment_reference": reference,
			"paid_amount_hnl": [">", 0],
			"is_logically_deleted": 0,
			"name": ["!=", doc.name or ""],
		},
	)
	if duplicate:
		frappe.throw(
			_("La referencia de pago {0} ya está utilizada por el gasto {1}.").format(
				frappe.bold(reference), frappe.bold(duplicate)
			)
		)


def _changed_fields(doc: Document, fieldnames: set[str]) -> set[str]:
	previous = _previous_doc(doc)
	if not previous:
		return set()
	return {fieldname for fieldname in fieldnames if previous.get(fieldname) != doc.get(fieldname)}


def _protect_approved_content(doc: Document, approval_status: str, total: float) -> None:
	if validation_bypass_active():
		return
	previous = _previous_doc(doc)
	if not previous or _previous_approval(doc) != "approved":
		return
	changed = _changed_fields(doc, _PROTECTED_APPROVED_FIELDS)
	if not changed:
		return
	previous_paid = flt(previous.get("paid_amount_hnl"))
	if previous_paid > 0:
		frappe.throw(
			_("No puede modificar los datos financieros o contractuales de un gasto que ya tiene pagos.")
		)
	if approval_status == "approved":
		frappe.throw(_("Devuelva el gasto a pendiente antes de modificar datos ya aprobados."))
	if not validation_bypass_active() and not _has_approver_role():
		frappe.throw(
			_("Solo un administrador o gerente puede reabrir un gasto aprobado."), frappe.PermissionError
		)
	if flt(previous.get("approved_amount_hnl")) and flt(previous.get("approved_amount_hnl")) != total:
		doc.approved_amount_hnl = 0


def _validate_payment_change(doc: Document, paid: float, requested_status: str) -> None:
	previous = _previous_doc(doc)
	previous_paid = flt(previous.get("paid_amount_hnl")) if previous else 0.0
	previous_status = str(previous.get("payment_status") or "draft").strip().lower() if previous else "draft"
	paid_changed = abs(previous_paid - paid) > 0.005
	inactive_changed = requested_status in _INACTIVE_STATES and requested_status != previous_status
	if (paid_changed or inactive_changed) and not validation_bypass_active() and not _has_approver_role():
		frappe.throw(
			_("Solo un administrador o gerente puede registrar pagos, anulaciones o reembolsos."),
			frappe.PermissionError,
		)
	if paid < previous_paid - 0.005 and requested_status != "reimbursed":
		frappe.throw(_("El monto pagado no puede disminuir. Registre un reembolso formal."))
	if previous_paid > 0:
		for fieldname in ("payment_reference", "payment_date"):
			old = previous.get(fieldname)
			new = doc.get(fieldname)
			if old not in (None, "") and old != new:
				frappe.throw(_("No puede cambiar {0} después de registrar un pago.").format(fieldname))


def _validate_payment_evidence(doc: Document, paid: float, historical: bool) -> None:
	if paid <= 0 or historical:
		return
	if not _clean_text(doc.get("payment_reference")):
		frappe.throw(_("Ingrese la referencia del pago."))
	if not doc.get("payment_date"):
		frappe.throw(_("Ingrese la fecha del pago."))
	if not _clean_text(doc.get("payment_evidence")):
		frappe.throw(_("Adjunte el comprobante del pago."))


def expense_amount_tuple(row: Any) -> tuple[float, float, float]:
	return expense_amounts(
		row.get("amount_hnl"),
		row.get("payment_status"),
		row.get("financial_status"),
		row.get("paid_amount_hnl"),
		row.get("balance_due_hnl"),
		row.get("professional_approval_status"),
	)


def expense_totals(
	link_field: str,
	link_name: str,
	exclude_name: str | None = None,
) -> tuple[float, float, float]:
	"""Return recognized, paid and pending FI02 totals for one canonical relation."""
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
		row_recognized, row_paid, row_pending = expense_amount_tuple(row)
		recognized += row_recognized
		paid += row_paid
		pending += row_pending
	return round(recognized, 2), round(paid, 2), round(pending, 2)


def _validate_phase_project(doc: Document) -> None:
	if not doc.get("phase"):
		return
	phase_project = frappe.db.get_value("CC Construction Phase", doc.phase, "project")
	if not phase_project:
		frappe.throw(_("La fase seleccionada no existe o está inactiva."))
	if doc.get("project") and phase_project != doc.project:
		frappe.throw(_("La fase pertenece a otro proyecto."))


def _validate_expense_contract(doc: Document) -> None:
	if not doc.get("labor_contract"):
		return
	contract = frappe.db.get_value(
		"CC Labor Contract",
		doc.labor_contract,
		["project", "phase", "status", "project_value_hnl", "labor_value_hnl"],
		as_dict=True,
	)
	if not contract:
		frappe.throw(_("El contrato seleccionado no existe."))
	if contract.project and doc.get("project") and contract.project != doc.project:
		frappe.throw(_("El contrato pertenece a otro proyecto."))
	if contract.phase:
		if doc.get("phase") and contract.phase != doc.phase:
			frappe.throw(_("El gasto pertenece a una fase distinta de la definida en el contrato."))
		if not doc.get("phase"):
			doc.phase = contract.phase
	if str(contract.status or "").lower() == "cancelled":
		frappe.throw(_("No puede registrar gastos contra un contrato anulado."))

	from erpnext.construcontrol.construction import contract_value

	current_recognized, _current_paid, _current_pending = expense_amount_tuple(doc)
	other_recognized, _other_paid, _other_pending = expense_totals(
		"labor_contract",
		doc.labor_contract,
		exclude_name=doc.name,
	)
	if other_recognized + current_recognized > contract_value(contract) + 0.005:
		frappe.throw(_("El gasto supera el saldo comprometible del contrato."))


def validate_expense_control(doc: Document, method: str | None = None) -> None:
	"""Validate FI02 project, fund, phase and contract relationships server-side."""
	validate_document_project_access(doc)
	amount = flt(doc.get("amount_hnl"))
	if amount < 0:
		frappe.throw(_("El monto no puede ser negativo."))
	if not doc.get("provider_name"):
		frappe.throw(_("Indique el proveedor o contratista."))
	_validate_phase_project(doc)

	if doc.get("funding_source"):
		fund = frappe.db.get_value(
			"CC Funding Source",
			doc.funding_source,
			["project", "net_amount_hnl", "amount_hnl", "status", "reconciliation_status"],
			as_dict=True,
		)
		if not fund:
			frappe.throw(_("La fuente de fondos seleccionada no existe."))
		if fund.project and doc.get("project") and fund.project != doc.project:
			frappe.throw(_("La fuente de fondos pertenece a otro proyecto."))

		_current_recognized, current_paid, current_pending = expense_amount_tuple(doc)
		_other_recognized, other_paid, other_pending = expense_totals(
			"funding_source",
			doc.funding_source,
			exclude_name=doc.name,
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

	_validate_expense_contract(doc)


def update_expense_relations(doc: Document, method: str | None = None) -> None:
	previous = _previous_doc(doc)
	funds = {doc.get("funding_source"), previous.get("funding_source") if previous else None} - {
		None,
		"",
	}
	contracts = {
		doc.get("labor_contract"),
		previous.get("labor_contract") if previous else None,
	} - {None, ""}
	from erpnext.construcontrol.construction import recalculate_contract
	from erpnext.construcontrol.finance import recalculate_funding_source

	for name in funds:
		recalculate_funding_source(name)
	for name in contracts:
		recalculate_contract(name)


def remove_expense_relations(doc: Document, method: str | None = None) -> None:
	from erpnext.construcontrol.construction import recalculate_contract
	from erpnext.construcontrol.finance import recalculate_funding_source

	if doc.get("funding_source"):
		recalculate_funding_source(doc.funding_source, exclude_name=doc.name)
	if doc.get("labor_contract"):
		recalculate_contract(doc.labor_contract, exclude_name=doc.name)


def validate_professional_expense(doc: Document, method: str | None = None) -> None:
	if not _has_field(doc, "payment_status"):
		return
	validate_document_project_access(doc)
	_normalize_supplier(doc)

	total = _calculated_total(doc)
	paid = flt(doc.get("paid_amount_hnl"))
	if paid < 0:
		frappe.throw(_("El monto pagado no puede ser negativo."))
	if paid > total + 0.005:
		frappe.throw(_("El monto pagado no puede superar el total del gasto."))

	requested_payment_status = str(doc.get("payment_status") or "draft").strip().lower()
	approval_status = _approval_state(doc)
	if requested_payment_status not in _ALLOWED_PAYMENT_STATES:
		frappe.throw(_("Seleccione un estado de pago válido."))
	if approval_status not in _ALLOWED_APPROVAL_STATES:
		frappe.throw(_("Seleccione un estado de aprobación válido."))

	_require_approver_for_approval_change(doc, approval_status)
	_protect_approved_content(doc, approval_status, total)
	_validate_payment_change(doc, paid, requested_payment_status)

	due_date = getdate(doc.get("due_date")) if doc.get("due_date") else None
	balance = round(total - paid, 2)
	payment_status = requested_payment_status
	historical = bool(doc.get("source_id") or doc.get("source_key"))

	if approval_status == "rejected":
		if paid > 0:
			frappe.throw(
				_(
					"No puede rechazarse un gasto que ya registra pagos. "
					"Registre primero el reembolso correspondiente."
				)
			)
		if not _clean_text(doc.get("rejection_reason")):
			frappe.throw(_("Indique el motivo del rechazo."))
		payment_status = "cancelled"
		paid = 0.0
		balance = 0.0
		doc.approved_amount_hnl = 0
		doc.approved_by_user = None
		doc.approved_at = None
	elif requested_payment_status == "cancelled":
		if paid > 0:
			frappe.throw(_("Un gasto pagado no puede anularse; debe registrarse como reembolsado."))
		if not _clean_text(doc.get("rejection_reason") or doc.get("notes")):
			frappe.throw(_("Indique el motivo de la anulación."))
		payment_status = "cancelled"
		balance = 0.0
	elif requested_payment_status == "reimbursed":
		if paid <= 0:
			frappe.throw(_("Solo puede reembolsarse un gasto que tenga pagos registrados."))
		if not _clean_text(doc.get("rejection_reason") or doc.get("notes")):
			frappe.throw(_("Indique el motivo del reembolso."))
		_validate_payment_evidence(doc, paid, historical)
		payment_status = "reimbursed"
		balance = 0.0
	else:
		if balance <= 0 and total > 0:
			payment_status = "paid"
		elif paid > 0:
			payment_status = "partially_paid"
		elif due_date and due_date < getdate(today()) and approval_status == "approved":
			payment_status = "overdue"
		elif approval_status == "approved":
			payment_status = "approved"
		elif approval_status == "pending":
			payment_status = "pending_approval"
		else:
			payment_status = "draft"

		if (
			payment_status in {"paid", "partially_paid", "overdue", "approved"}
			and approval_status != "approved"
		):
			frappe.throw(
				_("El gasto debe estar aprobado antes de registrar pagos, vencimiento o cuenta por pagar.")
			)

		if approval_status == "approved":
			if not doc.get("approved_by_user"):
				doc.approved_by_user = frappe.session.user
			if not doc.get("approved_at"):
				doc.approved_at = now_datetime()
			approved_amount = flt(doc.get("approved_amount_hnl"))
			if approved_amount and abs(approved_amount - total) > 0.005:
				frappe.throw(_("El total no coincide con el monto previamente aprobado."))
			doc.approved_amount_hnl = total
		else:
			doc.approved_amount_hnl = 0
			doc.approved_by_user = None
			doc.approved_at = None

	if paid > 0 and not doc.get("payment_date"):
		doc.payment_date = today()
	_validate_payment_evidence(doc, paid, historical)
	_validate_duplicate_invoice(doc)
	_validate_duplicate_payment_reference(doc, paid)

	doc.subtotal_hnl = flt(
		doc.get("subtotal_hnl")
		if doc.get("subtotal_hnl") not in (None, "")
		else total - flt(doc.get("tax_hnl")) + flt(doc.get("withholding_hnl")) + flt(doc.get("discount_hnl"))
	)
	doc.calculated_total_hnl = total
	doc.amount_hnl = total
	doc.paid_amount_hnl = paid
	doc.balance_due_hnl = balance
	doc.payment_status = payment_status
	_set_approval_fields(doc, approval_status)
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
	doc.status = (
		"cancelled"
		if payment_status in _INACTIVE_STATES
		else "pending"
		if payment_status in {"draft", "pending_approval", "approved", "overdue"}
		else "active"
	)


def _payable_status(doc: Document) -> str:
	status = str(doc.get("payment_status") or "draft")
	return {
		"partially_paid": "partial",
		"paid": "paid",
		"overdue": "overdue",
		"cancelled": "cancelled",
		"reimbursed": "reimbursed",
	}.get(status, "pending")


def _payable_identity(doc: Document, source_key: str) -> str | None:
	by_source = frappe.db.get_value("CC Payable Control", {"source_key": source_key}, "name")
	by_expense = frappe.db.get_value("CC Payable Control", {"expense_control": doc.name}, "name")
	if by_source and by_expense and by_source != by_expense:
		frappe.throw(
			_("El gasto tiene cuentas por pagar duplicadas. Corrija la relación antes de continuar.")
		)
	return by_source or by_expense


def _archive_payable(name: str) -> None:
	frappe.db.set_value(
		"CC Payable Control",
		name,
		{
			"is_logically_deleted": 1,
			"payable_status": "cancelled",
			"status": "cancelled",
			"amount_hnl": 0,
			"balance_due_hnl": 0,
		},
		update_modified=False,
	)


def sync_payable_from_expense(doc: Document, method: str | None = None) -> None:
	if not _has_field(doc, "balance_due_hnl") or doc.is_new():
		return
	source_key = f"expense-payable:{doc.name}"
	existing = _payable_identity(doc, source_key)
	approved = _approval_state(doc) == "approved"
	inactive = bool(
		doc.get("is_logically_deleted") or doc.get("payment_status") in _INACTIVE_STATES or not approved
	)
	if inactive:
		if existing:
			_archive_payable(existing)
		return

	payable = (
		frappe.get_doc("CC Payable Control", existing) if existing else frappe.new_doc("CC Payable Control")
	)
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
		"is_logically_deleted": 0,
	}
	changed = False
	for fieldname, value in values.items():
		if payable.meta.has_field(fieldname) and payable.get(fieldname) != value:
			payable.set(fieldname, value)
			changed = True
	if payable.is_new():
		payable.insert(ignore_permissions=True)
	elif changed:
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
		if value in {
			"paid",
			"partially_paid",
			"overdue",
			"cancelled",
			"reimbursed",
			"pending",
			"pending_approval",
			"approved",
		}:
			return value
	return None


def backfill_professional_expenses() -> dict[str, int]:
	"""Reconcile already imported FI02 rows after professional fields are installed."""
	if not frappe.db.exists("DocType", "CC Expense Control"):
		return {"updated": 0, "payables": 0}

	updated = 0
	payables = 0
	funding_sources: set[str] = set()
	contracts: set[str] = set()
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
				"approval_status": _APPROVAL_FIELD_MAP.get(approval, "draft"),
				"approved_amount_hnl": total if approval == "approved" else 0.0,
			}
			changed = {
				key: value
				for key, value in values.items()
				if doc.meta.has_field(key) and doc.get(key) != value
			}
			if changed:
				frappe.db.set_value("CC Expense Control", name, changed, update_modified=False)
				updated += 1
				for key, value in changed.items():
					doc.set(key, value)

			if doc.get("funding_source"):
				funding_sources.add(str(doc.get("funding_source")))
			if doc.get("labor_contract"):
				contracts.add(str(doc.get("labor_contract")))

			before = frappe.db.exists("CC Payable Control", {"source_key": f"expense-payable:{name}"})
			sync_payable_from_expense(doc)
			after = frappe.db.exists("CC Payable Control", {"source_key": f"expense-payable:{name}"})
			if after and not before:
				payables += 1
	finally:
		frappe.flags.in_construcontrol_migration = previous_flag

	from erpnext.construcontrol.construction import recalculate_contract
	from erpnext.construcontrol.finance import recalculate_funding_source

	for name in funding_sources:
		recalculate_funding_source(name)
	for name in contracts:
		recalculate_contract(name)
	return {"updated": updated, "payables": payables}


def archive_payable_from_expense(doc: Document, method: str | None = None) -> None:
	name = frappe.db.get_value("CC Payable Control", {"expense_control": doc.name}, "name")
	if name:
		_archive_payable(name)


__all__ = [
	"archive_payable_from_expense",
	"backfill_professional_expenses",
	"expense_amount_tuple",
	"expense_totals",
	"remove_expense_relations",
	"sync_payable_from_expense",
	"update_expense_relations",
	"validate_expense_control",
	"validate_professional_expense",
]
