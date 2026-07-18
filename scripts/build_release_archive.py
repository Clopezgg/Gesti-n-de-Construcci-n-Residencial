#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "dist"

EXCLUDED_PARTS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "sites",
    "logs",
    "migration-output",
    "backups",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".sql",
    ".sqlite",
    ".db",
    ".gz",
    ".tgz",
    ".tar",
    ".zip",
}
EXCLUDED_NAMES = {".env", "site_config.json", "currentsite.txt"}


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [ROOT / item.decode("utf-8") for item in raw.split(b"\0") if item]


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.name.startswith(".env.") and path.name != ".env.example":
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def zip_info(relative: PurePosixPath, executable: bool) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(str(relative), date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    mode = 0o755 if executable else 0o644
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def main() -> int:
    commit = git_output("rev-parse", "HEAD")
    short = commit[:12]
    if git_output("status", "--porcelain"):
        raise SystemExit("The working tree is not clean; refusing to package an uncommitted release.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / f"ConstruControl-{short}.zip"
    checksum_file = archive.with_suffix(".sha256")

    files = sorted((path for path in tracked_files() if should_include(path)), key=lambda path: path.as_posix())
    if not files:
        raise SystemExit("No tracked source files were selected for the release archive.")

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in files:
            relative = PurePosixPath(path.relative_to(ROOT).as_posix())
            executable = os.access(path, os.X_OK) or path.suffix == ".sh"
            output.writestr(zip_info(relative, executable), path.read_bytes())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum_file.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")

    print(f"archive={archive}")
    print(f"sha256={digest}")
    print(f"commit={commit}")
    print(f"files={len(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
