# NEXORA — Gap analysis, Bloque 12 (auditoría maestra de brechas)

## Origen y alcance

Este documento responde a una nueva "misión maestra" recibida en sesión (auditoría +
arquitectura + super experience + reconstrucción + validación + cierre). Antes de escribir
una sola línea de código se verificó el estado real del repositorio (Capítulo 32/33 de la
misión) y se encontró que **ya existe** una constitución vigente
(`NEXORA_CONSTITUTION.md`), un plan maestro ejecutado (`docs/nexora/PLAN_MAESTRO.md`,
`ORDEN_MAESTRA_FINALIZACION.md`), una matriz de 166 requisitos
(`docs/nexora/MATRIZ_REQUISITOS.md`) y un log de ejecución activo (`EXECUTION_STATE.md`,
actualmente en Bloque 11).

`AGENTS.md` prohíbe explícitamente "otra auditoría general" y "fuentes de estado
paralelas". Por decisión expresa del propietario de esta sesión, este documento **no
sustituye ni duplica** `MATRIZ_REQUISITOS.md` ni `EXECUTION_STATE.md`: es la auditoría de
brechas de una nueva ronda (Bloque 12), reconcilia contra esas fuentes y propone filas
nuevas que ya se añadieron a `MATRIZ_REQUISITOS.md` con evidencia real de código. Los seis
documentos que pedía la misión original (`NEXORA_FINAL_GAP_ANALYSIS.md`,
`NEXORA_FINAL_REQUIREMENTS_MATRIX.md`, `NEXORA_FINAL_EXECUTION_PLAN.md`,
`NEXORA_UX_AUDIT.md`, `NEXORA_EXPERIENCE_SYSTEM.md`, `NEXORA_GOLDEN_PATHS.md`) se
reinterpretan así:

| Documento pedido | Dónde vive realmente |
|---|---|
| Gap analysis | Este archivo |
| Matriz de requisitos | `docs/nexora/MATRIZ_REQUISITOS.md` (extendida, no reemplazada) |
| Plan de ejecución | Sección final de este archivo + `EXECUTION_STATE.md` |
| Auditoría UX/UI | `docs/nexora/NEXORA_UX_AUDIT.md` (nuevo) |
| Sistema de experiencia | `docs/nexora/NEXORA_EXPERIENCE_SYSTEM.md` (nuevo) |
| Golden Paths | `docs/nexora/NEXORA_GOLDEN_PATHS.md` (nuevo — no existía un equivalente formal) |

Metodología: verificación directa de código (no de documentación) sobre
`nexora_app/nexora/{financial,contracts,purchases,inventory,budget,close,directory,
intelligence,conversation,integrations,notifications,nexora/page,public,www}`,
ejecución real de los validadores y de la suite de pruebas disponible en este entorno
(sin `bench`/MariaDB/Redis/Docker/Playwright), y lectura íntegra de
`MATRIZ_REQUISITOS.md`, `CATALOGO_MAQUINAS_ESTADO.md`, `CATALOGO_CONTROLES.md`,
`DECISIONES.md`, `EXECUTION_STATE.md` y `NEXORA_INTELLIGENCE_ARCHITECTURE.md`.

## Qué está realmente confirmado (no solo documentado)

- **Núcleo financiero** (`financial/`): CONFIRMADO. Locks `FOR UPDATE` en orden estable,
  idempotencia real (`NXR Idempotency Record`), rechazo de saldo negativo
  (`financial/core.py:225-227`), auditoría por operación (`NXR Audit Event`). 53 pruebas.
- **Directorio universal** (`directory/`): CONFIRMADO. Locks dedicados anti-duplicado,
  permisos server-side por acción, 23 pruebas + probe de concurrencia.
- **Contratos, inventario, cierres** (`contracts/`, `inventory/`, `close/`): EXISTENTE Y
  REUTILIZABLE, mismo patrón arquitectónico sólido (savepoint → idempotencia → lock →
  ejecución → auditoría), sin defectos críticos detectados en esta ronda.
- **AI Gateway / orquestador de proveedores** (`intelligence/`): CONFIRMADO. 9 proveedores
  con adaptador real, circuit breaker, credenciales cifradas, sin secretos en código.
- **Contexto persistente, wizards progresivos, preview financiero, design system, PWA
  manifest/service worker**: CONFIRMADO. La "Super Experience" de la nueva misión ya está
  parcialmente construida — no se parte de cero (ver `NEXORA_EXPERIENCE_SYSTEM.md`).
- **Validadores de repositorio**: 13 de 13 ejecutables sin argumento pasan limpio ahora
  mismo; 934 de 953 tests unitarios pasan (los 19 restantes fallan solo por ausencia de
  `frappe` en este entorno, no por defecto de código — confirmado comparando contra
  `main` sin cambios).

## Brechas reales encontradas (nuevas filas en `MATRIZ_REQUISITOS.md`)

Cada una se agregó a la matriz con evidencia de archivo:línea. Resumen:

| ID nuevo | Título | Estado | Severidad |
|---|---|---|---|
| `NXR-COM-0010` | Bloqueo de sobre-recepción acumulada en órdenes de compra | EXISTENTE PERO DEFECTUOSO | Alta (integridad de inventario/compromiso) |
| `NXR-PRE-0008` | Enforcement transaccional presupuesto→compromiso→compra→pago | EXISTENTE PERO DESCONECTADO | Alta (requiere decisión de arquitectura) |
| `NXR-NOT-0006` | Entrega real multicanal de notificaciones (email/push) | EXISTENTE PERO DEFECTUOSO | Media |
| `NXR-INT-0007` | Verificación real de conexión de integraciones (no simulada) | EXISTENTE PERO DEFECTUOSO | Media (riesgo de confianza falsa) |
| `NXR-INT-0008` | Reapertura de integración real WhatsApp Business bajo NIP | OBSOLETO — RECONSIDERAR | Requiere decisión |
| `NXR-CNV-0001` | Conversational OS / Barra NEXORA Universal en lenguaje natural | REQUIERE IMPLEMENTACIÓN | Alta (pilar central de la nueva misión) |
| `NXR-UX-0008` | Acción Universal / Command Bar unificado | EXISTENTE PERO DEFECTUOSO | Media |
| `NXR-UX-0009` | Búsqueda con consulta en lenguaje natural e inicio de acciones | NO DEMOSTRADO / FALTANTE | Media |
| `NXR-UX-0010` | Página de contexto 360° por proyecto | FALTANTE | Alta (pedida explícitamente por la misión) |
| `NXR-UX-0011` | Línea de tiempo universal reutilizable por entidad | FALTANTE | Media |
| `NXR-UX-0012` | Resultado explicable tras ejecutar una operación | EXISTENTE PERO DEFECTUOSO | Media |
| `NXR-UX-0013` | Números explicables con composición inline (drill-down) | EXISTENTE PERO DEFECTUOSO | Baja |
| `NXR-UX-0014` | Navegación móvil inferior tipo app nativa | FALTANTE | Media |
| `NXR-UX-0015` | Captura de evidencia con cámara nativa desde iPhone | EXISTENTE PERO DEFECTUOSO | Baja |

### Detalle de las dos brechas de mayor riesgo financiero/de integridad

**`NXR-COM-0010` — sobre-recepción acumulada no bloqueada.**
`nexora_app/nexora/purchases/receipt_service.py:80-91` obtiene `prev_received` con
`frappe.db.get_value(...)` (una sola fila) y ese valor **nunca se usa** después. La
validación real vive en `purchases/receipt_core.py:23-54`
(`validate_receipt_lines()`), que compara la cantidad de **esta** recepción contra
`ordered_qty`, sin acumular recepciones previas de la misma línea. Efecto: dos
recepciones parciales que individualmente pasan la tolerancia pueden sumar más de lo
pedido sin que el sistema lo detecte. Adicionalmente, `_update_po_status()`
(`receipt_service.py:266-278`) marca la orden `Completed` contando filas de
`NXR Goods Receipt Line` sin filtrar por estado del documento padre (cuenta recepciones
`Draft`/`Cancelled` igual) ni comparar cantidades. Es un defecto de código verificado,
no una limitación de diseño.

**`NXR-PRE-0008` — presupuesto sin enforcement transaccional.**
`budget/core.py` y `budget/service.py` implementan correctamente
`compute_line_balances`, `validate_no_overspend` y una máquina de estados propia, pero
**ningún otro módulo los llama**: `financial/commitments.py`, `purchases/*` y
`contracts/*` no importan `budget/service.py`, y `NXR Commitment` no tiene un campo
`Link` hacia `NXR Budget Line`. El presupuesto es hoy una bitácora paralela consultada
solo en reportes de lectura (`dashboard/service.py`), no un control que bloquee un
compromiso o una compra que exceda el presupuesto de un centro de costo. Esto es una
**decisión de arquitectura pendiente**, no un bug simple: ¿debe el presupuesto ser
bloqueante (rechaza el compromiso) o solo informativo (alerta sin bloquear)? Ya existe
`validate_no_overspend()` listo para conectarse; falta la decisión de política y el
cableado.

### Contradicción documental resuelta (Capítulo 74 de la misión)

`NXR-INT-0006` en `MATRIZ_REQUISITOS.md` está marcado `OBSOLETO JUSTIFICADO` con la
nota: *"el adaptador WhatsApp fue excluido del alcance... no existe implementación
concreta"*. La nueva misión maestra pide explícitamente WhatsApp Business real (su
Sección 55). Se marca como **OBSOLETO — RECONSIDERAR**: la exclusión fue correcta para
el alcance de PLAN_MAESTRO (166 requisitos originales, sin IA conversacional), pero el
alcance cambió. Se abre `NXR-INT-0008` para rastrear la reapertura sin borrar la
decisión histórica ni fingir que nunca existió.

## Riesgos y bloqueos de esta ronda

- **Entorno de este sandbox** no tiene `bench`, `frappe`, MariaDB, Redis, Docker ni
  Playwright/Chromium/WebKit. Todo lo que requiere esos componentes (19 tests
  `*_integration.py`, `nexora_browser_smoke.mjs`, validación real de iPhone/PWA) queda
  clasificado **NO DEMOSTRADO** en esta sesión — se ejecuta y certifica en
  `nexora-app.yml` (job `browser`) y `server-tests-mariadb.yml` de GitHub Actions, no
  aquí. No se inventó ningún resultado de esos componentes.
- **Conversational OS y WhatsApp** son construcción nueva sustancial (no un ajuste),
  ya diseñada en `NEXORA_INTELLIGENCE_ARCHITECTURE.md` y
  `docs/nexora/NIP_BLOQUE_6_CONVERSATIONAL_OS.md` (código = 0 en `conversation/`).
  Requiere credenciales reales de Meta para WhatsApp — bloqueado hasta que el
  propietario las provea.
- **`NXR-PRE-0008`** requiere una decisión de producto antes de programar (bloqueante
  vs. informativo) — no se resuelve de forma autónoma.

## Plan de ejecución propuesto (próximos bloques)

Continuando la numeración de `EXECUTION_STATE.md` desde el Bloque 11 (este documento
cierra el Bloque 12 — auditoría, sin cambios de código):

1. **Bloque 13 (seguro, autónomo)** — corregir `NXR-COM-0010`: acumular
   `prev_received` real por línea en `receipt_core.py`, corregir `_update_po_status`
   para filtrar por estado de documento y comparar cantidades, agregar pruebas
   negativas de sobre-recepción acumulada. No toca dinero de forma irreversible, es un
   bug de validación — ejecutable sin decisión adicional del propietario.
2. **Bloque 14 (requiere decisión)** — `NXR-PRE-0008`: presentar al propietario la
   pregunta de política (bloqueante/informativo) antes de cablear
   `validate_no_overspend()` a `commitments.py`/`purchases/*`.
3. **Bloque 15 (seguro, autónomo)** — `NXR-INT-0007`: eliminar el
   `test_connection` simulado en `integrations/service.py:39-49`, ejecutar una
   verificación real (o marcar explícitamente "no verificable sin credenciales" en vez
   de "Success" falso).
4. **Bloque 16 (seguro, autónomo, UX)** — cerrar `NXR-UX-0012`/`NXR-UX-0013`
   (resultado explicable y números explicables) y `NXR-UX-0014` (navegación móvil
   inferior) — mejoras de experiencia sobre código ya existente, sin tocar modelo de
   negocio.
5. **Bloque 17 (grande, requiere decisión de alcance)** — `NXR-UX-0010` (página de
   contexto 360° por proyecto) y `NXR-UX-0011` (timeline universal) — nuevo
   componente de UX compartido, afecta varias páginas.
6. **Bloque 18 (grande, requiere decisión de alcance y presupuesto de proveedor IA)**
   — `NXR-CNV-0001` Conversational OS, siguiendo el diseño ya aprobado en
   `NIP_BLOQUE_6_CONVERSATIONAL_OS.md` (continúa como "NIP — Bloque 7", no reinicia la
   numeración NIP).
7. **Bloque 19 (bloqueado por credenciales externas)** — `NXR-INT-0008` WhatsApp
   Business real, solo cuando el propietario provea credenciales de Meta.

No se ejecuta ningún bloque de código en esta ronda: por Capítulo 32/75 de la misión,
esta sesión se detiene en la auditoría y espera decisión del propietario sobre el orden
y alcance antes de tocar código (ver resumen NEXORA AUDIT en el mensaje de cierre de
este bloque).
