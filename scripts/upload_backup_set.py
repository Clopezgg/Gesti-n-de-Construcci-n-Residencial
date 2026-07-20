#!/usr/bin/env python3
"""Compatibility tombstone for the obsolete Supabase backup uploader.

Production backups are stored and verified in the persistent AWS/Coolify
``sites`` volume. Supabase is only a historical migration source.
"""

from __future__ import annotations

import sys


MESSAGE = (
    "OBSOLETO: no se permiten respaldos productivos hacia Supabase. "
    "Use deploy/coolify/backup-now.sh y el volumen persistente sites."
)


def main() -> int:
    print(MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
