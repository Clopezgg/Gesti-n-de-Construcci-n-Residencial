from __future__ import annotations

from collections.abc import Iterable

GENERIC_EMAIL_IDS = frozenset(
	{
		"admin@nexora.com",
		"noreply@nexora.local",
	}
)


def split_prompt_users(value: object) -> list[str]:
	"""Normalize Frappe's comma-separated email password prompt default."""
	if not isinstance(value, str):
		return []
	return [entry.strip() for entry in value.split(",") if entry.strip()]


def pending_emails_are_generic(email_ids: Iterable[object]) -> bool:
	"""Return true only when every pending email is a known NEXORA placeholder."""
	normalized = [str(email_id or "").strip().lower() for email_id in email_ids]
	return bool(normalized) and all(email_id in GENERIC_EMAIL_IDS for email_id in normalized)


def remove_prompt_user(value: object, user: str) -> str | None:
	"""Remove one user from Frappe's prompt list while preserving the others."""
	remaining = [entry for entry in split_prompt_users(value) if entry != user]
	return ",".join(remaining) or None
