from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
VERIFY = ROOT / "scripts" / "verify_backup_manifest.py"
DEMO = ROOT / "erpnext" / "construcontrol" / "demo_data.py"
COMPOSE = ROOT / "docker-compose.yml"
BACKUP = ROOT / "deploy" / "coolify" / "backup-now.sh"
RESTORE = ROOT / "deploy" / "coolify" / "restore-verify.sh"
RESTORE_PROBE = ROOT / "erpnext" / "construcontrol" / "migration" / "restore_verification.py"
INIT_SITE = ROOT / "deploy" / "coolify" / "init-site.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "construcontrol-full-certification.yml"
DOCKERFILE = ROOT / "Dockerfile"
NGINX_TEMPLATE = ROOT / "deploy" / "coolify" / "nginx-template.conf"
BROWSER_COMPOSE = ROOT / "deploy" / "ci" / "docker-compose.browser.yml"


def load_module(path: Path, name: str):
	spec = importlib.util.spec_from_file_location(name, path)
	assert spec and spec.loader
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class InfrastructureContractTest(unittest.TestCase):
	def test_backup_manifest_verifies_size_hash_and_complete_set(self) -> None:
		module = load_module(VERIFY, "cc_verify_backup_test")
		with tempfile.TemporaryDirectory() as temporary:
			directory = Path(temporary)
			names = (
				"backup-database.sql.gz",
				"backup-files.tar",
				"backup-private-files.tar",
				"backup-site_config_backup.json",
			)
			rows = []
			for index, name in enumerate(names, start=1):
				path = directory / name
				path.write_bytes((name * index).encode())
				rows.append(
					{
						"name": name,
						"bytes": path.stat().st_size,
						"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
					}
				)
			manifest = directory / "backup-manifest.json"
			manifest.write_text(
				json.dumps(
					{
						"format": "construcontrol-local-backup-v1",
						"site": "construcontrol",
						"files": rows,
					}
				),
				encoding="utf-8",
			)
			result = module.verify_manifest(manifest)
			self.assertEqual(result["status"], "verified")
			self.assertEqual(
				set(result["categories"]),
				{"database", "public_files", "private_files", "site_config"},
			)
			(directory / names[0]).write_bytes(b"tampered")
			with self.assertRaises(RuntimeError):
				module.verify_manifest(manifest)

	def test_demo_classifier_is_inventory_only(self) -> None:
		fake = types.ModuleType("frappe")
		fake._ = lambda value: value
		fake.whitelist = lambda function=None: function if function else (lambda fn: fn)
		fake.PermissionError = PermissionError
		access = types.ModuleType("erpnext.construcontrol.access")
		access.require_construcontrol_access = lambda: None
		previous = {name: sys.modules.get(name) for name in ("frappe", "erpnext.construcontrol.access")}
		sys.modules["frappe"] = fake
		sys.modules["erpnext.construcontrol.access"] = access
		try:
			module = load_module(DEMO, "cc_demo_data_test")
			self.assertEqual(module.classify_demo_label("Sample Company"), (True, "name-pattern"))
			self.assertEqual(module.classify_demo_label("Casa López"), (False, "not-demo"))
			source = DEMO.read_text(encoding="utf-8")
			self.assertIn('"destructive_action_performed": False', source)
			self.assertNotIn(".delete(", source)
		finally:
			for name, value in previous.items():
				if value is None:
					sys.modules.pop(name, None)
				else:
					sys.modules[name] = value

	def test_compose_has_one_canonical_private_architecture(self) -> None:
		payload = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
		services = payload["services"]
		expected = {
			"mariadb",
			"redis-cache",
			"redis-queue",
			"backend",
			"websocket",
			"queue-short",
			"queue-long",
			"scheduler",
			"frontend",
			"backup",
		}
		self.assertEqual(set(services), expected)
		for name in expected:
			self.assertIn("healthcheck", services[name], name)
		self.assertNotIn("ports", services["mariadb"])
		self.assertNotIn("ports", services["redis-cache"])
		self.assertNotIn("ports", services["redis-queue"])
		self.assertEqual(payload["x-app-image"]["platform"], "linux/amd64")
		rendered = COMPOSE.read_text(encoding="utf-8")
		self.assertNotIn("SUPABASE_BACKUP_BUCKET", rendered)
		self.assertNotIn("render.com", rendered.lower())
		self.assertNotIn("oracle", rendered.lower())

	def test_backup_and_restore_are_fail_closed(self) -> None:
		backup = BACKUP.read_text(encoding="utf-8")
		restore = RESTORE.read_text(encoding="utf-8")
		probe = RESTORE_PROBE.read_text(encoding="utf-8")
		self.assertIn("verify_backup_manifest.py", backup)
		self.assertNotIn("upload_backup_set.py", backup)
		self.assertIn('if [[ "$test_site" == "$SITE_NAME" ]]', restore)
		self.assertIn("for migration in 1 2 3", restore)
		self.assertIn("runtime_smoke.run", restore)
		self.assertIn("restore runtime smoke start", restore)
		self.assertIn("restore runtime smoke failed", restore)
		self.assertIn("restore count reconciliation start", restore)
		self.assertIn("source_counts", restore)
		self.assertIn("restored_counts", restore)
		self.assertIn("mismatches", restore)
		self.assertIn("Restore count reconciliation failed", restore)
		self.assertIn("count_reconciliation=passed", restore)
		self.assertIn(
			"erpnext.construcontrol.migration.restore_verification.count_records",
			restore,
		)
		self.assertIn('"--kwargs"', restore)
		self.assertIn("json.loads(lines[-1])", restore)
		self.assertIn("No restore count result", restore)
		self.assertNotIn("expression =", restore)
		self.assertNotIn("frappe.client.get_count", restore)
		self.assertIn("def count_records", probe)
		self.assertIn("frappe.db.count", probe)

	def test_websocket_proxy_synthesizes_external_origin_and_preserves_host(self) -> None:
		template = NGINX_TEMPLATE.read_text(encoding="utf-8")
		dockerfile = DOCKERFILE.read_text(encoding="utf-8")
		self.assertIn("proxy_set_header Origin $proxy_x_forwarded_proto://$http_host;", template)
		self.assertEqual(template.count("proxy_set_header Host $http_host;"), 2)
		self.assertNotIn("proxy_set_header Host $host;", template)
		self.assertNotIn("proxy_set_header Origin $http_origin;", template)
		self.assertNotIn(
			"proxy_set_header Origin $proxy_x_forwarded_proto://${FRAPPE_SITE_NAME_HEADER};",
			template,
		)
		self.assertIn(
			"COPY deploy/coolify/nginx-template.conf /templates/nginx/frappe.conf.template",
			dockerfile,
		)

	def test_ci_hostname_resolves_to_the_same_frontend_outside_and_inside_docker(self) -> None:
		override = yaml.safe_load(BROWSER_COMPOSE.read_text(encoding="utf-8"))
		aliases = override["services"]["frontend"]["networks"]["default"]["aliases"]
		self.assertEqual(aliases, ["construcontrol-ci.test"])
		source = WORKFLOW.read_text(encoding="utf-8")
		self.assertEqual(source.count("FRAPPE_EXTERNAL_URL=http://construcontrol-ci.test:8080"), 2)
		self.assertEqual(source.count("CONSTRUCONTROL_BASE_URL=http://construcontrol-ci.test:8080"), 2)
		self.assertEqual(source.count('echo "127.0.0.1 construcontrol-ci.test"'), 2)
		self.assertEqual(source.count("getent hosts construcontrol-ci.test"), 2)
		self.assertNotIn("FRAPPE_EXTERNAL_URL=http://localhost:8080", source)

	def test_site_initialization_fails_closed_until_setup_is_complete(self) -> None:
		source = INIT_SITE.read_text(encoding="utf-8")
		setup_command = (
			'bench --site "$SITE_NAME" execute '
			"erpnext.construcontrol.install_entrypoint.ensure_setup_complete"
		)
		self.assertIn(setup_command, source)
		self.assertIn("[ConstruControl] step setup-complete start", source)
		self.assertIn("[ConstruControl] step setup-complete ok", source)
		self.assertLess(source.index(setup_command), source.index('bench use "$SITE_NAME"'))

	def test_certification_pipeline_is_sequential(self) -> None:
		workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
		jobs = workflow["jobs"]
		self.assertEqual(jobs["linters"]["needs"], "semantic")
		self.assertEqual(jobs["semgrep"]["needs"], "linters")
		self.assertEqual(jobs["freeze"]["needs"], "semgrep")
		self.assertIn("gate-a", jobs)
		self.assertEqual(jobs["gate-a"]["needs"], "freeze")
		self.assertNotIn("strategy", jobs["gate-a"])
		self.assertEqual(jobs["gate-b"]["needs"], "gate-a")
		self.assertEqual(jobs["gate-c"]["needs"], "gate-b")
		self.assertEqual(jobs["final"]["needs"], "gate-c")
		self.assertEqual(jobs["audit-1-to-1"]["needs"], "final")
		source = WORKFLOW.read_text(encoding="utf-8")
		for step in ("A1 ·", "A2 ·", "A3 ·", "A4 ·"):
			self.assertIn(step, source)
		self.assertIn("certify_acceptance_receipts.py", source)
		self.assertIn("MATRIZ_ACEPTACION_1A1_CERTIFICADA.md", source)
		self.assertIn('pattern: "*-${{ env.CERT_SHA }}"', source)
		self.assertNotIn("continue-on-error", source)
		self.assertNotIn("skip-ci", source.lower())


if __name__ == "__main__":
	unittest.main()
