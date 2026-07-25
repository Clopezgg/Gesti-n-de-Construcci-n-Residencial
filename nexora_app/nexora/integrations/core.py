from __future__ import annotations

import re

INTEGRATION_STATUSES = frozenset({"Active", "Inactive", "Error", "Disabled"})

_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


class IntegrationError(ValueError):
	pass


def validate_endpoint(url: str) -> None:
	if not _URL_RE.match(url):
		raise IntegrationError(f"URL de endpoint invalida: {url}")


def redact_credentials(text: str) -> str:
	redacted = re.sub(
		r'(?i)(password|secret|token|api_key|api_secret|credential|auth|key)\s*[:=]\s*["\']?\S+["\']?',
		r"\1: ***REDACTED***",
		text,
	)
	redacted = re.sub(
		r"(?i)(authorization|bearer)\s+\S+",
		r"\1 ***REDACTED***",
		redacted,
	)
	return redacted
