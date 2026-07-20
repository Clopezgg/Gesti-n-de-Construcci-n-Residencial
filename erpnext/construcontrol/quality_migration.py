from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
	return " ".join(str(value or "").strip().casefold().split()).replace(" ", "_")


def normalize_legacy_progress(status: Any, quality: Any) -> tuple[str, str]:
	legacy_status = _text(status)
	legacy_quality = _text(quality)
	progress_status = legacy_status if legacy_status in {"rejected", "cancelled"} else "approved"
	if legacy_quality in {"passed", "approved", "good", "excellent", "completed", "compliant"}:
		quality_status = "passed"
	elif legacy_quality in {"failed", "rejected", "poor", "damaged", "non_compliant"}:
		quality_status = "failed"
	elif legacy_quality == "corrective":
		quality_status = "corrective"
	else:
		quality_status = "pending"
	return progress_status, quality_status


def backfill_quality_metadata() -> dict[str, int]:
	import frappe
	from frappe.utils import now_datetime

	from erpnext.construcontrol.quality import reconcile_progress

	rows = frappe.get_all(
		"CC Progress Update",
		fields=[
			"name",
			"source_id",
			"source_key",
			"status",
			"quality",
			"responsible",
			"owner",
			"creation",
			"progress_status",
			"quality_status",
			"responsible_user",
			"progress_reference",
		],
	)
	updated = 0
	for row in rows:
		if not row.get("source_id") and not row.get("source_key"):
			continue
		progress_status, quality_status = normalize_legacy_progress(row.get("status"), row.get("quality"))
		values: dict[str, Any] = {}
		if not row.get("progress_status") or row.get("progress_status") == "draft":
			values["progress_status"] = progress_status
		if not row.get("quality_status") or row.get("quality_status") == "pending":
			values["quality_status"] = quality_status
		if not row.get("progress_reference"):
			values["progress_reference"] = str(row.get("source_key") or row.get("source_id") or row.name)
		responsible = str(row.get("responsible") or "").strip()
		if not row.get("responsible_user") and responsible and frappe.db.exists("User", responsible):
			values["responsible_user"] = responsible
		if progress_status == "approved":
			values.setdefault("approved_by_user", row.get("owner") or "Administrator")
			values.setdefault("approved_at", row.get("creation") or now_datetime())
		if values:
			frappe.db.set_value("CC Progress Update", row.name, values, update_modified=False)
			updated += 1
	reconcile_progress()
	return {"inspected": len(rows), "updated": updated}
