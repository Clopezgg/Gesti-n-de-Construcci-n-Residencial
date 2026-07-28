from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.analytics import execute_central_operation, preview_central_operation
from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import audit, correlation, parse_payload, rollback, savepoint
from nexora.financial.operational_dates import OperationalDateError, month_key, validate_document_date
from nexora.financial.sources import cancel_fund_source, create_fund_source
from nexora.permissions import require_action, require_project_access

MOVEMENT_CATALOG: dict[str, dict[str, str]] = {
	"101": {
		"label": "Entrada de saldo",
		"mode": "income",
		"operation_code": "",
		"economic_category": "",
	},
	"102": {
		"label": "Salida de saldo / gasto",
		"mode": "expense",
		"operation_code": "CONSTRUCTION_PAYMENT",
		"economic_category": "",
	},
	"303": {
		"label": "Anulación financiera",
		"mode": "correction",
		"operation_code": "REVERSAL_NO_CASH",
		"economic_category": "REVERSAL",
	},
	"304": {
		"label": "Corrección documental",
		"mode": "correction",
		"operation_code": "DOCUMENT_SUBSTITUTION",
		"economic_category": "DOCUMENTARY",
	},
	"501": {
		"label": "Cancelación total",
		"mode": "correction",
		"operation_code": "REVERSAL_NO_CASH",
		"economic_category": "REVERSAL",
	},
}
CHANNEL_LABELS = {
	"Remittance": "Remesa",
	"Cash": "Efectivo",
	"Deposit": "Depósito",
	"Transfer": "Transferencia",
	"Other": "Otro",
}
DAY_LABELS = ("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")
BANK_CHANNELS = {"Remittance", "Deposit", "Transfer"}


def _required(value: object, message: str) -> str:
	text = str(value or "").strip()
	if not text:
		frappe.throw(_(message))
	return text


def _masked_account(value: object) -> str:
	text = str(value or "").strip()
	if not text:
		return "—"
	visible = text[-5:] if len(text) > 5 else text
	return f"••••{visible}"


def _normalize_channel(value: object) -> str:
	channel = str(value or "Other").strip()
	if channel not in CHANNEL_LABELS:
		frappe.throw(_("El canal financiero no es válido."))
	return channel


def _account_fingerprint(data: Mapping[str, Any]) -> str:
	return canonical_payload_hash(
		{
			"project": str(data.get("project") or "").strip(),
			"direction": str(data.get("direction") or "Origin").strip(),
			"origin_or_sender": str(data.get("origin_or_sender") or "").strip().casefold(),
			"institution": str(data.get("institution") or "").strip().casefold(),
			"account_reference": str(data.get("account_reference") or "").strip().casefold(),
			"currency": str(data.get("currency") or "HNL").strip().upper(),
			"default_channel": str(data.get("default_channel") or data.get("channel") or "Other").strip(),
		}
	)


def _validate_account_payload(data: Mapping[str, Any]) -> dict[str, Any]:
	project = str(data.get("project") or "").strip()
	if project:
		require_project_access(project, action="create_source")
	else:
		require_action("create_source")
	channel = _normalize_channel(data.get("default_channel") or data.get("channel"))
	direction = str(data.get("direction") or "Origin").strip()
	if direction not in {"Origin", "Destination", "Both"}:
		frappe.throw(_("El uso de la cuenta frecuente no es válido."))
	account = {
		"account_name": _required(data.get("account_name"), "Escriba un nombre para la cuenta frecuente."),
		"active": 1,
		"project": project or None,
		"direction": direction,
		"origin_or_sender": _required(
			data.get("origin_or_sender"), "La cuenta frecuente requiere titular o remitente."
		),
		"institution": str(data.get("institution") or "").strip(),
		"account_reference": str(data.get("account_reference") or "").strip(),
		"currency": str(data.get("currency") or "HNL").strip().upper(),
		"default_channel": channel,
		"is_default": int(bool(data.get("is_default"))),
		"notes": str(data.get("notes") or "").strip(),
	}
	if channel == "Cash":
		account["institution"] = ""
		account["account_reference"] = ""
	elif channel in BANK_CHANNELS and (
		not account["institution"] or not account["account_reference"]
	):
		frappe.throw(_("La cuenta frecuente requiere banco o remesadora y número de cuenta."))
	account["account_fingerprint"] = _account_fingerprint(account)
	return account


def _account_row(name: str, project: str | None) -> dict[str, Any]:
	account = frappe.get_doc("NXR Financial Account", name)
	if not account.active:
		frappe.throw(_("La cuenta frecuente seleccionada está inactiva."))
	if account.project and str(account.project) != str(project or ""):
		frappe.throw(_("La cuenta frecuente no pertenece al proyecto seleccionado."), frappe.PermissionError)
	if account.direction not in {"Origin", "Both"}:
		frappe.throw(_("La cuenta seleccionada no está habilitada como origen de ingresos."))
	return account.as_dict()


def _save_account(data: Mapping[str, Any]) -> tuple[str, bool]:
	account_data = _validate_account_payload(data)
	existing = frappe.db.get_value(
		"NXR Financial Account", {"account_fingerprint": account_data["account_fingerprint"]}, "name"
	)
	if existing:
		return str(existing), True
	with service_write():
		account = frappe.get_doc({"doctype": "NXR Financial Account", **account_data}).insert(
			ignore_permissions=True
		)
	fingerprint = str(account_data["account_fingerprint"])
	audit(
		"financial_account_created",
		"NXR Financial Account",
		account.name,
		fingerprint,
		correlation(account_data),
		{"account": account.name, "project": account.project, "direction": account.direction},
	)
	return str(account.name), False


@frappe.whitelist(methods=["POST"])
def movement_catalog() -> list[dict[str, str]]:
	require_action("preview")
	return [{"code": code, **definition} for code, definition in MOVEMENT_CATALOG.items()]


@frappe.whitelist(methods=["POST"])
def list_financial_accounts(project: str | None = None) -> list[dict[str, Any]]:
	require_action("create_source")
	project_name = str(project or "").strip()
	if project_name:
		require_project_access(project_name, action="create_source")
	rows = frappe.get_all(
		"NXR Financial Account",
		filters={"active": 1, "direction": ["in", ["Origin", "Both"]]},
		fields=[
			"name",
			"account_name",
			"project",
			"origin_or_sender",
			"institution",
			"account_reference",
			"currency",
			"default_channel",
			"is_default",
		],
		order_by="is_default desc, account_name asc",
		limit_page_length=200,
	)
	return [
		{
			**dict(row),
			"masked_account_reference": _masked_account(row.get("account_reference")),
			"label": " · ".join(
				part
				for part in (
					str(row.get("account_name") or ""),
					str(row.get("institution") or ""),
					_masked_account(row.get("account_reference")),
				)
				if part and part != "—"
			),
		}
		for row in rows
		if not row.get("project") or str(row.get("project")) == project_name
	]


@frappe.whitelist(methods=["POST"])
def get_financial_account(account: str, project: str | None = None) -> dict[str, Any]:
	require_action("create_source")
	project_name = str(project or "").strip()
	if project_name:
		require_project_access(project_name, action="create_source")
	row = _account_row(_required(account, "Seleccione una cuenta frecuente."), project_name or None)
	row["masked_account_reference"] = _masked_account(row.get("account_reference"))
	return row


@frappe.whitelist(methods=["POST"])
def save_financial_account(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	point = savepoint()
	try:
		name, reused = _save_account(data)
		return {"account": name, "reused": reused}
	except frappe.DuplicateEntryError:
		rollback(point)
		fingerprint = _account_fingerprint(data)
		existing = frappe.db.get_value("NXR Financial Account", {"account_fingerprint": fingerprint}, "name")
		if existing:
			return {"account": str(existing), "reused": True}
		raise
	except Exception:
		rollback(point)
		raise


def _closed_month(project: str, document_date: Any) -> str | None:
	key = month_key(document_date)
	rows = frappe.get_all(
		"NXR Monthly Close",
		filters={"project": project, "status": "Approved"},
		fields=["name", "close_month", "close_date"],
		limit_page_length=500,
	)
	for row in rows:
		if str(row.get("close_month") or "").strip() == key:
			return str(row.get("name"))
		if row.get("close_date") and frappe.utils.getdate(row.get("close_date")).strftime("%Y-%m") == key:
			return str(row.get("name"))
	return None


def _document_date(data: Mapping[str, Any], *, reference_name: str = "") -> str:
	project = _required(data.get("project"), "Seleccione un proyecto.")
	reference_date = None
	if reference_name:
		reference_date = frappe.db.get_value("NXR Operation", reference_name, "operation_date")
		if not reference_date:
			frappe.throw(_("El documento original no existe."))
	try:
		value = validate_document_date(
			data.get("document_date") or data.get("operation_date") or data.get("source_date"),
			today=frappe.utils.getdate(frappe.utils.today()),
			reference_date=reference_date,
		)
	except OperationalDateError as exc:
		frappe.throw(_(str(exc)))
	closed = _closed_month(project, value)
	if closed:
		frappe.throw(
			_("El período {0} está cerrado por el documento {1}. Reabra o corrija el cierre antes de registrar.").format(
				month_key(value), closed
			)
		)
	return value.isoformat()


def _resolve_income(data: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
	prepared = dict(data)
	project = _required(prepared.get("project"), "Seleccione un proyecto.")
	require_project_access(project, action="create_source")
	account_name = str(prepared.get("financial_account") or "").strip() or None
	if account_name:
		account = _account_row(account_name, project)
		prepared.update(
			{
				"origin_or_sender": account.get("origin_or_sender"),
				"institution": account.get("institution"),
				"account_reference": account.get("account_reference"),
				"currency": account.get("currency") or "HNL",
				"channel": account.get("default_channel") or "Other",
			}
		)
	prepared["channel"] = _normalize_channel(prepared.get("channel"))
	prepared["source_date"] = _document_date(prepared)
	prepared["original_amount"] = money(prepared.get("original_amount", prepared.get("amount_hnl")))
	if prepared["original_amount"] <= 0:
		frappe.throw(_("El importe del ingreso debe ser mayor que cero."))
	prepared["currency"] = str(prepared.get("currency") or "HNL").strip().upper()
	prepared["exchange_rate"] = prepared.get("exchange_rate") or 1
	prepared["origin_or_sender"] = _required(
		prepared.get("origin_or_sender"), "El ingreso requiere remitente u origen."
	)
	if prepared["channel"] in BANK_CHANNELS:
		_required(prepared.get("institution"), "El ingreso requiere banco o remesadora.")
		_required(prepared.get("account_reference"), "El ingreso requiere cuenta destino.")
	if prepared["channel"] in BANK_CHANNELS:
		_required(prepared.get("external_reference"), "El ingreso requiere número de referencia.")
	prepared["custodian"] = prepared.get("custodian") or frappe.session.user
	prepared["source_name"] = str(prepared.get("source_name") or "").strip() or (
		f"{CHANNEL_LABELS[prepared['channel']]} · {prepared['origin_or_sender']} · {prepared['source_date']}"
	)
	return prepared, account_name


def _record_metadata(operation: str, movement_code: str, financial_account: str | None = None) -> None:
	existing = frappe.db.get_value("NXR Operation Metadata", {"operation": operation}, ["name", "movement_code"], as_dict=True)
	if existing:
		if str(existing.movement_code) != movement_code:
			frappe.throw(_("La operación ya conserva un código operativo diferente."))
		return
	with service_write():
		frappe.get_doc(
			{
				"doctype": "NXR Operation Metadata",
				"operation": operation,
				"movement_code": movement_code,
				"financial_account": financial_account,
			}
		).insert(ignore_permissions=True)


def _income_preview(data: Mapping[str, Any]) -> dict[str, Any]:
	prepared, account_name = _resolve_income(data)
	stable = {
		key: prepared.get(key)
		for key in (
			"project",
			"source_date",
			"currency",
			"original_amount",
			"exchange_rate",
			"channel",
			"origin_or_sender",
			"institution",
			"account_reference",
			"external_reference",
		)
	}
	stable["movement_code"] = "101"
	stable["financial_account"] = account_name
	return {
		"movement_code": "101",
		"movement_label": MOVEMENT_CATALOG["101"]["label"],
		"document_date": prepared["source_date"],
		"amount_hnl": f"{money(prepared['original_amount']) * money(prepared['exchange_rate']):.2f}",
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": "Fuente independiente + operación 101",
		"sources": [],
		"account": account_name,
	}


def _central_payload(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	definition = MOVEMENT_CATALOG[movement_code]
	project = _required(data.get("project"), "Seleccione un proyecto.")
	require_project_access(project, action="execute" if movement_code == "102" else "reclassify")
	reference_name = str(data.get("reference_name") or "").strip()
	if movement_code in {"303", "304", "501"} and not reference_name:
		frappe.throw(_("Seleccione el documento original."))
	if reference_name:
		original_project = frappe.db.get_value("NXR Operation", reference_name, "project")
		if not original_project:
			frappe.throw(_("El documento original no existe."))
		if str(original_project) != project:
			frappe.throw(_("La corrección debe conservar el proyecto del documento original."))
	document_date = _document_date(data, reference_name=reference_name)
	description = str(data.get("description") or data.get("reason") or "").strip()
	if movement_code in {"303", "304", "501"} and len(description) < 10:
		frappe.throw(_("Explique el motivo o la corrección con al menos 10 caracteres."))
	payload = {
		**dict(data),
		"operation_code": definition["operation_code"],
		"economic_category": definition["economic_category"] or data.get("economic_category"),
		"project": project,
		"operation_date": document_date,
		"reference_doctype": "NXR Operation" if reference_name else "",
		"reference_name": reference_name,
		"description": description or _("Operación registrada desde la consola operativa NEXORA"),
		"requester": data.get("requester") or frappe.session.user,
		"approved_by": data.get("approved_by") or frappe.session.user,
	}
	if movement_code == "304":
		payload["amount_hnl"] = 0
	elif movement_code in {"303", "501"}:
		payload["amount_hnl"] = data.get("amount_hnl") or 0
	if movement_code == "102" and not payload.get("economic_category"):
		frappe.throw(_("Seleccione la categoría económica del gasto."))
	return payload


def _reference_is_income(reference_name: str) -> bool:
	return frappe.db.get_value("NXR Operation", reference_name, "operation_type") == "Inflow"


def _source_for_income_operation(reference_name: str) -> str:
	source = frappe.db.get_value(
		"NXR Operation Effect",
		{"operation": reference_name, "dimension": "Funds", "effect_type": "Received"},
		"fund_source",
	)
	if not source:
		frappe.throw(_("El ingreso original no conserva una fuente anulable."))
	return str(source)


def _income_cancellation_preview(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	reference_name = _required(data.get("reference_name"), "Seleccione el ingreso original.")
	payload = _central_payload(data, movement_code)
	source_name = _source_for_income_operation(reference_name)
	source = frappe.get_doc("NXR Fund Source", source_name)
	stable = {
		"movement_code": movement_code,
		"reference_name": reference_name,
		"source": source_name,
		"project": source.project,
		"document_date": payload["operation_date"],
		"amount_hnl": f"{money(source.amount_hnl):.2f}",
		"reason": payload["description"],
	}
	return {
		"movement_code": movement_code,
		"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
		"document_date": payload["operation_date"],
		"amount_hnl": stable["amount_hnl"],
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": f"Documento compensatorio {movement_code}",
		"reference_name": reference_name,
		"source": source_name,
		"sources": [],
	}


@frappe.whitelist(methods=["POST"])
def preview_operational_movement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	movement_code = str(data.get("movement_code") or "").strip()
	if movement_code not in MOVEMENT_CATALOG:
		frappe.throw(_("Use un código de movimiento válido: 101, 102, 303, 304 o 501."))
	if movement_code == "101":
		return _income_preview(data)
	if movement_code in {"303", "501"} and _reference_is_income(
		_required(data.get("reference_name"), "Seleccione el documento original.")
	):
		return _income_cancellation_preview(data, movement_code)
	prepared = _central_payload(data, movement_code)
	preview = preview_central_operation(prepared)
	return {
		**preview,
		"movement_code": movement_code,
		"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
		"document_date": prepared["operation_date"],
	}


def _verify_income_preview(data: Mapping[str, Any], preview_hash: str) -> tuple[dict[str, Any], str | None]:
	preview = _income_preview(data)
	if not preview_hash or preview_hash != preview["preview_hash"]:
		frappe.throw(_("La vista previa del ingreso está vencida. Genérela nuevamente."))
	return _resolve_income(data)


def _execute_income(data: Mapping[str, Any]) -> dict[str, Any]:
	preview_hash = str(data.get("preview_hash") or "")
	prepared, account_name = _verify_income_preview(data, preview_hash)
	point = savepoint()
	try:
		if not account_name and bool(data.get("save_financial_account")):
			account_payload = {
				**prepared,
				"account_name": data.get("account_name"),
				"default_channel": prepared.get("channel"),
				"direction": "Origin",
			}
			account_name, _ = _save_account(account_payload)
		prepared["idempotency_key"] = _required(
			prepared.get("idempotency_key"), "La operación requiere clave de idempotencia."
		)
		result = create_fund_source(prepared)
		_record_metadata(str(result["operation"]), "101", account_name)
		return {
			**result,
			"movement_code": "101",
			"movement_label": MOVEMENT_CATALOG["101"]["label"],
			"financial_account": account_name,
			"document_date": prepared["source_date"],
		}
	except Exception:
		rollback(point)
		raise


def _execute_income_cancellation(data: Mapping[str, Any], movement_code: str) -> dict[str, Any]:
	preview = _income_cancellation_preview(data, movement_code)
	if str(data.get("preview_hash") or "") != preview["preview_hash"]:
		frappe.throw(_("La vista previa de la anulación está vencida. Genérela nuevamente."))
	point = savepoint()
	try:
		result = cancel_fund_source(
			preview["source"],
			str(data.get("description") or data.get("reason") or ""),
			_required(data.get("idempotency_key"), "La operación requiere clave de idempotencia."),
			operation_date=preview["document_date"],
		)
		operation = str(result["reversal_operation"])
		_record_metadata(operation, movement_code)
		return {
			**result,
			"operation": operation,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": preview["document_date"],
		}
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def execute_operational_movement(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	movement_code = str(data.get("movement_code") or "").strip()
	if movement_code not in MOVEMENT_CATALOG:
		frappe.throw(_("Use un código de movimiento válido: 101, 102, 303, 304 o 501."))
	if movement_code == "101":
		return _execute_income(data)
	if movement_code in {"303", "501"} and _reference_is_income(
		_required(data.get("reference_name"), "Seleccione el documento original.")
	):
		return _execute_income_cancellation(data, movement_code)
	prepared = _central_payload(data, movement_code)
	prepared["idempotency_key"] = _required(
		data.get("idempotency_key"), "La operación requiere clave de idempotencia."
	)
	prepared["preview_hash"] = _required(data.get("preview_hash"), "Genere una vista previa antes de ejecutar.")
	point = savepoint()
	try:
		result = execute_central_operation(prepared)
		operation = str(result["operation"])
		_record_metadata(operation, movement_code)
		return {
			**result,
			"movement_code": movement_code,
			"movement_label": MOVEMENT_CATALOG[movement_code]["label"],
			"document_date": prepared["operation_date"],
		}
	except Exception:
		rollback(point)
		raise


def _derived_movement_code(row: Mapping[str, Any], explicit: str | None) -> str:
	if explicit in MOVEMENT_CATALOG:
		return str(explicit)
	operation_code = str(row.get("operation_code") or "")
	operation_type = str(row.get("operation_type") or "")
	if operation_type == "Inflow":
		return "101"
	if operation_code == "DOCUMENT_SUBSTITUTION":
		return "304"
	if operation_code == "REVERSAL_NO_CASH" or row.get("reversal_of"):
		return "303"
	if operation_type in {"Outflow", "Commitment Execution"}:
		return "102"
	return "102"


def _operation_status(row: Mapping[str, Any]) -> str:
	status = str(row.get("status") or "")
	if status == "Draft":
		return "Borrador"
	if status == "Rejected":
		return "Rechazado"
	return "Contabilizado"


def _ledger_tone(code: str, row: Mapping[str, Any]) -> tuple[str, bool]:
	status = str(row.get("status") or "")
	voided = code in {"303", "304", "501"} or status in {"Cancelled", "Compensated Total"}
	if voided:
		return "voided", True
	if code == "101":
		return "income", False
	return "expense", False


@frappe.whitelist(methods=["POST"])
def list_operational_ledger(project: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
	require_action("preview")
	project_name = str(project or "").strip() or None
	require_project_access(project_name, action="preview")
	page_limit = min(max(int(limit or 100), 1), 200)
	operations = frappe.get_all(
		"NXR Operation",
		filters={"project": project_name} if project_name else None,
		fields=[
			"name",
			"document_number",
			"operation_date",
			"creation",
			"operation_code",
			"operation_type",
			"project",
			"amount_hnl",
			"currency",
			"beneficiary",
			"status",
			"reference_name",
			"reversal_of",
		],
		order_by="operation_date desc, creation desc",
		limit_page_length=page_limit,
	)
	operation_names = [str(row["name"]) for row in operations]
	if not operation_names:
		return []
	metadata_rows = frappe.get_all(
		"NXR Operation Metadata",
		filters={"operation": ["in", operation_names]},
		fields=["operation", "movement_code", "financial_account"],
		limit_page_length=len(operation_names),
	)
	metadata = {str(row["operation"]): dict(row) for row in metadata_rows}
	effects = frappe.get_all(
		"NXR Operation Effect",
		filters={"operation": ["in", operation_names], "fund_source": ["is", "set"]},
		fields=["operation", "fund_source", "creation", "name"],
		order_by="creation asc, name asc",
		limit_page_length=page_limit * 20,
	)
	allocations = frappe.get_all(
		"NXR Fund Allocation",
		filters={"operation": ["in", operation_names]},
		fields=["operation", "fund_source", "creation", "name"],
		order_by="creation asc, name asc",
		limit_page_length=page_limit * 20,
	)
	sources_by_operation: dict[str, list[str]] = {}
	for row in [*effects, *allocations]:
		operation = str(row.get("operation") or "")
		source = str(row.get("fund_source") or "")
		if operation and source and source not in sources_by_operation.setdefault(operation, []):
			sources_by_operation[operation].append(source)
	source_names = sorted({source for rows in sources_by_operation.values() for source in rows})
	source_rows = frappe.get_all(
		"NXR Fund Source",
		filters={"name": ["in", source_names]} if source_names else None,
		fields=[
			"name",
			"origin_or_sender",
			"institution",
			"account_reference",
			"currency",
			"channel",
			"original_amount",
		],
		limit_page_length=max(len(source_names), 1),
	) if source_names else []
	sources = {str(row["name"]): dict(row) for row in source_rows}
	result = []
	for operation in operations:
		name = str(operation["name"])
		meta = metadata.get(name, {})
		code = _derived_movement_code(operation, meta.get("movement_code"))
		date_value = frappe.utils.getdate(operation.get("operation_date"))
		source_list = sources_by_operation.get(name, [])
		primary_source = sources.get(source_list[0], {}) if source_list else {}
		channel = str(primary_source.get("channel") or "")
		movement_label = MOVEMENT_CATALOG[code]["label"]
		if code == "101" and channel:
			movement_label = f"{movement_label} · {CHANNEL_LABELS.get(channel, channel)}"
		counterparty = str(
			primary_source.get("origin_or_sender")
			if code == "101"
			else operation.get("beneficiary") or primary_source.get("origin_or_sender") or "—"
		)
		institution = str(primary_source.get("institution") or "—")
		account = _masked_account(primary_source.get("account_reference"))
		currency = str(primary_source.get("currency") or operation.get("currency") or "HNL")
		if len(source_list) > 1:
			account = _("{0} fuentes").format(len(source_list))
		tone, struck = _ledger_tone(code, operation)
		result.append(
			{
				"name": name,
				"document_number": operation.get("document_number"),
				"movement_code": code,
				"movement_label": movement_label,
				"day": DAY_LABELS[date_value.weekday()],
				"document_date": date_value.isoformat(),
				"registered_at": str(operation.get("creation") or ""),
				"counterparty": counterparty,
				"institution": institution,
				"account": account,
				"currency": currency,
				"amount_hnl": f"{money(operation.get('amount_hnl')):.2f}",
				"status": _operation_status(operation),
				"tone": tone,
				"struck": struck,
				"source_count": len(source_list),
				"reference_name": operation.get("reference_name") or operation.get("reversal_of"),
			}
		)
	return result
