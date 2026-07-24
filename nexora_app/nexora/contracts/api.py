from __future__ import annotations

import frappe

from nexora.contracts import service as _service


_execute_contract_estimate_payment = _service.execute_contract_estimate_payment


def bootstrap() -> None:
	"""Load the canonical contracts API contract before request dispatch."""

	_service.execute_contract_estimate_payment = execute_contract_estimate_payment


@frappe.whitelist(methods=["POST"])
def execute_contract_estimate_payment(payload):
	"""Retry one optimistic-lock conflict in a fresh transaction."""
	for attempt in range(2):
		try:
			return _execute_contract_estimate_payment(payload)
		except frappe.TimestampMismatchError:
			frappe.db.rollback()
			if attempt:
				raise
	raise AssertionError("unreachable")


create_contractor_profile = _service.create_contractor_profile
transition_contractor_profile = _service.transition_contractor_profile
create_contract = _service.create_contract
transition_contract = _service.transition_contract
create_contract_amendment = _service.create_contract_amendment
transition_contract_amendment = _service.transition_contract_amendment
create_contract_estimate = _service.create_contract_estimate
transition_contract_estimate = _service.transition_contract_estimate
disburse_contract_advance = _service.disburse_contract_advance
return_contract_retention = _service.return_contract_retention
correct_contract_transaction = _service.correct_contract_transaction
get_contract = _service.get_contract
list_contracts = _service.list_contracts
