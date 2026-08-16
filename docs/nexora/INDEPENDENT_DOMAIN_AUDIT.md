# NEXORA — Auditoría independiente por dominio

**Propósito:** segunda auditoría transversal después de los barridos funcionales previos. No sustituye CI, MariaDB, navegador ni certificación externa.

## Regla de certificación

Un dominio no puede declararse **IMPLEMENTADO Y VALIDADO** por este registro solamente. Requiere código verificable, flujo real, permiso de servidor, auditoría, prueba positiva, prueba negativa, CI y SHA publicado. Las integraciones externas además requieren evidencia real del sistema tercero.

## Estado de la auditoría

| Dominio | Alcance independiente | Evidencia primaria | Estado |
|---|---|---|---|
| Finanzas | Libro Central, NXR Operation Effect, fondos por fuente, correcciones, permisos | `financial/`, `ledger/`, pruebas de invariantes y contrato | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN DE FLUJO COMPLETO |
| Compras | Solicitud→cotización→orden→recepción→compromiso→pago | `purchases/`, puentes financiero/inventario, `test_purchase_*` | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN DE FLUJO COMPLETO |
| Inventario | recepción, movimientos, reversión, saldo negativo, permisos | `inventory/`, pruebas de regresión y contrato | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN DE FLUJO COMPLETO |
| Contratos | contrato→avance→estimación→pago→liquidación | `contracts/`, pruebas de concurrencia y contrato | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN DE FLUJO COMPLETO |
| Cierre | semanal y mensual, snapshot, hash, correcciones | `close/`, cierres canónicos y contratos | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN HUMANA |
| Reportes | FI-01/FI-02/CO-01, filtros, exportaciones, permisos | `reports/`, `dashboard/`, contratos de vistas | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN HUMANA |
| Directorio | entidades globales, datos sensibles, scoping, auditoría | `directory/`, pruebas de permisos y contrato | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN DE FLUJO COMPLETO |
| Evidencias / avance | captura, vínculo, revisión, cronología, exportación | `evidence/`, `progress/`, Context360 | CONFIRMADO EN CÓDIGO / PENDIENTE CERTIFICACIÓN HUMANA |
| Notificaciones | in-app/email/WhatsApp, deduplicación, reintentos, entrega | `notifications/`, contratos de entrega | CONFIRMADO EN CÓDIGO / PENDIENTE DE PRUEBA EXTERNA PARA WHATSAPP |
| Integraciones | SAP, WhatsApp, auditoría de conexiones, reintentos | `integrations/`, `conversation/channels/whatsapp.py` | EXISTENTE PERO NO CERTIFICADO CONTRA TERCEROS REALES |
| UX / PWA | escritorio, tableta, iPhone, PWA, español visible | browser CI, PWA contracts, Spanish audit | EXISTENTE PERO REQUIERE VALIDACIÓN HUMANA |

## Golden paths de segunda auditoría

1. Fuente de fondos → operación → efecto contable → saldo por fuente.
2. Operación → corrección compensatoria → reversión/sustitución → auditoría.
3. Solicitud de compra → cotización → orden aprobada.
4. Orden → recepción → inventario → reversión de recepción.
5. Orden aprobada → compromiso → pago → Libro Central → saldo de fondo.
6. Compra → presupuesto → comprometido → ejecutado → disponible → liberación/reversión.
7. Contrato → avance → estimación → pago → retención → liquidación.
8. Evidencia → proyecto → cronología → reporte/exportación.
9. Buscador universal → resultado → detalle → permiso de proyecto.
10. Cierre mensual → snapshot → hash → estado cerrado → corrección enlazada.
11. Notificación → deduplicación → entrega real → error/reintento → auditoría.
12. WhatsApp/SAP → credencial segura → llamada real → resultado → auditoría/idempotencia.

## Criterio negativo obligatorio

Cada golden path debe contener como mínimo una prueba de rechazo del servidor: permiso insuficiente, período cerrado, saldo insuficiente, transición inválida, duplicidad/idempotencia, documento inexistente, dato obligatorio ausente o error real del tercero, según corresponda.

## Riesgos que siguen abiertos

- Meta/WABA y webhook reales.
- SAP autorizado y credenciales reales.
- Staging/AWS/Coolify con backup y rollback autorizados.
- Operación humana sobre instancia desplegada.

Estos estados no se elevan artificialmente a "IMPLEMENTADO Y VALIDADO" por pruebas estáticas.
