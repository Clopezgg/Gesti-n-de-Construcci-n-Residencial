from __future__ import annotations

import unittest

from nexora.directory.core import (
	COMPLIANCE_TRANSITIONS,
	ENTITY_TRANSITIONS,
	ROLE_TRANSITIONS,
	assert_no_consolidation_cycle,
	assert_transition,
	duplicate_score,
	fingerprint,
	mask_value,
	normalize_contact,
	normalize_identifier,
	normalize_name,
	periods_overlap,
	unique_nonempty,
	validate_period,
)


class TestDirectoryCore(unittest.TestCase):
	def test_names_are_accent_insensitive_and_whitespace_stable(self) -> None:
		self.assertEqual("JOSE LOPEZ", normalize_name("  José   López "))
		self.assertEqual("ACME CONSTRUCCION SA", normalize_name("ACME Construcción, S.A."))

	def test_identifiers_normalize_rtn_passport_and_email(self) -> None:
		self.assertEqual("08011990123456", normalize_identifier("RTN", "0801-1990-123456"))
		self.assertEqual("AB12345", normalize_identifier("Passport", "ab-12345"))
		self.assertEqual("persona@example.test", normalize_identifier("Email", "Persona@Example.Test"))

	def test_contacts_normalize_email_phone_and_whatsapp(self) -> None:
		self.assertEqual("persona@example.test", normalize_contact("Email", "Persona@Example.Test"))
		self.assertEqual("+50499998888", normalize_contact("WhatsApp", "+504 9999-8888"))
		with self.assertRaisesRegex(ValueError, "correo electrónico"):
			normalize_contact("Email", "correo-invalido")

	def test_fingerprints_are_namespaced_and_deterministic(self) -> None:
		first = fingerprint("identifier", "RTN", "08011990123456")
		self.assertEqual(first, fingerprint("identifier", "RTN", "08011990123456"))
		self.assertNotEqual(first, fingerprint("contact", "RTN", "08011990123456"))
		self.assertEqual(64, len(first))

	def test_masks_never_return_full_sensitive_value(self) -> None:
		self.assertEqual("**********3456", mask_value("08011990123456"))
		self.assertEqual("p******@example.test", mask_value("persona@example.test"))
		self.assertNotIn("08011990123456", mask_value("08011990123456"))

	def test_entity_role_and_compliance_transitions(self) -> None:
		assert_transition("Draft", "Active", ENTITY_TRANSITIONS)
		assert_transition("Active", "Blocked", ENTITY_TRANSITIONS)
		assert_transition("Proposed", "Active", ROLE_TRANSITIONS)
		assert_transition("Pending", "Current", COMPLIANCE_TRANSITIONS)
		with self.assertRaisesRegex(ValueError, "Transición no permitida"):
			assert_transition("Inactive", "Active", ENTITY_TRANSITIONS)
		with self.assertRaisesRegex(ValueError, "Transición no permitida"):
			assert_transition("Expired", "Active", ROLE_TRANSITIONS)

	def test_period_validation_and_overlap_are_inclusive(self) -> None:
		self.assertTrue(periods_overlap("2026-01-01", "2026-01-31", "2026-01-31", "2026-02-10"))
		self.assertFalse(periods_overlap("2026-01-01", "2026-01-30", "2026-01-31", None))
		with self.assertRaisesRegex(ValueError, "fecha final"):
			validate_period("2026-02-01", "2026-01-01")

	def test_duplicate_score_prioritizes_exact_identifiers_and_users(self) -> None:
		score, reasons = duplicate_score(
			name_matches=True,
			identifier_matches=1,
			contact_matches=1,
			linked_user_matches=True,
		)
		self.assertEqual(255, score)
		self.assertIn("identificador exacto", reasons)
		self.assertIn("usuario vinculado exacto", reasons)
		self.assertIn("contacto coincidente", reasons)

	def test_consolidation_cycle_is_rejected(self) -> None:
		assert_no_consolidation_cycle("A", "B", {"B": "C", "C": None})
		with self.assertRaisesRegex(ValueError, "ciclo"):
			assert_no_consolidation_cycle("A", "B", {"B": "C", "C": "A"})
		with self.assertRaisesRegex(ValueError, "diferentes"):
			assert_no_consolidation_cycle("A", "A", {})

	def test_unique_nonempty_ignores_blank_values_but_rejects_duplicates(self) -> None:
		self.assertTrue(unique_nonempty(["a", "b", None, ""]))
		self.assertFalse(unique_nonempty(["a", "a", ""]))


if __name__ == "__main__":
	unittest.main()
