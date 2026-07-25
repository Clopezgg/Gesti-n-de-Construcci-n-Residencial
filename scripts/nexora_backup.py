#!/usr/bin/env python3
"""NEXORA — Utilidad de backup y restore (Bloque 20).

Proporciona comandos para backup/restore de la base de datos NEXORA
y los archivos de configuración. Diseñado para ejecución desde Coolify
o directamente en el servidor.

Uso:
    python scripts/nexora_backup.py backup [--output DIR]
    python scripts/nexora_backup.py restore ARCHIVO
    python scripts/nexora_backup.py list
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import subprocess
import sys

BACKUP_DIR = pathlib.Path("/tmp/nexora_backups")
DB_NAME = "nexora"
DB_USER = "nexora_user"


def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def cmd_backup(output: str | None) -> int:
    out = pathlib.Path(output) if output else BACKUP_DIR
    out.mkdir(parents=True, exist_ok=True)
    ts = get_timestamp()
    sql_file = out / f"nexora_{ts}.sql"
    result = run(["mariadb-dump", "-u", DB_USER, "--databases", DB_NAME, "--result-file", str(sql_file)])
    if result.returncode != 0:
        print(f"ERROR: backup falló: {result.stderr}")
        return 1
    print(f"Backup creado: {sql_file} ({sql_file.stat().st_size} bytes)")
    return 0


def cmd_restore(archive: str) -> int:
    path = pathlib.Path(archive)
    if not path.is_file():
        print(f"ERROR: archivo no encontrado: {path}")
        return 1
    result = run(["mariadb", "-u", DB_USER, DB_NAME, "-e", f"source {path}"])
    if result.returncode != 0:
        print(f"ERROR: restore falló: {result.stderr}")
        return 1
    print(f"Restore completado desde: {path}")
    return 0


def cmd_list() -> int:
    if not BACKUP_DIR.is_dir():
        print("No hay backups disponibles.")
        return 0
    backups = sorted(BACKUP_DIR.glob("nexora_*.sql"))
    if not backups:
        print("No hay backups disponibles.")
        return 0
    print("Backups disponibles:")
    for b in backups:
        size = b.stat().st_size
        print(f"  {b.name} ({size // 1024} KB)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NEXORA Backup Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)
    bp = subparsers.add_parser("backup", help="Create backup")
    bp.add_argument("--output", help="Output directory")
    subparsers.add_parser("restore", help="Restore from backup").add_argument("archive", help="SQL file to restore")
    subparsers.add_parser("list", help="List backups")
    args = parser.parse_args()
    if args.command == "backup":
        return cmd_backup(args.output)
    elif args.command == "restore":
        return cmd_restore(args.archive)
    elif args.command == "list":
        return cmd_list()
    return 1


if __name__ == "__main__":
    sys.exit(main())
