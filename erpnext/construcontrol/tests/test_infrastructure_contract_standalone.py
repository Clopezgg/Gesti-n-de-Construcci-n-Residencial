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
WORKFLOW = ROOT / ".github" / "workflows" / "construcontrol-full-certification.yml"


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
        previous = {
            name: sys.modules.get(name)
            for name in ("frappe", "erpnext.construcontrol.access")
        }
        sys.modules["frappe"] = fake
        sys.modules["erpnext.construcontrol.access"] = access
        try:
            module = load_module(DEMO, "cc_demo_data_test")
            self.assertEqual(
                module.classify_demo_label("Sample Company"), (True, "name-pattern")
            )
            self.assertEqual(
                module.classify_demo_label("Casa López"), (False, "not-demo")
            )
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
        self.assertIn("verify_backup_manifest.py", backup)
        self.assertNotIn("upload_backup_set.py", backup)
        self.assertIn('if [[ "$test_site" == "$SITE_NAME" ]]', restore)
        self.assertIn("for migration in 1 2 3", restore)
        self.assertIn("runtime_smoke.run", restore)

    def test_certification_pipeline_is_sequential(self) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        jobs = workflow["jobs"]
        self.assertIn("gate-a", jobs)
        self.assertEqual(jobs["gate-b"]["needs"], "gate-a")
        self.assertEqual(jobs["gate-c"]["needs"], "gate-b")
        self.assertEqual(jobs["final"]["needs"], "gate-c")
        self.assertEqual(jobs["audit-1-to-1"]["needs"], "final")
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error", source)
        self.assertNotIn("skip-ci", source.lower())


if __name__ == "__main__":
    unittest.main()
