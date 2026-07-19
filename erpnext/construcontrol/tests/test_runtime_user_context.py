from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def runtime_user(user: str) -> Iterator[None]:
	"""Switch Frappe user only inside an isolated runtime-test scope."""
	import frappe

	previous = str(frappe.session.user or "Administrator")
	frappe.set_user(str(user or "Administrator"))
	try:
		yield
	finally:
		frappe.set_user(previous or "Administrator")
