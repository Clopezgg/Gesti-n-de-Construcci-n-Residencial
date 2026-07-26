# NEXORA — Fase 1: recuperación del producto y experiencia central

## Estado

**EN EJECUCIÓN**

- Rama: `nexora-fase-1-recuperacion-ux`
- Base remota verificada: `3cfeda130b41263a857906040ea8cfdc2b49873b`
- Producción modificada: **NO**
- AWS, Coolify, DNS, secretos y datos modificados: **NO**

## Hallazgos verificados

| ID | Clasificación | Hallazgo | Evidencia | Acción |
|---|---|---|---|---|
| `NXR-F1-UX-0001` | EXISTENTE PERO DEFECTUOSO | El dashboard creaba el filtro Proyecto sin conservar su referencia y después llamaba `controls.project.get_value()`. | `nexora-dashboard.js` anterior al inicio de esta fase. | Corregido mediante una referencia real `projectControl`. |
| `NXR-F1-UX-0002` | EXISTENTE PERO DEFECTUOSO | Las operaciones recientes exponían valores técnicos como `Inflow`, `Outflow` y `Draft`. | Tabla de operaciones recientes del dashboard. | Se añadió presentación operativa en español sin cambiar valores canónicos del backend. |
| `NXR-F1-UX-0003` | NO DEMOSTRADO | El dashboard no ofrecía un recorrido directo y comprobable para registrar ingresos y egresos. | Acciones rápidas anteriores dirigían únicamente al núcleo financiero genérico. | Se añadieron accesos explícitos con contexto de tipo de operación. |
| `NXR-F1-UX-0004` | EXISTENTE PERO DEFECTUOSO | La carga del dashboard no manejaba errores visibles para el usuario. | `loadDashboard()` anterior sin bloque de control de errores. | Se añadió estado de error y mensaje operativo. |
| `NXR-F1-GOV-0001` | EXISTENTE PERO DEFECTUOSO | `EXECUTION_STATE.md` declara ramas y PR abiertos que no coinciden con el estado remoto actual. | La rama `nexora-reconstruccion` no aparece en remoto y `main` está en el merge `3cfeda1`. | Pendiente de normalización dentro de esta fase, sin falsificar continuidad. |

## Bloque funcional 1 — Dashboard operativo

### Requisitos trazables

| ID | Requisito | Estado |
|---|---|---|
| `NXR-F1-DASH-0001` | El dashboard debe cargar con o sin proyecto seleccionado. | IMPLEMENTADO, PENDIENTE DE CI |
| `NXR-F1-DASH-0002` | El cambio de proyecto debe recargar el resumen. | IMPLEMENTADO, PENDIENTE DE CI |
| `NXR-F1-DASH-0003` | Deben existir acciones visibles para registrar ingreso y egreso. | IMPLEMENTADO, PENDIENTE DE CI |
| `NXR-F1-DASH-0004` | Los tipos y estados técnicos deben presentarse en español. | IMPLEMENTADO, PENDIENTE DE CI |
| `NXR-F1-DASH-0005` | Los fallos de carga deben producir una respuesta visible y no un fallo silencioso. | IMPLEMENTADO, PENDIENTE DE CI |
| `NXR-F1-DASH-0006` | El backend y los valores canónicos no deben alterarse por la traducción visual. | IMPLEMENTADO, PENDIENTE DE CI |

## Pruebas añadidas

Pruebas contractuales para verificar:

- conservación de la referencia del filtro Proyecto;
- ausencia del acceso inválido `controls.project.get_value()`;
- acciones directas de ingreso y egreso;
- propagación del tipo de operación mediante `frappe.route_options`;
- traducción de valores técnicos;
- manejo explícito de fallos.

## Criterio de terminado del bloque

El bloque solo podrá clasificarse como **IMPLEMENTADO Y VALIDADO** cuando:

1. las pruebas del repositorio terminen sin fallos;
2. los controles de calidad y seguridad sean aprobados;
3. exista commit publicado y SHA verificable;
4. la interfaz sea validada en un sitio Frappe funcional;
5. no se haya modificado producción sin autorización.

Hasta entonces, la clasificación correcta es **IMPLEMENTADO, PENDIENTE DE CI Y VALIDACIÓN VISUAL**.
