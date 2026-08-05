#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "nexora-secrets" / "report.json"
TEXT_ROOTS = (
	"nexora_app/",
	".github/",
	"deploy/nexora/",
	"deploy/ci/",
	"docs/nexora/",
	"docs/final/",
	"scripts/",
)
TEXT_FILES = {
	"Dockerfile.nexora",
	"docker-compose.nexora.yml",
	".env.example",
	"EXECUTION_STATE.md",
}
BINARY_SUFFIXES = {
	".png",
	".jpg",
	".jpeg",
	".gif",
	".ico",
	".webp",
	".woff",
	".woff2",
	".ttf",
	".eot",
	".mp3",
	".mp4",
	".zip",
	".gz",
	".pdf",
	".pyc",
}
FORBIDDEN_TRACKED_NAMES = {
	".env",
	"id_rsa",
	"id_ed25519",
	"credentials.json",
	"service-account.json",
}
PATTERNS = {
	"private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
	"github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
	"github_fine_grained_token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
	"aws_access_key": re.compile(r"\b(?:A3T|AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASCA)[A-Z0-9]{16}\b"),
	"openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
	"slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
	"stripe_live_key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
	"supabase_secret": re.compile(r"\bsb_secret_[A-Za-z0-9_-]{12,}\b"),
	"credential_url": re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb|redis)://[^\s:/]+:[^\s@]{8,}@", re.I),
}


def tracked_files() -> list[Path]:
	result = subprocess.run(
		["git", "ls-files", "-z"],
		cwd=ROOT,
		check=True,
		capture_output=True,
	)
	paths: list[Path] = []
	for raw in result.stdout.split(b"\0"):
		if not raw:
			continue
		relative = raw.decode("utf-8", errors="strict")
		if relative in TEXT_FILES or relative.startswith(TEXT_ROOTS):
			paths.append(ROOT / relative)
	return paths


def scan() -> dict[str, object]:
	findings: list[dict[str, object]] = []
	for path in tracked_files():
		relative = path.relative_to(ROOT).as_posix()
		if path.name in FORBIDDEN_TRACKED_NAMES or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
			findings.append({"path": relative, "line": 1, "rule": "forbidden_secret_file"})
			continue
		if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file() or path.stat().st_size > 2_000_000:
			continue
		text = path.read_text(encoding="utf-8", errors="ignore")
		for line_number, line in enumerate(text.splitlines(), start=1):
			for rule, pattern in PATTERNS.items():
				if pattern.search(line):
					findings.append({"path": relative, "line": line_number, "rule": rule})
	return {
		"schema": "nexora-secret-scan/v1",
		"scope": [*TEXT_ROOTS, *sorted(TEXT_FILES)],
		"files_scanned": len(tracked_files()),
		"findings": findings,
		"ok": not findings,
	}


def main() -> int:
	report = scan()
	REPORT.parent.mkdir(parents=True, exist_ok=True)
	REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
	print(
		f"NEXORA secret scan: files={report['files_scanned']} findings={len(report['findings'])}",
		flush=True,
	)
	for finding in report["findings"]:
		print(f"- {finding['rule']}: {finding['path']}:{finding['line']}")
	return 0 if report["ok"] else 1


if __name__ == "__main__":
	raise SystemExit(main())
