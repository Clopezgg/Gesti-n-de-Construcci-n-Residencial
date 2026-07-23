from __future__ import annotations

import argparse
from pathlib import Path


def register_app(path: Path, app_name: str = "nexora") -> None:
	"""Append an app exactly once while preserving one app per line."""
	apps = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
	if app_name not in apps:
		apps.append(app_name)
	path.write_text("\n".join(apps) + "\n", encoding="utf-8")


def main() -> int:
	parser = argparse.ArgumentParser(description="Register NEXORA in a Frappe bench apps.txt file.")
	parser.add_argument("path", type=Path)
	args = parser.parse_args()
	register_app(args.path)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
