# NEXORA — Estado de correcciones NXR-FIX

Este documento distingue correcciones de código ya implementadas en esta fase de dependencias que requieren infraestructura, credenciales o validación humana real.

Documentación técnica externa usada por el repositorio: https://docs.frappe.io/framework

| ID | Estado en esta fase | Evidencia / siguiente verificación |
|---|---|---|
| NXR-FIX-001 | EN VALIDACIÓN CI | Compras conectadas al compromiso y ejecución financiera canónica; falta integración Frappe/MariaDB end-to-end. |
| NXR-FIX-002 | EN VALIDACIÓN CI | Cierre mensual canónico con snapshot/hash/corrección enlazada; falta runtime y UI certificada. |
| NXR-FIX-003 | EXTERNO PENDIENTE | Código WhatsApp existente; requiere Meta/WABA/webhook/credenciales reales. |
| NXR-FIX-004 | EXTERNO PENDIENTE | Adaptador SAP existente; requiere sistema SAP y credenciales autorizadas. |
| NXR-FIX-005 | PENDIENTE STAGING | Requiere instancia desplegada y validación humana real. |
| NXR-FIX-006 | PENDIENTE AUTORIZACIÓN | Requiere staging/producción AWS/Coolify con respaldo y rollback. |
| NXR-FIX-007 | EN VALIDACIÓN CI | UX técnica y smoke existentes; falta validación humana real. |
| NXR-FIX-008 | EN VALIDACIÓN CI | Cobertura de vocabulario visible existente; requiere barrido final humano. |
| NXR-FIX-009 | EN VALIDACIÓN CI | Buscador universal existente y protegido; falta golden path transversal. |
| NXR-FIX-010 | EN VALIDACIÓN CI | Infraestructura de notificaciones/canales existente; falta certificación transversal. |
| NXR-FIX-011 | EN VALIDACIÓN CI | Evidencias y cámara existentes; falta prueba end-to-end sobre instancia real. |
| NXR-FIX-012 | EN VALIDACIÓN CI | Máquina de estados de compras existente; integración financiera añadida en esta fase. |
| NXR-FIX-013 | EN VALIDACIÓN CI | Recepción→stock bridge añadido; falta integración Frappe/MariaDB. |
| NXR-FIX-014 | EN VALIDACIÓN CI | Compromiso/presupuesto/pago conectado al motor financiero; falta prueba end-to-end. |
| NXR-FIX-015 | PENDIENTE DOCUMENTAL | Normalizar referencias históricas de matriz sin borrar historia. |
| NXR-FIX-016 | PENDIENTE DOCUMENTAL | Separar estado actual de histórico en `EXECUTION_STATE.md`. |
| NXR-FIX-017 | EN VALIDACIÓN CI | Contratos y gates reforzados; el caso NXR-INV-0002 ya se mantiene como regresión histórica. |
| NXR-FIX-018 | PENDIENTE AUDITORÍA | Ejecutar segunda pasada independiente por dominio después de que el bloque CI quede verde. |
| NXR-FIX-019 | EN VALIDACIÓN CI | Añadir/confirmar golden paths transversales después del runtime de compras. |
| NXR-FIX-020 | SIN BLOQUEO | ConstruControl se mantiene únicamente como histórico; no es identidad visible. |
| NXR-FIX-021 | IMPLEMENTADO | `docs/nexora/RELEASE_GATES.md` define gates de salida. |
| NXR-FIX-022 | IMPLEMENTADO | `RELEASE_GATES.md` fija el criterio obligatorio de IMPLEMENTADO Y VALIDADO. |

## Regla

No se cambiará ningún estado a `IMPLEMENTADO Y VALIDADO` por la sola existencia de código o una prueba unitaria. Debe existir evidencia de flujo real, permisos server-side, auditoría/idempotencia cuando corresponda, pruebas positivas y negativas, integración/runtime, documentación, commit fusionado y SHA verificable.
