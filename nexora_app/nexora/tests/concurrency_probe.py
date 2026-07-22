from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import frappe

from nexora.financial.operations import execute_financial_operation
from nexora.financial.sources import create_fund_source, list_source_balances


def _ensure_user(email: str, role: str) -> str:
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype":"User","email":email,"first_name":email.split("@",1)[0],"enabled":1,"send_welcome_email":0,"roles":[{"role":role}]}).insert(ignore_permissions=True)
    return email


def run() -> dict[str, object]:
    marker=uuid.uuid4().hex[:12]; project="_Test Project"
    requester=_ensure_user(f"nxr-conc-requester-{marker}@example.test","NEXORA Finance Operator")
    executor=_ensure_user(f"nxr-conc-executor-{marker}@example.test","NEXORA Finance Operator")
    manager=_ensure_user(f"nxr-conc-manager-{marker}@example.test","NEXORA Finance Manager")
    frappe.set_user(executor)
    source=create_fund_source({"idempotency_key":f"conc-source-{marker}","source_name":f"Fuente concurrencia {marker}","channel":"Remittance","project":project,"currency":"HNL","original_amount":1000,"exchange_rate":1,"origin_or_sender":"Probe concurrencia","custodian":executor})["fund_source"]
    frappe.db.commit()
    site=frappe.local.site; sites_path=frappe.local.sites_path; barrier=threading.Barrier(2)

    def worker(suffix: str) -> str:
        frappe.init(site=site,sites_path=sites_path); frappe.connect(); frappe.set_user(executor)
        try:
            barrier.wait(timeout=20)
            execute_financial_operation({"idempotency_key":f"conc-{marker}-{suffix}","operation_type":"Outflow","project":project,"amount_hnl":700,"allocations":[{"source":source,"amount_hnl":700}],"requester":requester,"approved_by":manager})
            frappe.db.commit(); return "executed"
        except Exception as exc:
            frappe.db.rollback()
            return "denied_insufficient" if "disponible suficiente" in str(exc) else f"unexpected:{type(exc).__name__}:{exc}"
        finally:
            frappe.destroy()

    with ThreadPoolExecutor(max_workers=2) as pool: results=sorted(pool.map(worker,("a","b")))
    frappe.set_user(executor); balance=next(row for row in list_source_balances(project) if row["source"]==source)
    if results != ["denied_insufficient","executed"] or balance["balance_hnl"] != "300.00": raise AssertionError({"results":results,"balance":balance})
    return {"ok":True,"results":results,"balance":balance}
