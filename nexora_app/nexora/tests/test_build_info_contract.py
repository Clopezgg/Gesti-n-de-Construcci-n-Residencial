from __future__ import annotations

import pathlib
import unittest

import nexora


class TestBuildInfoContract(unittest.TestCase):
	def test_build_info_endpoint_is_safe_and_whitelisted(self) -> None:
		path = pathlib.Path(nexora.__file__).resolve().parent / "build_info.py"
		self.assertTrue(path.is_file())
		code = path.read_text(encoding="utf-8")
		self.assertIn('@frappe.whitelist(allow_guest=True, methods=["GET"])', code)
		self.assertIn('"product": "NEXORA"', code)
		self.assertIn('os.environ.get("NEXORA_BUILD_SHA")', code)
		self.assertIn('os.environ.get("NEXORA_ENVIRONMENT")', code)
		for forbidden in ("ADMIN_PASSWORD", "DB_PASSWORD", "FRAPPE_ENCRYPTION_KEY"):
			self.assertNotIn(forbidden, code)


if __name__ == "__main__":
	unittest.main()
