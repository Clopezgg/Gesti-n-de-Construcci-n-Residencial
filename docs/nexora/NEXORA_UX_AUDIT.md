# NEXORA — Auditoría UX/UI (Bloque 12; actualizada en el cierre de los 30 bloques)

**Nota de actualización (auditoría final, ver `NEXORA_30_BLOCKS_AUDIT.md`):** este
documento se escribió a mitad de la misión (Bloque 12). Las secciones "Navegación",
"Proyectos — página de contexto 360°" y "Búsqueda" tienen una nota de actualización
con lo que los Bloques 16-18 construyeron de verdad después. El resto de secciones
se re-verificó contra el código actual en el cierre y sigue siendo exacto.

Auditoría basada en lectura directa de `nexora_app/nexora/nexora/page/*`,
`nexora_app/nexora/public/js/*`, `nexora_app/nexora/public/css/*` y
`nexora_app/nexora/www/*`. No se pudo ejecutar un navegador real en este entorno (sin
Playwright/Chromium/WebKit) — donde el hallazgo depende de renderizado visual real se
marca **NO DEMOSTRADO** y se indica qué job de CI lo certifica (`nexora-app.yml`, job
`browser`).

Para cada pantalla: qué funciona, qué es mejorable, qué es defectuoso, qué falta, y si
debe conservarse o rediseñarse. Separando siempre modelo de negocio (correcto, no se
toca) de experiencia (evaluable).

## Inicio / Dashboard (`nexora_dashboard.js`)

- **Funciona:** panel ejecutivo real con dinero disponible/comprometido/ejecutado,
  "qué requiere su atención hoy", avance de obra, gastos por categoría, inventario
  crítico, estado contractual, actividad reciente (`nexora_dashboard.js:54-88`).
  Estados con texto explícito, no solo color (`statusLabels`, línea 34-52).
  Backend real detrás de cada cifra (`dashboard/service.py:264-361`).
- **Mejorable:** los números no tienen drill-down inline (composición del saldo
  expandible en el mismo lugar); solo navegan a un reporte aparte. Ver
  `NXR-UX-0013`.
- **Falta:** resultado explicable estructurado tras una acción rápida desde el
  dashboard mismo (solo hay `frappe.show_alert`).
- **Conservar:** la arquitectura de datos y el criterio de "atención" — es de lo más
  sólido del repositorio, no rediseñar desde cero.

## Navegación (`nexora_shell.js`)

- **Funciona:** agrupación por pregunta ("Hoy", "Dinero", "Compras", "Expediente") en
  vez de lista plana de 12 módulos — ya aplica el principio de "navegar por intención",
  aunque con nombres de dominio, no de modo (Inicio/Operar/Gestionar/Analizar/Buscar).
- **Mejorable:** reagrupar las 4 secciones actuales hacia los 5 modos de intención de
  la nueva misión sería un cambio de rotulado/agrupación, no de arquitectura — bajo
  riesgo, alto valor de coherencia con la visión del producto.
- **Defectuoso:** no hay atajo de teclado global (Ctrl+K) ni un punto único de "qué
  necesitas hacer" — la barra superior solo ofrece "Buscar" y "Registrar ingreso"
  fijos (`nexora_shell.js:184-191`). Ver `NXR-UX-0008`.
- **Actualización (Bloque 16, cierre de los 30 bloques):** sí se construyó una
  barra de navegación inferior tipo app nativa (`TABBAR_ITEMS` en
  `nexora_shell.js`, 4 destinos frecuentes, visible en móvil) — cierra
  `NXR-UX-0014`, verificado presente en el código actual. El Ctrl+K/Command Bar
  (`NXR-UX-0008`) sigue sin existir — re-verificado en el Bloque 30, cero
  coincidencias en `public/js`/`public/css`.

## Operaciones (ingreso/gasto) (`nexora_guided_operations.js`, `nexora_quick_flows.js`)

- **Funciona:** wizard progresivo real de 4 etapas con estado por paso
  (`nexora_guided_operations.js:72-124`), preview financiero con saldo antes/después
  (`financial/core.py:241-268`, `nexora_quick_flows.js:110-113,324-326`), contexto de
  proyecto activo propuesto automáticamente (`nexora_guided_operations.js:29-37`).
  Esto ya es "Super Experience" real, no aspiracional.
- **Falta:** el wizard cubre solo ingreso/gasto (movement_code 101/102). Contratos,
  compras y cotizaciones siguen usando diálogos tradicionales de Frappe
  (`nexora_contracts.js`, ~794 líneas) sin el mismo patrón. Extender el wizard a esos
  flujos es una mejora de consistencia, no una reconstrucción.
- **Mejorable:** el mensaje post-ejecución es un texto corto de estado
  (`.nxr-action-status`), no un panel de "esto es lo que pasó" con efectos financieros
  detallados. Ver `NXR-UX-0012`.

## Contratos (`nexora_contracts.js`)

- **Funciona:** panel maestro-detalle con monto vigente/ejecutado/pendiente/pagado,
  anticipo/retención, conteo de adendas/estimaciones, transiciones de estado con
  acciones claras (`nexora_contracts.js:300-360`). Es un resumen financiero real, no
  cosmético.
- **Falta:** no es una página de "expediente completo" con pestañas separadas
  (evidencias/avance/actividad); todo vive en un solo panel largo. Podría beneficiarse
  del mismo patrón de pestañas que se propone para `NXR-UX-0010` (proyecto 360°),
  reutilizando el mismo componente en vez de crear uno nuevo específico de contrato.

## Proyectos — página de contexto 360°

- **No existe** una página dedicada a "Proyecto X" con pestañas de
  resumen/finanzas/contratos/compras/inventario/evidencias/avance/actividad. El
  dashboard es global filtrable por proyecto, no una vista de expediente por proyecto.
  Esta es la brecha de UX más alineada con la petición explícita de la nueva misión
  (Sección 16). Clasificación: **FALTANTE**, requiere diseño y componente nuevo
  (`NXR-UX-0010`).
- **Actualización (Bloque 17, cierre de los 30 bloques):** se construyó
  `nexora-project`, respaldada por `context360/service.py::get_project_overview()`
  y `context360/timeline.py::get_project_timeline()` — resumen financiero,
  presupuesto, contratos, avance, evidencia, alertas, operaciones recientes,
  inventario crítico y una timeline universal cronológica real, todo con
  `require_project_access` como único punto de control de acceso. Reclasificación:
  ya no es **FALTANTE**, es **NO DEMOSTRADO** (código real y probado por unidad;
  sin recorrido visual real en navegador en este entorno).

## Búsqueda (`nexora_search.js`)

- **Funciona:** respeta permisos de verdad (`boot.py:360-390`,
  `universal_search_consolidated` con `require_action("preview")` y filtro por
  `PROJECT_SCOPED_DOCTYPES`); busca en 13 doctypes.
- **Funciona:** es un buscador estructurado (campo + filtro + lista) y, si no encuentra
  filas, delega la consulta completa al único motor conversacional mediante
  `nexora.conversation.dispatch.send_message`. La pantalla no calcula saldos ni
  permisos y reutiliza la confirmación/cancelación server-side del asistente.
- **Actualización (Bloque 32, PR #144 y continuidad):** `NXR-UX-0009` está conectado
  en código real. La limpieza posterior retiró el botón/panel explícito redundante
  que duplicaba esa misma llamada; la experiencia canónica es ahora una única búsqueda
  con fallback natural. El recorrido de navegador dedicado de esta pantalla sigue
  pendiente como ampliación de evidencia, aunque el motor compartido ya tiene recorrido
  vivo en `NXR-CNV-0001`.

## Compras / Proveedores / Inventario

- **Funciona:** flujos completos con locks, idempotencia y permisos server-side
  (confirmado en auditoría de backend). UI de formularios estándar de Frappe con
  validación de servidor.
- **Defectuoso (backend, no UX):** sobre-recepción acumulada no bloqueada
  (`NXR-COM-0010` — ver gap analysis). El formulario de recepción no puede advertir
  al usuario de algo que el backend tampoco valida — corregir backend primero.
  **Actualización (Bloque 13, cierre de los 30 bloques):** el backend ya bloquea la
  sobre-recepción acumulada (`receipt_core.py`, verificado en código); el formulario
  de recepción ahora puede confiar en un rechazo real del servidor.
- **Mejorable (UX):** sin el patrón de wizard progresivo que sí tienen ingreso/gasto;
  formularios más largos y menos guiados.

## Evidencia

- **Funciona:** captura con contexto heredado (proyecto/usuario/fecha), trazabilidad.
- **Defectuoso:** el campo de adjunto es un `Attach` genérico de Frappe
  (`nexora.js:396`); no hay `capture="camera"` ni integración nativa de cámara para
  iPhone (`NXR-UX-0015`). Es una mejora de input HTML, bajo riesgo.

## Reportes / Estados de cuenta

- **Funciona:** saldo corrido, conciliación, exportación PDF/Excel real (confirmado en
  auditoría de backend — no son archivos ficticios). Contexto de fecha propagado
  correctamente desde el dashboard (corregido en Bloque 11, `EXECUTION_STATE.md`).

## Configuración / Permisos

- No se auditó pantalla por pantalla en esta ronda (fuera del foco de brechas nuevas
  encontradas); el backend de permisos (`permissions.py`, `require_action`) ya está
  CONFIRMADO por la auditoría de todos los subsistemas de negocio.

## PWA / iPhone / Escritorio

- **Funciona (confirmado en código):** `public/manifest.json` con iconos, shortcuts y
  `display: standalone`; `www/nexora-service-worker.js` con cache-first del shell
  público y exclusión explícita de rutas sensibles (`isSensitive()`); safe-area-inset
  aplicado en varios CSS; objetivos táctiles de 44px.
- **Defectuoso:** no hay bottom tab bar — la navegación móvil es el mismo drawer lateral
  colapsado en hamburguesa (`NXR-UX-0014`).
- **NO DEMOSTRADO en esta sesión:** renderizado visual real en iPhone/WebKit y
  Chromium de escritorio — requiere el job `browser` de `nexora-app.yml`
  (Playwright + `docker-compose.browser.yml`), ausente en este sandbox. El código que
  sustenta la promesa (manifest, service worker, CSS responsivo) sí es real; lo que no
  se puede demostrar aquí es su renderizado final pixel a pixel.

## Design System

- **Confirmado real, no aspiracional:** `public/css/nexora_design_system.css` (662
  líneas), tokens `--nxr-*` en tres capas (primitivas/semántica/componentes),
  componentes `.nxr-ds-btn/-card/-field/-badge/-notice` usados de forma consistente en
  dashboard y contratos. Base sólida para extender a las pantallas que aún usan
  diálogos tradicionales de Frappe.

## Resumen de clasificación

| Pantalla/concepto | Estado (Bloque 12) | Estado real al cierre de los 30 bloques |
|---|---|---|
| Dashboard | Conservar, extender drill-down | Sin cambio |
| Navegación | Conservar, reagrupar rótulos hacia 5 modos de intención | Barra inferior móvil construida (`NXR-UX-0014`); Ctrl+K sigue sin existir (`NXR-UX-0008`) |
| Operaciones (ingreso/gasto) | Conservar, extender patrón a más flujos | Sin cambio |
| Contratos | Conservar, integrar con patrón de pestañas 360° | Sin cambio |
| Proyecto 360° | Rediseñar/crear — no existe | **Construido** (`nexora-project`, `context360/`); NO DEMOSTRADO en vivo |
| Búsqueda | Conservar motor de permisos, construir capa NLU encima | NLU construida como pantalla aparte (`nexora-assistant`); no fusionada aquí |
| Compras/Proveedores/Inventario | Conservar UI, corregir backend primero | Backend de sobre-recepción corregido (`NXR-COM-0010`) |
| Evidencia | Conservar, mejorar input de cámara | Sin cambio — `capture="camera"` sigue sin existir (`NXR-UX-0015`), re-verificado |
| Reportes | Conservar | Sin cambio |
| PWA/iPhone/Escritorio | Conservar código, validar visualmente en CI con Playwright | **Validado en CI real** (Bloque 27): etapa `pwa` en verde en los tres perfiles, dos veces |
| Design System | Conservar y extender cobertura | Sin cambio |

Ver `NEXORA_30_BLOCKS_AUDIT.md` para el detalle bloque por bloque con evidencia de
código y commit.
