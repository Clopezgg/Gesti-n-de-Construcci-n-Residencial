from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Iterable

POLICY_ENFORCEMENT_SHA = "6678c04878be3e6f87d88a871f068e9555415380"
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


def validation_range(base: str, head: str) -> str:
	"""Grandfather the immutable pre-policy history and validate every later commit."""
	ancestor = subprocess.run(
		["git", "merge-base", "--is-ancestor", POLICY_ENFORCEMENT_SHA, head],
		check=False,
		capture_output=True,
		text=True,
	)
	start = POLICY_ENFORCEMENT_SHA if ancestor.returncode == 0 else base
	return f"{start}..{head}"


def commit_titles(base: str, head: str) -> list[str]:
	completed = subprocess.run(
		["git", "log", "--format=%s", validation_range(base, head)],
		check=True,
		capture_output=True,
		text=True,
	)
	return [line for line in completed.stdout.splitlines() if line.strip()]


def main() -> int:
	parser = argparse.ArgumentParser(description="Validate pull-request commit titles.")
	parser.add_argument("--from", dest="base", required=True, help="Base commit SHA")
	parser.add_argument("--to", dest="head", required=True, help="Head commit SHA")
	args = parser.parse_args()

	titles = commit_titles(args.base, args.head)
	failures = invalid_titles(titles)
	if failures:
		print("Invalid commit titles after the policy enforcement checkpoint:")
		for title in failures:
			print(f"- {title}")
		print("Allowed: conventional commits, [B01] through [B12], or [CERT].")
		return 1

	print(f"Commit title validation passed ({len(titles)} policy-era commits).")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
