# NEXORA — Release Gates

Estado: ACTIVO
Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
Rama de publicación: `main`
HEAD de referencia al iniciar esta fase: `a6fb8553481a1df4e0b01abd2a42914a4f18a140`

## Regla principal

NEXORA no se declara listo para operación empresarial real hasta que todos los gates obligatorios estén cerrados con evidencia verificable.

## Gates obligatorios

| ID | Gate | Criterio de cierre | Estado inicial |
|---|---|---|---|
| RG-001 | Integridad documental | `EXECUTION_STATE`, matriz y esta puerta reflejan HEAD y siguiente acción reales | PENDIENTE |
| RG-002 | Compras financieras | Solicitud→cotización→orden→compromiso→recepción→pago→Libro Central→saldo/compromiso, con rollback e idempotencia | PENDIENTE |
| RG-003 | Cierre mensual | Snapshot histórico, presupuesto, reservas, obligaciones, evidencias, hash, inmutabilidad y corrección enlazada | PENDIENTE |
| RG-004 | Inventario integrado | Recepción de compra actualiza el inventario canónico y una salida posterior respeta el saldo real | PENDIENTE |
| RG-005 | Presupuesto integrado | Presupuesto→compromiso→ejecución→liberación queda conciliado con compras y pagos | PENDIENTE |
| RG-006 | Auditoría independiente | Auditorías por finanzas, compras, inventario, contratos, directorio, reportes, cierre, integraciones y UX | PENDIENTE |
| RG-007 | Golden paths | Flujos críticos positivos y negativos probados desde interfaz/API hasta persistencia y efectos | PENDIENTE |
| RG-008 | UX real | Validación humana real en escritorio, iPhone y PWA sobre una instancia desplegada | PENDIENTE |
| RG-009 | WhatsApp | Llamada real Meta Graph API, webhook real, deduplicación y prueba bidireccional | PENDIENTE EXTERNO |
| RG-010 | SAP | Llamada real contra SAP autorizado con auth, mapping, idempotencia y errores | PENDIENTE EXTERNO |
| RG-011 | Staging | AWS/Coolify, backup verificable, rollback, health checks y observabilidad | PENDIENTE |
| RG-012 | Producción | Cutover autorizado, validación posterior y rollback probado | PENDIENTE / AUTORIZACIÓN REQUERIDA |

## Criterio de IMPLEMENTADO Y VALIDADO

Un requisito solo puede utilizar ese estado cuando existe evidencia de:

1. código real conectado al flujo que lo ejecuta;
2. modelo de datos correcto;
3. permiso server-side;
4. auditoría e idempotencia cuando corresponda;
5. pruebas positivas y negativas;
6. prueba de integración o runtime real cuando el requisito dependa de Frappe/MariaDB/servicio externo;
7. documentación trazable;
8. commit publicado y SHA completo;
9. ausencia de regresión en los gates relacionados.

La existencia de una función, un test unitario o una pantalla aislada no certifica el requisito.

## Dependencias externas

WhatsApp, SAP, AWS, Coolify, DNS, secretos y producción quedan fuera del alcance de modificación automática mientras no exista la autorización y evidencia operacional exigidas por `AGENTS.md` y la arquitectura NEXORA.
