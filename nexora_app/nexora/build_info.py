from __future__ import annotations

import os
from typing import Any

import frappe

from nexora import __version__


@frappe.whitelist(methods=["GET"])
def get_build_info() -> dict[str, Any]:
	"""Return non-sensitive deployment identity to authenticated verifiers."""
	return {
		"product": "NEXORA",
		"version": __version__,
		"build_sha": str(os.environ.get("NEXORA_BUILD_SHA") or "unknown").strip(),
		"environment": str(os.environ.get("NEXORA_ENVIRONMENT") or "unknown").strip(),
	}
