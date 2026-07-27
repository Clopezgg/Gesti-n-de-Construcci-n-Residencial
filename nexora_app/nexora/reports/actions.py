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
	parse_payload,
	rollback,
	savepoint,
	start_idempotency,
)
from nexora.permissions import require_action, require_project_access


@frappe.whitelist(methods=["POST"])
def archive_saved_report(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	"""Archive a saved report without deleting its audit trail."""
	data = parse_payload(payload)
	require_action("view_reports")
	report_name = str(data.get("saved_report") or "").strip()
	key = str(data.get("idempotency_key") or "").strip()
	if not report_name:
		frappe.throw(_("Seleccione el reporte guardado que desea archivar."))
	if not key:
		frappe.throw(_("La solicitud requiere una clave de idempotencia."))

	fingerprint = canonical_payload_hash(
		{
			"saved_report": report_name,
			"target_status": "Archived",
			"actor": frappe.session.user,
		}
	)
	correlation_id = correlation(data)
	point = savepoint()
	try:
		idem, cached = start_idempotency(key, fingerprint, correlation_id)
		if cached is not None:
			return cached
		locked = frappe.db.sql("SELECT name FROM `tabNXR Saved Report` WHERE name=%s FOR UPDATE", report_name)
		if not locked:
			frappe.throw(_("El reporte guardado indicado no existe."))
		doc = frappe.get_doc("NXR Saved Report", report_name)
		if doc.owner_user != frappe.session.user:
			frappe.throw(_("Solo el propietario puede archivar este reporte guardado."), frappe.PermissionError)
		require_project_access(doc.project or None, action="view_reports")
		result = {
			"saved_report": doc.name,
			"document_number": doc.document_number,
			"status": "Archived",
		}
		if doc.status != "Archived":
			with service_write():
				doc.status = "Archived"
				doc.save(ignore_permissions=True)
			audit(
				"saved_report_archived",
				"NXR Saved Report",
				doc.name,
				fingerprint,
				correlation_id,
				result,
			)
		complete_idempotency(idem, "NXR Saved Report", doc.name, result)
		return result
	except Exception:
		rollback(point)
		raise
