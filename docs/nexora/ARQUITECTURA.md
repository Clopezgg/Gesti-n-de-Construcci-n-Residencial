# NEXORA — Arquitectura ejecutable

## Identidad y límites

- `PRODUCTO_VISIBLE: NEXORA`
- `REPOSITORIO_OFICIAL: Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- `RAMA_TECNICA: nexora-reconstruccion`
- `BASELINE_MAIN_HEAD: 73c9dadfb81f543e53f45887448fdecbee081850`
- `NO_MIGRACION_HISTORICA: true`
- `NO_SEGUNDO_REPOSITORIO: true`
- `NO_SEGUNDO_LEDGER_CANONICO: true`
- ConstruControl permanece intacto como referencia heredada temporal.
- ERPNext/Frappe permanece como motor técnico interno.

## Empaquetado autorizado

NEXORA se implementa como aplicación Frappe separada dentro de `nexora_app/` en este mismo repositorio.
La aplicación declara ERPNext como dependencia, no modifica el paquete `erpnext` para instalarse y no depende de módulos ConstruControl.
La convivencia es temporal: ambos paquetes pueden estar instalados, pero NEXORA no escribe DocTypes `CC *`.

## Fuentes canónicas

| Dimensión | Fuente canónica | Regla |
|---|---|---|
| Fondos disponibles y reservados | `NXR Operation Effect` | Efectos inmutables; asignaciones enlazan cada fuente. |
| Numeración | `NXR Document Sequence` | Secuencia global de 12 dígitos, perpetua y no reutilizable. |
| Inventario | ERPNext `Stock Ledger Entry` | NEXORA no escribe `CC Material Ledger`. |
| Contabilidad general | ERPNext `GL Entry` | Se crea por documento nativo cuando corresponda. |
| Documentos operativos | DocTypes NEXORA y documentos ERPNext enlazados | NEXORA orquesta la transacción. |

## Convención del Libro Central

- Moneda base: HNL; importes con precisión Decimal definida por moneda.
- Un efecto positivo aumenta la dimensión indicada; uno negativo la reduce.
- `available = inflows + proven_returns - executed_outflows - active_reservations`.
- `reserved = commitments_created - commitments_released - commitments_executed`.
- `cost` solo cambia cuando la clasificación económica lo indica; una salida puede reducir fondos sin aumentar costo.
- Una reclasificación cambia dimensiones analíticas, nunca restaura fondos.
- Una devolución real requiere evidencia y puede restaurar solo el importe comprobado.
- La suma de asignaciones de una operación ejecutada debe igualar su importe.

## Atomicidad e idempotencia

1. Validar permiso y payload.
2. Reservar o leer la clave idempotente.
3. Bloquear en orden estable: secuencia, operación/compromiso y fuentes ordenadas por nombre.
4. Recalcular saldos dentro de la transacción.
5. Crear Operation, Allocations, Effects y documentos ERPNext relacionados.
6. Confirmar una sola transacción MariaDB.
7. Ante fallo parcial, lanzar excepción y revertir todos los documentos.
8. La misma clave con el mismo hash devuelve el resultado previo; con otro hash se rechaza.

## Cutover y rollback

- El sitio nuevo se crea fuera de producción.
- Solo se cargan configuración técnica, HNL, país, roles, usuarios administrativos y catálogos indispensables.
- No se copian personas, remesas, contratos, compras, inventario u operaciones históricas.
- Rollback: desinstalar NEXORA del sitio de prueba o descartar el sitio nuevo; el sistema anterior permanece intacto.
