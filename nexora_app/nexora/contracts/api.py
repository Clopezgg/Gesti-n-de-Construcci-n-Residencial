from __future__ import annotations

from nexora.contracts import service as _service


def bootstrap() -> None:
	"""Load the canonical contracts API contract before request dispatch."""


create_contractor_profile = _service.create_contractor_profile
transition_contractor_profile = _service.transition_contractor_profile
create_contract = _service.create_contract
transition_contract = _service.transition_contract
create_contract_amendment = _service.create_contract_amendment
transition_contract_amendment = _service.transition_contract_amendment
create_contract_estimate = _service.create_contract_estimate
transition_contract_estimate = _service.transition_contract_estimate
disburse_contract_advance = _service.disburse_contract_advance
execute_contract_estimate_payment = _service.execute_contract_estimate_payment
return_contract_retention = _service.return_contract_retention
correct_contract_transaction = _service.correct_contract_transaction
get_contract = _service.get_contract
list_contracts = _service.list_contracts
