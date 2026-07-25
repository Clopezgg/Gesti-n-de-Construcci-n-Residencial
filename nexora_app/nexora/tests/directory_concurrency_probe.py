from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import frappe

from nexora.directory.api import create_entity


def _ensure_user(email: str, role: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@", 1)[0],
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


def run() -> dict[str, object]:
	marker = uuid.uuid4().hex[:12]
	actor = _ensure_user(f"nxr-directory-concurrency-actor-{marker}@example.test", "NEXORA Finance Operator")
	linked_user = _ensure_user(
		f"nxr-directory-concurrency-linked-{marker}@example.test", "NEXORA Project Viewer"
	)
	# Fixture users must be visible to both independent MariaDB connections.
	frappe.db.commit()  # nosemgrep
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	barrier = threading.Barrier(2)

	def worker(suffix: str) -> str:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		# Test-only identity switch inside an isolated worker connection.
		frappe.set_user(actor)  # nosemgrep
		try:
			barrier.wait(timeout=20)
			create_entity(
				{
					"entity_type": "Individual",
					"display_name": f"Entidad concurrente {marker} {suffix}",
					"linked_user": linked_user,
					"idempotency_key": f"directory-concurrency-{marker}-{suffix}",
				}
			)
			frappe.db.commit()  # nosemgrep
			return "created"
		except Exception as exc:  # noqa: BLE001
			frappe.db.rollback()
			return (
				"denied_duplicate_user"
				if "ya está vinculado" in str(exc)
				else f"unexpected:{type(exc).__name__}:{exc}"
			)
		finally:
			frappe.destroy()

	with ThreadPoolExecutor(max_workers=2) as pool:
		results = sorted(pool.map(worker, ("a", "b")))
	count = frappe.db.count("NXR Entity", {"linked_user": linked_user, "status": ["!=", "Consolidated"]})
	if results != ["created", "denied_duplicate_user"] or count != 1:
		raise AssertionError({"results": results, "count": count, "linked_user": linked_user})
	return {"ok": True, "results": results, "count": count, "linked_user": linked_user}
