"""Pruebas puras del núcleo conversacional (Bloque 18, NXR-CNV-0001).

Sin dependencia de Frappe — ejecutables en cualquier entorno (mismo principio
que ``test_context360_core.py``/``test_purchase_request_core.py``).
"""

from __future__ import annotations

import unittest

from nexora.conversation.core import (
	ConversationValidationError,
	IntentKind,
	IntentSpec,
	Slot,
	assert_pending_intent_transition,
	build_intent_prompt,
	format_money_hnl,
	merge_payload,
	missing_slots,
	next_question,
	parse_model_intent,
)


class TestSlotResolution(unittest.TestCase):
	def setUp(self) -> None:
		self.spec = IntentSpec(
			key="register_expense",
			kind=IntentKind.WRITE,
			description="Registrar un gasto",
			slots=(
				Slot("project", "¿En qué proyecto?"),
				Slot("beneficiary", "¿A quién se le paga?"),
				Slot("amount_hnl", "¿Por cuánto?"),
				Slot("notes", "¿Algo más?", required=False),
			),
			execute_method="nexora.financial.operational_commands.execute_operational_movement",
		)

	def test_all_slots_missing_on_empty_payload(self) -> None:
		self.assertEqual(missing_slots(self.spec, {}), ["project", "beneficiary", "amount_hnl"])

	def test_optional_slot_never_counted_as_missing(self) -> None:
		payload = {"project": "PROJ-0001", "beneficiary": "Electricidad López", "amount_hnl": "2500"}
		self.assertEqual(missing_slots(self.spec, payload), [])

	def test_blank_string_counts_as_missing(self) -> None:
		payload = {"project": "  ", "beneficiary": "X", "amount_hnl": "1"}
		self.assertEqual(missing_slots(self.spec, payload), ["project"])

	def test_next_question_asks_for_first_missing_slot_in_declared_order(self) -> None:
		payload = {"beneficiary": "Electricidad López"}
		self.assertEqual(next_question(self.spec, payload), "¿En qué proyecto?")

	def test_next_question_is_none_when_nothing_missing(self) -> None:
		payload = {"project": "PROJ-0001", "beneficiary": "X", "amount_hnl": "1"}
		self.assertIsNone(next_question(self.spec, payload))


class TestMergePayload(unittest.TestCase):
	def test_new_field_is_added(self) -> None:
		self.assertEqual(merge_payload({"a": 1}, {"b": 2}), {"a": 1, "b": 2})

	def test_existing_field_is_overwritten_by_a_real_correction(self) -> None:
		self.assertEqual(merge_payload({"amount_hnl": "1000"}, {"amount_hnl": "2500"}), {"amount_hnl": "2500"})

	def test_empty_or_none_update_never_erases_a_previously_captured_value(self) -> None:
		existing = {"project": "PROJ-0001", "beneficiary": "X"}
		self.assertEqual(merge_payload(existing, {"project": "", "beneficiary": None}), existing)


class TestIntentSpecValidation(unittest.TestCase):
	def test_read_intent_requires_read_method(self) -> None:
		with self.assertRaises(ValueError):
			IntentSpec(key="q", kind=IntentKind.READ, description="x", slots=())

	def test_write_intent_requires_execute_method(self) -> None:
		with self.assertRaises(ValueError):
			IntentSpec(key="w", kind=IntentKind.WRITE, description="x", slots=())

	def test_write_intent_without_preview_method_is_legal(self) -> None:
		spec = IntentSpec(key="w", kind=IntentKind.WRITE, description="x", slots=(), execute_method="a.b.c")
		self.assertIsNone(spec.preview_method)

	def test_navigate_intent_requires_route(self) -> None:
		with self.assertRaises(ValueError):
			IntentSpec(key="n", kind=IntentKind.NAVIGATE, description="x", slots=())


class TestPendingIntentStateMachine(unittest.TestCase):
	def test_legal_forward_path_is_allowed(self) -> None:
		assert_pending_intent_transition("Collecting", "AwaitingConfirmation")
		assert_pending_intent_transition("AwaitingConfirmation", "Confirmed")
		assert_pending_intent_transition("Confirmed", "Executed")

	def test_correction_back_to_collecting_from_awaiting_confirmation_is_allowed(self) -> None:
		assert_pending_intent_transition("AwaitingConfirmation", "Collecting")

	def test_cancellation_is_allowed_from_every_non_terminal_state(self) -> None:
		assert_pending_intent_transition("Collecting", "Cancelled")
		assert_pending_intent_transition("AwaitingConfirmation", "Cancelled")

	def test_same_state_is_a_no_op_not_an_error(self) -> None:
		assert_pending_intent_transition("Collecting", "Collecting")

	def test_terminal_states_never_transition_again(self) -> None:
		for terminal in ("Executed", "Failed", "Cancelled"):
			with self.assertRaises(ConversationValidationError):
				assert_pending_intent_transition(terminal, "Collecting")

	def test_cannot_skip_confirmation_straight_to_executed(self) -> None:
		with self.assertRaises(ConversationValidationError):
			assert_pending_intent_transition("Collecting", "Executed")

	def test_cannot_reopen_confirmed_back_to_collecting(self) -> None:
		with self.assertRaises(ConversationValidationError):
			assert_pending_intent_transition("Confirmed", "Collecting")


class TestParseModelIntent(unittest.TestCase):
	KNOWN = ("query_fund_balance", "register_expense")

	def test_valid_response_with_known_intent_is_accepted(self) -> None:
		raw = '{"intent": "register_expense", "confidence": 0.9, "fields": {"amount_hnl": "2500"}, "clarification_question": null}'
		result = parse_model_intent(raw, self.KNOWN)
		self.assertEqual(result["intent"], "register_expense")
		self.assertEqual(result["fields"], {"amount_hnl": "2500"})

	def test_null_intent_with_clarification_is_accepted(self) -> None:
		raw = '{"intent": null, "confidence": 0.1, "fields": {}, "clarification_question": "¿A qué te refieres?"}'
		result = parse_model_intent(raw, self.KNOWN)
		self.assertIsNone(result["intent"])
		self.assertEqual(result["clarification_question"], "¿A qué te refieres?")

	def test_invalid_json_is_rejected(self) -> None:
		with self.assertRaises(ConversationValidationError):
			parse_model_intent("esto no es json", self.KNOWN)

	def test_unknown_intent_key_is_rejected_never_executed_blindly(self) -> None:
		raw = '{"intent": "delete_everything", "confidence": 0.9, "fields": {}, "clarification_question": null}'
		with self.assertRaises(ConversationValidationError):
			parse_model_intent(raw, self.KNOWN)

	def test_confidence_out_of_range_is_rejected(self) -> None:
		raw = '{"intent": null, "confidence": 1.5, "fields": {}, "clarification_question": null}'
		with self.assertRaises(ConversationValidationError):
			parse_model_intent(raw, self.KNOWN)

	def test_confidence_as_boolean_is_rejected_despite_being_an_int_subtype(self) -> None:
		raw = '{"intent": null, "confidence": true, "fields": {}, "clarification_question": null}'
		with self.assertRaises(ConversationValidationError):
			parse_model_intent(raw, self.KNOWN)

	def test_non_object_json_is_rejected(self) -> None:
		with self.assertRaises(ConversationValidationError):
			parse_model_intent("[1, 2, 3]", self.KNOWN)

	def test_fields_with_wrong_type_is_rejected(self) -> None:
		raw = '{"intent": null, "confidence": 0.5, "fields": "not-a-dict", "clarification_question": null}'
		with self.assertRaises(ConversationValidationError):
			parse_model_intent(raw, self.KNOWN)

	def test_unexpected_top_level_key_is_rejected(self) -> None:
		raw = '{"intent": null, "confidence": 0.5, "fields": {}, "clarification_question": null, "extra": 1}'
		with self.assertRaises(ConversationValidationError):
			parse_model_intent(raw, self.KNOWN)


class TestBuildIntentPrompt(unittest.TestCase):
	def test_prompt_lists_every_intent_key_and_its_slots(self) -> None:
		specs = {
			"query_fund_balance": IntentSpec(
				key="query_fund_balance",
				kind=IntentKind.READ,
				description="Consultar saldo",
				slots=(Slot("project", "¿Qué proyecto?"),),
				read_method="a.b.c",
			)
		}
		prompt = build_intent_prompt(specs)
		self.assertIn("query_fund_balance", prompt)
		self.assertIn("¿Qué proyecto?", prompt)
		self.assertIn("JSON", prompt)


class TestFormatMoneyHnl(unittest.TestCase):
	def test_formats_with_thousands_separator_and_two_decimals(self) -> None:
		self.assertEqual(format_money_hnl(2500), "L 2,500.00")

	def test_handles_string_input(self) -> None:
		self.assertEqual(format_money_hnl("1234.5"), "L 1,234.50")

	def test_none_or_invalid_defaults_to_zero_never_raises(self) -> None:
		self.assertEqual(format_money_hnl(None), "L 0.00")
		self.assertEqual(format_money_hnl("no es un número"), "L 0.00")


if __name__ == "__main__":
	unittest.main()
