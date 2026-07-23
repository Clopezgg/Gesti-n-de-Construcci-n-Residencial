from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _


@contextmanager
def service_write():
	previous = getattr(frappe.flags, "in_nexora_service", False)
	frappe.flags.in_nexora_service = True
	try:
		yield
	finally:
		frappe.flags.in_nexora_service = previous


def require_service_write() -> None:
	if not getattr(frappe.flags, "in_nexora_service", False):
		frappe.throw(_("Este documento solo puede escribirse mediante un servicio transaccional NEXORA."))
