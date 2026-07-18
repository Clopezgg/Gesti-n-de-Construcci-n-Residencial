from __future__ import annotations
import io
import json
import tarfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "backup_reader.py"
spec = spec_from_file_location("cc_backup_reader", MODULE_PATH)
module = module_from_spec(spec); spec.loader.exec_module(module)


def _archive(data):
    encoded = json.dumps(data).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
    sql = 'COPY "public"."construction_projects" ("id", "project_name", "owner_name", "data", "created_at", "updated_at") FROM stdin;\n'
    sql += f'p1\tObra\tCarlos\t{encoded}\t2026-01-01\t2026-01-02\n\\.\n'
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode="w:gz") as tar:
        raw=sql.encode(); info=tarfile.TarInfo("data.sql"); info.size=len(raw); tar.addfile(info,io.BytesIO(raw))
    return output.getvalue()


class BackupReaderTest(unittest.TestCase):
    def test_backup_reader_omits_images_and_secrets(self):
        data={"settings":{"projectName":"Obra","pinHash":"secret"},"phases":[],"incomes":[{"id":"i1","evidence":[{"id":"e1","name":"foto.jpg","type":"image/jpeg","size":10,"uploadedAt":"2026-01-01","dataUrl":"data:image/jpeg;base64,abc"}]}],"expenses":[]}
        payload,report=module.load_backup_content(_archive(data),"backup.tar.gz")
        snapshot=payload["construction_projects"][0]["data"]
        self.assertNotIn("pinHash", snapshot["settings"])
        evidence=snapshot["incomes"][0]["evidence"][0]
        self.assertNotIn("dataUrl", evidence); self.assertTrue(evidence["_file_omitted"])
        self.assertEqual(evidence["name"],"foto.jpg"); self.assertEqual(report["images_imported"],0)

if __name__ == "__main__":
    unittest.main()
