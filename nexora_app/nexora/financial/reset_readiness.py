"""Solo lectura: cuenta registros reales por DocType para el runbook de
inicialización/reset (``docs/nexora/RUNBOOK_INICIALIZACION_RESET_ENTORNO.md``).

Ninguna función de este módulo borra, escribe ni modifica nada — cada una es
`frappe.db.count`/`frappe.get_all` puro. Seguro de ejecutar contra un sitio
real, incluida producción, en cualquier momento: es exactamente el "conteo
previo"/"conteo posterior" que el runbook exige antes y después de cualquier
reset real, y no requiere que ese reset se haya decidido siquiera.

La clasificación de qué DocType es "histórico de negocio" frente a
"configuración a conservar" es una decisión de producto, no una decisión
técnica unilateral — ver el runbook para el razonamiento completo detrás de
cada categoría.
"""

from __future__ import annotations

from typing import Any

import frappe

# Registros transaccionales reales: lo que un lanzamiento limpio de
# producción debe empezar en cero. Excluye explícitamente tablas hijas
# (`istable: 1`) — se cuentan a través de su documento padre real, contarlas
# aparte duplicaría el mismo hecho de negocio dos veces.
TRANSACTIONAL_BUSINESS_DOCTYPES = (
	"NXR Operation",
	"NXR Operation Effect",
	"NXR Operation Metadata",
	"NXR Fund Source",
	"NXR Fund Allocation",
	"NXR Contract",
	"NXR Contract Amendment",
	"NXR Contract Estimate",
	"NXR Contract Transaction",
	"NXR Commitment",
	"NXR Budget",
	"NXR Purchase Request",
	"NXR Purchase Order",
	"NXR Goods Receipt",
	"NXR Supplier Quotation",
	"NXR Stock Transaction",
	"NXR Quality Check",
	"NXR Progress Record",
	"NXR Evidence",
	"NXR Weekly Close",
	"NXR Monthly Close",
	"NXR Remittance",
	"NXR Saved Report",
)

# Datos maestros: probablemente deben sobrevivir a un reset (describen
# entidades del mundo real — proveedores, bodegas, cuentas — no eventos
# fechados), pero la decisión final es del propietario del producto, no de
# este módulo. Ver la sección "Requiere decisión" del runbook.
MASTER_DATA_REQUIRES_DECISION = (
	"NXR Entity",
	"NXR Entity Compliance",
	"NXR Entity Consolidation",
	"NXR Entity Role",
	"NXR Warehouse",
	"NXR Financial Account",
	"NXR Contractor Profile",
	"NXR Supplier Profile",
)

# Bitácora/sistema: referencian los registros de negocio de arriba. Si se
# limpian los registros de negocio sin tocar esto, la bitácora queda
# apuntando a documentos que ya no existen — decisión de producto, no
# técnica (¿se conserva como evidencia del propio reset, o se limpia junto
# con lo que documenta?).
AUDIT_AND_SYSTEM_LOG_DOCTYPES = (
	"NXR Audit Event",
	"NXR AI Usage Event",
	"NXR Idempotency Record",
	"NXR Document Sequence",
	"NXR Notification",
	"NXR Conversation",
	"NXR Conversation Message",
	"NXR Conversation Pending Intent",
	"NXR Channel Message",
)

# Configuración — nunca datos históricos. Un reset de negocio no debe pedir
# reconfigurar cómo se conecta el sistema a SAP, WhatsApp o un proveedor de
# IA.
CONFIGURATION_DOCTYPES_NEVER_PURGED = (
	"NXR AI Provider",
	"NXR AI Provider Credential",
	"NXR Channel Account",
	"NXR Channel Credential",
	"NXR Integration",
	"NXR SAP Connection",
	"NXR SAP Field Mapping",
)

# Catálogos técnicos sembrados por `seed_analytic_catalogs()` — nunca datos
# históricos, y una app recién instalada los necesita para funcionar.
TECHNICAL_CATALOG_DOCTYPES = (
	"NXR Economic Category",
	"NXR Operation Type",
)


def _counts(doctypes: tuple[str, ...]) -> dict[str, int]:
	return {doctype: frappe.db.count(doctype) for doctype in doctypes}


def count_business_records() -> dict[str, Any]:
	"""`bench --site <site> execute nexora.financial.reset_readiness.count_business_records`

	Conteo real, de solo lectura, de cada categoría — el "conteo previo"/
	"conteo posterior" que el runbook de reset exige. No decide nada por su
	cuenta: reporta lo que hay."""
	transactional = _counts(TRANSACTIONAL_BUSINESS_DOCTYPES)
	master_data = _counts(MASTER_DATA_REQUIRES_DECISION)
	audit_and_logs = _counts(AUDIT_AND_SYSTEM_LOG_DOCTYPES)
	configuration = _counts(CONFIGURATION_DOCTYPES_NEVER_PURGED)
	technical_catalogs = _counts(TECHNICAL_CATALOG_DOCTYPES)
	return {
		"transactional_business_records": transactional,
		"transactional_business_records_total": sum(transactional.values()),
		"master_data_requires_decision": master_data,
		"audit_and_system_logs": audit_and_logs,
		"configuration_never_purged": configuration,
		"technical_catalogs_never_purged": technical_catalogs,
		"users_total": frappe.db.count("User", {"user_type": "System User"}),
	}
