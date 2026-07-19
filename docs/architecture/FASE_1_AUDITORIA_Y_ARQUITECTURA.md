# FASE 1 — Auditoría integral y arquitectura única

## Objetivo contractual

ConstruControl debe ser una sola aplicación integral de gestión residencial. ERPNext/Frappe permanece como motor interno de documentos, permisos, colas, archivos, impresión y persistencia, pero no debe competir visualmente ni convertirse en la navegación principal del usuario.

Este documento es el diagnóstico vinculante para las fases 2 a 12. No cambia datos productivos, volúmenes, secretos ni configuración directa de AWS/Coolify.

## Infraestructura confirmada

- Fuente única de verdad: rama `main` de GitHub.
- Despliegue: `docker-compose.yml`.
- Infraestructura: AWS EC2 x86_64 administrada por Coolify.
- Servicios: frontend Nginx, backend Gunicorn, WebSocket, workers, scheduler, backup, MariaDB y Redis.
- Persistencia: volúmenes `mariadb-data`, `redis-queue-data`, `sites` y `logs`.
- Regla absoluta: nunca eliminar volúmenes ni ejecutar `docker compose down -v`.
- Los secretos permanecen en Coolify; no deben almacenarse en GitHub.

## Inventario funcional actual

ConstruControl dispone de páginas propias para:

- CC00 Centro de control.
- MIG Migración segura.
- BI01 Reportes y notificaciones.
- CL01 Cierre semanal.

También dispone de DocTypes operativos para ingresos, gastos, contratos, fases, materiales, inventario, compras, avances, auditoría, usuarios, evidencias, cuentas por pagar, proveedores, equipos, cambios y aprobaciones.

El inventario autoritativo y la asignación de fases se encuentran en `docs/architecture/module_inventory.json`.

## Hallazgos críticos

### A-01 — La experiencia sigue dividida entre ConstruControl y ERPNext

**Severidad:** crítica  
**Estado:** confirmado

El workspace ConstruControl dirige la mayoría de sus opciones directamente a listas y formularios estándar de Frappe. El panel propio es una página adicional, pero no constituye todavía un shell persistente para toda la experiencia.

**Consecuencia:** al abrir un módulo, el usuario vuelve a percibir ERPNext y siente que existen dos sistemas.

**Resolución:** fases 3 y 11. Se implementará un shell único, navegación consistente, cabecera, regreso, cierre, acciones y rutas autorizadas.

### A-02 — La activación visual solo cubre una parte de los DocTypes

**Severidad:** crítica  
**Estado:** confirmado

El JavaScript móvil reconoce únicamente un conjunto limitado de DocTypes. El workspace expone otros módulos como cuentas por pagar, proveedores, equipos, cambios, aprobaciones, reportes generados, contactos, reglas y evidencias que no están en esa lista.

**Consecuencia:** varias rutas pierden el estilo y la navegación ConstruControl.

**Resolución:** fases 3 y 4. La cobertura se derivará del registro de módulos y no de una lista manual incompleta.

### A-03 — El panel ejecutivo es un resumen parcial

**Severidad:** alta  
**Estado:** confirmado

El resumen actual calcula recibido, gastado, disponible, contratado, cantidad de fases y avance promedio. No presenta presupuesto original/actual, comprometido, cuentas por pagar, vencimientos, inventario crítico, desviaciones, incidencias, próximos pagos ni actividad reciente.

**Consecuencia:** no permite comprender el estado total de la obra.

**Resolución:** fase 10.

### A-04 — FI01 no representa todavía una tesorería profesional

**Severidad:** alta  
**Estado:** confirmado

El control actual se centra en monto recibido, gasto, pendiente y saldo. Falta un catálogo administrable de institución, tipo de operación, moneda, tipo de cambio, comisión, monto bruto/neto, cuenta receptora, referencia, remitente, beneficiario y conciliación.

**Consecuencia:** remesas, depósitos, transferencias y efectivo no tienen la trazabilidad esperada.

**Resolución:** fase 6.

### A-05 — FI02 no representa todavía un ciclo profesional de gasto

**Severidad:** alta  
**Estado:** confirmado

Existen validaciones de monto, proveedor, proyecto, fuente y contrato, pero el flujo aún no integra de manera completa factura, impuestos, retenciones, vencimiento, pagos parciales, aprobación, cuenta por pagar, recepción y conciliación.

**Consecuencia:** el gasto se percibe como un formulario simple.

**Resolución:** fase 7.

### A-06 — El perfil administrativo es una extensión visual mínima

**Severidad:** alta  
**Estado:** confirmado

Actualmente se añade una insignia de identidad al panel, pero no existe una experiencia propia de perfil administrativo con fotografía, proyectos, permisos, sesiones, seguridad, preferencias y actividad.

**Consecuencia:** el perfil sigue dependiendo de la pantalla estándar y no representa el rol profesional del sistema.

**Resolución:** fase 5.

### A-07 — Integraciones está consolidada por nombre, no gestionada como producto

**Severidad:** alta  
**Estado:** confirmado

El código actual busca workspaces llamados Integrations/Integraciones/Integraciones NEXT, fusiona filas y oculta duplicados. Esto evita parte de la duplicación visual, pero no crea un registro administrable de integraciones.

**Consecuencia:** permanecen enlaces técnicos innecesarios y no existe un flujo seguro para crear, activar, probar, archivar o eliminar integraciones personalizadas.

**Resolución:** fase 9.

### A-08 — La PWA no cumple todavía el estándar esperado para iPhone

**Severidad:** alta  
**Estado:** confirmado

El manifest utiliza únicamente un SVG y el `apple-touch-icon` también apunta al SVG. No existe una familia de iconos PNG para iOS ni un service worker versionado.

**Consecuencia:** el icono puede no actualizarse correctamente y la instalación no se siente como una aplicación completa.

**Resolución:** fase 4.

### A-09 — La navegación móvil es una adaptación, no una aplicación completa

**Severidad:** alta  
**Estado:** confirmado

Existe una barra inferior y un menú “Más”, pero se basa en símbolos de texto, cubre rutas limitadas y no implementa una capa uniforme para formularios, acciones rápidas, regreso, cierre, borradores y pasos.

**Consecuencia:** la experiencia móvil se percibe como ERPNext reducido.

**Resolución:** fase 4.

### A-10 — El workspace expone demasiados enlaces directos

**Severidad:** media-alta  
**Estado:** confirmado

La página ConstruControl contiene enlaces directos a numerosos DocTypes técnicos y administrativos, incluidos migración, registros históricos y configuración.

**Consecuencia:** aumenta la complejidad y expone funciones que deberían depender del rol o vivir dentro de centros administrados.

**Resolución:** fases 3, 5 y 9.

### A-11 — Las pruebas actuales validan presencia de texto, no experiencia completa

**Severidad:** alta  
**Estado:** confirmado

El validador de completitud comprueba archivos, frases, enlaces y marcadores. No ejecuta navegación real, renderizado de formularios, accesibilidad, PWA, permisos por rol ni flujos financieros completos.

**Consecuencia:** una ejecución verde puede coexistir con una experiencia incompleta o fragmentada.

**Resolución:** fases 3, 4, 6, 7, 11 y 12 mediante pruebas de contrato, navegador y migración.

### A-12 — El modelo actual mezcla definiciones runtime con controladores de aplicación

**Severidad:** media-alta  
**Estado:** confirmado

Varios DocTypes se crean o actualizan desde JSON runtime durante `after_migrate`, mientras páginas y scripts también existen en archivos físicos.

**Consecuencia:** aumenta el riesgo de divergencia entre base de datos, archivos, migraciones y UX.

**Resolución:** fase 2. Se definirá una estrategia única, idempotente y verificable para esquema y activos.

### A-13 — La navegación general de ERPNext continúa disponible como experiencia primaria

**Severidad:** crítica  
**Estado:** confirmado

El sistema conserva los workspaces estándar visibles según roles. ConstruControl no ha establecido todavía una política completa de landing page, workspace permitido y rutas visibles.

**Consecuencia:** el usuario puede entrar a módulos genéricos como Manufactura, CRM, Ventas, Compras o Sitio Web aunque no formen parte de la operación residencial.

**Resolución:** fase 3 mediante visibilidad por rol y navegación propia, sin eliminar dependencias internas.

### A-14 — Falta un contrato único para cerrar, cancelar y regresar

**Severidad:** alta  
**Estado:** confirmado por experiencia reportada y ausencia de una capa global específica

El CSS adapta tamaños y modales, pero no existe un controlador transversal que garantice en cada formulario: regresar, cerrar, cancelar, guardar borrador, guardar y guardar/nuevo.

**Consecuencia:** existen callejones sin salida y acciones inconsistentes.

**Resolución:** fase 11.

## Arquitectura objetivo aprobada

```text
Usuario escritorio / móvil / PWA
              |
              v
Shell único ConstruControl
- navegación
- identidad
- acciones
- rutas
- permisos visuales
              |
              v
Servicios de aplicación ConstruControl
- tesorería
- gastos
- contratos
- obra
- inventario
- reportes
- integraciones
- usuarios
              |
              v
Motor ERPNext/Frappe interno
- documentos
- permisos
- archivos
- colas
- impresión
- auditoría técnica
              |
              v
MariaDB + volúmenes persistentes
```

## Decisiones vinculantes para fases posteriores

1. ERPNext no se elimina ni se bifurca innecesariamente; se utiliza como motor interno.
2. Ninguna fase puede requerir edición manual permanente en AWS o Coolify.
3. El registro de módulos será la fuente de verdad para navegación, rutas, permisos y pruebas.
4. Toda pantalla ConstruControl debe conservar shell y navegación.
5. Los módulos genéricos de ERPNext se ocultarán por rol, no se borrarán si son dependencias.
6. El modelo financiero se ampliará sin destruir los datos migrados.
7. Los catálogos eliminables usarán desactivación o borrado controlado con auditoría.
8. Los logos institucionales se almacenarán localmente y requerirán procedencia oficial o autorización de uso.
9. La PWA usará iconos PNG versionados y comportamiento específico para iPhone/Android.
10. La migración y configuración crítica permanecerán restringidas a administradores.
11. Cada fase añadirá pruebas que validen comportamiento, no solo presencia de archivos.
12. No se dará una fase por completada con pruebas fallidas.

## Matriz de ejecución

| Fase | Alcance | Hallazgos principales |
|---|---|---|
| 2 | Datos, migraciones y esquema | A-12 |
| 3 | Shell y escritorio | A-01, A-02, A-10, A-13 |
| 4 | Móvil y PWA | A-02, A-08, A-09 |
| 5 | Usuarios y perfil | A-06, A-10 |
| 6 | Tesorería e ingresos | A-04 |
| 7 | Gastos y cuentas por pagar | A-05 |
| 8 | Gestión integral de obra | Integración transversal de módulos operativos |
| 9 | Integraciones | A-07, A-10 |
| 10 | Panel y reportes | A-03 |
| 11 | UX, formularios y errores | A-01, A-11, A-14 |
| 12 | Seguridad, pruebas y entrega | A-11 y validación total |

## Controles de aceptación de la FASE 1

- [x] Fuente única de verdad confirmada.
- [x] Infraestructura y persistencia documentadas.
- [x] Guardrails de AWS/Coolify documentados.
- [x] Módulos actuales inventariados.
- [x] Páginas propias inventariadas.
- [x] Workspaces y rutas directas auditados.
- [x] Shell de escritorio auditado.
- [x] Navegación móvil auditada.
- [x] Manifest e iconografía auditados.
- [x] Panel ejecutivo auditado.
- [x] Tesorería auditada.
- [x] Gastos auditados.
- [x] Usuarios y perfil auditados.
- [x] Integraciones auditadas.
- [x] Permisos críticos auditados.
- [x] Migraciones runtime auditadas.
- [x] CI actual auditado.
- [x] Riesgos priorizados.
- [x] Arquitectura objetivo definida.
- [x] Fases posteriores vinculadas a los hallazgos.

## Impacto de esta fase

- Datos productivos modificados: **ninguno**.
- Esquema de MariaDB modificado: **no**.
- Docker Compose modificado: **no**.
- AWS/Coolify modificado: **no**.
- Volúmenes modificados: **no**.
- Despliegue requerido: **no**.
