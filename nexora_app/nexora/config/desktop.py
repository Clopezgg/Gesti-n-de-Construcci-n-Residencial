from __future__ import annotations

from frappe import _


def get_data() -> list[dict[str, object]]:
	return [
		{
			"module_name": "NEXORA",
			"type": "module",
			"label": _("NEXORA"),
			"icon": "octicon octicon-briefcase",
			"color": "grey",
			"description": _("Gestión Integral de Fondos, Proyectos y Operaciones"),
		}
	]
