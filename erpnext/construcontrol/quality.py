from __future__ import annotations

import hashlib
import mimetypes
from collections.abc import Mapping
from typing import Any

PROGRESS_STATES = {"draft", "submitted", "approved", "rejected", "cancelled"}
QUALITY_STATES = {"pending", "passed", "failed", "corrective"}
ALERT_LEVELS = {"normal", "attention", "critical"}
CAPTURE_SOURCES = {"camera", "gallery", "file"}
ALLOWED_MIME_PREFIXES = ("image/",)
ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_EVIDENCE_SIZE = 15 * 1024 * 1024


def _text(value: Any) -> str:
	return " ".join(str(value or "").strip().casefold().split())


def validate_progress_contract(
	values: Mapping[str, Any],
	*,
	previous_percent: Any = 0,
	manager_override: bool = False,
	historical: bool = False,
) -> dict[str, Any]:
	project = str(values.get("project") or "").strip()
	phase = str(values.get("phase") or "").strip()
	responsible = str(values.get("responsible_user") or values.get("responsible") or "").strip()
	posting_date = str(values.get("posting_date") or "").strip()
	status = _text(values.get("progress_status") or values.get("status") or "draft").replace(" ", "_")
	quality = _text(values.get("quality_status") or values.get("quality") or "pending").replace(" ", "_")
	alert = _text(values.get("alert_level") or "normal").replace(" ", "_")
	percent = float(values.get("progress_percent") or 0)
	previous = float(previous_percent or 0)
	observations = str(values.get("observations") or values.get("description") or "").strip()
	regression_reason = str(values.get("regression_reason") or "").strip()
	rejection_reason = str(values.get("rejection_reason") or "").strip()

	if not project or not phase or not posting_date or (not responsible and not historical):
		raise ValueError("Seleccione proyecto, fase, fecha y responsable del avance.")
	if not 0 <= percent <= 100:
		raise ValueError("El avance físico debe estar entre 0 y 100 por ciento.")
	if status not in PROGRESS_STATES:
		raise ValueError("Seleccione un estado de avance válido.")
	if quality not in QUALITY_STATES:
		raise ValueError("Seleccione un estado de calidad válido.")
	if alert not in ALERT_LEVELS:
		raise ValueError("Seleccione un nivel de alerta válido.")
	if quality in {"failed", "corrective"} and (not observations or alert == "normal"):
		raise ValueError("Una falla de calidad requiere observaciones y una alerta activa.")
	if status == "rejected" and not rejection_reason:
		raise ValueError("Indique el motivo de rechazo del avance.")
	if percent + 1e-9 < previous and not historical and not (manager_override and regression_reason):
		raise ValueError("Una reducción del avance requiere autorización y motivo de reversión.")
	return {
		"progress_percent": round(percent, 4),
		"progress_status": status,
		"quality_status": quality,
		"alert_level": alert,
		"observations": observations,
	}


def validate_evidence_contract(
	values: Mapping[str, Any],
	*,
	file_is_private: bool,
	file_size: Any,
	mime_type: Any,
	historical: bool = False,
) -> dict[str, Any]:
	project = str(values.get("project") or "").strip()
	progress = str(values.get("progress_update") or "").strip()
	file_url = str(values.get("evidence_file") or "").strip()
	capture_source = _text(values.get("capture_source") or "file").replace(" ", "_")
	size = int(file_size or 0)
	mime = str(mime_type or "").strip().lower()
	if not project or (not historical and (not progress or not file_url)):
		raise ValueError("La evidencia nueva requiere proyecto, avance relacionado y archivo.")
	if not historical and not file_is_private:
		raise ValueError("La evidencia de ConstruControl debe almacenarse como archivo privado.")
	if capture_source not in CAPTURE_SOURCES:
		raise ValueError("Seleccione cámara, galería o archivo como origen de la evidencia.")
	if size < 0 or size > MAX_EVIDENCE_SIZE:
		raise ValueError("La evidencia supera el tamaño máximo permitido de 15 MB.")
	if mime and not (mime.startswith(ALLOWED_MIME_PREFIXES) or mime in ALLOWED_MIME_TYPES):
		raise ValueError("Solo se permiten imágenes o archivos PDF como evidencia.")
	return {
		"capture_source": capture_source,
		"size_bytes": size,
		"mime_type": mime,
	}


def evidence_checksum(file_url: Any, content_hash: Any = "") -> str:
	value = f"{str(file_url or '').strip()}|{str(content_hash or '').strip()}"
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def infer_mime(filename: Any) -> str:
	return str(mimetypes.guess_type(str(filename or ""))[0] or "").lower()


def _frappe():
	import frappe
	from frappe import _
	from frappe.utils import flt, now_datetime

	return frappe, _, flt, now_datetime


def ensure_quality_schema() -> None:
	frappe, _, flt, now_datetime = _frappe()
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	fields = {
		"CC Progress Update": [
			{
				"fieldname": "progress_reference",
				"label": "Referencia única",
				"fieldtype": "Data",
				"insert_after": "posting_date",
			},
			{
				"fieldname": "responsible_user",
				"label": "Responsable",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "progress_reference",
			},
			{
				"fieldname": "progress_status",
				"label": "Estado del avance",
				"fieldtype": "Select",
				"options": "draft\nsubmitted\napproved\nrejected\ncancelled",
				"default": "draft",
				"in_list_view": 1,
				"insert_after": "progress_percent",
			},
			{
				"fieldname": "quality_status",
				"label": "Estado de calidad",
				"fieldtype": "Select",
				"options": "pending\npassed\nfailed\ncorrective",
				"default": "pending",
				"in_list_view": 1,
				"insert_after": "progress_status",
			},
			{
				"fieldname": "observations",
				"label": "Observaciones",
				"fieldtype": "Small Text",
				"insert_after": "quality_status",
			},
			{
				"fieldname": "alert_level",
				"label": "Nivel de alerta",
				"fieldtype": "Select",
				"options": "normal\nattention\ncritical",
				"default": "normal",
				"in_list_view": 1,
				"insert_after": "observations",
			},
			{
				"fieldname": "incident_status",
				"label": "Estado de incidencia",
				"fieldtype": "Select",
				"options": "none\nopen\ncorrective_action\nresolved",
				"default": "none",
				"insert_after": "alert_level",
			},
			{
				"fieldname": "corrective_action",
				"label": "Acción correctiva",
				"fieldtype": "Small Text",
				"insert_after": "incident_status",
			},
			{
				"fieldname": "regression_reason",
				"label": "Motivo de reversión",
				"fieldtype": "Small Text",
				"insert_after": "corrective_action",
			},
			{
				"fieldname": "rejection_reason",
				"label": "Motivo de rechazo",
				"fieldtype": "Small Text",
				"insert_after": "regression_reason",
			},
			{
				"fieldname": "evidence_count",
				"label": "Evidencias",
				"fieldtype": "Int",
				"read_only": 1,
				"insert_after": "rejection_reason",
			},
			{
				"fieldname": "approved_by_user",
				"label": "Aprobado por",
				"fieldtype": "Link",
				"options": "User",
				"read_only": 1,
				"insert_after": "evidence_count",
			},
			{
				"fieldname": "approved_at",
				"label": "Fecha de aprobación",
				"fieldtype": "Datetime",
				"read_only": 1,
				"insert_after": "approved_by_user",
			},
		],
		"CC Evidence": [
			{
				"fieldname": "evidence_file",
				"label": "Evidencia privada",
				"fieldtype": "Attach",
				"insert_after": "description",
			},
			{
				"fieldname": "phase",
				"label": "Fase",
				"fieldtype": "Link",
				"options": "CC Construction Phase",
				"insert_after": "evidence_file",
			},
			{
				"fieldname": "progress_update",
				"label": "Avance relacionado",
				"fieldtype": "Link",
				"options": "CC Progress Update",
				"insert_after": "phase",
			},
			{
				"fieldname": "capture_source",
				"label": "Origen de captura",
				"fieldtype": "Select",
				"options": "camera\ngallery\nfile",
				"default": "file",
				"insert_after": "progress_update",
			},
			{
				"fieldname": "captured_at",
				"label": "Fecha de captura",
				"fieldtype": "Datetime",
				"insert_after": "capture_source",
			},
			{
				"fieldname": "checksum_sha256",
				"label": "SHA-256",
				"fieldtype": "Data",
				"read_only": 1,
				"insert_after": "captured_at",
			},
		],
	}
	for doctype, definitions in fields.items():
		standard = set(frappe.get_all("DocField", filters={"parent": doctype}, pluck="fieldname"))
		fields[doctype] = [field for field in definitions if field["fieldname"] not in standard]
	create_custom_fields(fields, update=True)
	for doctype in fields:
		frappe.clear_cache(doctype=doctype)
	reconcile_progress()


def _phase_project(phase: str) -> str:
	frappe, _, flt, now_datetime = _frappe()
	return str(frappe.db.get_value("CC Construction Phase", phase, "project") or "")


def _manager() -> bool:
	from erpnext.construcontrol.access import current_roles

	return bool(current_roles() & {"System Manager", "ConstruControl Manager"})


def _previous_progress(doc: Any) -> float:
	frappe, _, flt, now_datetime = _frappe()
	filters: dict[str, Any] = {
		"project": doc.get("project"),
		"phase": doc.get("phase"),
		"is_logically_deleted": 0,
		"name": ["!=", doc.name or ""],
	}
	if frappe.get_meta("CC Progress Update").has_field("progress_status"):
		filters["progress_status"] = ["in", ["submitted", "approved"]]
	return flt(
		frappe.db.get_value(
			"CC Progress Update",
			filters,
			"progress_percent",
			order_by="posting_date desc, creation desc",
		)
	)


def validate_progress_update(doc: Any, method: str | None = None) -> None:
	frappe, _, flt, now_datetime = _frappe()
	from erpnext.construcontrol.access import require_construcontrol_access, validate_document_project_access

	validate_document_project_access(doc)
	if _phase_project(str(doc.get("phase") or "")) != doc.get("project"):
		frappe.throw(_("La fase del avance no pertenece al proyecto."))
	historical = bool(doc.get("source_id") or doc.get("source_key"))
	status = str(doc.get("progress_status") or doc.get("status") or "draft").strip().lower()
	if status in {"approved", "rejected", "cancelled"} and not historical:
		require_construcontrol_access(manage=True)
	try:
		result = validate_progress_contract(
			doc.as_dict(),
			previous_percent=_previous_progress(doc),
			manager_override=_manager(),
			historical=historical,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	for fieldname, value in result.items():
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, value)
	if not doc.get("responsible_user") and doc.meta.has_field("responsible_user"):
		responsible = str(doc.get("responsible") or "").strip()
		if responsible and frappe.db.exists("User", responsible):
			doc.responsible_user = responsible
	if not historical and not doc.get("progress_reference"):
		doc.progress_reference = (
			f"{doc.project}|{doc.phase}|{doc.posting_date}|{flt(doc.progress_percent):.4f}"
		)
	if doc.get("progress_reference") and frappe.db.exists(
		"CC Progress Update",
		{
			"project": doc.project,
			"progress_reference": doc.progress_reference,
			"is_logically_deleted": 0,
			"name": ["!=", doc.name or ""],
		},
	):
		frappe.throw(_("Ya existe un avance con la misma referencia dentro del proyecto."))
	if status == "approved":
		doc.approved_by_user = frappe.session.user
		doc.approved_at = now_datetime()


def _refresh_phase(phase: str, exclude: str | None = None) -> None:
	frappe, _, flt, now_datetime = _frappe()
	if not phase or not frappe.db.exists("CC Construction Phase", phase):
		return
	filters: dict[str, Any] = {"phase": phase, "is_logically_deleted": 0}
	if frappe.get_meta("CC Progress Update").has_field("progress_status"):
		filters["progress_status"] = ["in", ["submitted", "approved"]]
	rows = frappe.get_all(
		"CC Progress Update",
		filters=filters,
		fields=["name", "progress_percent"],
		order_by="posting_date desc, creation desc",
	)
	progress = next((flt(row.progress_percent) for row in rows if row.name != exclude), 0.0)
	frappe.db.set_value(
		"CC Construction Phase",
		phase,
		{"progress_percent": progress},
		update_modified=False,
	)


def update_progress_relations(doc: Any, method: str | None = None) -> None:
	previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	for phase in {doc.get("phase"), previous.get("phase") if previous else None} - {None, ""}:
		_refresh_phase(phase)


def remove_progress_relations(doc: Any, method: str | None = None) -> None:
	from erpnext.construcontrol.access import require_construcontrol_access, validation_bypass_active

	if not validation_bypass_active():
		require_construcontrol_access(manage=True)
	_refresh_phase(doc.get("phase"), doc.name)


def validate_evidence(doc: Any, method: str | None = None) -> None:
	frappe, _, flt, now_datetime = _frappe()
	from erpnext.construcontrol.access import validate_document_project_access

	validate_document_project_access(doc)
	historical = bool(doc.get("source_id") or doc.get("source_key")) and not doc.get("evidence_file")
	progress = None
	if doc.get("progress_update"):
		progress = frappe.db.get_value(
			"CC Progress Update", doc.progress_update, ["project", "phase"], as_dict=True
		)
		if not progress or progress.project != doc.project:
			frappe.throw(_("El avance relacionado pertenece a otro proyecto."))
		if doc.get("phase") and progress.phase != doc.phase:
			frappe.throw(_("La evidencia pertenece a una fase distinta del avance."))
		if not doc.get("phase"):
			doc.phase = progress.phase
	file_row = None
	if doc.get("evidence_file"):
		file_row = frappe.db.get_value(
			"File",
			{"file_url": doc.evidence_file},
			["name", "file_name", "file_size", "is_private", "content_hash"],
			as_dict=True,
		)
		if not file_row:
			frappe.throw(_("El archivo de evidencia no existe."))
	mime = doc.get("mime_type") or infer_mime(file_row.file_name if file_row else "")
	try:
		result = validate_evidence_contract(
			doc.as_dict(),
			file_is_private=bool(file_row and file_row.is_private),
			file_size=file_row.file_size if file_row else doc.get("size_bytes"),
			mime_type=mime,
			historical=historical,
		)
	except ValueError as exc:
		frappe.throw(_(str(exc)))
	for fieldname, value in result.items():
		if doc.meta.has_field(fieldname):
			doc.set(fieldname, value)
	if file_row:
		doc.original_name = file_row.file_name
		doc.source_reference = doc.evidence_file
		doc.file_imported = 1
		doc.checksum_sha256 = evidence_checksum(doc.evidence_file, file_row.content_hash)
		doc.captured_at = doc.get("captured_at") or now_datetime()
		doc.related_doctype = "CC Progress Update"
		doc.related_name = doc.progress_update


def _refresh_evidence_count(progress: str) -> None:
	frappe, _, flt, now_datetime = _frappe()
	if not progress or not frappe.db.exists("CC Progress Update", progress):
		return
	count = frappe.db.count(
		"CC Evidence", {"progress_update": progress, "is_logically_deleted": 0, "file_imported": 1}
	)
	frappe.db.set_value("CC Progress Update", progress, "evidence_count", count, update_modified=False)


def update_evidence_relations(doc: Any, method: str | None = None) -> None:
	frappe, _, flt, now_datetime = _frappe()
	previous = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	for progress in {
		doc.get("progress_update"),
		previous.get("progress_update") if previous else None,
	} - {None, ""}:
		_refresh_evidence_count(progress)
	if doc.get("evidence_file") and doc.name:
		frappe.db.set_value(
			"File",
			{"file_url": doc.evidence_file},
			{"attached_to_doctype": "CC Evidence", "attached_to_name": doc.name, "is_private": 1},
			update_modified=False,
		)


def protect_evidence_delete(doc: Any, method: str | None = None) -> None:
	from erpnext.construcontrol.access import require_construcontrol_access, validation_bypass_active

	if not validation_bypass_active():
		require_construcontrol_access(manage=True)
	_refresh_evidence_count(doc.get("progress_update"))


def reconcile_progress() -> dict[str, int]:
	frappe, _, flt, now_datetime = _frappe()
	phases = frappe.get_all("CC Construction Phase", filters={"is_logically_deleted": 0}, pluck="name")
	updates = frappe.get_all("CC Progress Update", filters={"is_logically_deleted": 0}, pluck="name")
	for phase in phases:
		_refresh_phase(phase)
	for update in updates:
		_refresh_evidence_count(update)
	return {"phases": len(phases), "progress_updates": len(updates)}
