from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from nexora.intelligence.core import (
	AdapterInvocationError,
	ProviderAuthenticationError,
	ProviderModelNotFoundError,
	ProviderQuotaExhaustedError,
	ProviderRateLimitError,
	ProviderRecord,
	ProviderTimeoutError,
)
from nexora.intelligence.orchestrator_core import (
	DEFAULT_COOLDOWN_SECONDS,
	DEFAULT_FAILURE_THRESHOLD,
	MAX_COOLDOWN_SECONDS,
	HealthState,
	begin_trial,
	is_available,
	rank_candidates,
	record_failure,
	record_success,
	score_candidate,
	should_retry_same_provider,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _record(
	key: str, *, priority: int = 100, cost_hint: str = "Medium", capabilities=("text",)
) -> ProviderRecord:
	return ProviderRecord(
		provider_key=key,
		display_name=key.title(),
		status="Active",
		capabilities=capabilities,
		priority=priority,
		cost_hint=cost_hint,
	)


class TestHealthState(TestCase):
	def test_default_is_closed_with_no_failures(self) -> None:
		state = HealthState()
		self.assertEqual("Closed", state.circuit_state)
		self.assertEqual(0, state.consecutive_failures)
		self.assertIsNone(state.degraded_until)

	def test_rejects_unknown_circuit_state(self) -> None:
		with self.assertRaises(ValueError):
			HealthState(circuit_state="Broken")

	def test_rejects_negative_failures(self) -> None:
		with self.assertRaises(ValueError):
			HealthState(consecutive_failures=-1)

	def test_is_immutable(self) -> None:
		state = HealthState()
		with self.assertRaises(AttributeError):
			state.circuit_state = "Open"  # type: ignore[misc]


class TestIsAvailable(TestCase):
	def test_closed_is_always_available(self) -> None:
		self.assertTrue(is_available(HealthState(), now=NOW))

	def test_half_open_is_available(self) -> None:
		state = HealthState(circuit_state="Half-Open", consecutive_failures=3, degraded_until=NOW)
		self.assertTrue(is_available(state, now=NOW))

	def test_open_before_cooldown_is_not_available(self) -> None:
		state = HealthState(
			circuit_state="Open", consecutive_failures=3, degraded_until=NOW + timedelta(seconds=60)
		)
		self.assertFalse(is_available(state, now=NOW))

	def test_open_after_cooldown_is_available(self) -> None:
		state = HealthState(
			circuit_state="Open", consecutive_failures=3, degraded_until=NOW + timedelta(seconds=60)
		)
		self.assertTrue(is_available(state, now=NOW + timedelta(seconds=61)))

	def test_open_exactly_at_cooldown_boundary_is_available(self) -> None:
		state = HealthState(
			circuit_state="Open", consecutive_failures=3, degraded_until=NOW + timedelta(seconds=60)
		)
		self.assertTrue(is_available(state, now=NOW + timedelta(seconds=60)))


class TestRecordSuccess(TestCase):
	def test_resets_from_closed(self) -> None:
		state = record_success(HealthState(consecutive_failures=1))
		self.assertEqual(HealthState(), state)

	def test_heals_from_open(self) -> None:
		degraded = HealthState(circuit_state="Open", consecutive_failures=5, degraded_until=NOW)
		self.assertEqual(HealthState(), record_success(degraded))

	def test_heals_from_half_open(self) -> None:
		trial = HealthState(circuit_state="Half-Open", consecutive_failures=3, degraded_until=NOW)
		self.assertEqual(HealthState(), record_success(trial))


class TestRecordFailure(TestCase):
	def test_stays_closed_below_threshold(self) -> None:
		state = record_failure(HealthState(), now=NOW)
		self.assertEqual("Closed", state.circuit_state)
		self.assertEqual(1, state.consecutive_failures)
		self.assertIsNone(state.degraded_until)

	def test_opens_at_threshold(self) -> None:
		state = HealthState(consecutive_failures=DEFAULT_FAILURE_THRESHOLD - 1)
		result = record_failure(state, now=NOW)
		self.assertEqual("Open", result.circuit_state)
		self.assertEqual(DEFAULT_FAILURE_THRESHOLD, result.consecutive_failures)

	def test_first_opening_uses_base_cooldown_not_doubled(self) -> None:
		state = HealthState(consecutive_failures=DEFAULT_FAILURE_THRESHOLD - 1)
		result = record_failure(state, now=NOW)
		self.assertEqual(NOW + timedelta(seconds=DEFAULT_COOLDOWN_SECONDS), result.degraded_until)

	def test_failing_again_after_a_trial_doubles_the_cooldown(self) -> None:
		opened = HealthState(
			circuit_state="Open", consecutive_failures=DEFAULT_FAILURE_THRESHOLD, degraded_until=NOW
		)
		trial = begin_trial(opened)
		failed_again = record_failure(trial, now=NOW)
		self.assertEqual(NOW + timedelta(seconds=DEFAULT_COOLDOWN_SECONDS * 2), failed_again.degraded_until)

	def test_cooldown_is_capped_at_max(self) -> None:
		state = HealthState(circuit_state="Half-Open", consecutive_failures=20, degraded_until=NOW)
		result = record_failure(state, now=NOW)
		self.assertLessEqual((result.degraded_until - NOW).total_seconds(), MAX_COOLDOWN_SECONDS)

	def test_rate_limit_opens_immediately_regardless_of_threshold(self) -> None:
		result = record_failure(HealthState(), now=NOW, retry_after_seconds=45)
		self.assertEqual("Open", result.circuit_state)
		self.assertEqual(NOW + timedelta(seconds=45), result.degraded_until)

	def test_rate_limit_with_zero_retry_after_still_opens_with_minimum_cooldown(self) -> None:
		result = record_failure(HealthState(), now=NOW, retry_after_seconds=0)
		self.assertEqual("Open", result.circuit_state)
		self.assertEqual(NOW + timedelta(seconds=1), result.degraded_until)

	def test_failure_count_keeps_incrementing_across_trials(self) -> None:
		state = HealthState()
		for _ in range(5):
			state = record_failure(state, now=NOW)
			if state.circuit_state == "Open":
				state = begin_trial(state)
		self.assertEqual(5, state.consecutive_failures)


class TestBeginTrial(TestCase):
	def test_transitions_open_to_half_open(self) -> None:
		state = HealthState(circuit_state="Open", consecutive_failures=3, degraded_until=NOW)
		trial = begin_trial(state)
		self.assertEqual("Half-Open", trial.circuit_state)
		self.assertEqual(3, trial.consecutive_failures)
		self.assertEqual(NOW, trial.degraded_until)

	def test_is_a_no_op_when_already_closed(self) -> None:
		state = HealthState()
		self.assertEqual(state, begin_trial(state))

	def test_is_a_no_op_when_already_half_open(self) -> None:
		state = HealthState(circuit_state="Half-Open", consecutive_failures=3, degraded_until=NOW)
		self.assertEqual(state, begin_trial(state))


class TestShouldRetrySameProvider(TestCase):
	def test_timeout_is_retryable(self) -> None:
		self.assertTrue(should_retry_same_provider(ProviderTimeoutError("x")))

	def test_generic_adapter_error_is_retryable(self) -> None:
		self.assertTrue(should_retry_same_provider(AdapterInvocationError("x")))

	def test_authentication_error_is_never_retryable(self) -> None:
		self.assertFalse(should_retry_same_provider(ProviderAuthenticationError("x")))

	def test_model_not_found_is_never_retryable(self) -> None:
		self.assertFalse(should_retry_same_provider(ProviderModelNotFoundError("x")))

	def test_rate_limit_is_never_retryable(self) -> None:
		self.assertFalse(should_retry_same_provider(ProviderRateLimitError("x")))

	def test_quota_exhausted_is_never_retryable(self) -> None:
		self.assertFalse(should_retry_same_provider(ProviderQuotaExhaustedError("x")))


class TestScoreCandidate(TestCase):
	def test_lower_priority_number_scores_better(self) -> None:
		fast = score_candidate(_record("provider-a", priority=1), HealthState())
		slow = score_candidate(_record("provider-b", priority=100), HealthState())
		self.assertLess(fast, slow)

	def test_cost_hint_breaks_ties_at_same_priority(self) -> None:
		cheap = score_candidate(_record("provider-a", priority=10, cost_hint="Low"), HealthState())
		expensive = score_candidate(_record("provider-b", priority=10, cost_hint="High"), HealthState())
		self.assertLess(cheap, expensive)

	def test_half_open_is_penalized_relative_to_closed_at_same_priority(self) -> None:
		record = _record("provider-a", priority=10)
		closed_score = score_candidate(record, HealthState())
		half_open_score = score_candidate(record, HealthState(circuit_state="Half-Open"))
		self.assertLess(closed_score, half_open_score)


class TestRankCandidates(TestCase):
	def test_orders_by_priority(self) -> None:
		records = [_record("slow", priority=200), _record("fast", priority=1)]
		ranked = rank_candidates(records, {}, now=NOW)
		self.assertEqual(["fast", "slow"], [r.provider_key for r in ranked])

	def test_excludes_open_providers_still_in_cooldown(self) -> None:
		records = [_record("degraded", priority=1), _record("healthy", priority=100)]
		healths = {"degraded": HealthState(circuit_state="Open", degraded_until=NOW + timedelta(seconds=60))}
		ranked = rank_candidates(records, healths, now=NOW)
		self.assertEqual(["healthy"], [r.provider_key for r in ranked])

	def test_includes_open_providers_past_cooldown(self) -> None:
		records = [_record("recovering", priority=1)]
		healths = {"recovering": HealthState(circuit_state="Open", degraded_until=NOW - timedelta(seconds=1))}
		ranked = rank_candidates(records, healths, now=NOW)
		self.assertEqual(["recovering"], [r.provider_key for r in ranked])

	def test_prefer_wins_when_available(self) -> None:
		records = [_record("fast", priority=1), _record("preferred", priority=999)]
		ranked = rank_candidates(records, {}, now=NOW, prefer="preferred")
		self.assertEqual("preferred", ranked[0].provider_key)

	def test_prefer_falls_back_when_preferred_is_degraded(self) -> None:
		records = [_record("preferred", priority=1), _record("fallback", priority=999)]
		healths = {"preferred": HealthState(circuit_state="Open", degraded_until=NOW + timedelta(seconds=60))}
		ranked = rank_candidates(records, healths, now=NOW, prefer="preferred")
		self.assertEqual(["fallback"], [r.provider_key for r in ranked])

	def test_returns_empty_list_when_nothing_is_available(self) -> None:
		records = [_record("degraded", priority=1)]
		healths = {"degraded": HealthState(circuit_state="Open", degraded_until=NOW + timedelta(seconds=60))}
		self.assertEqual([], rank_candidates(records, healths, now=NOW))

	def test_missing_health_defaults_to_closed_and_available(self) -> None:
		records = [_record("brand-new", priority=1)]
		self.assertEqual(["brand-new"], [r.provider_key for r in rank_candidates(records, {}, now=NOW)])
