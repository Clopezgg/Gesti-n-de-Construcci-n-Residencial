from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.close import service as weekly_service
from nexora.dashboard.analytics_core import stable_payload_hash as canonical_payload_hash
from nexora.dashboard.snapshot_query import get_executive_snapshot

CANONICAL_WEEKLY_ENGINE_VERSION = "nexora-analytics-v3"


def _stable_close_hash(payload: Mapping[str, Any]) -> str:
	"""Hash financial content while excluding the volatile generation timestamp."""
	stable_payload = dict(payload)
	stable_payload.pop("generated_at", None)
	return canonical_payload_hash(stable_payload)


def bind_canonical_snapshot() -> None:
	"""Bind weekly-close calculations to the same filtered snapshot used by BI01."""
	weekly_service.get_executive_snapshot = get_executive_snapshot
	weekly_service.WEEKLY_ENGINE_VERSION = CANONICAL_WEEKLY_ENGINE_VERSION
	weekly_service.stable_payload_hash = _stable_close_hash


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
