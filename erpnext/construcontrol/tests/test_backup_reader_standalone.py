from __future__ import annotations

import io
import json
import tarfile
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "backup_reader.py"
spec = spec_from_file_location("cc_backup_reader", MODULE_PATH)
assert spec and spec.loader
module = module_from_spec(spec)
spec.loader.exec_module(module)


def _archive(data, member_name: str = "data.sql") -> bytes:
    encoded = json.dumps(data).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
    sql = 'COPY "public"."construction_projects" ("id", "project_name", "owner_name", "data", "created_at", "updated_at") FROM stdin;\n'
    sql += f"p1\tObra\tCarlos\t{encoded}\t2026-01-01\t2026-01-02\n\\.\n"
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        raw = sql.encode()
        info = tarfile.TarInfo(member_name)
        info.size = len(raw)
        archive.addfile(info, io.BytesIO(raw))
    return output.getvalue()


class BackupReaderTest(unittest.TestCase):
    def test_backup_reader_omits_images_storage_locations_and_secrets(self):
        data = {
            "settings": {
                "projectName": "Obra",
                "pinHash": "secret",
                "access_token": "token",
                "service_role_key": "server-secret",
                "client-secret": "client-secret",
            },
            "phases": [],
            "incomes": [
                {
                    "id": "i1",
                    "evidence": [
                        {
                            "id": "e1",
                            "name": "foto.jpg",
                            "type": "image/jpeg",
                            "size": 10,
                            "uploadedAt": "2026-01-01",
                            "dataUrl": "data:image/jpeg;base64,abc",
                            "storagePath": "private/foto.jpg",
                            "storageUrl": "https://example.invalid/foto.jpg",
                        }
                    ],
                }
            ],
            "expenses": [],
        }
        payload, report = module.load_backup_content(_archive(data), "backup.tar.gz")
        snapshot = payload["construction_projects"][0]["data"]
        for key in ("pinHash", "access_token", "service_role_key", "client-secret"):
            self.assertNotIn(key, snapshot["settings"])
        evidence = snapshot["incomes"][0]["evidence"][0]
        for key in ("dataUrl", "storagePath", "storageUrl"):
            self.assertNotIn(key, evidence)
        self.assertTrue(evidence["_file_omitted"])
        self.assertEqual(evidence["name"], "foto.jpg")
        self.assertEqual(report["images_imported"], 0)
        self.assertEqual(report["image_payloads_removed"], 1)
        self.assertEqual(report["storage_locations_removed"], 2)
        self.assertEqual(report["secrets_removed"], 4)

    def test_archive_must_contain_exactly_one_data_sql(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz"):
            pass
        with self.assertRaises(module.BackupFormatError):
            module.load_backup_content(output.getvalue(), "empty.tar.gz")

    def test_nested_member_is_read_without_extracting_to_disk(self):
        payload, report = module.load_backup_content(
            _archive({"settings": {"projectName": "Obra"}, "phases": [], "incomes": [], "expenses": []}, "safe/data.sql"),
            "nested.tar.gz",
        )
        self.assertEqual(payload["construction_projects"][0]["project_id"], "p1")
        self.assertEqual(report["source_kind"], "Supabase Logical Backup")


if __name__ == "__main__":
    unittest.main()
