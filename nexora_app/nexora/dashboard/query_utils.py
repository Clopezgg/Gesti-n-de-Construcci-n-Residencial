from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe
from frappe import _

from nexora.dashboard.analytics_core import normalize_period
from nexora.permissions import require_project_access

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def payload(value: str | Mapping[str, Any]) -> dict[str, Any]:
	data = dict(value) if isinstance(value, Mapping) else frappe.parse_json(value)
	if not isinstance(data, dict):
		frappe.throw(_("El payload analítico debe ser un objeto JSON."))
	return data


def text(data: Mapping[str, Any], fieldname: str) -> str | None:
	value = str(data.get(fieldname) or "").strip()
	return value or None


def period(data: Mapping[str, Any]) -> tuple[str, str]:
	try:
		return normalize_period(data.get("from_date"), data.get("to_date"))
	except (TypeError, ValueError) as exc:
		frappe.throw(_(str(exc)))
		raise AssertionError from exc


def pagination(data: Mapping[str, Any], default_size: int = DEFAULT_PAGE_SIZE) -> tuple[int, int, int]:
	page = max(int(data.get("page") or 1), 1)
	page_size = min(max(int(data.get("page_size") or default_size), 1), MAX_PAGE_SIZE)
	return page, page_size, (page - 1) * page_size


def project(data: Mapping[str, Any]) -> str | None:
	value = text(data, "project")
	require_project_access(value, action="view_reports")
	return value
