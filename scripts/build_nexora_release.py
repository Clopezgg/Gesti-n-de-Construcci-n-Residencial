#!/usr/bin/env python3
"""Build a deterministic, secret-free NEXORA source delivery archive."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDED_PREFIXES = (".git/", "dist/", "node_modules/", ".venv/", "venv/")
EXCLUDED_NAMES = {".env", ".nexora-ui.env"}
EXCLUDED_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def application_version() -> str:
    source = (ROOT / "nexora_app" / "nexora" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', source)
    if not match:
        raise RuntimeError("NEXORA application version is missing")
    return match.group(1)


def tracked_files() -> list[str]:
    paths = git("ls-files").splitlines()
    result: list[str] = []
    for raw in paths:
        path = raw.replace("\\", "/")
        name = Path(path).name
        if path.startswith(EXCLUDED_PREFIXES):
            continue
        if name in EXCLUDED_NAMES or path.endswith(EXCLUDED_SUFFIXES):
            continue
        result.append(path)
    return sorted(result)


def zip_timestamp() -> tuple[int, int, int, int, int, int]:
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0") or 0)
    if epoch <= 0:
        epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    import datetime as dt

    moment = dt.datetime.fromtimestamp(max(epoch, 315532800), tz=dt.timezone.utc)
    return (moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second)


def main() -> int:
    sha = git("rev-parse", "HEAD")
    short_sha = sha[:12]
    version = os.environ.get("NEXORA_VERSION") or application_version()
    base = f"NEXORA-ENTREGA-FINAL-{version}-{short_sha}"
    DIST.mkdir(parents=True, exist_ok=True)
    archive = DIST / f"{base}.zip"
    checksum = DIST / f"{base}.sha256"
    timestamp = zip_timestamp()

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for relative in tracked_files():
            source = ROOT / relative
            if not source.is_file():
                continue
            info = zipfile.ZipInfo(f"{base}/{relative}", date_time=timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if os.access(source, os.X_OK) else 0o644) << 16
            bundle.writestr(info, source.read_bytes())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"archive={archive.relative_to(ROOT)}")
    print(f"version={version}")
    print(f"sha256={digest}")
    print(f"source_sha={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
