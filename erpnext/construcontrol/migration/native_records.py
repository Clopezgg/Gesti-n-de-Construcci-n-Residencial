from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import frappe

from erpnext.construcontrol.migration.schema import sha256_json

_ITEM_GROUP_PARENT = "Materiales de Construcción"
_SUPPLIER_GROUP = "Proveedores de Construcción"

_CATEGORY_RULES = (
    (("cement", "cemento"), "Cemento"),
    (("sand", "arena", "gravel", "grava", "agregado", "balastre"), "Arena y agregados"),
    (("block", "bloque", "brick", "ladrillo", "mamposter"), "Mampostería"),
    (("rebar", "varilla", "acero", "hierro"), "Acero y varilla"),
    (("wood", "madera", "tabla"), "Madera"),
    (("pipe", "tuber", "sanitari", "plomer"), "Material hidrosanitario"),
    (("electric", "cable", "breaker"), "Material eléctrico"),
    (("paint", "pintura", "sellador"), "Pintura"),
    (("tool", "herramient"), "Herramientas"),
    (("finish", "acabado", "ceramic", "porcelanato"), "Acabados"),
    (("door", "puerta", "window", "ventana"), "Puertas y ventanas"),
    (("roof", "cubierta", "teja", "lámina", "lamina"), "Cubiertas"),
)

_UOM_ALIASES = {
    "unidad": "Nos",
    "unidades": "Nos",
    "und": "Nos",
    "unid": "Nos",
    "pieza": "Nos",
    "piezas": "Nos",
    "metro": "Meter",
    "metros": "Meter",
    "m": "Meter",
    "kg": "Kg",
    "kilogramo": "Kg",
    "kilogramos": "Kg",
    "litro": "Litre",
    "litros": "Litre",
    "l": "Litre",
}


def _deleted(record: Mapping[str, Any]) -> bool:
    deletion = record.get("deletion")
    return bool(isinstance(deletion, Mapping) and deletion.get("deleted"))


def _leaf_group(doctype: str, fieldname: str, preferred_root: str) -> str | None:
    root = frappe.db.get_value(doctype, preferred_root, "name")
    if root:
        return root
    return frappe.db.get_value(doctype, {"is_group": 1}, "name")


def _ensure_item_group(group_name: str, parent: str, is_group: int) -> str:
    existing = frappe.db.get_value("Item Group", {"item_group_name": group_name}, "name")
    if existing:
        return existing
    return frappe.get_doc(
        {
            "doctype": "Item Group",
            "item_group_name": group_name,
            "parent_item_group": parent,
            "is_group": is_group,
        }
    ).insert(ignore_permissions=True).name


def _construction_group(record: Mapping[str, Any]) -> str | None:
    root = _leaf_group("Item Group", "item_group_name", "All Item Groups")
    if not root:
        return None
    parent = _ensure_item_group(_ITEM_GROUP_PARENT, root, 1)
    haystack = " ".join(
        str(record.get(field) or "")
        for field in ("category", "subcategory", "name", "title", "description")
    ).casefold()
    child = "Otros materiales de construcción"
    for needles, group_name in _CATEGORY_RULES:
        if any(needle in haystack for needle in needles):
            child = group_name
            break
    return _ensure_item_group(child, parent, 0)


def _ensure_supplier_group() -> str | None:
    existing = frappe.db.get_value("Supplier Group", {"supplier_group_name": _SUPPLIER_GROUP}, "name")
    if existing:
        return existing
    root = _leaf_group("Supplier Group", "supplier_group_name", "All Supplier Groups")
    if not root:
        return None
    return frappe.get_doc(
        {
            "doctype": "Supplier Group",
            "supplier_group_name": _SUPPLIER_GROUP,
            "parent_supplier_group": root,
            "is_group": 0,
        }
    ).insert(ignore_permissions=True).name


def _uom(record: Mapping[str, Any]) -> str | None:
    raw = str(record.get("unit") or "").strip()
    normalized = raw.casefold()
    preferred = _UOM_ALIASES.get(normalized) or raw or "Nos"
    existing = frappe.db.get_value("UOM", preferred, "name")
    if existing:
        return existing
    if not raw:
        return frappe.db.get_value("UOM", "Nos", "name")
    whole = int(normalized in {"unidad", "unidades", "und", "unid", "pieza", "piezas", "saco", "sacos", "bolsa", "bolsas"})
    return frappe.get_doc(
        {"doctype": "UOM", "uom_name": raw, "must_be_whole_number": whole}
    ).insert(ignore_permissions=True).name


def ensure_supplier(name: Any, record: Mapping[str, Any]) -> tuple[str | None, bool]:
    if _deleted(record):
        return None, False
    supplier_name = str(name or "").strip()
    if not supplier_name or supplier_name.upper() in {"N/A", "NA", "NINGUNO"}:
        return None, False
    existing = frappe.db.get_value("Supplier", {"supplier_name": supplier_name}, "name")
    if existing:
        return existing, False
    group = _ensure_supplier_group()
    if not group:
        return None, False
    document = frappe.get_doc(
        {
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": group,
            "supplier_type": "Individual" if record.get("identity") else "Company",
            "tax_id": record.get("taxId"),
        }
    ).insert(ignore_permissions=True)
    return document.name, True


def ensure_item(record: Mapping[str, Any]) -> tuple[str | None, bool]:
    if _deleted(record):
        return None, False
    raw = str(record.get("code") or record.get("id") or record.get("name") or sha256_json(record)[:12])
    code = f"CC-{re.sub(r'[^A-Za-z0-9_-]+', '-', raw).strip('-')}"[:140]
    if frappe.db.exists("Item", code):
        return code, False
    group = _construction_group(record)
    uom = _uom(record)
    if not group or not uom:
        return None, False
    document = frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": code,
            "item_name": str(record.get("name") or record.get("title") or code),
            "description": str(record.get("description") or ""),
            "item_group": group,
            "stock_uom": uom,
            "is_stock_item": 1,
            "is_purchase_item": 1,
            "is_sales_item": 0,
        }
    ).insert(ignore_permissions=True)
    return document.name, True
