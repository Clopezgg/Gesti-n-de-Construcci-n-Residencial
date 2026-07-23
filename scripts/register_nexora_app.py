from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = Path.home() / "frappe-bench"
SAFE_SITE_TOKENS = {"staging", "test"}
FORBIDDEN_SITE_TOKENS = {"prod", "production", "live"}


def _run(*command: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
	print("+", " ".join(command), flush=True)
	subprocess.run(command, cwd=cwd, env=env, check=True)


def _output(*command: str, cwd: Path | None = None) -> str:
	print("+", " ".join(command), flush=True)
	return subprocess.run(
		command,
		cwd=cwd,
		check=True,
		capture_output=True,
		text=True,
		encoding="utf-8",
	).stdout


def _clear_bench_module_cache(apps_file: Path) -> None:
	"""Invalidate Frappe's cached app_modules after changing bench-global apps.txt."""
	bench = apps_file.resolve().parent.parent
	if not (bench / "apps").is_dir() or not (bench / "sites").is_dir():
		return
	_run("bench", "--site", "all", "clear-cache", cwd=bench)


def register_app(path: Path, app_name: str = "nexora") -> None:
	"""Append an app exactly once and invalidate Frappe's module registry."""
	apps = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
	if app_name not in apps:
		apps.append(app_name)
	path.write_text("\n".join(apps) + "\n", encoding="utf-8")
	_clear_bench_module_cache(path)


def _require_staging_site(site: str) -> None:
	value = site.casefold().strip()
	tokens = {token for token in re.split(r"[._-]+", value) if token}
	if tokens.intersection(FORBIDDEN_SITE_TOKENS):
		raise SystemExit(f"El sitio {site!r} contiene un indicador de producción y está prohibido.")
	if value == "localhost" or value.endswith(".localhost") or tokens.intersection(SAFE_SITE_TOKENS):
		return
	raise SystemExit(
		f"El sitio {site!r} no parece staging/test/local. Use un nombre seguro; producción está prohibida."
	)


def _ensure_bench(bench: Path) -> None:
	if (bench / "env/bin/python").is_file() and (bench / "env/bin/pip").is_file():
		return
	helper = ROOT / ".github/helper/install.sh"
	if not helper.is_file():
		raise SystemExit(f"No existe un bench y falta {helper}")
	environment = os.environ.copy()
	environment.setdefault("DB", "mariadb")
	environment.setdefault("TYPE", "server")
	environment.setdefault("FRAPPE_USER", "frappe")
	environment.setdefault("FRAPPE_BRANCH", "version-15")
	environment.setdefault("PAYMENTS_BRANCH", "version-15")
	_run("bash", str(helper), cwd=ROOT, env=environment)
	if not (bench / "env/bin/python").is_file():
		raise SystemExit(f"El instalador no produjo el bench esperado en {bench}")


def _prepare_app(bench: Path) -> None:
	app_link = bench / "apps/nexora"
	app_source = ROOT / "nexora_app"
	app_link.parent.mkdir(parents=True, exist_ok=True)
	if app_link.is_symlink():
		if app_link.resolve() != app_source.resolve():
			raise SystemExit(f"{app_link} apunta a otro checkout")
	elif app_link.exists():
		raise SystemExit(f"{app_link} ya existe y no es un enlace simbólico")
	else:
		app_link.symlink_to(app_source, target_is_directory=True)
	_run(str(bench / "env/bin/pip"), "install", "-e", str(app_link), cwd=bench)
	register_app(bench / "sites/apps.txt")


def _site_has_app(bench: Path, site: str, app: str) -> bool:
	apps = _output("bench", "--site", site, "list-apps", cwd=bench)
	return app in {line.split()[0] for line in apps.splitlines() if line.split()}


def bootstrap(bench: Path, site: str, admin_password: str | None) -> None:
	"""Install, migrate, build and load deterministic non-historical NEXORA 0.1 staging data."""
	_require_staging_site(site)
	_ensure_bench(bench)
	_prepare_app(bench)
	if not _site_has_app(bench, site, "erpnext"):
		raise SystemExit(f"El sitio {site} no tiene ERPNext instalado")
	if not _site_has_app(bench, site, "nexora"):
		_run("bench", "--site", site, "install-app", "nexora", cwd=bench)
	_run("bench", "--site", site, "migrate", cwd=bench)
	_run("bench", "--site", site, "set-config", "nexora_staging", "1", cwd=bench)
	if admin_password:
		_run("bench", "--site", site, "set-admin-password", admin_password, cwd=bench)
	_run("bench", "build", "--app", "nexora", cwd=bench)
	for _ in range(2):
		_run("bench", "--site", site, "execute", "nexora.financial.seeds.seed_demo_data", cwd=bench)
	_run("bench", "--site", site, "execute", "nexora.financial.seeds.assert_staging_health", cwd=bench)
	print(f"NEXORA 0.1 preparada en {site}. Use el comando serve para iniciar el bench.")


def verify(bench: Path, site: str) -> None:
	"""Run static, installation, MariaDB, financial, ledger, concurrency and staging health gates."""
	_require_staging_site(site)
	static_commands = (
		(
			sys.executable,
			"scripts/validate_nexora_governance.py",
			"--expected-main-head",
			"73c9dadfb81f543e53f45887448fdecbee081850",
		),
		(sys.executable, "scripts/validate_nexora_app.py"),
		(sys.executable, "scripts/validate_nexora_financial_models.py"),
		(
			sys.executable,
			"-m",
			"unittest",
			"discover",
			"-s",
			"nexora_app/nexora/tests",
			"-p",
			"test_*contract.py",
			"-v",
		),
		("node", "--check", "nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js"),
		("node", "--check", "nexora_app/nexora/public/js/nexora.js"),
		(sys.executable, "-m", "compileall", "-q", "nexora_app/nexora", "scripts"),
	)
	for command in static_commands:
		_run(*command, cwd=ROOT)
	environment = os.environ.copy()
	environment["PYTHONPATH"] = str(ROOT / "nexora_app")
	_run(
		sys.executable,
		"-m",
		"unittest",
		"nexora.tests.test_financial_core",
		"nexora.tests.test_ledger_core",
		"nexora.tests.test_reference_rules",
		"-v",
		cwd=ROOT,
		env=environment,
	)
	_run("bench", "--site", site, "migrate", cwd=bench)
	for module in (
		"nexora.tests.test_installation",
		"nexora.tests.test_financial_integration",
		"nexora.tests.test_ledger_integration",
	):
		_run("bench", "--site", site, "run-tests", "--app", "nexora", "--module", module, cwd=bench)
	_run("bench", "--site", site, "execute", "nexora.tests.concurrency_probe.run", cwd=bench)
	_run("bench", "--site", site, "execute", "nexora.financial.seeds.assert_staging_health", cwd=bench)
	print(f"NEXORA app y NEXORA financial invariants aprobadas en {site}.")


def serve(bench: Path, site: str) -> None:
	_require_staging_site(site)
	if not bench.is_dir():
		raise SystemExit(f"Bench no encontrado en {bench}")
	os.chdir(bench)
	os.execvp("bench", ["bench", "start"])


def _parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Registrar o preparar NEXORA 0.1 en un sitio Frappe seguro.")
	subparsers = parser.add_subparsers(dest="command", required=True)
	register = subparsers.add_parser("register", help="Registrar nexora en sites/apps.txt")
	register.add_argument("path", type=Path)
	for name in ("bootstrap", "verify", "serve"):
		command = subparsers.add_parser(name)
		command.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
		command.add_argument("--site", default="test_site")
		if name == "bootstrap":
			command.add_argument("--admin-password")
	return parser


def main() -> int:
	# Compatibility with the permanent workflows: register_nexora_app.py sites/apps.txt
	if len(sys.argv) == 2 and sys.argv[1] not in {"register", "bootstrap", "verify", "serve", "-h", "--help"}:
		register_app(Path(sys.argv[1]))
		return 0
	args = _parser().parse_args()
	if args.command == "register":
		register_app(args.path)
	elif args.command == "bootstrap":
		bootstrap(args.bench, args.site, args.admin_password)
	elif args.command == "verify":
		verify(args.bench, args.site)
	elif args.command == "serve":
		serve(args.bench, args.site)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
