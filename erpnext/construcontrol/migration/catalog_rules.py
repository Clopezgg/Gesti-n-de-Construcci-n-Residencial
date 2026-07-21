from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

# These rules are intentionally conservative: explicit retail/demo products are
# rejected, while real construction records are accepted by domain vocabulary
# or by the operational fields used by the historical ConstruControl inventory.
_CONSTRUCTION_TERMS = (
	"acero",
	"aditivo",
	"agregado",
	"aislante",
	"alambre",
	"andamio",
	"arena",
	"azulejo",
	"balastre",
	"bloque",
	"bombillo",
	"boquilla",
	"breaker",
	"cable",
	"cal",
	"canaleta",
	"cemento",
	"ceramica",
	"clavo",
	"codo",
	"concreto",
	"conduit",
	"cpvc",
	"cubierta",
	"disco de corte",
	"ducha",
	"electric",
	"formaleta",
	"geotextil",
	"grava",
	"griferia",
	"hierro",
	"herramienta",
	"impermeabilizante",
	"interruptor",
	"lamina",
	"lampara",
	"lavamanos",
	"ladrillo",
	"llave de paso",
	"madera",
	"malla",
	"mamposteria",
	"material de construccion",
	"mortero",
	"pala",
	"pegamento",
	"perno",
	"piedra",
	"pintura",
	"piso",
	"plomeria",
	"porcelanato",
	"puerta",
	"pvc",
	"sanitario",
	"sellador",
	"silicona",
	"tabla",
	"teja",
	"tornillo",
	"tomacorriente",
	"tuberia",
	"tubo",
	"tuerca",
	"valvula",
	"varilla",
	"ventana",
	"vidrio",
	"yeso",
	"brick",
	"cement",
	"construction material",
	"concrete",
	"door",
	"electrical",
	"gravel",
	"lumber",
	"masonry",
	"paint",
	"pipe",
	"plumbing",
	"rebar",
	"roof",
	"sand",
	"steel",
	"tile",
	"tool",
	"window",
	"wood",
)

_NON_CONSTRUCTION_TERMS = (
	"coffee mug",
	"demo item",
	"demo product",
	"food",
	"grant plastics",
	"headphone",
	"juguete",
	"laptop",
	"mobile phone",
	"producto demo",
	"running shoe",
	"sample item",
	"smartphone",
	"sneaker",
	"television",
	"toy",
	"taza de cafe",
	"zapatilla",
	"zapato",
	"zuckerman security",
)

_MATERIAL_FIELD_HINTS = {
	"category",
	"subcategory",
	"unit",
	"unitPrice",
	"unit_price",
	"quantity",
	"currentStock",
	"current_stock",
	"minimumStock",
	"minimum_stock",
	"phaseId",
	"phase_id",
	"supplier",
	"supplierId",
	"supplier_id",
}


def _normalized(value: Any) -> str:
	decomposed = unicodedata.normalize("NFKD", str(value or ""))
	without_marks = "".join(character for character in decomposed if not unicodedata.combining(character))
	return re.sub(r"[^a-z0-9]+", " ", without_marks.casefold()).strip()


def _record_text(record: Mapping[str, Any]) -> str:
	return " ".join(
		_normalized(record.get(field))
		for field in ("code", "id", "name", "title", "description", "category", "subcategory", "type")
		if record.get(field)
	)


def is_construction_record(record: Mapping[str, Any]) -> bool:
	"""Return True only for records that belong to the construction catalog."""
	haystack = _record_text(record)
	if not haystack:
		return False
	if any(term in haystack for term in _NON_CONSTRUCTION_TERMS):
		return False
	if any(term in haystack for term in _CONSTRUCTION_TERMS):
		return True

	# Historical material rows sometimes use short local names. Accept those
	# only when they carry at least two inventory-specific fields, preventing a
	# generic ERPNext retail product from entering the ConstruControl catalog.
	hints = sum(1 for field in _MATERIAL_FIELD_HINTS if record.get(field) not in (None, ""))
	return hints >= 2


__all__ = ["is_construction_record"]
