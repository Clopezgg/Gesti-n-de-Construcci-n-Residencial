from __future__ import annotations

from erpnext.construcontrol.page_registry import ensure_canonical_pages


def ensure_product_pages() -> None:
	"""Compatibility entry point; canonical page ownership lives in page_registry."""
	ensure_canonical_pages()


__all__ = ["ensure_product_pages"]
