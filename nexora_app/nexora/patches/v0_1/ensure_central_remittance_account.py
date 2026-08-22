from __future__ import annotations

from nexora.financial.central_treasury import ensure_central_remittance_account


def execute() -> None:
	ensure_central_remittance_account()
