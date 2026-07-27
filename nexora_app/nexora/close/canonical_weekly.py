from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.close import service as weekly_service

CANONICAL_WEEKLY_ENGINE_VERSION = weekly_service.WEEKLY_ENGINE_VERSION


@frappe.whitelist(methods=["POST"])
def calculate_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return weekly_service.calculate_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def save_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return weekly_service.save_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def correct_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	return weekly_service.correct_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def list_weekly_closes(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	return weekly_service.list_weekly_closes(payload)
