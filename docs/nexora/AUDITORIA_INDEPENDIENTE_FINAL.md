# NEXORA — Auditoría independiente por dominio

## Objetivo

Segunda pasada independiente sobre las fronteras del producto, separada de las auditorías mecánicas de permisos e idempotencia del Bloque 44.

## Resultado

| Dominio | Cobertura | Resultado provisional | Bloqueador |
|---|---|---|---|
| Finanzas / Libro Central | Fuentes, efectos, compromisos, correcciones, locks, idempotencia | Sólido; no reabrir arquitectura | No |
| Compras | Solicitud, cotización, orden, recepción y nuevos puentes financieros | Corregido en esta fase; requiere runtime MariaDB | Sí, hasta CI verde |
| Inventario | Kardex, saldo, negativo, recepción y reversión | Corregido; recepción y reversión añadidas | Sí, hasta CI verde |
| Contratos | Contrato, adendas, anticipos, pagos, retenciones, liquidación, concurrencia | Evidencia fuerte ya existente | No |
| Directorio / Entidades | Canonicalidad, permisos, búsqueda, compliance | Evidencia fuerte ya existente | No |
| Reportes | FI01/FI02/CO01, filtros, PDF/Excel, historial | Evidencia fuerte; filtro FI02 se regresionó y se endureció el contrato | Sí, hasta CI verde |
| Cierre | Semanal certificado; mensual añadido en esta fase | Mensual requiere runtime/UI y verificación histórica | Sí |
| Evidencias / Avance | Evidencia, revisión, fotografías, avance | Infraestructura existente; requiere golden-path real | Media |
| Notificaciones | In-app/email/WhatsApp delivery bookkeeping | Contratos de entrega existentes | Media |
| UX / PWA | escritorio, tableta, iPhone WebKit, PWA, accesibilidad | Smoke permanente; validación humana queda pendiente | Alta para release |
| WhatsApp | Graph API, webhook, deduplicación, auditoría | Código real; activación externa pendiente | Externo |
| SAP | Adaptador, auth, idempotencia, auditoría | Código real; llamada real pendiente | Externo |
| Seguridad | server-side permissions, service-write, no deletion | Auditorías existentes y CI permanente | No |
| Gobernanza | matriz, estados, gates, inventario, decisiones | Gates añadidos; CI debe quedar verde | Sí |

## Regla de evidencia

Este registro no marca ninguna dependencia externa como terminada por la existencia de código. WhatsApp y SAP permanecen pendientes hasta que exista una llamada real autorizada y evidencia positiva/negativa.

## Siguiente pasada

Después del CI verde del bloque de correcciones: ejecutar golden paths cruzados y revisar la matriz de requisitos contra el HEAD fusionado, sin declarar estados históricos como actuales.
