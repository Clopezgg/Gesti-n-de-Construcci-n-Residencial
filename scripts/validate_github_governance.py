from __future__ import annotations

import re
from pathlib import Path

WORKFLOW_ROOT = Path(".github/workflows")
CONTROLLED_WORKFLOWS = {
	"apply-construcontrol-consolidation.yml",
	"construcontrol-branch-cleanup.yml",
	"construcontrol-container-receipt.yml",
	"construcontrol-runtime-receipt.yml",
	"construcontrol-verification-receipt.yml",
}

_DIRECT_MAIN_PUSH = re.compile(r"\bgit\s+push\b[^\n]*(?:HEAD:main|refs/heads/main|\bmain\b)", re.IGNORECASE)
_REMOTE_BRANCH_DELETE = re.compile(r"\bgit\s+push\b[^\n]*(?:--delete|:\s*refs/heads/)", re.IGNORECASE)
_CONTENTS_WRITE = re.compile(r"(?m)^\s*contents\s*:\s*write\s*(?:#.*)?$")
_PATCH_APPLICATOR = re.compile(r"\bgit\s+apply\b", re.IGNORECASE)
_FRAGMENT_TRANSPORT = re.compile(
	r"(?:\.part-[*0-9]+|base64\s+--decode|\.patch\.gz\.b64|cat\s+[^\n]*\.part-)",
	re.IGNORECASE,
)


def workflow_violations(path: Path, text: str) -> list[str]:
	violations: list[str] = []
	if _DIRECT_MAIN_PUSH.search(text):
		violations.append("direct push to main")
	if _REMOTE_BRANCH_DELETE.search(text):
		violations.append("remote branch deletion")
	if path.name in CONTROLLED_WORKFLOWS and _CONTENTS_WRITE.search(text):
		violations.append("write permission in controlled ConstruControl workflow")
	if path.name in CONTROLLED_WORKFLOWS and _PATCH_APPLICATOR.search(text):
		violations.append("patch applicator in controlled ConstruControl workflow")
	if path.name in CONTROLLED_WORKFLOWS and _FRAGMENT_TRANSPORT.search(text):
		violations.append("fragmented payload transport in controlled ConstruControl workflow")
	return violations


def scan_workflows(root: Path = WORKFLOW_ROOT) -> dict[str, list[str]]:
	failures: dict[str, list[str]] = {}
	for path in sorted(root.glob("*.y*ml")):
		violations = workflow_violations(path, path.read_text(encoding="utf-8"))
		if violations:
			failures[path.as_posix()] = violations
	return failures


def main() -> int:
	failures = scan_workflows()
	if failures:
		print("Unsafe GitHub workflow mutations detected:")
		for path, violations in failures.items():
			print(f"- {path}: {', '.join(violations)}")
		return 1
	print("GitHub workflow governance validation passed.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
