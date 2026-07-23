from __future__ import annotations

import unittest

from nexora.financial.evidence_core import (
	assert_evidence_transition,
	evaluate_evidence_policy,
	is_sha256,
	sha256_content,
)


class TestEvidenceCore(unittest.TestCase):
	def test_deposit_and_transfer_always_require_evidence(self) -> None:
		for method in ("Deposit", "Transfer"):
			policy = evaluate_evidence_policy(method, 1, "CONSTRUCTION_MATERIALS")
			self.assertTrue(policy.required)
			self.assertFalse(policy.requires_external_authorization)

	def test_cash_threshold_is_exact(self) -> None:
		self.assertFalse(evaluate_evidence_policy("Cash", "2000.00", "TAX").required)
		self.assertTrue(evaluate_evidence_policy("Cash", "2000.01", "TAX").required)

	def test_special_category_requires_external_authorization(self) -> None:
		policy = evaluate_evidence_policy("Cash", 10, "DONATION")
		self.assertTrue(policy.required)
		self.assertTrue(policy.requires_external_authorization)

	def test_profile_requirement_overrides_optional_cash(self) -> None:
		policy = evaluate_evidence_policy("Cash", 10, "RETURN", profile_requires_evidence=True)
		self.assertTrue(policy.required)

	def test_evidence_state_machine_rejects_regression(self) -> None:
		assert_evidence_transition("Uploaded", "Validated")
		assert_evidence_transition("Validated", "Superseded")
		with self.assertRaisesRegex(ValueError, "no permitida"):
			assert_evidence_transition("Validated", "Uploaded")

	def test_sha256_is_deterministic(self) -> None:
		digest = sha256_content("NEXORA")
		self.assertEqual(digest, sha256_content(b"NEXORA"))
		self.assertTrue(is_sha256(digest))
		self.assertFalse(is_sha256("invalid"))

	def test_negative_amount_is_rejected(self) -> None:
		with self.assertRaisesRegex(ValueError, "negativo"):
			evaluate_evidence_policy("Cash", -1, "TAX")


if __name__ == "__main__":
	unittest.main()
