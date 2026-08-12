"""Resolución de texto humano a referencias reales (Bloque 18, NXR-CNV-0001).

``Project.name`` es una serie autogenerada (``naming_series:``, p. ej.
``PROJ-0001``), no el título humano ("Casa 04") que un usuario escribiría en
una conversación — a diferencia de un campo Link normal en Desk, aquí no hay
un control de Frappe que resuelva la ambigüedad por el usuario, así que este
módulo la resuelve explícitamente contra ``project_name``. Para entidades
(contratistas/proveedores) se reutiliza ``directory.service.search_entities``
tal cual — no se reimplementa la búsqueda de entidades.
"""

from __future__ import annotations

from typing import Any

import frappe

from nexora.directory.service import search_entities


class AmbiguousReferenceError(Exception):
	"""Más de una coincidencia real para el texto dado; requiere aclaración."""

	def __init__(self, candidates: list[dict[str, Any]]) -> None:
		self.candidates = candidates
		super().__init__("Referencia ambigua.")


def resolve_project(text: str) -> str | None:
	"""Devuelve el ``name`` (serie) del proyecto cuyo título coincide con ``text``.

	``None`` si no hay ninguna coincidencia (proyecto inexistente). Lanza
	``AmbiguousReferenceError`` si hay más de una coincidencia real, con la
	lista de candidatos para que el llamador pueda pedir aclaración en vez de
	adivinar cuál quiso decir el usuario.
	"""

	needle = str(text or "").strip()
	if not needle:
		return None
	if frappe.db.exists("Project", needle):
		return needle
	matches = frappe.get_list(
		"Project",
		filters=[["project_name", "like", f"%{needle}%"]],
		fields=["name", "project_name"],
		limit=6,
		ignore_permissions=True,
	)
	if not matches:
		return None
	if len(matches) > 1:
		raise AmbiguousReferenceError(matches)
	return matches[0]["name"]


def resolve_cost_center(text: str) -> str | None:
	"""Devuelve el ``name`` del centro de costo (``Cost Center``, estándar ERPNext)
	cuyo título coincide con ``text``. Mismo criterio que ``resolve_project``:
	``name`` es una ruta de árbol autogenerada, no lo que un usuario escribiría.
	"""

	needle = str(text or "").strip()
	if not needle:
		return None
	if frappe.db.exists("Cost Center", needle):
		return needle
	matches = frappe.get_list(
		"Cost Center",
		filters=[["cost_center_name", "like", f"%{needle}%"], ["is_group", "=", 0]],
		fields=["name", "cost_center_name"],
		limit=6,
		ignore_permissions=True,
	)
	if not matches:
		return None
	if len(matches) > 1:
		raise AmbiguousReferenceError(matches)
	return matches[0]["name"]


def resolve_entity(text: str) -> str | None:
	"""Devuelve el ``name`` (hash) de la entidad cuyo nombre coincide con ``text``.

	Reutiliza ``search_entities`` (ya usado por el directorio real) en vez de
	consultar ``NXR Entity`` directamente, para no duplicar su lógica de
	búsqueda/normalización.
	"""

	needle = str(text or "").strip()
	if not needle:
		return None
	if frappe.db.exists("NXR Entity", needle):
		return needle
	matches = search_entities(query=needle, limit=6) or []
	if not matches:
		return None
	if len(matches) > 1:
		raise AmbiguousReferenceError(matches)
	return matches[0].get("name")
