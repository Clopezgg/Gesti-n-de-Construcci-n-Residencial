
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document
from nexora.contracts.core import AMENDMENT_TRANSITIONS, assert_transition, money
from nexora.financial.context import require_service_write
from nexora.financial.model_utils import validate_document_number

class NXRContractAmendment(Document):
    def before_insert(self) -> None: require_service_write()
    def before_save(self) -> None: require_service_write()
    def validate(self) -> None:
        validate_document_number(self.document_number)
        if self.status not in AMENDMENT_TRANSITIONS: frappe.throw(_("Estado de adenda desconocido."))
        if self.amendment_type in {"Increase", "Reduction"} and not (money(self.labor_delta) or money(self.material_delta)):
            frappe.throw(_("La adenda económica requiere una variación."))
        if not self.is_new() and (previous := self.get_doc_before_save()):
            try: assert_transition(str(previous.status), str(self.status), AMENDMENT_TRANSITIONS)
            except ValueError as exc: frappe.throw(_(str(exc)))
            if previous.status in {"Active","Superseded","Cancelled Before Active"}:
                immutable=("contract","version","amendment_type","effective_date","labor_delta","material_delta","new_end_date","scope_change","reason","evidence","idempotency_key","payload_hash")
                if any(self.get(field) != previous.get(field) for field in immutable): frappe.throw(_("La adenda aplicada es inmutable."))
    def on_trash(self) -> None: frappe.throw(_("Las adendas no se eliminan."))
