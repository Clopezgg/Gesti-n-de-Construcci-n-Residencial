from __future__ import annotations

import frappe

from erpnext.construcontrol.integration import _ensure_page

_PRODUCT_PAGES = (
    {
        "name": "construcontrol-profile",
        "page_name": "construcontrol-profile",
        "title": "ConstruControl · Mi perfil",
        "script": "",
        "roles": [
            "System Manager",
            "ConstruControl Manager",
            "ConstruControl Auditor",
            "ConstruControl Operator",
            "ConstruControl Viewer",
        ],
    },
)


def ensure_product_pages() -> None:
    for definition in _PRODUCT_PAGES:
        _ensure_page(definition)
    frappe.clear_cache()


__all__ = ["ensure_product_pages"]
