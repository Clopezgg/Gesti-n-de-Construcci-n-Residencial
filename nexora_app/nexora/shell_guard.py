"""Envoltorio delgado de `nexora.shell_guard_core` para el hook `before_request` (Bloque 154).

Toda la decisión —qué ruta bloquear, para quién, a dónde redirigir— vive en
`nexora.shell_guard_core.resolve_redirect()`, una función pura sin ningún `import
frappe`. Este módulo es el único punto que sí toca Frappe: lee la sesión y el
`request` reales y traduce la decisión en una redirección real.
"""

from __future__ import annotations

import frappe

from nexora.shell_guard_core import resolve_redirect


def enforce() -> None:
	"""Hook de `before_request`. Ver `nexora.shell_guard_core` para el porqué de la guarda."""
	if frappe.session.user == "Guest":
		return
	request = getattr(frappe.local, "request", None)
	if request is None:
		return
	target = resolve_redirect(request.path, frappe.get_roles(frappe.session.user))
	if not target:
		return
	frappe.local.flags.redirect_location = target
	raise frappe.Redirect
