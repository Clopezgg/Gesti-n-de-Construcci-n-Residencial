"""Catálogo declarativo de intenciones conversacionales (Bloque 18, NXR-CNV-0001).

Cada entrada apunta a una función real ya auditada del dominio — nunca
reimplementa una regla de negocio. Añadir una intención nueva nunca implica
escribir una función de negocio nueva: implica declarar qué función real ya
existente se invoca y qué campos necesita ("expandir el catálogo es trabajo
de catálogo, no de arquitectura"). Esta primera versión cubre los siete casos
mínimos de la misión (sección 23): consultar saldo, consultar pagos
pendientes, consultar contrato/entidad, registrar gasto, registrar ingreso,
registrar evidencia y preparar una compra. Sin dependencia de Frappe: las
rutas punteadas se resuelven en ``dispatch.py``.
"""

from __future__ import annotations

from nexora.conversation.core import IntentKind, IntentSpec, Slot

REGISTRY: dict[str, IntentSpec] = {
	spec.key: spec
	for spec in (
		IntentSpec(
			key="query_fund_balance",
			kind=IntentKind.READ,
			description="Consultar cuánto dinero disponible/comprometido/reservado tiene un proyecto",
			slots=(Slot("project", "¿De qué proyecto quieres el saldo?"),),
			read_method="nexora.financial.sources.list_source_balances",
		),
		IntentSpec(
			key="query_pending_payments",
			kind=IntentKind.READ,
			description="Consultar pagos u obligaciones pendientes de un proyecto",
			slots=(Slot("project", "¿De qué proyecto quieres ver los pagos pendientes?"),),
			read_method="nexora.dashboard.snapshot_query.get_executive_snapshot",
		),
		IntentSpec(
			key="query_contract",
			kind=IntentKind.READ,
			description="Consultar contratos por contratista/proveedor o por proyecto",
			slots=(
				Slot("contractor", "¿De qué contratista o proveedor quieres ver los contratos?"),
				Slot("project", "¿De qué proyecto?", required=False),
			),
			read_method="nexora.contracts.service.list_contracts",
		),
		IntentSpec(
			key="register_expense",
			kind=IntentKind.WRITE,
			description="Registrar un gasto o pago operacional (dinero que sale de un proyecto)",
			slots=(
				Slot("project", "¿En qué proyecto?"),
				Slot("beneficiary", "¿A quién se le paga?"),
				Slot("amount_hnl", "¿Por cuánto, en lempiras?"),
				Slot("payment_method", "¿Cómo se pagó (efectivo, transferencia, depósito)?"),
				# Las dos únicas categorías económicas permitidas para un gasto operacional
				# (materiales y mano de obra de construcción) exigen centro de costo —
				# `apply_profile()`/`normalize_analytic_splits()` en financial/catalog.py lo
				# rechazan sin él. Sin este slot, todo gasto por chat quedaba atascado en
				# "Collecting" para siempre: el mensaje de rechazo del servidor nunca se
				# traduce en una pregunta que el usuario pueda responder, porque el catálogo
				# de intenciones no sabe que existe ese campo.
				Slot("cost_center", "¿A qué centro de costo pertenece?"),
				# `financial/core.py::preview_operation()` rechaza el movimiento si sus
				# `allocations` (de qué fuente de fondos concreta sale el dinero) no suman
				# exactamente el importe — un proyecto puede tener más de una fuente activa
				# (NXR-FND-0005), así que no hay una sola fuente que asumir en silencio.
				Slot("source", "¿De qué fuente de fondos sale el dinero?"),
			),
			preview_method="nexora.financial.operational_commands.preview_operational_movement",
			execute_method="nexora.financial.operational_commands.execute_operational_movement",
		),
		IntentSpec(
			key="register_income",
			kind=IntentKind.WRITE,
			description="Registrar una entrada de dinero a un proyecto (remesa, depósito, ingreso)",
			slots=(
				Slot("project", "¿En qué proyecto?"),
				Slot("beneficiary", "¿De quién viene el dinero?"),
				Slot("amount_hnl", "¿Por cuánto, en lempiras?"),
				Slot("payment_method", "¿Por qué canal llegó (remesa, depósito, transferencia)?"),
			),
			preview_method="nexora.financial.operational_commands.preview_operational_movement",
			execute_method="nexora.financial.operational_commands.execute_operational_movement",
		),
		IntentSpec(
			key="register_evidence",
			kind=IntentKind.WRITE,
			description="Guardar un archivo ya subido (foto/factura/comprobante) como evidencia de un proyecto",
			slots=(
				Slot("project", "¿En qué proyecto va esta evidencia?"),
				Slot("file_url", "Adjunta primero el archivo desde la pantalla de evidencia."),
				Slot("evidence_kind", "¿Qué tipo de comprobante es (pago, autorización, otro)?"),
				Slot("channel", "¿Por dónde llegó (WhatsApp, recibo bancario, efectivo, correo)?"),
			),
			preview_method=None,
			execute_method="nexora.financial.evidence.register_evidence",
		),
		IntentSpec(
			key="create_purchase_request",
			kind=IntentKind.NAVIGATE,
			description="Preparar una nueva solicitud de compra de materiales para un proyecto",
			slots=(Slot("project", "¿Para qué proyecto es la compra?"),),
			route="nexora-purchase-requests",
		),
	)
}
