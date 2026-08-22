# NEXORA — Bloque Fondo Central y Entrada Guiada de Contratación

Estado al iniciar: PROPUESTO/EN EJECUCIÓN.

## Decisión operativa

El dinero recibido pertenece a la fuente financiera/remesa y entra a Caja Central. El Proyecto es una dimensión analítica del gasto y no una cuenta con saldo propio.

## Cambios de código de este bloque

- `NXR Fund Source.project` deja de ser obligatorio.
- `NXR Remittance.project` deja de ser obligatorio.
- Una remesa nueva crea una sola fuente financiera central y conserva el documento padre y su trazabilidad.
- `NXR Operation.project` y `NXR Operation Effect.project` son opcionales a nivel de almacenamiento; los servicios exigen proyecto en operaciones donde el destino analítico lo requiere.
- El selector financiero muestra fuentes del proyecto y también fuentes de Caja Central para ejecutar gastos.
- El alta de ingreso/fuente rápida deja de pedir proyecto.
- La pantalla de contratistas añade `Nueva contratación`, una entrada guiada que reutiliza `NXR Contractor Profile` y `NXR Contract` existentes.
- Las fuentes centrales pueden financiar contratos; el proyecto continúa siendo obligatorio en el contrato.

## Migración de registros existentes

No se ejecuta automáticamente. `scripts/nexora_central_fund_migration.py` solo audita el inventario y permanece en modo no destructivo. La migración real requiere respaldo verificable, rollback y revisión de cada referencia antes de aplicar cambios.

## Criterio de terminación

Código publicado, pruebas positivas y negativas, regresión de remesas/operaciones/contratos, documentación y SHA verificable. La migración de datos reales es un paso separado y bloqueado hasta contar con acceso al entorno y respaldo.
