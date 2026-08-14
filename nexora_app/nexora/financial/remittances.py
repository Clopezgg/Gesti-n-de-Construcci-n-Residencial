from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

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
from nexora.financial.sources import cancel_fund_source, open_fund_source
from nexora.permissions import require_action


@frappe.whitelist(methods=["POST"])
def create_remittance(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Split a single received amount across several new fund sources.

	Reuses `open_fund_source()` — the same "one fondo, one operación 101" path
	`create_fund_source()` uses — once per destino, inside one savepoint and one
	idempotency key shared by the whole family. Cada `NXR Fund Source` creado
	queda con `remittance` apuntando al padre para trazabilidad; el reparto en
	sí (que la suma cuadre) lo exige `NXRRemittance.validate()`, no aquí, para
	no duplicar la regla."""
	require_action("create_source")
	data = parse_payload(payload)
	data["idempotency_key"] = str(data.get("idempotency_key") or "")
	source_date = frappe.utils.getdate(data.get("source_date") or frappe.utils.today())
	data["source_date"] = source_date.isoformat()
	destinations = list(data.get("destinations") or [])
	if not destinations:
		frappe.throw(_("Una remesa requiere al menos un destino."))
	fingerprint = canonical_payload_hash(data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(data["idempotency_key"], fingerprint, correlation_id)
		if cached is not None:
			return cached
		remittance_number, remittance_sequence = issue_document_number(
			"NXR Remittance", data["idempotency_key"]
		)
		with service_write():
			remittance = frappe.get_doc(
				{
					"doctype": "NXR Remittance",
					"remittance_code": remittance_number,
					"project": data["project"],
					"remittance_date": data["source_date"],
					"currency": data.get("currency") or "HNL",
					"total_original_amount": data["original_amount"],
					"exchange_rate": data.get("exchange_rate") or 1,
					"origin_or_sender": data["origin_or_sender"],
					"custodian": data.get("custodian") or frappe.session.user,
					"institution": data.get("institution"),
					"account_reference": data.get("account_reference"),
					"external_reference": data.get("external_reference"),
					"evidence": data.get("evidence"),
					"channel": data["channel"],
					"destinations": [
						{
							"label": row["label"],
							"amount_hnl": row["amount_hnl"],
							"project": row.get("project") or data["project"],
						}
						for row in destinations
					],
				}
			).insert(ignore_permissions=True)
		link_sequence(remittance_sequence, remittance.name)
		opened = []
		for row in remittance.destinations:
			source_data = {
				**data,
				"source_name": f"{remittance.remittance_code} · {row.label}",
				"project": row.project or data["project"],
				"currency": "HNL",
				"original_amount": row.amount_hnl,
				"exchange_rate": 1,
				"remittance": remittance.name,
				"idempotency_key": f"{data['idempotency_key']}::{row.name}",
			}
			result = open_fund_source(source_data, correlation_id)
			row.fund_source = result["fund_source"]
			opened.append({"label": row.label, **result})
		with service_write():
			remittance.save(ignore_permissions=True)
		result = {
			"remittance": remittance.name,
			"remittance_number": remittance_number,
			"destinations": opened,
			"total_amount_hnl": f"{remittance.total_amount_hnl:.2f}",
		}
		audit("remittance_created", "NXR Remittance", remittance.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Remittance", remittance.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def cancel_remittance(remittance: str, reason: str, idempotency_key: str) -> dict[str, Any]:
	"""Cancel a remittance and every fund source it opened — all or nothing.

	No hay cancelación parcial de un solo destino en esta primera versión:
	cancelar uno solo dejaría la suma del padre sin sentido. Reutiliza el
	`cancel_fund_source()` público (no una copia de su lógica) una vez por
	destino, dentro del mismo `savepoint` — si cualquiera falla, ninguno queda
	anulado."""
	require_action("cancel_source")
	remittance_name = str(remittance or "").strip()
	if not remittance_name:
		frappe.throw(_("Seleccione la remesa que desea anular."))
	cancellation_reason = str(reason or "").strip()
	if len(cancellation_reason) < 10:
		frappe.throw(_("Explique el motivo de la anulación con al menos 10 caracteres."))
	key = str(idempotency_key or "").strip()
	fingerprint = canonical_payload_hash(
		{"remittance": remittance_name, "reason": cancellation_reason, "idempotency_key": key}
	)
	correlation_id = correlation({})
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = frappe.get_doc("NXR Remittance", remittance_name)
		if doc.status == "Cancelled":
			frappe.throw(_("Esta remesa ya está anulada."))
		cancelled = [
			cancel_fund_source(
				row.fund_source,
				cancellation_reason,
				f"{key}::cancel::{row.name}",
			)
			for row in doc.destinations
		]
		with service_write():
			doc.status = "Cancelled"
			doc.cancellation_reason = cancellation_reason
			doc.cancelled_by = frappe.session.user
			doc.cancelled_at = frappe.utils.now_datetime()
			doc.save(ignore_permissions=True)
		result = {"remittance": doc.name, "status": "Cancelled", "sources": cancelled}
		audit("remittance_cancelled", "NXR Remittance", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Remittance", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
