from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import frappe

from nexora.dashboard.contract_page import contract_page
from nexora.dashboard.inventory_query import critical_inventory
from nexora.dashboard.query_utils import payload
from nexora.dashboard.source_query import (
	income_by_channel,
	source_movement_page,
	source_statement,
	source_totals,
)
from nexora.permissions import require_action

# Stable internal names retained for existing callers while implementation lives in focused query modules.
_contract_page = contract_page
_critical_inventory = critical_inventory
_income_by_channel = income_by_channel
_source_movement_page = source_movement_page
_source_statement = source_statement
_source_totals = source_totals


@frappe.whitelist(methods=["POST"])
def get_source_statement_page(value: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_financial_details")
	return source_statement(payload(value))


@frappe.whitelist(methods=["POST"])
def get_source_movement_page(value: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_financial_details")
	return source_movement_page(payload(value))


@frappe.whitelist(methods=["POST"])
def get_expense_page(value: str | Mapping[str, Any]) -> dict[str, Any]:
	from nexora.dashboard.expense_query import get_expense_page as canonical_expense_page

	return canonical_expense_page(value)


@frappe.whitelist(methods=["POST"])
def get_contract_page(value: str | Mapping[str, Any]) -> dict[str, Any]:
	require_action("view_reports")
	return contract_page(payload(value))


@frappe.whitelist(methods=["POST"])
def get_executive_snapshot(value: str | Mapping[str, Any]) -> dict[str, Any]:
	from nexora.dashboard.snapshot_query import get_executive_snapshot as canonical_snapshot

	return canonical_snapshot(value)
