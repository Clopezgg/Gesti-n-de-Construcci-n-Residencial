from pathlib import Path

path = Path("erpnext/construcontrol/tests/runtime_smoke.py")
source = path.read_text(encoding="utf-8")
source = source.replace(
    "from erpnext.construcontrol.users import (\n",
    "from erpnext.construcontrol.tests.test_runtime_user_context import runtime_user\n"
    "from erpnext.construcontrol.users import (\n",
)
source = source.replace("frappe.set_user(\"Administrator\")", "runtime_user(\"Administrator\")")
path.write_text(source, encoding="utf-8")
