"""Pruebas puras del canal WhatsApp Business (Bloque 21, NXR-INT-0008).

Sin dependencia de Frappe — ejecutables en cualquier entorno.
"""

from __future__ import annotations

import hashlib
import hmac
import unittest

from nexora.conversation.channels.whatsapp_core import (
	extract_inbound_messages,
	extract_status_updates,
	extract_verification_challenge,
	verify_signature,
)


def _sign(secret: str, body: bytes) -> str:
	digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
	return f"sha256={digest}"


class TestVerifySignature(unittest.TestCase):
	def test_valid_signature_over_the_exact_body_is_accepted(self) -> None:
		body = b'{"entry": []}'
		secret = "app-secret-value"
		self.assertTrue(verify_signature(secret, body, _sign(secret, body)))

	def test_signature_computed_with_a_different_secret_is_rejected(self) -> None:
		body = b'{"entry": []}'
		self.assertFalse(verify_signature("real-secret", body, _sign("wrong-secret", body)))

	def test_signature_over_a_different_body_is_rejected(self) -> None:
		secret = "app-secret-value"
		signed_for = b'{"entry": []}'
		actually_sent = b'{"entry": [1]}'
		self.assertFalse(verify_signature(secret, actually_sent, _sign(secret, signed_for)))

	def test_a_single_byte_difference_invalidates_the_signature(self) -> None:
		secret = "app-secret-value"
		original = b'{"a": 1}'
		tampered = b'{"a": 2}'
		self.assertFalse(verify_signature(secret, tampered, _sign(secret, original)))

	def test_missing_header_is_rejected(self) -> None:
		self.assertFalse(verify_signature("secret", b"{}", None))

	def test_header_without_the_sha256_prefix_is_rejected(self) -> None:
		self.assertFalse(verify_signature("secret", b"{}", "md5=deadbeef"))

	def test_empty_signature_value_is_rejected(self) -> None:
		self.assertFalse(verify_signature("secret", b"{}", "sha256="))


class TestExtractVerificationChallenge(unittest.TestCase):
	def test_matching_token_and_subscribe_mode_returns_the_challenge(self) -> None:
		query = {"hub.mode": "subscribe", "hub.verify_token": "correct-token", "hub.challenge": "12345"}
		self.assertEqual(extract_verification_challenge(query, "correct-token"), "12345")

	def test_wrong_token_never_echoes_the_challenge(self) -> None:
		query = {"hub.mode": "subscribe", "hub.verify_token": "guessed-token", "hub.challenge": "12345"}
		self.assertIsNone(extract_verification_challenge(query, "correct-token"))

	def test_mode_other_than_subscribe_is_rejected_even_with_the_right_token(self) -> None:
		query = {"hub.mode": "unsubscribe", "hub.verify_token": "correct-token", "hub.challenge": "12345"}
		self.assertIsNone(extract_verification_challenge(query, "correct-token"))

	def test_missing_expected_token_never_matches_anything(self) -> None:
		query = {"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "12345"}
		self.assertIsNone(extract_verification_challenge(query, ""))


class TestExtractInboundMessages(unittest.TestCase):
	def test_extracts_a_real_text_message(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{
										"id": "wamid.ABC123",
										"from": "50499999999",
										"type": "text",
										"timestamp": "1699999999",
										"text": {"body": "¿Cuánto tengo en Casa 04?"},
									}
								]
							}
						}
					]
				}
			]
		}
		messages = extract_inbound_messages(payload)
		self.assertEqual(len(messages), 1)
		self.assertEqual(messages[0]["message_id"], "wamid.ABC123")
		self.assertEqual(messages[0]["from"], "50499999999")
		self.assertEqual(messages[0]["type"], "text")
		self.assertEqual(messages[0]["text"], "¿Cuánto tengo en Casa 04?")

	def test_extracts_an_image_with_caption_never_inventing_a_text_body(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{
										"id": "wamid.IMG1",
										"from": "50499999999",
										"type": "image",
										"image": {"id": "media-123", "caption": "Factura de Casa 04"},
									}
								]
							}
						}
					]
				}
			]
		}
		messages = extract_inbound_messages(payload)
		self.assertEqual(messages[0]["media_id"], "media-123")
		self.assertEqual(messages[0]["caption"], "Factura de Casa 04")
		self.assertIsNone(messages[0]["text"])

	def test_status_updates_are_not_messages_and_are_ignored(self) -> None:
		payload = {
			"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.X", "status": "delivered"}]}}]}]
		}
		self.assertEqual(extract_inbound_messages(payload), [])

	def test_an_empty_payload_yields_no_messages(self) -> None:
		self.assertEqual(extract_inbound_messages({}), [])

	def test_multiple_entries_and_changes_are_all_collected(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [{"id": "a", "from": "1", "type": "text", "text": {"body": "x"}}]
							}
						}
					]
				},
				{
					"changes": [
						{
							"value": {
								"messages": [{"id": "b", "from": "2", "type": "text", "text": {"body": "y"}}]
							}
						}
					]
				},
			]
		}
		messages = extract_inbound_messages(payload)
		self.assertEqual([m["message_id"] for m in messages], ["a", "b"])

	def test_a_message_missing_a_real_id_or_sender_is_never_fabricated(self) -> None:
		payload = {
			"entry": [
				{"changes": [{"value": {"messages": [{"type": "text", "text": {"body": "sin remitente"}}]}}]}
			]
		}
		self.assertEqual(extract_inbound_messages(payload), [])

	def test_an_unrecognized_message_type_is_kept_but_never_given_invented_text(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{
										"id": "wamid.LOC",
										"from": "50499999999",
										"type": "location",
										"location": {},
									}
								]
							}
						}
					]
				}
			]
		}
		messages = extract_inbound_messages(payload)
		self.assertEqual(len(messages), 1)
		self.assertEqual(messages[0]["type"], "location")
		self.assertIsNone(messages[0]["text"])
		self.assertIsNone(messages[0]["media_id"])


class TestExtractStatusUpdates(unittest.TestCase):
	"""NXR-INT-0008: estados reales de entrega/lectura de un mensaje saliente
	— antes reconocidos y descartados en silencio por `extract_inbound_messages`
	(ver `test_status_updates_are_not_messages_and_are_ignored`), ahora
	persistidos de verdad por `_process_status_update` en `whatsapp.py`."""

	def test_extracts_a_real_delivered_status(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"statuses": [
									{
										"id": "wamid.SENT1",
										"status": "delivered",
										"timestamp": "1699999999",
										"recipient_id": "50499999999",
									}
								]
							}
						}
					]
				}
			]
		}
		updates = extract_status_updates(payload)
		self.assertEqual(len(updates), 1)
		self.assertEqual(updates[0]["message_id"], "wamid.SENT1")
		self.assertEqual(updates[0]["status"], "delivered")
		self.assertIsNone(updates[0]["error_detail"])

	def test_a_failed_status_keeps_the_real_error_title_never_a_generic_message(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"statuses": [
									{
										"id": "wamid.FAIL1",
										"status": "failed",
										"errors": [{"code": 131047, "title": "Re-engagement message"}],
									}
								]
							}
						}
					]
				}
			]
		}
		updates = extract_status_updates(payload)
		self.assertEqual(updates[0]["status"], "failed")
		self.assertEqual(updates[0]["error_detail"], "Re-engagement message")

	def test_a_failed_status_without_any_real_error_entry_never_invents_a_detail(self) -> None:
		payload = {
			"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.FAIL2", "status": "failed"}]}}]}]
		}
		updates = extract_status_updates(payload)
		self.assertIsNone(updates[0]["error_detail"])

	def test_an_unrecognized_status_value_is_never_fabricated_into_a_known_one(self) -> None:
		payload = {
			"entry": [
				{
					"changes": [
						{"value": {"statuses": [{"id": "wamid.X", "status": "deleted_by_meta_future"}]}}
					]
				}
			]
		}
		self.assertEqual(extract_status_updates(payload), [])

	def test_a_status_missing_a_real_message_id_is_never_fabricated(self) -> None:
		payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "read"}]}}]}]}
		self.assertEqual(extract_status_updates(payload), [])

	def test_inbound_messages_are_not_status_updates_and_are_ignored(self) -> None:
		"""Simétrico a `test_status_updates_are_not_messages_and_are_ignored`."""
		payload = {
			"entry": [
				{
					"changes": [
						{
							"value": {
								"messages": [
									{"id": "wamid.M1", "from": "1", "type": "text", "text": {"body": "hola"}}
								]
							}
						}
					]
				}
			]
		}
		self.assertEqual(extract_status_updates(payload), [])

	def test_an_empty_payload_yields_no_status_updates(self) -> None:
		self.assertEqual(extract_status_updates({}), [])


if __name__ == "__main__":
	unittest.main()
