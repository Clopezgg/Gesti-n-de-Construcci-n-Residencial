# NEXORA — Sistema de experiencia ("Super Experience"), Bloque 12 (actualizado en el cierre de los 30 bloques)

Este documento describe la arquitectura de experiencia de NEXORA tal como existe
realmente hoy (verificado en código), y dónde debe crecer para cumplir la visión de
"centro de mando inteligente" de la misión maestra. No es un documento aspiracional:
cada afirmación de "ya existe" cita archivo:línea; cada "falta" referencia la fila de
`MATRIZ_REQUISITOS.md` que la rastrea.

**Nota de actualización (auditoría final, ver `NEXORA_30_BLOCKS_AUDIT.md`):**
escrito en el Bloque 12, a mitad de la misión. Las secciones "Lo que falta para
cerrar el ciclo completo" y "Barra NEXORA Universal" tienen una nota con lo que los
Bloques 17-18 construyeron de verdad después.

## Principio validado: el usuario piensa en intenciones, el sistema resuelve complejidad

Este principio **ya está parcialmente construido**, no es una idea nueva para este
repositorio:

- **Contexto persistente** (Sección 12 de la misión): `public/js/nexora_report_actions.js:171-268`
  mantiene `contextState`/`loadContext()`/`publishContext()` disparando el evento
  `nexora:context-changed`; `public/js/nexora_guided_operations.js:29-37` lo consume
  para proponer el proyecto activo automáticamente. Funciona de extremo a extremo hoy.
- **Formularios progresivos** (Sección 13): wizard real de 4 etapas para ingreso/gasto
  (`nexora_guided_operations.js:72-124`), con estado por paso, no un formulario gigante.
- **Preview financiero** (Sección 14): saldo antes/después calculado en servidor
  (`financial/core.py:241-268`) y mostrado antes de confirmar
  (`nexora_quick_flows.js:110-113,324-326`).
- **Estados claros** (Sección 20): diccionarios de texto explícito por estado
  (`nexora_dashboard.js:34-52`), el color es complementario, no el único vehículo.
- **Búsqueda universal con permisos reales** (Sección 23): `boot.py:360-390`, filtra por
  `PROJECT_SCOPED_DOCTYPES` y usa `frappe.has_permission` — no hay fuga de información
  por búsqueda hoy.

## Lo que falta para cerrar el ciclo completo (Sección 6 de la misión)

El ciclo ENTENDER → ENCONTRAR → ACTUAR → REVISAR → CONFIRMAR → EJECUTAR → EXPLICAR →
TRAZAR → CONTINUAR tiene soporte real en ACTUAR/REVISAR/CONFIRMAR/EJECUTAR/TRAZAR (el
wizard + preview + auditoría). Los eslabones débiles, verificados por código:

- **EXPLICAR** (resultado explicable, Sección 15): hoy es una alerta corta con el monto
  y número de documento, no un panel de efectos financieros detallados (qué fondos
  cambiaron, qué compromiso se liberó). → `NXR-UX-0012`.
- **ENTENDER en contexto de una entidad** (páginas de contexto, Sección 16): no existe
  una vista 360° de proyecto. El dashboard es global; los contratos tienen un resumen
  parcial pero no pestañas completas. → `NXR-UX-0010`.
  **Actualización (Bloque 17):** construida (`nexora-project`, `context360/`) —
  ver `NEXORA_30_BLOCKS_AUDIT.md`. NO DEMOSTRADO en vivo, ya no "no existe".
- **CONTINUAR sin perder contexto** (drill-down, Sección 19): existe navegación a
  reportes desde el dashboard, pero no expansión inline de la composición de un número
  en el mismo lugar. → `NXR-UX-0013`.

## Barra NEXORA Universal (Secciones 10 y 11 de la misión)

**Estado real: no existe como concepto unificado.** Hoy son piezas separadas:

```
[Buscar (nexora_search.js)]     → motor de búsqueda con permisos, sin NLU
[Registrar ingreso/gasto (nexora.js)] → 2 acciones fijas, sin catálogo de "qué necesitas hacer"
[Wizard guiado (nexora_guided_operations.js)] → INTERPRETAR→VALIDAR→PREVIEW→CONFIRMAR→EJECUTAR ya
                                                  implementado, pero solo alcanzable navegando
                                                  manualmente al formulario, no desde una barra
```

Para llegar a la barra descrita en la misión (consulta en lenguaje natural → interpretación
mostrada → preview → confirmación → ejecución → auditoría) faltan dos piezas nuevas, no
una reconstrucción de las tres existentes:

1. Una capa de interpretación de lenguaje natural que traduzca la consulta a una
   estructura (tipo de operación, entidad, proyecto, monto, período) — no existe hoy
   (`grep` de "lenguaje natural"/NLU sin resultados en el repo). Esto es exactamente el
   alcance de `NIP_BLOQUE_6_CONVERSATIONAL_OS.md`, ya diseñado pero sin código
   (`nexora_app/nexora/conversation/` está vacío).
2. Un punto de entrada único en la UI que reemplace/unifique la barra de búsqueda actual
   con la posibilidad de iniciar una acción, reutilizando el wizard y el preview que ya
   existen como motor de ejecución — la barra es una nueva fachada sobre motores que ya
   funcionan, no un nuevo motor financiero.

**Actualización (Bloque 18, cierre de los 30 bloques):** la pieza 1 (capa de NLU) se
construyó de verdad — `conversation/` (1091 líneas, `NXR-CNV-0001`) implementa
exactamente la arquitectura descrita abajo (interpretar → dominio → permisos →
preview → confirmación → ejecución → auditoría), reutilizando las funciones de
dominio reales, nunca un segundo camino. La pieza 2 (fachada única que sustituya la
barra de búsqueda actual) **no se construyó** — el asistente vive en una pantalla
propia (`nexora-assistant`), separada de `nexora_search.js`, no como un reemplazo
de la barra existente. La "Barra NEXORA Universal" unificada sigue sin existir como
concepto único; existen dos piezas reales y separadas donde antes no había ninguna.

Arquitectura obligatoria a respetar cuando se construya (Sección 26 de la misión, ya
alineada con cómo está construido el resto del sistema):

```
IA interpreta / propone
        ↓
Dominio valida (financial/, contracts/, purchases/ — código ya existente)
        ↓
Permisos validan (permissions.require_action — código ya existente)
        ↓
Usuario confirma (preview ya existente)
        ↓
Dominio ejecuta (execute() ya existente)
        ↓
Auditoría registra (NXR Audit Event — ya existente)
```

Ningún adaptador de IA debe escribir directamente en `NXR Operation`/`NXR Commitment`:
debe llamar a los mismos servicios (`financial/operations.py`, `financial/commitments.py`)
que ya usan la UI y that ya tienen permisos y auditoría. Esto no es una recomendación
nueva, es una restricción que ya cumple todo el código existente — la nueva capa solo
debe heredarla, no inventar un segundo camino.

## Design System como base de la Super Experience

`public/css/nexora_design_system.css` (662 líneas, tokens `--nxr-*` en tres capas) es la
base real sobre la que debe construirse cualquier componente nuevo (Command Bar, timeline
universal, página 360°). No crear un sistema de estilos paralelo: extender este.

## Móvil real (Sección 27)

Confirmado: PWA con manifest/service worker reales, safe-area-inset aplicado, objetivos
táctiles de 44px. Falta: navegación inferior tipo app nativa (hoy es drawer lateral
colapsado) y captura de cámara nativa para evidencia (hoy es `Attach` genérico). Ambas
son extensiones acotadas del código existente, no una reconstrucción del shell móvil.

## Principio de no sacrificar integridad por UX (Sección 70)

Verificado que no hay violaciones: ningún atajo de UX encontrado en esta auditoría
elimina permisos, oculta errores o salta validación de servidor. El único patrón a
vigilar hacia adelante es el propio Conversational OS: su diseño ya documentado exige
confirmación humana obligatoria antes de cualquier efecto financiero — se valida en el
Bloque de implementación, no se asume aquí.
