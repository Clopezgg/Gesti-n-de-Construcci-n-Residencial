from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.close import service as weekly_service
from nexora.dashboard.snapshot_query import get_executive_snapshot

CANONICAL_WEEKLY_ENGINE_VERSION = "nexora-analytics-v3"


def bind_canonical_snapshot() -> None:
	"""Bind weekly-close calculations to the same filtered snapshot used by BI01."""
	weekly_service.get_executive_snapshot = get_executive_snapshot
	weekly_service.WEEKLY_ENGINE_VERSION = CANONICAL_WEEKLY_ENGINE_VERSION


@frappe.whitelist(methods=["POST"])
def calculate_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	bind_canonical_snapshot()
	return weekly_service.calculate_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def save_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	bind_canonical_snapshot()
	return weekly_service.save_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def correct_weekly_close(payload: str | Mapping[str, Any]) -> dict[str, Any]:
	bind_canonical_snapshot()
	return weekly_service.correct_weekly_close(payload)


@frappe.whitelist(methods=["POST"])
def list_weekly_closes(payload: str | Mapping[str, Any] | None = None) -> dict[str, Any]:
	return weekly_service.list_weekly_closes(payload)
