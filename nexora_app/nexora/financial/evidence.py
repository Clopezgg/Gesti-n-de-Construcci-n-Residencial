from __future__ import annotations

import mimetypes
from typing import Any, Mapping

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
from nexora.financial.evidence_core import EvidencePolicy, evaluate_evidence_policy, normalize_file_content, sha256_content
from nexora.permissions import require_action

MAX_EVIDENCE_BYTES = 15 * 1024 * 1024
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "application/pdf", "text/plain"})
ALLOWED_KINDS = frozenset(
	{"Payment Proof", "External Authorization", "Real Return", "Document Substitution", "Other"}
)
ALLOWED_CHANNELS = frozenset({"WhatsApp", "Bank Receipt", "Cash Receipt", "Email", "Other"})


def operation_evidence_policy(data: Mapping[str, Any], *, profile_requires_evidence: bool) -> EvidencePolicy:
	return evaluate_evidence_policy(
		data.get("payment_method"),
		data.get("amount_hnl", data.get("amount")),
		data.get("economic_category"),
		profile_requires_evidence=profile_requires_evidence,
	)


def expected_evidence_kind(operation_code: str, policy: EvidencePolicy) -> str:
	if operation_code == "REAL_RETURN":
		return "Real Return"
	if operation_code == "DOCUMENT_SUBSTITUTION":
		return "Document Substitution"
	if policy.requires_external_authorization:
		return "External Authorization"
	return "Payment Proof"


def _required(data: Mapping[str, Any], fieldname: str, message: str) -> str:
	value = str(data.get(fieldname) or "").strip()
	if not value:
		frappe.throw(_(message))
	return value


def _file_snapshot(file_url: str) -> dict[str, Any]:
	row = frappe.db.get_value(
		"File", {"file_url": file_url}, ["name", "file_name", "is_private"], as_dict=True
	)
	if not row:
		frappe.throw(_("El archivo de evidencia no existe."))
	if not bool(row.is_private) or not str(file_url).startswith("/private/files/"):
		frappe.throw(_("La evidencia debe almacenarse como archivo privado."))
	file_doc = frappe.get_doc("File", row.name)
	content = normalize_file_content(file_doc.get_content())
	if not content:
		frappe.throw(_("El archivo de evidencia está vacío."))
	if len(content) > MAX_EVIDENCE_BYTES:
		frappe.throw(_("La evidencia supera el límite de 15 MB."))
	mime_type = mimetypes.guess_type(str(row.file_name or file_url))[0] or "application/octet-stream"
	if mime_type not in ALLOWED_MIME_TYPES:
		frappe.throw(_("Tipo de archivo de evidencia no permitido: {0}.").format(mime_type))
	return {
		"file_url": file_url,
		"file_name": row.file_name or str(file_url).rsplit("/", 1)[-1],
		"mime_type": mime_type,
		"file_size": len(content),
		"content_sha256": sha256_content(content),
	}


def _lock_evidence(name: str) -> Any:
	rows = frappe.db.sql("SELECT name FROM `tabNXR Evidence` WHERE name=%s FOR UPDATE", name)
	if not rows:
		frappe.throw(_("La evidencia indicada no existe."))
	return frappe.get_doc("NXR Evidence", name)


def _evidence_record(value: str) -> Any | None:
	name = value if frappe.db.exists("NXR Evidence", value) else frappe.db.get_value(
		"NXR Evidence", {"file_url": value}, "name"
	)
	return frappe.get_doc("NXR Evidence", name) if name else None


def validate_operation_evidence(
	evidence_name: str | None,
	*,
	project: str,
	policy: EvidencePolicy,
	expected_kind: str,
) -> str | None:
	value = str(evidence_name or "").strip()
	if not value:
		if policy.required:
			frappe.throw(_(policy.reason))
		return None
	doc = _evidence_record(value)
	if not doc:
		if policy.requires_external_authorization:
			frappe.throw(_("La autorización externa requiere un expediente NXR Evidence validado."))
		if not value.startswith("/private/files/"):
			frappe.throw(_("La evidencia debe ser un expediente validado o una referencia de archivo privado."))
		return value
	if doc.project != project:
		frappe.throw(_("La evidencia debe pertenecer al mismo proyecto de la operación."))
	if doc.status != "Validated":
		frappe.throw(_("La evidencia debe estar validada antes de ejecutar la operación."))
	if doc.evidence_kind != expected_kind:
		frappe.throw(_("La evidencia debe ser de tipo {0} para esta operación.").format(expected_kind))
	is_private = frappe.db.get_value("File", {"file_url": doc.file_url}, "is_private")
	if not bool(is_private) or not str(doc.file_url).startswith("/private/files/"):
		frappe.throw(_("El archivo vinculado dejó de ser privado o ya no existe."))
	if policy.requires_external_authorization:
		if doc.channel != "WhatsApp":
			frappe.throw(_("La autorización externa de esta etapa debe conservarse como evidencia WhatsApp."))
		if not doc.sender or not doc.source_message_date or not doc.external_reference:
			frappe.throw(_("La evidencia WhatsApp requiere autorizador, fecha y referencia."))
	return str(doc.file_url)


@frappe.whitelist(methods=["POST"])
def register_evidence(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("upload_evidence")
	data = parse_payload(payload)
	project = _required(data, "project", "La evidencia requiere proyecto.")
	file_url = _required(data, "file_url", "La evidencia requiere archivo privado.")
	kind = _required(data, "evidence_kind", "La evidencia requiere tipo.")
	channel = _required(data, "channel", "La evidencia requiere canal.")
	idempotency_key = _required(data, "idempotency_key", "La evidencia requiere clave de idempotencia.")
	if kind not in ALLOWED_KINDS:
		frappe.throw(_("Tipo de evidencia no permitido."))
	if channel not in ALLOWED_CHANNELS:
		frappe.throw(_("Canal de evidencia no permitido."))
	file_data = _file_snapshot(file_url)
	fingerprint_data = {
		"project": project,
		"evidence_kind": kind,
		"channel": channel,
		"content_sha256": file_data["content_sha256"],
		"source_message_date": data.get("source_message_date"),
		"sender": data.get("sender"),
		"external_reference": data.get("external_reference"),
		"notes": data.get("notes"),
		"supersedes": data.get("supersedes"),
	}
	fingerprint = canonical_payload_hash(fingerprint_data)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		version = 1
		previous = None
		if data.get("supersedes"):
			previous = _lock_evidence(str(data["supersedes"]))
			if previous.status not in {"Validated", "Rejected"}:
				frappe.throw(_("Solo una evidencia validada o rechazada puede sustituirse."))
			if previous.project != project:
				frappe.throw(_("La evidencia sustituta debe pertenecer al mismo proyecto."))
			if previous.content_sha256 == file_data["content_sha256"]:
				frappe.throw(_("La sustitución debe contener un archivo diferente."))
			version = int(previous.version or 1) + 1
		number, sequence = issue_document_number("NXR Evidence", idempotency_key)
		with service_write():
			doc = frappe.get_doc(
				{
					"doctype": "NXR Evidence",
					"document_number": number,
					"status": "Uploaded",
					"project": project,
					"evidence_kind": kind,
					"channel": channel,
					**file_data,
					"source_message_date": data.get("source_message_date"),
					"sender": data.get("sender"),
					"external_reference": data.get("external_reference"),
					"notes": data.get("notes"),
					"version": version,
					"supersedes": previous.name if previous else None,
					"uploaded_by": frappe.session.user,
					"uploaded_at": frappe.utils.now_datetime(),
					"idempotency_key": idempotency_key,
					"payload_hash": fingerprint,
					"correlation_id": correlation_id,
				}
			).insert(ignore_permissions=True)
			if previous:
				previous.status = "Superseded"
				previous.save(ignore_permissions=True)
		link_sequence(sequence, doc.name)
		result = {
			"evidence": doc.name,
			"document_number": number,
			"status": doc.status,
			"version": version,
			"content_sha256": file_data["content_sha256"],
		}
		audit("evidence_uploaded", "NXR Evidence", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Evidence", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def review_evidence(
	evidence: str,
	decision: str,
	idempotency_key: str,
	notes: str | None = None,
) -> dict[str, Any]:
	require_action("review_evidence")
	status = str(decision or "").strip().title()
	if status not in {"Validated", "Rejected"}:
		frappe.throw(_("La decisión debe ser Validated o Rejected."))
	payload = {
		"evidence": evidence,
		"decision": status,
		"notes": notes or "",
		"idempotency_key": idempotency_key,
	}
	fingerprint = canonical_payload_hash(payload)
	correlation_id = correlation(payload)
	point = savepoint()
	try:
		idem, cached = start_idempotency(idempotency_key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		doc = _lock_evidence(evidence)
		if doc.status != "Uploaded":
			frappe.throw(_("Solo una evidencia cargada puede revisarse."))
		with service_write():
			doc.status = status
			doc.reviewed_by = frappe.session.user
			doc.reviewed_at = frappe.utils.now_datetime()
			doc.review_notes = notes or ""
			doc.save(ignore_permissions=True)
		result = {"evidence": doc.name, "document_number": doc.document_number, "status": doc.status}
		audit("evidence_reviewed", "NXR Evidence", doc.name, fingerprint, correlation_id, result)
		complete_idempotency(idem, "NXR Evidence", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise


@frappe.whitelist(methods=["POST"])
def list_evidence(project: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
	require_action("preview")
	filters = {"project": project} if project else None
	return frappe.get_all(
		"NXR Evidence",
		filters=filters,
		fields=[
			"name",
			"document_number",
			"status",
			"project",
			"evidence_kind",
			"channel",
			"file_url",
			"file_name",
			"content_sha256",
			"source_message_date",
			"sender",
			"external_reference",
			"version",
			"supersedes",
			"uploaded_by",
			"uploaded_at",
			"reviewed_by",
			"reviewed_at",
		],
		order_by="uploaded_at desc, creation desc",
		limit_page_length=min(max(int(limit or 50), 1), 200),
	)
