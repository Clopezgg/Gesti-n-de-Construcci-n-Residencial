from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.financial.context import service_write
from nexora.financial.core import canonical_payload_hash, money
from nexora.financial.db import (
	complete_idempotency,
	correlation,
	issue_document_number,
	link_sequence,
	parse_payload,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.financial.model_utils import rate
from nexora.financial.operational_common import (
	BANK_CHANNELS,
	CHANNEL_LABELS,
	_closed_month,
	_masked_account,
	_normalize_channel,
	_required,
)
from nexora.financial.operational_dates import OperationalDateError, validate_document_date
from nexora.financial.operational_metadata import record_operation_metadata
from nexora.permissions import require_project_access

CORRECTION_OPERATION_CODE = "DOCUMENT_SUBSTITUTION"
CORRECTION_MOVEMENT_CODE = "304"
CORRECTABLE_STATUS = "Executed"


def _document_token(value: object) -> str:
	token = str(value or "").strip()
	if not token:
		frappe.throw(_("Escriba el número de documento que desea corregir."))
	return token


def _resolve_operation_name(value: object) -> str:
	token = _document_token(value)
	if frappe.db.exists("NXR Operation", token):
		return token
	if not token.isdigit() or len(token) != 12:
		frappe.throw(_("El número de documento debe contener exactamente 12 dígitos."))
	name = frappe.db.get_value("NXR Operation", {"document_number": token}, "name")
	if not name:
		frappe.throw(_("No existe una operación con el número {0}.").format(token))
	return str(name)


def _lock(doctype: str, name: str) -> None:
	table = frappe.qb.DocType(doctype)
	rows = (frappe.qb.from_(table).select(table.name).where(table.name == name).for_update()).run()
	if not rows:
		frappe.throw(_("El documento cambió o ya no existe. Vuelva a buscarlo."))


def _load_income_context(document: object, *, lock: bool = False) -> dict[str, Any]:
	operation_name = _resolve_operation_name(document)
	if lock:
		_lock("NXR Operation", operation_name)
	operation = frappe.get_doc("NXR Operation", operation_name)
	if operation.status != CORRECTABLE_STATUS:
		frappe.throw(_("Solo se pueden corregir operaciones contabilizadas que sigan ejecutadas."))
	if operation.operation_type != "Inflow":
		frappe.throw(_("La corrección guiada de fecha, remesa e importe aplica únicamente a ingresos."))
	if operation.operation_code == CORRECTION_OPERATION_CODE:
		frappe.throw(_("Seleccione el documento base, no un documento de corrección."))
	require_project_access(str(operation.project), action="reclassify")

	effects = frappe.get_all(
		"NXR Operation Effect",
		filters={
			"operation": operation.name,
			"dimension": "Funds",
			"effect_type": "Received",
		},
		fields=["name", "fund_source", "amount_hnl"],
		order_by="creation asc, name asc",
		limit_page_length=2,
	)
	if len(effects) != 1 or not effects[0].get("fund_source"):
		frappe.throw(_("El ingreso no conserva una fuente inicial única y no admite esta corrección guiada."))
	effect_name = str(effects[0]["name"])
	source_name = str(effects[0]["fund_source"])
	if lock:
		_lock("NXR Fund Source", source_name)
		_lock("NXR Operation Effect", effect_name)
	source = frappe.get_doc("NXR Fund Source", source_name)
	effect = frappe.get_doc("NXR Operation Effect", effect_name)
	return {"operation": operation, "source": source, "effect": effect}


def _amount_is_editable(context: Mapping[str, Any]) -> tuple[bool, str]:
	source = context["source"]
	effect = context["effect"]
	effect_count = frappe.db.count("NXR Operation Effect", filters={"fund_source": source.name})
	allocation_count = frappe.db.count("NXR Fund Allocation", filters={"fund_source": source.name})
	editable = bool(
		source.status in {"Active", "Exhausted"}
		and effect_count == 1
		and allocation_count == 0
		and money(effect.amount_hnl) == money(source.amount_hnl)
	)
	if editable:
		return True, ""
	return (
		False,
		_(
			"El importe y la tasa están bloqueados porque el fondo ya tiene gastos, reservas, transferencias o ajustes. "
			"Corrija primero esos movimientos mediante documentos compensatorios."
		),
	)


def _date(value: object) -> str:
	return frappe.utils.getdate(value).isoformat()


def _snapshot(context: Mapping[str, Any]) -> dict[str, str]:
	operation = context["operation"]
	source = context["source"]
	return {
		"document_date": _date(operation.operation_date),
		"source_name": str(source.source_name or ""),
		"channel": str(source.channel or "Other"),
		"currency": str(source.currency or "HNL"),
		"original_amount": f"{money(source.original_amount):.2f}",
		"exchange_rate": f"{rate(source.exchange_rate):.9f}",
		"amount_hnl": f"{money(source.amount_hnl):.2f}",
		"origin_or_sender": str(source.origin_or_sender or ""),
		"institution": str(source.institution or ""),
		"account_reference": str(source.account_reference or ""),
		"external_reference": str(source.external_reference or operation.external_reference or ""),
		"evidence": str(source.evidence or operation.evidence or ""),
	}


def _validate_open_period(project: str, value: str, label: str) -> None:
	closed = _closed_month(project, value)
	if closed:
		frappe.throw(
			_("No se puede cambiar {0}: el período está cerrado por el documento {1}.").format(label, closed)
		)


def _normalized_proposal(data: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
	before = _snapshot(context)
	operation = context["operation"]
	amount_editable, amount_block_reason = _amount_is_editable(context)
	try:
		document_date = validate_document_date(
			data.get("document_date") or before["document_date"],
			today=frappe.utils.getdate(frappe.utils.today()),
		).isoformat()
	except OperationalDateError as exc:
		frappe.throw(_(str(exc)))

	source_name = _required(
		data.get("source_name") or before["source_name"],
		"Escriba el nombre de la remesa o fuente.",
	)
	channel = _normalize_channel(data.get("channel") or before["channel"])
	currency = _required(data.get("currency") or before["currency"], "Seleccione la moneda.").upper()
	if not frappe.db.exists("Currency", currency):
		frappe.throw(_("La moneda seleccionada no existe."))
	original_amount = money(data.get("original_amount", before["original_amount"]))
	exchange_rate = rate(data.get("exchange_rate", before["exchange_rate"]))
	if original_amount <= 0 or exchange_rate <= 0:
		frappe.throw(_("El importe y la tasa deben ser mayores que cero."))
	amount_hnl = money(original_amount * exchange_rate)
	origin_or_sender = _required(
		data.get("origin_or_sender") or before["origin_or_sender"],
		"Escriba el remitente u origen.",
	)
	institution = str(data.get("institution") if "institution" in data else before["institution"]).strip()
	account_reference = str(
		data.get("account_reference") if "account_reference" in data else before["account_reference"]
	).strip()
	external_reference = str(
		data.get("external_reference") if "external_reference" in data else before["external_reference"]
	).strip()
	evidence = str(data.get("evidence") if "evidence" in data else before["evidence"]).strip()
	if channel == "Cash":
		institution = ""
		account_reference = ""
		external_reference = ""
	elif channel in BANK_CHANNELS:
		_required(institution, "Seleccione el banco o remesadora.")
		if not frappe.db.exists("Bank", institution):
			frappe.throw(_("El banco o remesadora seleccionado no existe."))
		_required(account_reference, "Escriba la cuenta destino.")
		_required(external_reference, "Escriba el número de referencia.")

	reason = str(data.get("reason") or data.get("description") or "").strip()
	if len(reason) < 10:
		frappe.throw(_("Explique la corrección con al menos 10 caracteres."))
	after = {
		"document_date": document_date,
		"source_name": source_name,
		"channel": channel,
		"currency": currency,
		"original_amount": f"{original_amount:.2f}",
		"exchange_rate": f"{exchange_rate:.9f}",
		"amount_hnl": f"{amount_hnl:.2f}",
		"origin_or_sender": origin_or_sender,
		"institution": institution,
		"account_reference": account_reference,
		"external_reference": external_reference,
		"evidence": evidence,
	}
	changed_fields = [field for field, value in after.items() if value != before[field]]
	if not changed_fields:
		frappe.throw(_("No hay cambios para registrar."))
	financial_fields = {"currency", "original_amount", "exchange_rate", "amount_hnl"}
	financial_change = bool(financial_fields.intersection(changed_fields))
	if financial_change and not amount_editable:
		frappe.throw(amount_block_reason)
	if "document_date" in changed_fields:
		_validate_open_period(
			str(operation.project),
			before["document_date"],
			_("la fecha del documento"),
		)
		_validate_open_period(
			str(operation.project),
			after["document_date"],
			_("la fecha del documento"),
		)
	if financial_change:
		_validate_open_period(str(operation.project), before["document_date"], _("el importe"))
	return {
		"before": before,
		"after": after,
		"changed_fields": changed_fields,
		"financial_change": financial_change,
		"amount_editable": amount_editable,
		"amount_block_reason": amount_block_reason,
		"reason": reason,
	}


def _preview(context: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
	operation = context["operation"]
	source = context["source"]
	stable = {
		"operation": operation.name,
		"operation_modified": str(operation.modified),
		"source": source.name,
		"source_modified": str(source.modified),
		"before": proposal["before"],
		"after": proposal["after"],
		"changed_fields": proposal["changed_fields"],
		"reason": proposal["reason"],
	}
	before_amount = money(proposal["before"]["amount_hnl"])
	after_amount = money(proposal["after"]["amount_hnl"])
	return {
		"operation": operation.name,
		"document_number": operation.document_number,
		"project": operation.project,
		"source": source.name,
		"before": proposal["before"],
		"after": proposal["after"],
		"changed_fields": proposal["changed_fields"],
		"financial_change": proposal["financial_change"],
		"financial_delta_hnl": f"{money(after_amount - before_amount):.2f}",
		"amount_editable": proposal["amount_editable"],
		"amount_block_reason": proposal["amount_block_reason"],
		"evidence_required": False,
		"preview_hash": canonical_payload_hash(stable),
		"document_to_generate": _("Corrección documental 304"),
	}


@frappe.whitelist(methods=["POST"])
def get_operation_for_correction(document: str) -> dict[str, Any]:
	context = _load_income_context(document)
	operation = context["operation"]
	source = context["source"]
	amount_editable, amount_block_reason = _amount_is_editable(context)
	values = _snapshot(context)
	return {
		"operation": operation.name,
		"document_number": operation.document_number,
		"project": operation.project,
		"source": source.name,
		"source_code": source.source_code,
		**values,
		"masked_account_reference": _masked_account(values["account_reference"]),
		"channel_label": CHANNEL_LABELS.get(values["channel"], values["channel"]),
		"amount_editable": amount_editable,
		"amount_block_reason": amount_block_reason,
		"evidence_required": False,
	}


@frappe.whitelist(methods=["POST"])
def preview_operation_correction(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	context = _load_income_context(data.get("document") or data.get("document_number"))
	proposal = _normalized_proposal(data, context)
	return _preview(context, proposal)


def _insert_correction_operation(
	*,
	context: Mapping[str, Any],
	proposal: Mapping[str, Any],
	preview_hash: str,
	idempotency_key: str,
	correlation_id: str,
) -> tuple[Any, str]:
	operation = context["operation"]
	document_number, sequence = issue_document_number("NXR Operation", idempotency_key)
	with service_write():
		correction = frappe.get_doc(
			{
				"doctype": "NXR Operation",
				"document_number": document_number,
				"operation_code": CORRECTION_OPERATION_CODE,
				"operation_type": "Reclassification",
				"status": "Executed",
				"project": operation.project,
				"operation_date": frappe.utils.today(),
				"currency": "HNL",
				"amount": 0,
				"exchange_rate": 1,
				"economic_category": "DOCUMENTARY",
				"idempotency_key": idempotency_key,
				"payload_hash": canonical_payload_hash(
					{
						"operation": operation.name,
						"after": proposal["after"],
						"reason": proposal["reason"],
					}
				),
				"preview_hash": preview_hash,
				"requester": frappe.session.user,
				"approved_by": frappe.session.user,
				"executed_by": frappe.session.user,
				"evidence": proposal["after"]["evidence"] or None,
				"reference_doctype": "NXR Operation",
				"reference_name": operation.name,
				"reference_amount_hnl": proposal["before"]["amount_hnl"],
				"reference_balance_before_hnl": 0,
				"reference_balance_after_hnl": 0,
				"substitutes_operation": operation.name,
				"correlation_id": correlation_id,
			}
		)
		correction.flags.nexora_guided_correction = True
		correction.insert(ignore_permissions=True)
	link_sequence(sequence, correction.name)
	return correction, document_number


def _apply_effective_values(context: Mapping[str, Any], proposal: Mapping[str, Any]) -> None:
	operation = context["operation"]
	source = context["source"]
	effect = context["effect"]
	after = proposal["after"]
	with service_write():
		source.flags.nexora_documentary_correction = True
		source.source_date = after["document_date"]
		source.source_name = after["source_name"]
		source.channel = after["channel"]
		source.currency = after["currency"]
		source.original_amount = after["original_amount"]
		source.exchange_rate = after["exchange_rate"]
		source.origin_or_sender = after["origin_or_sender"]
		source.institution = after["institution"] or None
		source.account_reference = after["account_reference"] or None
		source.external_reference = after["external_reference"] or None
		source.evidence = after["evidence"] or None
		source.save(ignore_permissions=True)

		operation.flags.nexora_documentary_correction = True
		operation.operation_date = after["document_date"]
		operation.amount = after["amount_hnl"]
		operation.exchange_rate = 1
		operation.external_reference = after["external_reference"] or None
		operation.evidence = after["evidence"] or None
		operation.save(ignore_permissions=True)

		if proposal["financial_change"]:
			effect.flags.nexora_documentary_correction = True
			effect.amount_hnl = after["amount_hnl"]
			effect.save(ignore_permissions=True)


def _write_audit(
	*,
	context: Mapping[str, Any],
	proposal: Mapping[str, Any],
	correction: Any,
	correlation_id: str,
) -> None:
	operation = context["operation"]
	payload = {
		"correction_operation": correction.name,
		"correction_document_number": correction.document_number,
		"reason": proposal["reason"],
		"changed_fields": proposal["changed_fields"],
		"values": proposal["after"],
	}
	with service_write():
		frappe.get_doc(
			{
				"doctype": "NXR Audit Event",
				"event_type": "operation_document_corrected",
				"actor": frappe.session.user,
				"reference_doctype": "NXR Operation",
				"reference_name": operation.name,
				"payload_hash": canonical_payload_hash(payload),
				"before_json": json.dumps(
					proposal["before"],
					ensure_ascii=False,
					sort_keys=True,
				),
				"after_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
				"correlation_id": correlation_id,
			}
		).insert(ignore_permissions=True)


def _idempotency_fingerprint(data: Mapping[str, Any]) -> str:
	return canonical_payload_hash(
		{
			"document": data.get("document") or data.get("document_number"),
			"document_date": data.get("document_date"),
			"source_name": data.get("source_name"),
			"channel": data.get("channel"),
			"currency": data.get("currency"),
			"original_amount": data.get("original_amount"),
			"exchange_rate": data.get("exchange_rate"),
			"origin_or_sender": data.get("origin_or_sender"),
			"institution": data.get("institution"),
			"account_reference": data.get("account_reference"),
			"external_reference": data.get("external_reference"),
			"evidence": data.get("evidence"),
			"reason": data.get("reason") or data.get("description"),
			"preview_hash": data.get("preview_hash"),
		}
	)


@frappe.whitelist(methods=["POST"])
def execute_operation_correction(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	data = parse_payload(payload)
	idempotency_key = _required(
		data.get("idempotency_key"),
		"La corrección requiere clave de idempotencia.",
	)
	fingerprint = _idempotency_fingerprint(data)
	existing_idem = frappe.db.get_value(
		"NXR Idempotency Record",
		idempotency_key,
		["payload_hash", "status", "response_json"],
		as_dict=True,
	)
	if existing_idem:
		if str(existing_idem.payload_hash) != fingerprint:
			frappe.throw(_("La clave de idempotencia ya fue usada con un payload diferente."))
		if existing_idem.status == "Completed" and existing_idem.response_json:
			return json.loads(existing_idem.response_json)
		frappe.throw(_("La misma solicitud ya está en procesamiento."))
	point = savepoint()
	try:
		context = _load_income_context(
			data.get("document") or data.get("document_number"),
			lock=True,
		)
		proposal = _normalized_proposal(data, context)
		preview = _preview(context, proposal)
		if str(data.get("preview_hash") or "") != preview["preview_hash"]:
			frappe.throw(_("La vista previa de la corrección está vencida. Genérela nuevamente."))
		correlation_id = correlation(data)
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		correction, correction_number = _insert_correction_operation(
			context=context,
			proposal=proposal,
			preview_hash=preview["preview_hash"],
			idempotency_key=idempotency_key,
			correlation_id=correlation_id,
		)
		_apply_effective_values(context, proposal)
		record_operation_metadata(correction.name, CORRECTION_MOVEMENT_CODE)
		_write_audit(
			context=context,
			proposal=proposal,
			correction=correction,
			correlation_id=correlation_id,
		)
		result = {
			"operation": context["operation"].name,
			"document_number": context["operation"].document_number,
			"correction_operation": correction.name,
			"correction_document_number": correction_number,
			"changed_fields": proposal["changed_fields"],
			"financial_delta_hnl": preview["financial_delta_hnl"],
			"document_date": proposal["after"]["document_date"],
		}
		complete_idempotency(idem, "NXR Operation", correction.name, result)
		return result
	except Exception:
		rollback(point)
		raise
