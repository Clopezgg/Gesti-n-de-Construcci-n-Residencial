from __future__ import annotations

import frappe

from erpnext.construcontrol.integration import _ensure_page

_PAGE_ROLES = [
    "System Manager",
    "ConstruControl Manager",
    "ConstruControl Auditor",
    "ConstruControl Operator",
    "ConstruControl Viewer",
]

_PRODUCT_PAGES = (
    {
        "name": "construcontrol-profile",
        "page_name": "construcontrol-profile",
        "title": "ConstruControl · Mi perfil",
        "script": "",
        "roles": _PAGE_ROLES,
    },
    {
        "name": "construcontrol-project-center",
        "page_name": "construcontrol-project-center",
        "title": "ConstruControl · Centro de proyecto",
        "script": "",
        "roles": _PAGE_ROLES,
    },
    {
        "name": "construcontrol-integrations",
        "page_name": "construcontrol-integrations",
        "title": "ConstruControl · Integraciones",
        "script": "",
        "roles": ["System Manager"],
    },
)


def ensure_product_pages() -> None:
    for definition in _PRODUCT_PAGES:
        _ensure_page(definition)
    frappe.clear_cache()


__all__ = ["ensure_product_pages"]
