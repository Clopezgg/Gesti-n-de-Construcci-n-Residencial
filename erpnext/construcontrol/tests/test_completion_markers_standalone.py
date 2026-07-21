from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "scripts" / "validation_markers.py"


def load_helper():
	spec = importlib.util.spec_from_file_location("cc_validation_markers", HELPER)
	module = importlib.util.module_from_spec(spec)
	assert spec and spec.loader
	spec.loader.exec_module(module)
	return module


class CompletionMarkersTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		cls.helper = load_helper()

	def _write(self, suffix: str, content: str) -> Path:
		handle = tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False)
		with handle:
			handle.write(content)
		self.addCleanup(Path(handle.name).unlink, missing_ok=True)
		return Path(handle.name)

	def test_frappe_todo_identifier_is_not_pending_work(self) -> None:
		path = self._write(".py", 'frappe.get_doc({"doctype": "ToDo", "description": "marker"})\n')
		self.assertFalse(self.helper.unresolved_implementation_marker(path))

	def test_real_python_comment_marker_is_detected(self) -> None:
		path = self._write(".py", "# TODO: implement the missing operation\nvalue = 1\n")
		self.assertTrue(self.helper.unresolved_implementation_marker(path))

	def test_non_python_marker_is_detected(self) -> None:
		path = self._write(".js", "// FIXME: replace placeholder\n")
		self.assertTrue(self.helper.unresolved_implementation_marker(path))


if __name__ == "__main__":
	unittest.main()
