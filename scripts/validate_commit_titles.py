from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Iterable

POLICY_ENFORCEMENT_SHA = "ccb6e0921fc6e5a3363a7076334d130aacac2ef5"
IMMUTABLE_TITLE_EXCEPTIONS = {
	"01d5684d3449e22669c81fdc91539dd64278f86b": "noop",
}
CONVENTIONAL_TYPES = (
	"build",
	"chore",
	"ci",
	"docs",
	"feat",
	"fix",
	"perf",
	"refactor",
	"revert",
	"style",
	"test",
)

_CONVENTIONAL_PATTERN = re.compile(rf"^(?:{'|'.join(CONVENTIONAL_TYPES)})(?:\([a-z0-9_.\-/]+\))?!?:\s+\S.*$")
_BLOCK_PATTERN = re.compile(r"^\[B(?:0[1-9]|1[0-2])\]\s+\S.*$")
_CERTIFICATION_PATTERN = re.compile(r"^\[CERT\]\s+\S.*$")


def is_valid_title(title: str) -> bool:
	"""Accept strict conventional or controlled ConstruControl titles."""
	normalized = " ".join(str(title or "").split())
	if not normalized or len(normalized) > 120:
		return False
	return bool(
		_CONVENTIONAL_PATTERN.fullmatch(normalized)
		or _BLOCK_PATTERN.fullmatch(normalized)
		or _CERTIFICATION_PATTERN.fullmatch(normalized)
	)


def invalid_titles(titles: Iterable[str]) -> list[str]:
	return [title for title in titles if not is_valid_title(title)]


def is_valid_commit(sha: str, title: str) -> bool:
	normalized_sha = str(sha or "").strip().lower()
	normalized_title = " ".join(str(title or "").split())
	return (
		is_valid_title(normalized_title) or IMMUTABLE_TITLE_EXCEPTIONS.get(normalized_sha) == normalized_title
	)


def invalid_commits(commits: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
	return [(sha, title) for sha, title in commits if not is_valid_commit(sha, title)]


def validation_range(base: str, head: str) -> str:
	"""Validate only commits introduced by the pull request.

	History already present in the protected base branch is immutable and is
	validated by that branch's own controls.
	"""
	return f"{base}..{head}"


def commit_records(base: str, head: str) -> list[tuple[str, str]]:
	completed = subprocess.run(
		["git", "log", "--format=%H%x00%s", validation_range(base, head)],
		check=True,
		capture_output=True,
		text=True,
	)
	records = []
	for line in completed.stdout.splitlines():
		if not line.strip():
			continue
		sha, separator, title = line.partition("\0")
		if not separator:
			raise RuntimeError(f"Unable to parse git log record: {line!r}")
		records.append((sha, title))
	return records


def commit_titles(base: str, head: str) -> list[str]:
	return [title for _sha, title in commit_records(base, head)]


def main() -> int:
	parser = argparse.ArgumentParser(description="Validate pull-request commit titles.")
	parser.add_argument("--from", dest="base", required=True, help="Base commit SHA")
	parser.add_argument("--to", dest="head", required=True, help="Head commit SHA")
	args = parser.parse_args()

	commits = commit_records(args.base, args.head)
	failures = invalid_commits(commits)
	if failures:
		print("Invalid commit titles introduced by this pull request:")
		for sha, title in failures:
			print(f"- {sha}: {title}")
		print("Allowed: conventional commits, [B01] through [B12], or [CERT].")
		return 1

	print(f"Commit title validation passed ({len(commits)} pull-request commits).")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
