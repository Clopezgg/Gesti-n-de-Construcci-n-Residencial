from __future__ import annotations

from typing import ClassVar
from unittest import TestCase

from nexora.context360.core import (
	clamp_limit,
	normalize_event,
	resolve_actor,
	resolve_amount,
	resolve_categories,
	sort_and_truncate,
)


class TestResolveActor(TestCase):
	def test_picks_the_first_non_empty_field_in_priority_order(self) -> None:
		row = {"executed_by": None, "approved_by": "manager@example.test", "requester": "req@example.test"}
		self.assertEqual(
			"manager@example.test", resolve_actor(row, ("executed_by", "approved_by", "requester"))
		)

	def test_falls_back_to_owner_when_no_priority_field_is_set(self) -> None:
		row = {"executed_by": None, "approved_by": "", "owner": "creator@example.test"}
		self.assertEqual("creator@example.test", resolve_actor(row, ("executed_by", "approved_by")))

	def test_returns_none_when_nothing_is_available(self) -> None:
		self.assertIsNone(resolve_actor({}, ("executed_by",)))


class TestResolveAmount(TestCase):
	def test_returns_none_when_no_amount_field_applies(self) -> None:
		self.assertIsNone(resolve_amount({"amount_hnl": 100}, None))

	def test_returns_none_for_missing_or_empty_value(self) -> None:
		self.assertIsNone(resolve_amount({"amount_hnl": None}, "amount_hnl"))
		self.assertIsNone(resolve_amount({"amount_hnl": ""}, "amount_hnl"))

	def test_coerces_to_float(self) -> None:
		self.assertEqual(1500.5, resolve_amount({"amount_hnl": "1500.5"}, "amount_hnl"))

	def test_zero_is_a_valid_amount_not_missing(self) -> None:
		self.assertEqual(0.0, resolve_amount({"amount_hnl": 0}, "amount_hnl"))


class TestNormalizeEvent(TestCase):
	def _row(self, **overrides):
		row = {
			"name": "OP-1",
			"document_number": "000000000123",
			"operation_date": "2026-08-01",
			"amount_hnl": 2500,
			"status": "Executed",
			"evidence": "EVI-1",
			"executed_by": "operator@example.test",
		}
		row.update(overrides)
		return row

	def test_produces_the_common_event_shape(self) -> None:
		event = normalize_event(
			category="financiero",
			doctype="NXR Operation",
			row=self._row(),
			date_field="operation_date",
			title="Gasto",
			actor_fields=("executed_by",),
			amount_field="amount_hnl",
		)
		self.assertEqual(
			{
				"key": "NXR Operation:OP-1",
				"category": "financiero",
				"category_label": "Financiero",
				"doctype": "NXR Operation",
				"name": "OP-1",
				"document_number": "000000000123",
				"date": "2026-08-01",
				"title": "Gasto",
				"status": "Executed",
				"is_exception": False,
				"actor": "operator@example.test",
				"amount_hnl": 2500.0,
				"evidence": "EVI-1",
			},
			event,
		)

	def test_a_document_without_a_usable_date_does_not_become_an_event(self) -> None:
		"""No se fabrica una fecha para que el evento aparezca de todos modos."""
		event = normalize_event(
			category="financiero",
			doctype="NXR Operation",
			row=self._row(operation_date=None),
			date_field="operation_date",
			title="Gasto",
			actor_fields=("executed_by",),
			amount_field="amount_hnl",
		)
		self.assertIsNone(event)

	def test_cancelled_operation_is_flagged_as_an_exception(self) -> None:
		event = normalize_event(
			category="financiero",
			doctype="NXR Operation",
			row=self._row(status="Cancelled"),
			date_field="operation_date",
			title="Gasto",
			actor_fields=("executed_by",),
			amount_field="amount_hnl",
		)
		self.assertTrue(event["is_exception"])

	def test_compensated_operation_is_flagged_as_an_exception(self) -> None:
		"""Una reversión/corrección de operación (Compensated Partial/Total) debe
		distinguirse visualmente, no mezclarse como si fuera una operación normal."""
		for status in ("Compensated Partial", "Compensated Total"):
			with self.subTest(status=status):
				event = normalize_event(
					category="financiero",
					doctype="NXR Operation",
					row=self._row(status=status),
					date_field="operation_date",
					title="Gasto",
					actor_fields=("executed_by",),
					amount_field="amount_hnl",
				)
				self.assertTrue(event["is_exception"])

	def test_executed_operation_is_not_flagged_as_an_exception(self) -> None:
		event = normalize_event(
			category="financiero",
			doctype="NXR Operation",
			row=self._row(status="Executed"),
			date_field="operation_date",
			title="Gasto",
			actor_fields=("executed_by",),
			amount_field="amount_hnl",
		)
		self.assertFalse(event["is_exception"])

	def test_released_commitment_is_not_an_exception_it_is_the_normal_lifecycle(self) -> None:
		"""Liberar un compromiso es el ciclo de vida normal, no un incidente — a
		diferencia de cancelarlo o rechazarlo."""
		event = normalize_event(
			category="financiero",
			doctype="NXR Commitment",
			row={"name": "C-1", "commitment_date": "2026-08-01", "status": "Released"},
			date_field="commitment_date",
			title="Compromiso",
			actor_fields=(),
			amount_field=None,
		)
		self.assertFalse(event["is_exception"])

	def test_cancelled_commitment_is_an_exception(self) -> None:
		event = normalize_event(
			category="financiero",
			doctype="NXR Commitment",
			row={"name": "C-1", "commitment_date": "2026-08-01", "status": "Cancelled"},
			date_field="commitment_date",
			title="Compromiso",
			actor_fields=(),
			amount_field=None,
		)
		self.assertTrue(event["is_exception"])

	def test_unknown_doctype_has_no_exception_statuses_and_never_flags(self) -> None:
		event = normalize_event(
			category="avance",
			doctype="Some Unmapped Doctype",
			row={"name": "X-1", "operation_date": "2026-08-01", "status": "Anything"},
			date_field="operation_date",
			title="Evento",
			actor_fields=(),
			amount_field=None,
		)
		self.assertFalse(event["is_exception"])


class TestSortAndTruncate(TestCase):
	def _event(self, name: str, date: str) -> dict:
		return {"key": name, "date": date}

	def test_orders_most_recent_first(self) -> None:
		events = [
			self._event("a", "2026-01-01"),
			self._event("b", "2026-06-01"),
			self._event("c", "2026-03-01"),
		]
		ordered, _ = sort_and_truncate(events, limit=10)
		self.assertEqual(["b", "c", "a"], [e["key"] for e in ordered])

	def test_truncates_to_the_requested_limit(self) -> None:
		events = [self._event(str(i), f"2026-01-{i:02d}") for i in range(1, 11)]
		ordered, has_more = sort_and_truncate(events, limit=3)
		self.assertEqual(3, len(ordered))
		self.assertTrue(has_more)

	def test_has_more_is_false_when_nothing_was_cut(self) -> None:
		events = [self._event("a", "2026-01-01"), self._event("b", "2026-01-02")]
		ordered, has_more = sort_and_truncate(events, limit=10)
		self.assertEqual(2, len(ordered))
		self.assertFalse(has_more)

	def test_duplicate_keys_are_preserved_not_collapsed(self) -> None:
		"""Dos eventos distintos pueden compartir la misma fecha exacta (dos
		operaciones el mismo día): no deben perderse el uno al otro."""
		events = [self._event("a", "2026-01-01"), self._event("b", "2026-01-01")]
		ordered, _ = sort_and_truncate(events, limit=10)
		self.assertEqual(2, len(ordered))


class TestResolveCategories(TestCase):
	AVAILABLE: ClassVar[dict] = {"financiero": None, "compras": None, "contratos": None}

	def test_a_single_string_is_treated_as_one_category(self) -> None:
		self.assertEqual(["financiero"], resolve_categories("financiero", self.AVAILABLE))

	def test_a_list_is_filtered_to_known_categories(self) -> None:
		result = resolve_categories(["financiero", "unknown", "compras"], self.AVAILABLE)
		self.assertEqual(["financiero", "compras"], result)

	def test_no_filter_returns_every_available_category(self) -> None:
		result = resolve_categories(None, self.AVAILABLE)
		self.assertEqual(set(self.AVAILABLE), set(result))

	def test_a_filter_with_only_unknown_categories_falls_back_to_all(self) -> None:
		"""Un filtro mal escrito no debe devolver una timeline vacía en silencio."""
		result = resolve_categories(["not-a-real-category"], self.AVAILABLE)
		self.assertEqual(set(self.AVAILABLE), set(result))


class TestClampLimit(TestCase):
	def test_default_when_not_provided(self) -> None:
		self.assertEqual(30, clamp_limit(None))

	def test_clamped_to_the_maximum(self) -> None:
		self.assertEqual(100, clamp_limit(9999))

	def test_clamped_to_at_least_one(self) -> None:
		self.assertEqual(1, clamp_limit(-5))
		self.assertEqual(1, clamp_limit(0))

	def test_invalid_value_falls_back_to_default(self) -> None:
		self.assertEqual(30, clamp_limit("not-a-number"))
