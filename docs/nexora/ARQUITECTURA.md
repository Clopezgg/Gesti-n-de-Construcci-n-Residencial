# NEXORA — Arquitectura ejecutable

## Identidad y límites

- `PRODUCTO_VISIBLE: NEXORA`
- `REPOSITORIO_OFICIAL: Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- `RAMA_FINAL: main`
- `NO_MIGRACION_HISTORICA: true`
- `NO_SEGUNDO_REPOSITORIO: true`
- `NO_SEGUNDO_LEDGER_CANONICO: true`
- ConstruControl queda únicamente como referencia heredada; no es producto, navegación ni identidad visible.
- Frappe/ERPNext son **plataforma técnica interna**, no producto, marca, navegación ni experiencia de usuario.
- Ningún usuario ordinario debe percibir NEXORA como ERPNext/Frappe ni operar desde su interfaz técnica.

## Empaquetado autorizado

NEXORA se implementa como aplicación propia dentro de `nexora_app/` en este mismo repositorio.
La plataforma Frappe/ERPNext puede permanecer internamente cuando reduzca riesgo y evite duplicar capacidades técnicas, pero sus nombres, DocTypes, rutas y detalles de implementación no forman parte de la identidad funcional de NEXORA.

No se elimina Frappe/ERPNext por sustitución cosmética: cualquier capacidad interna que se conserve debe tener una frontera explícita detrás de servicios NEXORA y pruebas que protejan el dominio. No se permite crear un segundo sistema paralelo para reemplazarlo parcialmente.

## Fuentes canónicas

| Dimensión | Fuente canónica | Regla |
|---|---|---|
| Fondos disponibles y reservados | `NXR Operation Effect` | Efectos inmutables; asignaciones enlazan cada fuente. |
| Numeración | `NXR Document Sequence` | Secuencia global de 12 dígitos, perpetua y no reutilizable. |
| Inventario | ERPNext `Stock Ledger Entry` como infraestructura interna | NEXORA no crea un segundo ledger de inventario. |
| Contabilidad general | ERPNext `GL Entry` como infraestructura interna | Solo cuando el documento NEXORA realmente requiera asiento contable. |
| Documentos operativos | DocTypes NEXORA y adaptadores internos | NEXORA orquesta la transacción; la plataforma no define la experiencia. |

## Convención del Libro Central

- Moneda base: HNL; importes con precisión Decimal definida por moneda.
- Un efecto positivo aumenta la dimensión indicada; uno negativo la reduce.
- La entrada de fondos se presenta al usuario como **registro de fondos/remesa/fuente**, nunca como módulo de ingresos.
- El efecto interno `Received` permanece únicamente como semántica contable/auditiva del fondo para conservar trazabilidad e integridad.
- `available = received_fund_effects + proven_returns - executed_outflows - active_reservations`.
- `reserved = commitments_created - commitments_released - commitments_executed`.
- `cost` solo cambia cuando la clasificación económica lo indica; una salida puede reducir fondos sin aumentar costo.
- Una reclasificación cambia dimensiones analíticas, nunca restaura fondos.
- Una devolución real requiere evidencia y puede restaurar solo el importe comprobado.
- La suma de asignaciones de una operación ejecutada debe igualar su importe.

## Integraciones externas

### WhatsApp Business

WhatsApp Business Cloud API es un canal externo de NEXORA. El código del canal realiza llamadas reales contra Graph API, procesa webhooks, deduplica mensajes y registra estados. La certificación productiva depende de que el entorno tenga credenciales Meta válidas, número/WABA configurados y webhook verificado; nunca se fabricará una prueba de éxito sin una llamada real.

### SAP

SAP es un sistema externo, nunca la base de identidad de NEXORA. La integración debe vivir detrás de un adaptador NEXORA y soportar únicamente el contrato SAP realmente configurado en el entorno. No se asumirá una variante concreta de SAP, endpoint, tenant ni credencial que no estén disponibles. Una integración SAP solo podrá declararse **IMPLEMENTADA Y VALIDADA** después de una llamada real contra el sistema SAP autorizado y pruebas positivas/negativas de autenticación, idempotencia, errores y mapeo.

## Atomicidad e idempotencia

1. Validar permiso y payload.
2. Reservar o leer la clave idempotente.
3. Bloquear en orden estable: secuencia, operación/compromiso y fuentes ordenadas por nombre.
4. Recalcular saldos dentro de la transacción.
5. Crear Operation, Allocations, Effects y documentos internos relacionados.
6. Confirmar una sola transacción MariaDB.
7. Ante fallo parcial, lanzar excepción y revertir todos los documentos.
8. La misma clave con el mismo hash devuelve el resultado previo; con otro hash se rechaza.

## Cutover y rollback

- El sitio nuevo se crea fuera de producción.
- Solo se cargan configuración técnica, HNL, país, roles, usuarios administrativos y catálogos indispensables.
- No se copian personas, remesas, contratos, compras, inventario u operaciones históricas.
- Rollback: desinstalar NEXORA del sitio de prueba o descartar el sitio nuevo; el sistema anterior permanece intacto.
- No se modifican AWS, Coolify, DNS, secretos, volúmenes ni producción durante esta corrección sin autorización específica y respaldo verificable.
