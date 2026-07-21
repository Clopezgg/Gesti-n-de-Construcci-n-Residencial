from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

WEBSITE_REPOS = ["erpnext_com", "frappe_io"]
DOCUMENTATION_DOMAINS = ["docs.erpnext.com", "docs.frappe.io", "frappeframework.com"]


def is_valid_url(url: str) -> bool:
	parts = urlparse(url)
	return all((parts.scheme, parts.netloc, parts.path))


def is_documentation_link(word: str) -> bool:
	cleaned = word.strip("<>()[]{}.,;!\"'")
	if not cleaned.startswith("http") or not is_valid_url(cleaned):
		return False

	parsed_url = urlparse(cleaned)
	if parsed_url.netloc in DOCUMENTATION_DOMAINS:
		return True

	if parsed_url.netloc == "github.com":
		parts = parsed_url.path.split("/")
		if len(parts) >= 5 and parts[1] == "frappe" and parts[2] in WEBSITE_REPOS:
			return True

	return False


def contains_documentation_link(body: str) -> bool:
	return any(is_documentation_link(word) for line in body.splitlines() for word in line.split())


def evaluate_pull_request(payload: dict[str, object]) -> tuple[int, str]:
	title = str(payload.get("title") or "").lower().strip()
	head = payload.get("head") or {}
	head_sha = head.get("sha") if isinstance(head, dict) else None
	body = str(payload.get("body") or "").lower()

	if not title.startswith("feat") or not head_sha or "no-docs" in body or "backport" in body:
		return 0, "Skipping documentation checks... 🏃"

	if contains_documentation_link(body):
		return 0, "Documentation Link Found. You're Awesome! 🎉"

	return 1, "Documentation Link Not Found! ⚠️"


def payload_from_event(event_path: str | None = None) -> dict[str, object] | None:
	path = Path(event_path or os.environ.get("GITHUB_EVENT_PATH", ""))
	if not path.is_file():
		return None
	event = json.loads(path.read_text(encoding="utf-8"))
	pull_request = event.get("pull_request")
	return pull_request if isinstance(pull_request, dict) else None


def payload_from_api(number: str, repository: str | None = None) -> dict[str, object] | None:
	repo = repository or os.environ.get("GITHUB_REPOSITORY")
	if not repo or "/" not in repo:
		return None

	request = Request(
		f"https://api.github.com/repos/{repo}/pulls/{number}",
		headers={"Accept": "application/vnd.github+json", "User-Agent": "ConstruControl-docs-check"},
	)
	try:
		with urlopen(request, timeout=15) as response:
			payload = json.load(response)
	except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
		return None
	return payload if isinstance(payload, dict) else None


def check_pull_request(
	number: str, event_path: str | None = None, repository: str | None = None
) -> tuple[int, str]:
	payload = payload_from_event(event_path) or payload_from_api(number, repository)
	if payload is None:
		return 1, "Pull Request Not Found! ⚠️"
	return evaluate_pull_request(payload)


if __name__ == "__main__":
	exit_code, message = check_pull_request(sys.argv[1])
	print(message)
	raise SystemExit(exit_code)
