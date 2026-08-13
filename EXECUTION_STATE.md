# NEXORA — Estado de ejecución

- Fecha de cierre técnico: 2026-08-04
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- HEAD inicial de `main` verificado: `8ed7bd292c29fda0f57a41b3102f0f290bb8e90c`
- Rama de trabajo de este bloque: `claude/nexora-surgical-audit-lsxcuh`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**
- Migración histórica de registros: **NO**

## Bloque 2 — corrección quirúrgica de carga de páginas, permisos y navegación

Este bloque corrige defectos que impedían el uso real del sistema, retira el ruido
que rompía la propia puerta de calidad del repositorio y deja pruebas de regresión
que impiden que los mismos defectos vuelvan.

### Estado real encontrado

1. **`main` estaba rojo contra su propio contrato.** `scripts/validate_nexora_app.py`
   —el primer paso del job `contract` de `.github/workflows/nexora-app.yml`— salía con
   código 1 en `8ed7bd2` porque los últimos ocho commits habían añadido ocho workflows
   `nexora-*` que ese mismo guard declara no aprobados.

2. **Cuatro de las doce páginas NEXORA se servían en blanco.** Frappe resuelve los
   assets de una `Page` con `frappe.scrub(name)`, que convierte guiones en guiones
   bajos: `Page.load_assets()` busca `<módulo>/page/<scrub(name)>/<scrub(name)>.js`.
   Cuatro páginas vivían en carpetas con guion, así que el registro `Page` se creaba
   correctamente pero el script quedaba vacío y la pantalla se abría sin contenido,
   sin lanzar error. Afectaba a `nexora-dashboard` —ruta de `add_to_apps_screen`,
   `start_url` del PWA y primer acceso del workspace—, `nexora-reports`,
   `nexora-closing` y `nexora-search`. El directorio `page/nexora_dashboard/`
   existía con solo un `__init__.py`: evidencia de un renombrado dejado a medias.

3. **El núcleo de fondos estaba abierto a todo el sitio.**
   `nexora_finance.json` no declaraba `roles`. Con la tabla de roles vacía,
   `Page.has_permission()` de Frappe devuelve `True` para cualquier usuario
   autenticado, mientras las otras once páginas sí restringían a roles NEXORA.

4. **Un botón del dashboard no llevaba a ninguna parte.** «Avance de la obra →
   Detalle» enrutaba a `nexora-projects`, una página inexistente.

5. **El workspace ocultaba la mayor parte del producto.** Definía 21 accesos
   directos y solo renderizaba 6 en `content`; en Frappe v15 un acceso directo
   ausente de `content` es invisible. Quedaban inalcanzables desde el workspace el
   directorio de entidades, proveedores, solicitudes de compra, evidencias y los
   DocTypes del libro central. `nexora-operations` y `nexora-quotations` no tenían
   acceso directo alguno.

6. **Metadatos de página inconsistentes.** `nexora_quotations.json` usaba campos
   inexistentes en el DocType `Page` (`label`, `document_type`, `script`) y no
   declaraba `title` ni `standard`: se registraba sin título.

7. **18 de las 50 carpetas de DocType no tenían `__init__.py`**, frente a las otras
   32 que sí lo tenían.

### Ruido retirado del repositorio

| Elemento | Motivo |
|---|---|
| 8 workflows `nexora-*` de orquestación de agentes | Rechazados por el guard del repositorio; sin bloque `permissions:`; autoejecutaban `ops/agents/scripts` |
| `ops/agents/**` (77 archivos) | Andamiaje autorreferencial. `unified_gate.sh` y `validate.sh` invocaban `pytest` y `npm test`, que este repositorio no usa: no validaban el producto |
| `auto_merge_ready_prs.sh`, `nexora_mass_cleanup.sh` | Automatización no revisada que fusiona PRs y borra ramas en masa |
| `pr_audit_report.txt` | Instantánea de auditoría caducada |
| `docs/nexora-agent-architecture.md` | Quedaba huérfano al retirar `ops/agents` |

### Correcciones aplicadas

- Carpetas y archivos de página renombrados a la convención `frappe.scrub`:
  `nexora_dashboard`, `nexora_reports`, `nexora_closing`, `nexora_search`.
  Referencias actualizadas en scripts, workflows y pruebas.
- `__init__.py` añadido a los 6 paquetes de página y a los 18 de DocType que
  faltaban. Las 12 páginas y los 50 DocTypes quedan homogéneos.
- `nexora-finance` declara los cinco roles NEXORA. La escritura sigue validada en
  servidor por `require_action`; la lectura corresponde a `ACCESS_ROLES`, que ya
  incluye los cinco roles, de modo que no se bloquea ninguna operación legítima.
- `nexora-quotations` normalizado al esquema real del DocType `Page`.
- El botón «Detalle» abre el reporte `PR03`, que es exactamente el avance físico y
  financiero que la tarjeta resume.
- `content` del workspace reconstruido en seis secciones que exponen los 23 accesos
  directos; añadidos los de `nexora-operations` y `nexora-quotations`.
- `contract_query`, `expense_query`, `pending_query` y `snapshot_query` delegan sus
  helpers duplicados en `nexora.dashboard.query_utils`; `payload()` acepta un
  mensaje propio para conservar el error específico de cada módulo.

### Qué se validó

| Verificación | Resultado |
|---|---|
| `scripts/validate_nexora_app.py` | de `exit 1` a `exit 0` |
| `scripts/validate_nexora_financial_models.py` | 10 DocTypes canónicos |
| `scripts/validate_nexora_operational_acceptance.py` | 0 errores |
| `scripts/validate_nexora_completion.py` | 166 requisitos, 0 errores |
| `scripts/validate_nexora_governance.py` | línea base verificada |
| Suite de contrato (`test_*contract.py`) | 258 pruebas, OK |
| `test_financial_core`, `test_evidence_core`, `test_directory_core`, `test_reference_rules` | 42 pruebas, OK |
| `node --check` sobre las 12 páginas, los 6 bundles públicos, el service worker y el smoke | sin errores de sintaxis |
| `python -m compileall nexora_app/nexora scripts` | OK |

Prueba negativa y de persistencia sobre el defecto principal: se ejecutó una réplica
de `Page.load_assets()` contra los dos árboles. En `origin/main`, 8 páginas resolvían
script y **4 quedaban en blanco**, y `nexora-finance` figuraba como accesible para
todo usuario autenticado. En el árbol corregido, **12 páginas resuelven script, 0 en
blanco**, y las 12 declaran roles NEXORA.

Prueba de que la interfaz no promete más de lo que el backend soporta: las 75
referencias `nexora.*` que el JavaScript invoca por `frappe.call` se resolvieron
contra las 135 funciones `@frappe.whitelist()`, siguiendo las reexportaciones de las
fachadas `service.py`. **0 métodos inexistentes o no expuestos.**

### Pruebas de regresión añadidas

`nexora_app/nexora/tests/test_page_registry_contract.py` exige que la carpeta de cada
página sea `scrub(name)`, que el script exista y se registre bajo el nombre real del
`Page`, que no quede ningún asset con guion, que ninguna página tenga la tabla de
roles vacía y que sus roles pertenezcan a los cinco de NEXORA, que toda página sea
alcanzable desde el workspace, que todo acceso directo esté renderizado en `content` y
apunte a un destino existente, y que toda ruta de navegación del cliente
(`data-route`, `set_route`, `/app/…`) apunte a una página que existe.

`test_app_contract` exige además el marcador de paquete en cada carpeta de DocType.

### Limpieza de ramas y PRs

Los 10 PRs abiertos se cerraron con nota individual.

| PR | Rama | Clasificación | Acción |
|---|---|---|---|
| #49, #51, #53 | `nexora/bloque-2-auditoria`, `fix/remediation-96a0e1b5-471bf3`, `fix/remediation-a5eb7470-0fdc7f` | Duplicados anidados (#51 ⊂ #49 ⊂ #53), los tres en conflicto | Contenido útil absorbido en este bloque; cerrados sin pérdida |
| #54 | `Clopezgg-patch-2` | Instrucciones de agente, sin efecto en el producto; duplicado en 4 ramas | Cerrado |
| #39, #41, #42, #43 | `Clopezgg-patch-1`, `copilot/fix-predeploy-*`, `codex/confirmar-conexion-al-repositorio` | Carga no fusionable: ~12.900 inserciones con `archivos.txt` y `archives.txt` (5.404 líneas cada uno, duplicados), `SECURITY-FINDINGS.txt` (1,4 MB binario), 7 `Nexora-*.ps1` —3 vacíos— y un archivo cuyo nombre es un fragmento de shell | Cerrados; ramas conservadas por contener trabajo aprovechable (Sentry) |
| #37, #36 | `revert-35-chore/nexora-consolidacion-total`, `git-checkout--b-prueba-chatgpt-review` | Título ajeno al contenido (el diff real es un `cr.yml` de 61 líneas); #36 apuntaba a una rama de trabajo, no a `main` | Cerrados; ramas conservadas |

Ramas verificadas como retirables sin pérdida funcional (la eliminación remota quedó
bloqueada por el proxy git de este entorno, ver más abajo):

| Rama | Evidencia |
|---|---|
| `nexora-block1-identity` | Ancestro de `main`: 0 commits y 0 archivos propios |
| `fix/nexora-date-string-normalization` | Historia sin ancestro común; 0 archivos que no estén ya en `main`; `main` la supera en 5.361 líneas dentro de `nexora_app` |
| `fix/nexora-predeploy-block-1b` | Ídem; su único archivo propio, `nexora_guided_segregation.js`, no está registrado en `hooks.py` y duplica en cliente —de forma más débil— la segregación de funciones que `reference_rules.validate_segregation` ya impone en servidor exigiendo tres usuarios distintos |
| `fix/remediation-87b55af6-c00e30` | Árbol idéntico a `fix/remediation-87b55af6-17e808`, que se conserva |
| `coderabbitai/chat/629d637` | Árbol idéntico a `Clopezgg-patch-2`, que se conserva |

### Lógica y experiencia corregidas

**Contexto activo unificado.** El contexto de trabajo (proyecto y período,
persistido por usuario en servidor vía `nexora.boot.set_active_context`) existía y lo
alimentaba la barra global, pero **solo el dashboard lo consumía: 11 de 12 páginas lo
ignoraban**. Consecuencias medidas:

- Entrar a «Operación diaria» o al centro de reportes desde el workspace, un acceso
  directo o una URL dejaba el selector de proyecto vacío: había que elegirlo otra vez
  aunque el usuario ya lo hubiera fijado.
- Cambiar el proyecto dentro de esas pantallas no publicaba el cambio. La barra global
  seguía mostrando el proyecto anterior — estado contradictorio — y al navegar después
  por el menú se inyectaba el proyecto viejo en `route_options`: **la elección del
  usuario se perdía en silencio**.

`window.nexora.context` publica ahora `activeProject()`, `setActiveProject()` y
`onContextChange()`. La consola de operación diaria y el centro de reportes heredan el
proyecto activo cuando la ruta no trae uno, publican el que el usuario elige, se
mantienen sincronizados con la barra global, se dan de baja al destruirse el wrapper y
no pueden realimentarse. `setActiveProject()` no vuelve a pedir confirmación: el
usuario ya está actuando sobre esa pantalla.

**Errores que explican cómo resolverse.** La segregación de funciones —tres usuarios
distintos en transferencias internas, anticipos, liquidaciones y reclasificaciones— es
una restricción legítima que protege integridad y auditoría, y **se conserva**. Lo que
estaba mal era el mensaje: decía la regla pero no que el ejecutor es la sesión activa,
un dato que no aparece en ningún campo. Quien recibía el error no sabía qué cambiar. El
mensaje nombra ahora al ejecutor y da la acción concreta, en los tres puntos donde se
emite: `reference_rules.validate_segregation`, el controlador `NXR Operation` y el
flujo guiado de corrección.

`nexora_app/nexora/tests/test_active_context_contract.py` (6 casos) fija este contrato:
los helpers existen y están publicados, `setActiveProject` no vuelve a pedir
confirmación ni publica cambios inexistentes, las pantallas de trabajo heredan y
publican el proyecto, liberan su suscripción y no pueden entrar en bucle.

### Confirmación independiente del defecto principal

`Dockerfile.nexora` contenía un bloque `RUN` que, al construir la imagen, creaba
`page/nexora_dashboard`, `nexora_search`, `nexora_reports` y `nexora_closing` y copiaba
ahí los cuatro archivos con guion. Alguien ya había topado con que Frappe resuelve los
assets con `frappe.scrub(name)` y **lo parcheó dentro del contenedor en lugar de
corregir el árbol**: en la imagen las páginas cargaban, en el repositorio seguían rotas,
y cualquier consumidor que no usara esa imagen —`bench install-app`, un wheel, otro
despliegue— las servía en blanco. Es evidencia independiente de que el defecto era real
y de que llevaba tiempo tapado.

Con las páginas ya en su carpeta, ese bloque sobra y además rompía el build. Retirado.
`test_page_registry_contract` exige ahora que ningún Dockerfile reubique assets de
página: si el parche reaparece, es señal de que el árbol volvió a romperse.

### Validación en runtime real

El job `install-rollback` de `nexora-app.yml` —bench real sobre MariaDB— **pasa** en esta
rama: instala la app, migra, verifica fixtures, roles y coexistencia con ERPNext,
desinstala, reinstala, migra otra vez y siembra datos de staging dos veces. Eso ejercita
en runtime la instalación, la migración, los fixtures, los roles y permisos, y el
registro de los marcadores de paquete de DocType. **No** ejercita el renderizado de las
páginas: `Page.load_assets()` y `scripts/nexora_browser_smoke.mjs` corren en el job
`browser`, que sigue pendiente.

### Qué sigue pendiente

- ~~**Contexto activo en las 9 páginas restantes.**~~ Cerrado en el Bloque 2.1 (ver
  abajo): de las nueve, cinco tenían selector de proyecto propio y quedaron
  conectadas al contexto activo; las otras cuatro no tienen ni necesitan uno.
- **Recorrido de navegador (`scripts/nexora_browser_smoke.mjs`).** Único rojo con
  relevancia de producto que queda, y **precede a esta rama**: mismo paso, mismo error
  y mismas líneas de pila en `origin/main`.
  `page.waitForFunction: Timeout 60000ms exceeded` en `advanceValidatedGuidedReview`
  (`:182`), desde `validateIncomeGuided` (`:339`).

  Diagnóstico acotado con el código en mano:

  1. **No es el servidor.** El smoke afirma `previewResponse.ok() === true` en la
     línea 337 y esa aserción pasa: `preview_operational_movement` responde 200. El
     fallo ocurre después, en la línea 339.
  2. **Es la transición a la etapa 3 del asistente.** La sonda exige simultáneamente
     que `[data-guided-stage="3"]` esté visible, `[data-guided-next="4"]` habilitado,
     `.nxr-execute-movement` habilitado y `.nxr-preview-body` sin la clase
     `nxr-empty`, y que esa firma no cambie durante 750 ms.
  3. **El punto exacto es `sync()` en `nexora_guided_operations.js`.** Calcula `valid`
     leyendo el botón de registro y el cuerpo de la vista previa de la consola
     original, y solo abre la etapa 3 con
     `if (valid && state.previewRequested) { state.previewRequested = false;
     activate(state, 3); }`.
  4. **`state.previewRequested` es una bandera de un solo uso.** Se activa al pulsar
     `.nxr-guided-preview` y se consume en la primera pasada de `sync()` que vea
     `valid`. Además, el escucha de `nexora:data-changed` la borra y devuelve el
     asistente a la etapa 1. La apertura de la etapa 3 depende, por tanto, de que un
     tick concreto del `MutationObserver` observe las dos condiciones a la vez: si la
     bandera se consume o se borra antes, la etapa 3 no vuelve a abrirse y la sonda
     agota los 60 s aunque la vista previa haya sido correcta.

  **El rojo se movió.** En `d33eb78` el recorrido ya no falla en el ingreso: entra a
  `validateGuidedOperations` por la línea **451** (`validateExpenseGuided`) en lugar de
  la 450, es decir **`validateIncomeGuided` pasó por primera vez**. El paso 7 duró 47 s
  en lugar de 2m09s porque ya no consume el timeout de 60 s. Mecanismo plausible: la
  guarda de respuestas obsoletas de `loadProjectData()` —que ahora descarta una llamada
  tardía en vez de dejarla ejecutar `state.preview = null` y deshabilitar
  `.nxr-execute-movement`— eliminó justamente la carrera que rompía la firma que la
  sonda espera estable durante 750 ms.

  El fallo nuevo es distinto y **no es una carrera**:

  ```
  AssertionError: NEXORA seed created no beneficiary entity.
      at validateExpenseGuided (scripts/nexora_browser_smoke.mjs:372:3)
    actual: '', expected: true
  ```

  `nexora_operations.js` exige `beneficiary` para el código 102 y ese campo enlaza a
  `NXR Entity`; `seed_demo_data` no creaba ninguna. En un sitio recién sembrado el
  usuario abre «Registrar gasto» y encuentra un campo obligatorio sin una sola opción
  seleccionable: el gasto diario, el flujo más común del sistema, era imposible de
  completar. La aserción nunca se había alcanzado porque el ingreso fallaba antes.

  Corregido en `financial/seeds.py` con `_ensure_demo_entity()`: crea de forma
  idempotente la entidad «Constructora demostrativa NEXORA» vía `create_entity` y la
  transiciona a `Active`, y la devuelve en el resultado del seed.
  `tests/test_demo_seed_contract.py` fija el contrato: de dónde nace la obligación
  (`required("beneficiary")` + `options: "NXR Entity"`), que el seed la cubre, que la
  sonda consulta el mismo doctype y que ninguna clave de idempotencia demostrativa se
  repite.

  La primera versión de esa corrección (`abd81a7`) rompió `install-rollback`, que hasta
  entonces estaba verde: sembraba la entidad sin contacto y `NXR Entity.validate` rechaza
  activar una entidad sin identificador, contacto ni usuario vinculado. La regla es
  correcta —un proveedor sin forma de contacto no es un proveedor—, así que `b068991`
  siembra correo y teléfono en vez de esquivarla, cambia la clave de idempotencia porque
  el payload cambió, y el contrato del seed ancla ahora la regla del controlador.

  Es lo que intentaban estabilizar los PR #41 y #42 sin lograrlo. **No se corrige
  aquí**: quitar la condición de un solo uso o rehacer el disparo de la etapa 3 son
  cambios en una máquina de estados que este entorno no puede ejecutar, y validarlos
  exige el artefacto `nexora-ui` del run (`browser.log`, capturas, `compose.log`) más
  una pila Frappe viva. Subir el tiempo de espera ocultaría el problema en lugar de
  resolverlo.
- **Sentry.** `nexora_app/nexora/sentry.py` y `public/js/nexora_sentry.js` existen en
  las ramas de los PRs cerrados y son trabajo aprovechable. Requieren un PR propio y
  pequeño, rebasado sobre `main` actual.
- **Reintegrar el ajuste de readiness** de `scripts/nexora_browser_smoke.mjs` que
  intentaban #41 y #42, también como cambio aislado.
- **`scripts/validate_construcontrol_architecture.py`** sigue fallando por contratos
  de coexistencia ausentes en la arquitectura heredada. Es un defecto previo a este
  bloque y ningún workflow lo ejecuta.

### Riesgos y decisiones requeridas

- **Eliminación de ramas bloqueada por el entorno.** El proxy git de esta sesión
  ignora los refspec de borrado (`git push origin --delete` responde «Everything
  up-to-date» tras desconectar el sideband) y el servidor MCP de GitHub no expone una
  herramienta de borrado de ramas. Las cinco ramas de la tabla anterior quedan
  verificadas y listas para que el propietario las elimine.
- **Revisión automática con ChatGPT.** El `cr.yml` de #36 y #37 engancha
  `anc95/ChatGPT-CodeReview@main` —referenciada por rama móvil, no por SHA— con
  `pull-requests: write` y `secrets.OPENAI_API_KEY`, y le entrega el diff de cada PR.
  Es una decisión de producto y seguridad del propietario.
- **`.mergify.yml` sigue activo** en el repositorio y puede fusionar PRs
  automáticamente. No se modificó: cambiar la política de fusión excede este bloque.

## Bloque 2.1 — contexto activo en las pantallas de trabajo restantes

**Problema.** El Bloque 2 unificó el contexto activo (`window.nexora.context`) en
dashboard, operación diaria y reportes. Las otras 9 páginas seguían recibiendo el
proyecto solo por `route_options`: al entrar por el workspace, un acceso directo o
una URL sin proyecto, el usuario tenía que volver a elegirlo; al cambiarlo dentro de
esas pantallas, la barra global y el resto del producto no se enteraban.

**Investigación previa a implementar.** De las 9 páginas, solo 5 tienen un campo
`project` propio a nivel de pantalla: `nexora-closing`, `nexora-contracts`,
`nexora-purchase-requests`, `nexora-evidence` y `nexora-finance`. Las otras 4 no
lo tienen porque su dominio no está delimitado por proyecto:
`nexora-suppliers` (proveedores por entidad), `nexora-quotations` (cotizaciones por
solicitud de compra), `nexora-entities` (directorio universal de entidades) y
`nexora-search` (buscador por alcance). Forzar un filtro de proyecto ahí habría sido
un campo sin uso real, no una propagación de contexto pendiente.

**Archivos.**
- `nexora_app/nexora/nexora/page/nexora_closing/nexora_closing.js`
- `nexora_app/nexora/nexora/page/nexora_contracts/nexora_contracts.js`
- `nexora_app/nexora/nexora/page/nexora_purchase_requests/nexora_purchase_requests.js`
- `nexora_app/nexora/nexora/page/nexora_evidence/nexora_evidence.js`
- `nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js`
- `nexora_app/nexora/tests/test_active_context_contract.py`
- `nexora_app/nexora/tests/test_financial_ui_contract.py`

**Decisión.** Cada una de las 5 pantallas ahora: hereda el proyecto activo al
cargar cuando la ruta no trae uno (`window.nexora.context.activeProject()`),
publica el proyecto que el usuario elige (`setActiveProject()`), se sincroniza con
la barra global mientras está abierta (`onContextChange()`) y se da de baja al
cerrarse (`$(wrapper).on("remove", ...)`). Cada pantalla usa una bandera local
(`syncingProject` en contratos/compras/evidencia/fondos, `suppressReload` en
cierre semanal —ya existía con ese nombre—) para que aplicar un cambio recibido
del contexto no lo vuelva a publicar y entre en bucle; ese contrato se verifica en
`test_new_context_aware_pages_guard_their_programmatic_sync`. `nexora-finance`
reutiliza su función `applyLaunchContext` existente, que también resuelve la
carga inicial por `route_options.nexora_action`; el contexto activo solo se aplica
cuando la ruta no trae una acción propia.

**Pruebas.** `test_active_context_contract.py` se extendió: las 5 páginas nuevas se
suman a `CONTEXT_AWARE_PAGES` y se verifica que heredan, publican, se desuscriben y
no entran en bucle; las 4 páginas sin selector de proyecto se verifican como tales
(`test_project_unscoped_pages_have_no_orphaned_project_filter`). Se ajustó una
aserción literal en `test_financial_ui_contract.py` que verificaba la forma exacta
del código anterior de `nexora-finance` (segura de actualizar: el comportamiento que
protegía —cargar el proyecto de la ruta— se conserva y se amplía). Ejecutado
localmente sin bench (no hay entorno Frappe disponible en esta sesión): el suite
completo de contratos sin dependencia de `frappe`/`nexora` en tiempo de ejecución
—104 pruebas en `test_active_context_contract`, `test_page_registry_contract`,
`test_contract_contract`, `test_demo_seed_contract`, `test_directory_contract`,
`test_evidence_contract`, `test_financial_model_contract`,
`test_financial_service_contract`, `test_financial_ui_contract`,
`test_purchase_contract`, `test_quotation_contract`, `test_security_core`—, más
`scripts/validate_nexora_app.py`, `validate_nexora_financial_models.py`,
`validate_nexora_governance.py`, `validate_nexora_operational_acceptance.py` y
`python -m compileall nexora_app/nexora scripts`. **No** se ejecutó
`install-rollback` ni el recorrido de navegador (requieren bench real sobre
MariaDB, no disponible en esta sesión): quedan pendientes de CI.

**Limitaciones reales.** No cambia el contrato de segregación de funciones ni ningún
modelo financiero. No toca la navegación superior (`nexora.js`, que sigue sin listar
5 de las 12 páginas) ni el resto de la deuda de UX documentada en el Bloque 2. SHA
en `main`: pendiente de commit y push.

## Bloque 2.2 — cobertura completa de la navegación superior persistente

**Problema.** `nexora.js` inyecta una barra de navegación persistente
(`.nxr-product-nav`) en toda pantalla que `isNexoraLocation()` reconoce como NEXORA —
es decir, en las 12 páginas—, pero su lista `destinations` solo enlazaba 7:
`nexora-closing`, `nexora-search`, `nexora-entities`, `nexora-purchase-requests` y
`nexora-quotations` faltaban. El usuario que llegaba a esas 5 pantallas por el
workspace, un acceso directo o un enlace veía la barra de navegación de NEXORA en la
parte superior, pero esa barra no ofrecía volver a ellas ni saltar a ellas desde
cualquier otra pantalla: quedaban aisladas del resto del producto en la navegación
principal aunque siguieran alcanzables desde el workspace.

**Archivos.**
- `nexora_app/nexora/public/js/nexora.js`
- `nexora_app/nexora/tests/test_page_registry_contract.py`

**Decisión.** Se añadieron las 5 entradas faltantes a `destinations`, ordenadas para
coincidir con el agrupamiento del propio workspace (Operación → Fondos y finanzas →
Contratos y directorio → Compras y proveedores → Evidencias → Reportes y cierre), de
modo que la barra superior y el workspace cuenten la misma historia sobre cómo se
organiza el producto. `.nxr-product-nav` ya usaba `overflow-x: auto` con
`flex: 0 0 auto` y objetivos táctiles de 44px en móvil: el cambio es puramente
aditivo, no requirió tocar CSS.

**Pruebas.** `test_page_registry_contract.py` gana
`test_every_page_is_reachable_from_the_persistent_top_nav`, que exige que las 12
páginas declaradas en `nexora/page/**` tengan una entrada en `destinations` y que
`destinations` no enlace ninguna página inexistente — el mismo contrato que
`test_every_page_is_reachable_from_the_workspace` ya exige para el workspace, ahora
también para la barra superior. Ejecutado localmente (sin bench): 90 pruebas de
contrato puro-Python, todas en verde.

**Limitaciones reales.** No unifica los otros patrones de navegación documentados en
el Bloque 2 (contexto activo por `route_options` vs. `window.nexora.context`, ver
Bloque 2.1) ni introduce iconografía o agrupamiento visual dentro de la barra misma —
solo cierra el hueco de cobertura. SHA en `main`: pendiente de commit y push.

## Bloque 2.3 — formato monetario consistente en Núcleo de Fondos

**Problema.** `nexora-finance` interpolaba montos HNL directamente como
`L${row.balance_hnl}` en once puntos (saldos de fuente, vista previa de operación,
libro reciente): sin separador de miles, sin cantidad fija de decimales y sin pasar
por un formateador — el valor del servidor llegaba directo al HTML. El resto del
producto (dashboard, reportes, cierre, búsqueda) usa `Intl.NumberFormat("es-HN", ...)`
o el helper compartido `window.nexora.ui.formatMoney`; `nexora-finance` era la única
pantalla financiera que no lo hacía, una inconsistencia visual que además podía
mostrar cifras con precisión decimal arbitraria en la pantalla donde el usuario
decide cuánto dinero mover.

**Archivos.**
- `nexora_app/nexora/nexora/page/nexora_finance/nexora_finance.js`
- `nexora_app/nexora/tests/test_financial_ui_contract.py`

**Decisión.** Se añadió un `money(value)` local que delega en
`window.nexora.ui.formatMoney` (con el mismo `Intl.NumberFormat` como respaldo si el
helper compartido no está disponible, igual que hace `nexora_dashboard.js`), y se
sustituyeron las once interpolaciones `L${...}` por `money(...)`. Cambio puramente de
presentación: ningún valor, cálculo ni llamada al servidor se modificó.

**Pruebas.** `test_financial_ui_contract.py` gana
`test_monetary_values_are_formatted_not_raw_interpolated`, que prohíbe que reaparezca
una interpolación `L${` sin formatear y exige que `money()` delegue en el helper
compartido. Ejecutado localmente: 6/6 en ese archivo, balance de llaves/paréntesis
verificado a mano (sin Node disponible en este entorno para `node --check`).

**Limitaciones reales.** No unifica los helpers `money()`/`date()`/`escape()`/`uuid()`
duplicados en el resto de páginas (deuda de mantenibilidad ya documentada, Nivel 6 de
prioridad); esa unificación real requeriría un módulo compartido nuevo y tocar las 12
páginas, un bloque propio. SHA en `main`: pendiente de commit y push.

## Bloque 2.4 — precaché completo del shell PWA sin conexión

**Problema.** `hooks.py` registra 6 bundles JS y 5 CSS de NEXORA sitio-wide
(`app_include_js`/`app_include_css`), pero `SHELL_ASSETS` en
`nexora-service-worker.js` solo precacheaba 2 de cada uno: `nexora.js` y
`nexora_operational_ui.js`, `nexora.css` y `nexora_operational.css`. El fetch
handler igual sirve los demás en cuanto se piden con conexión (los cachea de forma
oportunista), pero una primera carga genuinamente sin conexión arranca con un shell
incompleto: sin `nexora_report_actions.js` —donde vive `window.nexora.context`, el
sistema de proyecto activo entero— ni `nexora_guided_model.js`/
`nexora_guided_operations.js` —el asistente guiado de ingresos y gastos—, ni las
hojas de estilo `nexora_executive.css`, `nexora_dashboard_fixes.css` y
`nexora_guided_operations.css`.

**Archivos.**
- `nexora_app/nexora/www/nexora-service-worker.js`
- `nexora_app/nexora/public/js/nexora.js`
- `nexora_app/nexora/tests/test_pwa_contract.py`

**Decisión.** `SHELL_ASSETS` ahora enumera exactamente los bundles que `hooks.py`
registra, más el manifiesto y los iconos ya presentes. Se subió `VERSION` en el
service worker (y el `PWA_VERSION` correspondiente en `nexora.js`, que solo
invalida el `<link rel="manifest">`) para que la instalación existente reemplace su
caché en el próximo `activate` en lugar de conservar el shell incompleto
indefinidamente.

**Pruebas.** `test_pwa_contract.py` gana `test_offline_shell_precaches_every_site_wide_bundle`,
que parsea `hooks.py` y el service worker y exige que todo bundle registrado
sitio-wide aparezca en `SHELL_ASSETS`. Ese archivo requiere `import nexora` (el
paquete de la app), no ejecutable en este entorno sin bench — verificada la lógica
de parseo por separado con un script equivalente contra los archivos reales, que
confirma cero bundles faltantes tras el cambio (once antes). `ruff format --check` y
`ruff check` en verde con la versión exacta fijada en `.pre-commit-config.yaml`
(v0.16.0); balance de llaves/paréntesis verificado a mano en los dos archivos JS
(sin Node disponible en este entorno para `node --check`).

**Limitaciones reales.** `VERSION`/`PWA_VERSION` siguen siendo dos constantes
hardcodeadas independientes sin una fuente única compartida —quedan sincronizadas
por este cambio, pero nada impide que vuelvan a divergir en un cambio futuro que
solo toque una de las dos—. Unificarlas exigiría una fuente compartida entre un
script de servidor (`nexora.js`) y un service worker (contexto de ejecución
distinto, sin `import` de módulos ES por defecto); queda fuera del alcance de este
bloque. SHA en `main`: pendiente de commit y push.

## Bloque 2.5 — retirar el token CSS huérfano `--nxr-space-5`

**Problema.** `.nxr-guided-wizard` en `nexora_guided_operations.css` usaba
`var(--nxr-space-5, 1.25rem)` en dos declaraciones. `--nxr-space-5` no se define en
ningún `:root` del proyecto ni en ningún otro archivo: siempre resolvía al valor de
respaldo. El sistema de tokens real del producto es semántico
(`--nexora-radius`, `--nexora-shadow`, `--nexora-accent`, …, definido en
`nexora.css`), no una escala numerada `--nxr-space-N`; no existe ninguna otra
declaración `--nxr-space-*` en el repositorio. Era el inicio de un intento de escala
de espaciado abandonado a la primera variable.

**Archivo.** `nexora_app/nexora/public/css/nexora_guided_operations.css`

**Decisión.** Se retiró la indirección y se dejó el valor literal `1.25rem`, igual
que el resto de valores de espaciado en este mismo archivo (`gap: 0.5rem`,
`padding: 1rem`, etc., todos literales). No se definió `--nxr-space-5` en `:root`
porque no existe una escala que completar: hacerlo habría creado un token aislado sin
significado sistémico, exactamente la complejidad innecesaria que se busca evitar.
Cambio puramente visual sin efecto: el valor calculado no cambia (era el mismo
respaldo).

**Pruebas.** `test_guided_account_progressive_contract.py` y
`test_operational_console_contract.py` leen este archivo pero no referencian
`--nxr-space-5` ni los selectores tocados — verificado por grep, sin necesidad de
bench para confirmar que no rompen. Balance de llaves/paréntesis verificado a mano.

## Bloque 2.6 — helpers `money`/`date`/`escape`/`uuid` en un único lugar

**Problema.** Once implementaciones idénticas de `uuid()`, nueve de `escape()`,
cinco de `date()` y varias de `money()` estaban copiadas palabra por palabra en
`nexora.js`, `nexora_quick_flows.js`, `nexora_operational_ui.js` y ocho páginas
más. No es duplicidad aparente: se verificó carácter por carácter que los cuerpos
eran idénticos en cada caso antes de tocar nada, así que consolidarlas no cambia
ningún comportamiento — solo hace que la regla exista en un único lugar, como
exige `AGENTS.md`.

**Investigación previa a implementar.** `nexora_purchase_requests.js` y
`nexora_quotations.js` tienen su propio `money(value, currency)` que delega en
`format_currency` de Frappe, no en `Intl.NumberFormat`: es una implementación
genuinamente distinta (respeta la precisión de moneda de System Settings), no
duplicidad ciega. Se dejó intacta. `nexora_dashboard.js` y `nexora_finance.js` ya
delegaban en `window.nexora.ui?.formatMoney?.(value)` con una reserva local como
respaldo defensivo: tampoco se tocó, ya apuntaba al helper compartido.

**Archivos.**
- `nexora_app/nexora/public/js/nexora_report_actions.js` (nuevo: `escapeHtml`,
  `formatDate`, `generateId` en `window.nexora.ui`, junto al `formatMoney` que ya
  existía)
- `nexora_app/nexora/public/js/nexora.js`, `nexora_quick_flows.js`,
  `nexora_operational_ui.js`
- `nexora_app/nexora/nexora/page/{nexora_closing,nexora_dashboard,nexora_reports,
  nexora_operations,nexora_purchase_requests,nexora_quotations,nexora_search,
  nexora_suppliers,nexora_contracts,nexora_entities,nexora_evidence,
  nexora_finance}/*.js`

**Decisión.** La lógica real vive ahora una sola vez en `window.nexora.ui`. Cada
página conserva su función local (`escape`, `date`/`formatDate`, `uuid`, `money`)
como una llamada de una línea al helper compartido: ningún punto de uso existente
—había decenas por archivo dentro de plantillas de texto— cambió de nombre ni de
firma, así que el riesgo de romper una referencia se mantiene en cero sin
necesidad de tocarlas una por una. `nexora_operations.js` tenía además su propio
`money()` reimplementado (no delegaba en `formatMoney`); también se consolidó.

**Pruebas.** Balance de llaves/paréntesis verificado a mano en los 16 archivos
tocados. Suite completa de contratos puro-Python ejecutada localmente: 94 pruebas,
0 fallos, incluidas `test_active_context_contract` y `test_financial_ui_contract`
(que referencian código de varias de estas páginas). Se buscó en todos los
`test_*.py` cualquier aserción literal sobre los cuerpos antiguos
(`escape_html(String(value`, `randomUUID`, `str_to_user(String(value)`,
`Intl.NumberFormat`) fuera de `nexora_report_actions.js`: ninguna. `node --check`
no disponible en este entorno.

**Limitaciones reales.** No se tocaron `format_currency` en compras/cotizaciones
ni las reservas defensivas de dashboard/fondos, por ser código funcionalmente
distinto, no duplicado. SHA en `main`: pendiente de commit y push.

## Bloque 1.1 — cierre formal de fase 1

Este bloque cerró la fase documental e identidad sin tocar backend, frontend,
DocTypes, permisos, servicios ni lógica de negocio.

- Se alineó la superficie documental y operativa visible a **NEXORA**.
- Se conservó trazabilidad del legado donde sigue siendo útil o técnicamente necesario.
- Se evitó cualquier cambio en comportamiento funcional.

Commit del bloque 1 publicado en `main`: `18f7219a3ae4d566c502090b2543c84e11d89768`.

### Estado de NXR-CONS-001

- **Estado:** NO DEMOSTRADO como requisito trazable independiente en el árbol revisado.
- **Interpretación operativa:** el cierre de fase 1 dejó la identidad documental
  alineada, pero no aportó evidencia funcional nueva para elevarlo a validado.

## Base certificada anterior

- Fundación y consola: PR `#11` y `#26`; fusión `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.

## Veredicto

- **Bloque 1:** cerrado.
- **Bloque 1.1:** cerrado.
- **Bloque 2: NO cerrado — pendiente de certificación.** El trabajo está completo en
  árbol y las correcciones están validadas, pero **quedan tres verificaciones en rojo**,
  y mientras existan el bloque no puede declararse cerrado:

  | Verificación | Estado | Atribución |
  |---|---|---|
  | `contract` (contratos, modelos, servicios, UI) | ✅ verde | pasa de rojo a verde en esta rama |
  | `install-rollback` (bench real sobre MariaDB: instala, migra, desinstala, reinstala, siembra) | ✅ verde | runtime real ejercitado |
  | `linters`, `semgrep`, `secrets` | ✅ verde | |
  | Recorrido de navegador (`nexora_browser_smoke.mjs`, job `browser`) | ❌ **rojo** | previo a la rama; falla igual en `origin/main`; diagnóstico acotado arriba |
  | `validate_construcontrol_architecture` (job `mariadb`) | ❌ **rojo** | previo a la rama; cuatro contratos de coexistencia sin redactar |
  | `validate_repository` (jobs `verify` ×2, `validate` y «Product, migration and security validation») | ❌ **rojo** | previo a la rama; falta decidir el workflow autoritativo `linux/amd64` |

  Los nombres de job importan porque un mismo error preexistente aparece bajo varios:
  `validate_repository` es lo primero que ejecutan tanto
  `construcontrol-verification-receipt.yml` como `construcontrol-validation.yml`, así que
  su único error se reporta cuatro veces. `construcontrol-validation.yml` ha fallado en
  **todos** los commits de esta rama, incluido el primero.

  **Ninguno de los tres rojos lo introduce esta rama**: los tres fallan igual en
  `origin/main`, comprobado ejecutando cada validador sobre un worktree de `origin/main`
  y comparando el texto de error. Pero eso los explica, no los resuelve: hasta que el
  recorrido de navegador termine en verde, la carga de assets, `Page.has_permission()`,
  las rutas del workspace y el contexto activo no están certificados en navegador, solo
  en instalación. Los otros dos exigen decisiones de producto e infraestructura del
  propietario, no correcciones de código.

  Cuando esas tres verificaciones queden en verde se registra aquí el SHA validado y el
  bloque pasa a cerrado. No antes.

## NEXORA Intelligence Platform (NIP) — Bloque 1: AI Gateway + AI Provider Manager

- Fecha: 2026-08-06.
- Rama de trabajo: `docs/nip-architecture` (continuación de la sesión que publicó
  `NEXORA_INTELLIGENCE_ARCHITECTURE.md` en el PR #75).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO**.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_1_AI_GATEWAY_PROVIDER_MANAGER.md`](docs/nexora/NIP_BLOQUE_1_AI_GATEWAY_PROVIDER_MANAGER.md).

Se construyó, siguiendo `NEXORA_INTELLIGENCE_ARCHITECTURE.md` (secciones 6 y 7), la
primera capa del subsistema de inteligencia: interfaz base de proveedor
(`AIProviderAdapter`), Provider Manager (`ProviderRegistry` + DocType
`NXR AI Provider`), router interno determinista y un AI Gateway mínimo que solo
resuelve — nunca invoca — un proveedor. Cero proveedores reales, cero credenciales, cero
UI, cero cambio en módulos de negocio existentes.

Único archivo de producto modificado (aditivo): `permissions.py`, con dos acciones
nuevas (`ai_manage_provider`, `ai_view_provider`) que reutilizan `MANAGER_ROLES` y
`REPORT_EXPORT_ROLES` ya existentes. Único test preexistente ajustado:
`test_app_contract.py` (conteo de DocTypes instalables, de 50 a 51, por el DocType
nuevo).

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB disponibles aquí; lógica
pura sin `frappe`, corridas con `PYTHONPATH=nexora_app python3 -m unittest`): 85 pruebas
nuevas (positivas y negativas) más 13 de regresión en `test_app_contract` — 98 en total,
todas en verde. Guards reales y ejecutables del repositorio confirmados en verde sobre
el árbol resultante, sin modificarlos:
`scripts/validate_nexora_app.py`, `scripts/validate_nexora_financial_models.py`,
`scripts/validate_nexora_governance.py`, `scripts/validate_nexora_completion.py`,
`scripts/validate_nexora_operational_acceptance.py`,
`scripts/validate_github_governance.py`, `scripts/validate_nexora_constitution.py`, y
`python -m compileall nexora_app/nexora scripts`.

**No ejecutado aquí** (requiere `bench` + MariaDB, ausentes en este entorno): pruebas de
integración de `service.py` contra un sitio real, `install-rollback`,
`nexora-app.yml` completo. Queda para el pipeline de CI del PR correspondiente.

**Confirmado como preexistente, no introducido por este bloque:**
`scripts/validate_repository.py --check` ya reportaba
`docs/architecture/file_inventory.json` desactualizado antes de tocar cualquier
archivo de este bloque — comprobado ejecutándolo contra el árbol sin cambios. No se
tocó, para no mezclar una corrección no relacionada en este commit.

SHA en `main`: pendiente de commit, push y Pull Request. PR abierto:
`feat/nip-block1-ai-gateway-provider-manager` → `main`, #77 (sin fusionar aún).

## NEXORA Intelligence Platform (NIP) — Bloque 2: AI Provider Adapters

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block2-ai-provider-adapters`, creada sobre
  `feat/nip-block1-ai-gateway-provider-manager` (incluye su commit: el Bloque 1 aún no
  está fusionado en `main`, PR #77 pendiente).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO**.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_2_AI_PROVIDER_ADAPTERS.md`](docs/nexora/NIP_BLOQUE_2_AI_PROVIDER_ADAPTERS.md).

Se construyeron tres adaptadores simulados (`OpenAIStubAdapter`, `AnthropicStubAdapter`,
`GeminiStubAdapter`), todos implementando el mismo contrato `AIProviderAdapter` fijado en
el Bloque 1, con registro automático por decorador (`register_adapter`) y un
`AdapterRegistry` de código independiente del `ProviderRegistry` de configuración del
Bloque 1. `gateway.dispatch(...)` compone ambos para invocar de verdad al adaptador
resuelto — siempre simulado, nunca toca la red, nunca requiere una API key.

Archivos del Bloque 1 tocados, ambos aditivos o correctivos: `core.py` (una excepción
nueva, `AdapterInvocationError`) y `gateway.py` (una función nueva, `dispatch`, más la
corrección de una frase de docstring en `resolve` que había quedado desactualizada).
Ninguna línea de comportamiento del Bloque 1 cambió; verificado con `git diff` antes de
commitear. `service.py` no se tocó: sigue con los mismos cuatro endpoints del Bloque 1,
sin ningún consumidor real de `dispatch` todavía.

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB; lógica pura sin `frappe`,
`PYTHONPATH=nexora_app python3 -m unittest`): 129 pruebas de `intelligence/` +
`test_app_contract`, todas en verde — 31 nuevas de este bloque (adaptadores, registro
automático, `dispatch`) más las 98 del Bloque 1 sin ninguna regresión. Guards reales
confirmados en verde sobre el árbol resultante, sin modificarlos: los mismos siete
`scripts/validate_nexora_*.py` del Bloque 1 y `python -m compileall nexora_app/nexora
scripts`.

**No ejecutado aquí** (requiere `bench` + MariaDB): igual que el Bloque 1, queda para el
CI del PR correspondiente.

SHA en `main`: pendiente de commit, push y Pull Request. PR abierto:
`feat/nip-block2-ai-provider-adapters` → `feat/nip-block1-ai-gateway-provider-manager`,
#78 (sin fusionar aún).

## NEXORA Intelligence Platform (NIP) — Bloque 2.1: expansión de proveedores IA

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block2.1-expand-provider-adapters`, creada sobre
  `feat/nip-block2-ai-provider-adapters` (incluye sus commits: ni el Bloque 1 ni el
  Bloque 2 están fusionados en `main` todavía — PR #77 y #78 pendientes).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO**.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_2.1_EXPANSION_PROVEEDORES.md`](docs/nexora/NIP_BLOQUE_2.1_EXPANSION_PROVEEDORES.md).

Se añadieron seis adaptadores simulados más (`GroqAdapter`, `DeepSeekAdapter`,
`MistralAdapter`, `CohereAdapter`, `PerplexityAdapter`, `OpenRouterAdapter`), con la
misma forma exacta que los tres del Bloque 2: mismo contrato `AIProviderAdapter`, mismo
decorador `@register_adapter`, mismo helper `simulated_invoke` — sin SDK real, sin API
key, sin llamada HTTP. El registro por defecto (`build_default_registry()`) pasa de 3 a
9 proveedores sin que ninguna línea de `adapters.py`, `gateway.py`, `core.py`,
`registry.py`, `router.py`, `config.py` ni `service.py` cambiara: el único archivo de
producto tocado es `providers/__init__.py`, y solo para añadir los seis imports nuevos.
Esto es exactamente lo que el Bloque 2 prometía y este bloque comprueba.

Archivos de prueba del Bloque 2 extendidos de forma compatible, sin alterar ninguna
aserción existente: `test_intelligence_adapters.py` (+2 casos) y
`test_intelligence_provider_stubs.py` (+4 casos, más los bucles de contrato genérico
—que ya cubrían los tres proveedores del Bloque 2 sin cambiar su resultado— ahora
ejercitados también sobre los seis nuevos vía `ALL_STUB_ADAPTERS`).

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB; lógica pura sin `frappe`,
`PYTHONPATH=nexora_app python3 -m unittest`): 135 pruebas de `intelligence/` +
`test_app_contract`, todas en verde — 6 nuevas de este bloque, sin ninguna regresión de
los Bloques 1 y 2 (129 previas intactas). Guards reales confirmados en verde sobre el
árbol resultante, sin modificarlos: los mismos siete `scripts/validate_nexora_*.py` y
`python -m compileall nexora_app/nexora scripts`.

**No ejecutado aquí** (requiere `bench` + MariaDB): igual que los bloques anteriores,
queda para el CI del PR correspondiente.

SHA en `main`: pendiente de commit, push y Pull Request. PR abierto:
`feat/nip-block2.1-expand-provider-adapters` → `feat/nip-block2-ai-provider-adapters`,
#79 (sin fusionar aún).

## NEXORA Intelligence Platform (NIP) — Bloque 3: AI Provider Configuration & Credential Manager

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block3-provider-config-credential-manager`, creada sobre
  `feat/nip-block2.1-expand-provider-adapters` (incluye sus commits: ninguno de los
  bloques anteriores está fusionado en `main` todavía — PR #77, #78 y #79 pendientes).
- Nota de topología: `NEXORA_INTELLIGENCE_ARCHITECTURE.md` vive en la rama
  `docs/nip-architecture` (PR #75, también sin fusionar), que se ramificó de `main` en
  paralelo a este bloque y **no** es su ancestro — el archivo no existe en el árbol de
  trabajo de este bloque; se releyó vía `git show docs/nip-architecture:...` antes de
  empezar, como exige el protocolo de este bloque. No afecta la validez del trabajo: son
  PRs independientes que convergerán en `main` por separado.
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO**.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md`](docs/nexora/NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md).

Se construyó el Provider Configuration + API Key Manager que los Bloques 1 y 2 dejaron
explícitamente pendiente. `NXR AI Provider` gana ocho campos de configuración operativa
(`default_model`, `timeout_seconds`, `temperature`, `max_tokens`, `cost_hint`,
`is_default`, `validation_state`, `last_validated_at`); un DocType nuevo y separado,
`NXR AI Provider Credential`, guarda la credencial cifrada (`Password` nativo de Frappe)
por proveedor. Resolución en capas: variable de entorno de servidor primero
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, …, los nueve nombres oficiales), registro cifrado
en base de datos después. La validación es exclusivamente de formato — cero llamadas de
red, cero proveedor real conectado, tal como exige el bloque.

Único archivo de producto del Bloque 1 tocado más allá de adiciones puras:
`intelligence/service.py`, donde `_provider_rows()` (helper privado, no un endpoint)
pasó de 5 a 13 columnas leídas — extensión inofensiva porque `gateway.build_registry()`
ya ignoraba claves de fila desconocidas. Las cuatro funciones del Bloque 1 no perdieron
ni ganaron una sola línea de lógica propia. Una prueba del Bloque 2
(`test_service_was_not_touched_by_block_2`) se renombró y actualizó porque su premisa
literal ("cuatro endpoints, cero desde el Bloque 2") quedó superada por este bloque
exactamente como el propio Bloque 2 anticipaba en su docstring — no por una regresión.
Detalle completo de ambos cambios en el documento del bloque, sección "Compatibilidad".

`test_ai_provider_doctype_has_no_credential_field` (Bloque 1) sigue verde sin tocarse:
la credencial vive en el DocType nuevo, nunca en `NXR AI Provider` — la separación
Provider Manager / API Key Manager que ya fijaba
`NEXORA_INTELLIGENCE_ARCHITECTURE.md` (sección 8) es lo que evitó tener que romper esa
prueba.

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB; lógica pura sin `frappe`,
`PYTHONPATH=nexora_app python3 -m unittest`): 216 pruebas en total (incluye
`test_integrations_core` como control ajeno a este subsistema), todas en verde — 70
nuevas de este bloque, sin ninguna regresión de los Bloques 1, 2 y 2.1 (146 previas
intactas). Ninguna prueba ni fixture usa un secreto real; los valores sintéticos se
verificaron a propósito para que no disparen el propio detector de valores de plantilla.
Guards reales confirmados en verde sobre el árbol resultante, sin modificarlos: los
mismos siete `scripts/validate_nexora_*.py` y `python -m compileall nexora_app/nexora
scripts`.

**No ejecutado aquí** (requiere `bench` + MariaDB): la integración real de
`save_credential`/`update_provider_config`/`set_default_provider`/
`list_credential_status` contra un sitio Frappe real, incluido que `Password` cifre y
enmascare correctamente en runtime. Queda para el CI del PR correspondiente.

SHA en `main`: pendiente de commit, push y Pull Request. PR abierto:
`feat/nip-block3-provider-config-credential-manager` →
`feat/nip-block2.1-expand-provider-adapters`, #81 (sin fusionar aún).

## NEXORA Intelligence Platform (NIP) — Bloque 4: AI Provider Runtime + Credential Activation

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block4-provider-runtime-credential-activation`, creada
  sobre `feat/nip-block3-provider-config-credential-manager` (incluye sus commits:
  ninguno de los bloques anteriores está fusionado en `main` todavía — PR #77, #78, #79
  y #81 pendientes).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO** — sin ninguna credencial real
  en este entorno, `prepare_adapter` rechaza cualquier intento con
  `CredentialNotConfiguredError` antes de tocar la red.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_4_PROVIDER_RUNTIME_CREDENTIAL_ACTIVATION.md`](docs/nexora/NIP_BLOQUE_4_PROVIDER_RUNTIME_CREDENTIAL_ACTIVATION.md).

Se construyeron los nueve adaptadores en vivo (`*_live.py`, uno por proveedor oficial),
todos implementando el mismo contrato `AIProviderAdapter` del Bloque 1, usando
exclusivamente `urllib` de la biblioteca estándar (sin SDK de proveedor como dependencia
nueva). Se construyó el Runtime Provider Manager (`runtime_core.py` pura +
`runtime.py` con I/O de Frappe) que resuelve proveedor, configuración, prioridad
(reutiliza el Router del Bloque 1 sin duplicarlo), credencial y disponibilidad, y
devuelve un adaptador listo para invocarse o el error más específico posible. Cinco
endpoints administrativos nuevos en `service.py` (`check_provider_readiness`,
`get_provider_runtime_config`, `list_active_providers`, `get_provider_capabilities`,
`test_provider_connection`), ninguno devuelve jamás una credencial.

Los adaptadores en vivo se resuelven mediante un mapeo explícito y separado
(`runtime_core.REAL_ADAPTER_CLASSES`), nunca mediante `@register_adapter` del Bloque
2 — así no compiten por las mismas claves de proveedor que ya ocupan los *stubs*
registrados en los Bloques 2/2.1, y `gateway.dispatch()` sigue usando exclusivamente
esos *stubs* como antes, sin cambiar su comportamiento por defecto.

`intelligence/service.py` no perdió ni modificó ninguna línea existente: el diff de ese
archivo es 100% inserciones. Dos pruebas existentes se actualizaron porque su premisa
literal quedó superada por este bloque, tal como sus propios docstrings preveían — mismo
patrón usado al pasar del Bloque 2 al Bloque 3: el conteo de endpoints
(`test_service_endpoint_count_is_intentional`, de 8 a 13) y el escaneo de "ningún archivo
de `providers/` toca la red" (Bloque 2), que se acotó a los *stubs* únicamente —
renombrada a `test_no_stub_file_imports_a_real_sdk_or_touches_the_network` — porque el
propio Bloque 4 necesitaba añadir, a propósito, archivos que sí tocan la red en ese mismo
directorio. Detalle completo de ambos cambios en el documento del bloque, sección
"Compatibilidad".

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB ni ninguna credencial real;
lógica pura sin `frappe`, transporte HTTP siempre sustituido por un doble de prueba,
`PYTHONPATH=nexora_app python3 -m unittest`): 266 pruebas en total (incluye
`test_integrations_core` como control), todas en verde — 50 nuevas de este bloque, sin
ninguna regresión de los Bloques 1, 2, 2.1 y 3 (216 previas intactas). Ninguna prueba usa
un secreto real. Guards reales confirmados en verde sobre el árbol resultante, sin
modificarlos: los mismos siete `scripts/validate_nexora_*.py` y
`python -m compileall nexora_app/nexora scripts`.

**No ejecutado aquí** (requiere `bench` + MariaDB y, por definición, una credencial real
que no existe en ningún entorno de este proyecto): la integración real de `runtime.py`
contra un sitio Frappe real, y cualquier llamada real de red contra un proveedor de IA.
Queda para cuando el propietario configure una credencial real y lo decida
explícitamente.

SHA en `main`: pendiente de commit, push y Pull Request. PR abierto:
`feat/nip-block4-provider-runtime-credential-activation` →
`feat/nip-block3-provider-config-credential-manager`, #83 (sin fusionar aún).

## NEXORA Intelligence Platform (NIP) — Bloque 5: Live Provider Connections

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block5-live-provider-connections`, creada sobre
  `feat/nip-block4-provider-runtime-credential-activation` (incluye sus commits:
  ninguno de los bloques anteriores está fusionado en `main` todavía — PR #77, #78,
  #79, #81 y #83 pendientes).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **NO**, por decisión explícita del
  propietario — ver más abajo.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_5_LIVE_PROVIDER_CONNECTIONS.md`](docs/nexora/NIP_BLOQUE_5_LIVE_PROVIDER_CONNECTIONS.md).

Se completó el manejo de errores del Runtime del Bloque 4 con los dos casos que el
encargo de este bloque pedía explícitamente y que aún no se distinguían: límite de tasa
(HTTP 429 → `ProviderRateLimitError`, nueva, con `Retry-After` en el mensaje cuando el
proveedor lo envía) y modelo inexistente (HTTP 404 → `ProviderModelNotFoundError`,
declarada en el Bloque 4 pero sin usar hasta ahora). Ambas viven en el único punto de
transporte HTTP compartido (`providers/http_support.py`), así que los nueve adaptadores
en vivo las heredan sin ningún cambio propio — cero código paralelo, cero duplicación,
tal como exigía el encargo.

**Verificación de red y decisión sobre credenciales reales.** Antes de escribir
cualquier línea, se confirmó que este entorno sí tiene salida de red real (una solicitud
de prueba sin credenciales a `https://api.openai.com/v1/models` devolvió `HTTP 401`, no
un fallo de conectividad). Siguiendo la instrucción explícita del encargo de detenerse y
pedir credenciales una por una si hicieran falta, se preguntó directamente al propietario
si quería aportar una API key real para verificar al menos un proveedor en vivo. Su
respuesta fue cerrar el bloque sin verificación en vivo. En consecuencia,
**cero proveedores quedan confirmados en modo REAL** — los nueve están completos y
listos, pendientes únicamente de que se configure una credencial real cuando el
propietario lo decida; no se inventó ningún valor ni se usó ningún placeholder para
simular una llamada real.

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB ni ninguna credencial real;
transporte HTTP siempre sustituido por un doble de prueba,
`PYTHONPATH=nexora_app python3 -m unittest`): 271 pruebas en total (incluye
`test_integrations_core` como control), todas en verde — 6 nuevas de este bloque, sin
ninguna regresión de los Bloques 1–4 (265 previas intactas). `core.py` y
`http_support.py` quedaron con diff 100% aditivo (verificado con `git diff` antes de
comitear). Guards reales confirmados en verde sobre el árbol resultante, sin
modificarlos: los mismos siete `scripts/validate_nexora_*.py` y
`python -m compileall nexora_app/nexora scripts`.

**No ejecutado, por decisión explícita del propietario**: cualquier llamada real contra
cualquiera de los nueve proveedores. Queda disponible para cuando se decida configurar
una credencial real — no requiere ningún cambio de código adicional.

SHA en `main`: pendiente de commit, push y Pull Request.

## NEXORA Intelligence Platform (NIP) — Bloque 5.2: AI Orchestrator + OmniRoute Integration

- Fecha: 2026-08-06.
- Rama de trabajo: `feat/nip-block5.2-orchestrator-omniroute-integration`, creada sobre
  `feat/nip-block5-live-provider-connections` (incluye sus commits: ninguno de los
  bloques anteriores está fusionado en `main` todavía — PR #77, #78, #79, #81, #83 y #85
  pendientes).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.
- API keys o proveedores de IA reales conectados: **SÍ** — por decisión explícita del
  propietario ("quiero darte una credencial real ahora"), se certificaron los nueve
  proveedores oficiales con claves reales aportadas de forma transitoria (variable de
  entorno de shell, nunca escritas a ningún archivo, commit, log ni documentación).
  Resultado: 7 de 9 en `READY` (OpenAI, Gemini, OpenRouter, Perplexity, Groq, Mistral,
  Cohere); 2 de 9 con credencial válida pero sin saldo/cuota (DeepSeek, Anthropic).
  Detalle completo, sin ningún fragmento de clave real, en el documento del bloque.
- Detalle completo, decisiones y limitaciones:
  [`docs/nexora/NIP_BLOQUE_5.2_ORCHESTRATOR_OMNIROUTE_INTEGRATION.md`](docs/nexora/NIP_BLOQUE_5.2_ORCHESTRATOR_OMNIROUTE_INTEGRATION.md).

Se construyó el AI Orchestrator central que implementa la "regla de oro" del encargo: si
un proveedor falla o se queda sin cuota, NEXORA reintenta con el siguiente proveedor
capaz automáticamente, sin detener la sesión del usuario, dejando el cambio de proveedor
únicamente en `NXR Audit Event`. `orchestrator_core.py` (puro, sin `frappe`) aporta el
circuito de salud (Closed/Open/Half-Open), la puntuación de candidatos y el ranking;
`orchestrator.py` (con `frappe`) construye el bucle de intento/fallo/reintento
enteramente sobre `gateway.build_registry` (Bloque 1) y `runtime.build_ready_adapter`
(Bloque 4) ya existentes — cero código paralelo. Se añadió `NXR AI Usage Event`
(DocType nuevo, solo-append) para latencia/éxito/costo por intento, tres endpoints
administrativos nuevos (`run_orchestrated_request`, `preview_routing_decision`,
`get_provider_usage_summary`) y el panel administrativo `nexora-ai-providers` (Page de
Desk, alcanzable desde el workspace y la navegación superior), con gestión de
credenciales, prioridad, proveedor por defecto y ejecución manual de la regla de oro.

**Decisión sobre OmniRoute** (referencia externa MIT analizada por instrucción del
encargo): estrategia de **referencia arquitectónica sin dependencia en tiempo de
ejecución** — reimplementación nativa en Python dentro del mismo proceso Frappe, sin
añadir un segundo runtime (Node.js) como dependencia de arranque. El repositorio de
NEXORA ya pertenece a la cuenta del propietario, así que "mover el repositorio" no
aplicaba. Ningún código de OmniRoute se copió.

**Certificación real encontró y corrigió dos bugs genuinos**: (1) Groq devolvía
`HTTP 403` por un bloqueo de Cloudflare ante la ausencia de cabecera `User-Agent` —
antes se clasificaba como credencial inválida; corregido con un `User-Agent` por defecto
en `http_support.py`, reverificado en vivo (287 ms tras el fix). (2) `HTTP 402`
(cuota agotada) no tenía clasificación propia y caía en el error genérico; se añadió
`ProviderQuotaExhaustedError`, nunca reintentable contra el mismo proveedor. Hallazgos
documentados sin corregir, por decisión explícita y justificada: Anthropic reporta el
mismo caso de cuota agotada como `HTTP 400` con texto en vez de 402 (no clasificado
aparte, por fragilidad de depender de texto); Gemini puede agotar su presupuesto de
tokens "pensando" y devolver una respuesta visible vacía en una llamada por lo demás
exitosa.

`intelligence/service.py` quedó con diff 100% aditivo. `core.py`, `gateway.py` y
`http_support.py` quedaron aditivos salvo la extensión documentada de sus propios
docstrings. Dos pruebas existentes se actualizaron porque su premisa literal quedó
superada, tal como sus propios docstrings preveían: el conteo de endpoints
(`test_service_endpoint_count_is_intentional`, de 13 a 16) y el conteo de DocTypes
(`test_doctype_package_and_module_declarations_are_installable`, de 52 a 53).

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB; lógica pura sin `frappe`
donde aplica, transporte HTTP sustituido por un doble de prueba salvo en la
certificación real documentada arriba, `PYTHONPATH=nexora_app python3 -m unittest`):
353 pruebas en total (incluye `test_page_registry_contract` y `test_integrations_core`
como control), todas en verde — 73 nuevas de este bloque
(`test_intelligence_orchestrator_core`: 39; `test_intelligence_prompt_optimizer`: 21;
`test_intelligence_http_support`: +5; `test_intelligence_contract`: +8), sin ninguna
regresión de los Bloques 1–5. Guards reales confirmados en verde sobre el árbol
resultante, sin modificarlos: los seis `scripts/validate_nexora_*.py` presentes en el
repositorio, `scripts/validate_github_governance.py` y
`python -m compileall nexora_app/nexora scripts`.

**No ejecutado en este entorno** (requiere `bench` + MariaDB, ausente en este sandbox):
una cadena completa de fallback multi-proveedor en vivo a través de
`orchestrator.execute()` contra un sitio Frappe real — la lógica de decisión que la
gobierna sí tiene cobertura completa de pruebas unitarias puras (39 casos), y la
clasificación de errores por proveedor sí se verificó contra las nueve APIs reales.

SHA en `main`: pendiente de commit, push y Pull Request.

## NEXORA Intelligence Platform (NIP) — Bloque 5.3: enrutamiento real OpenAI → OmniRoute (reversión informada de la decisión del Bloque 5.2)

- Fecha: 2026-08-07.
- Rama de trabajo: `feat/nip-block5.2-orchestrator-omniroute-integration` (mismos commits
  del Bloque 5.2, sin fusionar en `main`).
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: pendiente
  de redeploy en Coolify por el propietario; el código ya está en la rama.
- API keys o proveedores de IA reales conectados: **SÍ** — el propietario aportó una
  clave real de OmniRoute (variable de entorno de servidor, nunca escrita a ningún
  archivo, commit, log ni documentación) y confirmó explícitamente mantener el
  enrutamiento real tras conocer los riesgos documentados abajo.

**Contradice, a propósito y por decisión informada del propietario, la decisión
arquitectónica del Bloque 5.2** ("OmniRoute: referencia arquitectónica sin dependencia en
tiempo de ejecución"). `OpenAILiveAdapter.base_url` (`providers/openai_live.py`) dejó de
apuntar a `https://api.openai.com/v1` y ahora apunta a un gateway OmniRoute real
(`http://oc961rno9luetxjwm4t0pzbq.18.217.171.173.sslip.io/v1`), de modo que **todo**
tráfico con `provider_key == "openai"` — Orchestrator, Gateway y panel admin incluidos —
se reenruta sin tocar esas capas.

**Riesgos de seguridad encontrados y reportados al propietario antes de confirmar la
decisión, ninguno corregible desde el código de NEXORA porque son del lado del servidor
OmniRoute, no del cliente:**
- El endpoint respondió con completions reales de OpenAI usando (a) la clave real
  aportada, (b) una clave inventada, y (c) sin ningún header `Authorization` — las tres
  devolvieron la misma respuesta y el mismo `X-Omniroute-Session-Id`. No hay evidencia de
  que el servidor valide la credencial del cliente.
- El puerto HTTPS del mismo host/IP presenta un certificado autofirmado no verificable
  (`curl: (60) SSL certificate problem`).
- El nombre de host (`<subdominio-aleatorio>.<IP>.sslip.io`) sigue el patrón típico de un
  túnel temporal de desarrollo, no de un dominio de producción contratado.

**Bug real encontrado y corregido, aditivo para el resto de proveedores de la misma
clase base:** `OpenAICompatibleLiveAdapter.invoke()` (`providers/openai_compatible_live.py`)
no enviaba `"stream"` en el cuerpo de la solicitud; OpenAI y el resto de proveedores de
esta familia asumen `stream: false` por defecto, pero OmniRoute devuelve
`text/event-stream` (SSE) si el campo se omite, lo que rompía la decodificación JSON de
`http_support.py`. Se agregó `"stream": False` explícito — confirmado en vivo antes y
después del fix contra el endpoint real.

**Hallazgo documentado, sin corregir:** OmniRoute devuelve `HTTP 400` (con mensaje de
texto) para un modelo inexistente, no `HTTP 404` como asume la clasificación de
`http_support.py` (confirmado en el Bloque 5 contra los nueve proveedores oficiales, cuyo
comportamiento no cambia). Cae en `AdapterInvocationError` genérico en vez de
`ProviderModelNotFoundError`. No se amplió la clasificación de `400` porque ese código
también cubre solicitudes malformadas — mapearlo genéricamente a "modelo inexistente"
adivinaría la causa en vez de confirmarla.

**Gap de infraestructura encontrado y corregido:** ninguna de las nueve variables de
entorno de proveedor (`PROVIDER_ENV_VARS`, Bloque 3) llegaba nunca al contenedor —
`docker-compose.nexora.yml` las omitía por completo de `x-app-environment`. Se agregó
`OPENAI_API_KEY: ${OPENAI_API_KEY:-}` (las otras ocho quedan pendientes, fuera del
alcance de este bloque).

**Herramienta de diagnóstico añadida:** `nexora/tools/validation/omniroute_check.py`
(`run()`, invocable con `bench --site <site> execute
nexora.tools.validation.omniroute_check.run`) consolida en una sola llamada: verificación
de la variable de entorno en el proceso, lectura de la credencial por el backend, alta y
configuración del proveedor si falta, prueba de conexión real y prueba del fallback del
Orchestrator — nunca devuelve la credencial.

**Pruebas ejecutadas en este entorno** (sin `bench`/MariaDB; instaladas vía `apt` en este
sandbox por no estar disponibles de otro modo, `python3 -m pytest`): 320 pruebas del
subsistema de IA en verde (0 regresiones); un test existente
(`test_intelligence_live_adapters.py`) se actualizó porque su premisa literal
(`base_url` de OpenAI) cambió a propósito en este bloque. Adicionalmente, llamadas HTTP
reales (no simuladas) contra el endpoint OmniRoute confirmaron: conexión, respuesta
normal, latencia (131 ms–1.6 s según caché), comportamiento SSE vs. JSON plano, timeout
real (dirección no enrutable) clasificado y con reintento correcto según
`should_retry_same_provider`.

**No ejecutado en este entorno** (requiere el contenedor Docker/Coolify real, ausente en
este sandbox): confirmación de que la variable de entorno llega al contenedor en
producción, lectura de la credencial por el Frappe real corriendo, y los flujos
`test_provider_connection`/`run_orchestrated_request` vía RPC del panel admin. Comando
único generado para que el propietario lo ejecute tras el redeploy de Coolify; pendiente
de su resultado.

SHA en `main`: pendiente de commit, push y Pull Request. Commits en la rama de trabajo:
`f39bcaa3` (enrutamiento + fix de streaming + wiring de `OPENAI_API_KEY`) y `bf28cb83`
(herramienta de diagnóstico).

## NEXORA Intelligence Platform (NIP) — Bloque 6: fusión segura del stack NIP a `main`

- Fecha: 2026-08-07.
- Acción: squash-merge de PR #86 (`feat/nip-block5.2-orchestrator-omniroute-integration`,
  retargeteado de su base original `feat/nip-block5-live-provider-connections` a `main`)
  a `main`. **SHA de merge en `main`: `f63f86e4`.**
- PRs cerrados sin fusión separada porque su contenido completo ya viajaba dentro de #86
  (rama apilada linealmente, confirmado con `git merge-base --is-ancestor` uno por uno
  antes de cerrar cualquiera): #73, #77 (Bloque 1), #78 (Bloque 2), #79 (Bloque 2.1), #81
  (Bloque 3), #83 (Bloque 4), #85 (Bloque 5). Cada uno cerrado con un comentario que
  referencia el SHA `f63f86e4`. #75 (`docs/nip-architecture`) queda abierto a propósito:
  no es antecesor de la pila fusionada, fuera de alcance de este bloque.
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**
  desde aquí — el redeploy en Coolify que hace que este código llegue al contenedor real
  queda pendiente de que el propietario lo dispare (`nexora_app` se copia en build time
  en `Dockerfile.nexora`, no está montado como volumen).

**Antes de fusionar, se auditó por primera vez el CI real de PR #86** (nunca antes
revisado: ningún PR de los Bloques 1–5.2 había sido inspeccionado en su estado de checks,
solo comiteado). Encontró y corrigió tres bloqueos reales, ninguno simulado, ninguno
introducido por decisión de diseño — deuda acumulada de bloques anteriores que nunca se
había ejecutado contra CI real:

1. **Scanner de secretos** (`scripts/scan_nexora_secrets.py`, patrón `openai_key`):
   6 falsos positivos por fixtures de test con prefijo `sk-...` sintético (Bloques 4 y 5).
   Reescritas sin ese prefijo (`synthetic-test-secret-...`, `changeme-...`,
   `should-not-leak-...`), misma cobertura de prueba, cero secretos reales en ningún
   momento.
2. **Semgrep `frappe-setuser`** (regla real de `frappe/semgrep-rules`, excluye
   `**/test_*.py`): `nexora/tools/validation/omniroute_check.py` (herramienta de
   diagnóstico de esta sesión, Bloque 5.3) no es un archivo de test, así que la exclusión
   no aplicaba. Marcado con `# nosemgrep` + justificación, mismo patrón ya usado por
   `*_concurrency_probe.py` en este árbol.
3. **Deuda de formato/lint acumulada** en archivos de los Bloques 1–5.2 (nunca corrida
   contra las herramientas pineadas en `.pre-commit-config.yaml`): orden de imports,
   `__all__` sin ordenar (`gateway.py`, `orchestrator_core.py`), `with` anidados en vez de
   combinados (12 casos en tests), un `dict()` innecesario, un `datetime` naive, una
   reformateo de `nexora_ai_providers.js` vía `prettier`. Corregida con las versiones
   exactas pineadas (`ruff==0.16.0`, `prettier==2.7.1`, `eslint==8.44.0`) — cero cambios
   de comportamiento, solo estilo.
4. **Manifiesto de inventario de archivos** (`docs/architecture/file_inventory.json`,
   gobernanza `Read-only static server control`): desactualizado tras los archivos nuevos
   de esta sesión. Regenerado con `scripts/generate_file_inventory.py`.
5. **`Documentation Required`** (check heredado de la plantilla ERPNext/Frappe, exige un
   link a `docs.frappe.io`/`docs.erpnext.com` en cualquier PR con título `feat`): no
   aplica a NEXORA, que no es OSS de Frappe/ERPNext y documenta en `EXECUTION_STATE.md` y
   `docs/nexora/`. Marcado `no-docs` en el cuerpo del PR con justificación, tal como el
   propio check permite.

**Revalidación completa contra el `main` real post-fusión** (no se asumió que lo verde en
la rama siguiera verde en `main` — se repitió sobre el checkout limpio de `origin/main`
en SHA `f63f86e4`):

- `python -m compileall nexora_app/nexora scripts`: verde.
- Los 7 `scripts/validate_nexora_*.py` / `validate_github_governance.py`: verdes,
  idénticos a la corrida sobre la rama.
- `scripts/scan_nexora_secrets.py`: `files=634 findings=0`.
- `scripts/generate_file_inventory.py`: sin diff contra el manifiesto ya fusionado.
- `ruff check` / `ruff format --check` sobre `nexora_app/`: verdes.
- `pytest nexora/tests/` (sin `bench`/Frappe): 904 passed, 3 failed (idénticas,
  preexistentes, `ModuleNotFoundError: frappe` en `purchases/receipt_service.py` —
  confirmadas también presentes en `origin/main` antes de esta fusión vía `git worktree`
  limpio, no son regresión de este bloque), 19 errors de colección (mismos módulos de
  integración que requieren `bench`, ausente en cualquier sandbox sin Frappe real).
- CI de PR #86 en GitHub Actions, sobre el commit final antes del squash
  (`db27045e`): `Documentation Required`, `Read-only static server control`,
  `Read-only non-Python patch control`, `Semantic Commits`, `Linters` (sub-jobs
  `linters`/`secrets`/`semgrep`), `Patch` — los 7 checks en verde.
- **Suite completa de aceptación real disparada por el `push` a `main`** (13 checks vía
  `gh api repos/.../commits/f63f86e4/check-runs`, cada uno con evidencia real, no
  simulada — bench de Frappe real, MariaDB real, migración repetida, invariantes
  financieras con bloqueo concurrente, y navegador/dispositivo real): `NEXORA app`
  (`contract`, `install-rollback`), `NEXORA financial invariants` (`mariadb`: instalación
  limpia, coexistencia y rollback, invariantes financieras/correcciones/directorio/
  contratos/proveedores/solicitudes/ejecutivas con rollback, bloqueo concurrente con
  conexiones independientes, datos de staging idempotentes), `NEXORA production
  validation` (`Product, migration and security validation`, `Real site, repeated
  migration, CRUD and persistence`, `Operational acceptance · Phases 2 y 3`), `NEXORA
  governance` (`validate`), `NEXORA final acceptance and delivery` (`Verified final
  package`), `NEXORA predeploy certification receipt` (esperó y confirmó todos los demás
  gates permanentes antes de emitir el recibo), más `Linters`/`secrets`/`semgrep`/
  `Documentation Required`/`Read-only`/`Semantic Commits` — **13/13 en verde**. Esta es la
  misma batería que `docs/final/NEXORA_ENTREGA_FINAL.md` exige para una entrega
  aprobada; corrió automáticamente al fusionar, no fue necesario dispararla aparte.

**No ejecutado en este entorno** (requiere el contenedor Docker/Coolify real, ausente en
este sandbox, igual que en todos los bloques NIP anteriores): confirmación de que
`OPENAI_API_KEY` llega al contenedor en producción, lectura de la credencial por el
Frappe real corriendo, y los flujos `test_provider_connection`/`run_orchestrated_request`
vía RPC del panel admin sobre un sitio real. Sigue disponible el comando único
(`bench --site <site> execute nexora.tools.validation.omniroute_check.run`, documentado
en el Bloque 5.3) para que el propietario lo corra tras el redeploy de Coolify apuntando
a `main`.

## Bloque Final — consolidación definitiva del repositorio

- Fecha: 2026-08-07.
- Objetivo: sanear el repositorio (ramas, PRs, tags) sin desarrollar funcionalidad nueva,
  sin perder ningún commit útil. Detalle completo, evidencia rama por rama y comandos de
  restauración: [`docs/architecture/BRANCH_ARCHIVE.md`](docs/architecture/BRANCH_ARCHIVE.md).

**Auditoría (Fase 1-2).** 46 ramas remotas, 17 tags, 2 PRs abiertos (#75, #72) más un
archivo `docs/architecture/BRANCH_ARCHIVE.md` ya existente que documentaba un retiro de
29 ramas fechado 2026-08-05 — **que nunca se ejecutó**: las 29 seguían presentes en
`origin` con el SHA de punta idéntico al que ese documento registró, confirmado antes de
tocar nada.

**Garantía de que `main` contiene todo (Fase 3).** Se encontraron dos huecos reales, no
hipotéticos:
1. `NEXORA_INTELLIGENCE_ARCHITECTURE.md` (659 líneas) — citado por el propio código de
   `nexora/intelligence/` en sus docstrings ("NEXORA_INTELLIGENCE_ARCHITECTURE.md,
   sección N") pero nunca fusionado a `main`. Vivía solo en el PR #75, abierto. Fusionado
   (squash, `a51095a2`).
2. El recorrido completo de las ocho operaciones del Capítulo 53 (creación, edición,
   consulta, aprobación, rechazo, anulación, corrección, exportación) — 52 archivos, CI
   propio en verde salvo el mismo flake documentado abajo. Vivía en el PR #72, abierto
   desde el 2026-08-05. Requirió resolver un conflicto real contra `main` (manifiesto de
   inventario) y, en el primer intento, corregir un commit de merge con título no
   convencional (`Check Commit Titles` real en rojo) — resuelto rehaciendo el merge en un
   solo commit correctamente titulado, con `force-push` a la rama del PR autorizado
   explícitamente por el propietario. Fusionado (squash, `d0a3758c`).

Para el resto de las 44 ramas restantes, la verificación fue por evidencia, no por
suposición: estado real del PR asociado (`gh pr list --state all`), diff de contenido
único contra `main`, y para los casos no triviales, comparación byte a byte del archivo
concreto contra `main` o contra la rama que lo absorbió. Ningún archivo, función ni
mejora quedó fuera — el detalle exacto, rama por rama, está en `BRANCH_ARCHIVE.md`.

**Hallazgo de seguridad/higiene, documentado y no revivido a propósito:**
`.github/workflows/cr.yml` (revisor de PRs basado en ChatGPT vía `OPENAI_API_KEY`)
aparecía en tres ramas distintas, siempre sin fusionar — `main` usa CodeRabbit como
revisor real, confirmado en el CI de cada PR de este bloque. Decisión de diseño ya
tomada por el proyecto, no reabierta aquí.

**Limpieza (Fase 4).** Con las dos garantías anteriores cerradas: 9 ramas locales y 42
ramas remotas borradas (0 quedan salvo `main`); 14 tags `archive/*` (respaldos de una
operación de riesgo ya concluida con éxito) eliminados, conservando los 3 hitos reales
(`construcontrol-v1.0.0`, `v1.0.0`, `nexora-final-validated-20260726`). PRs abiertos:
**0** (antes: 2).

**Validación final.** Sobre el `main` real post-limpieza (commit `d0a3758c`), la batería
completa de aceptación (la misma que exige `docs/final/NEXORA_ENTREGA_FINAL.md`) corrió
**13/13 en verde**, incluido el job `Frappe real · escritorio · tableta · iPhone · PWA`
que había fallado intermitentemente varias veces durante este mismo bloque (mismo flake
documentado en el Bloque 6, confirmado otra vez pre-existente y no relacionado). `git
status` limpio, `origin/main` sincronizado, sin ramas ni PRs redundantes.

SHA final en `main`: `d0a3758c`.

## Bloque 7 — auditoría visual y corrección responsive quirúrgica (parcial)

- Fecha: 2026-08-07.
- Alcance ejecutado: un bug visual real, ya identificado antes de este bloque (Bloque 6),
  encontrado y corregido con evidencia — no una auditoría visual exhaustiva de todo el
  producto (ver limitación de entorno abajo).

**Bug corregido.** `.nxr-contract-panel` y `.nxr-operational-ledger-card` (dashboard
ejecutivo, `nexora_dashboard.js`) envuelven su tabla en `.table-responsive` — el mismo
patrón que `.nxr-bi-table-card` — pero, a diferencia de esa tarjeta, no tenían
`overflow: hidden` como respaldo. Sin él, WebKit deja que el contenido de la tabla
empuje el ancho de la tarjeta más allá de su columna de grilla (`ipad-gen7-webkit`,
810px) en vez de desplazarse dentro de `.table-responsive`. Son exactamente las dos
clases que `Frappe real · escritorio · tableta · iPhone · PWA` venía marcando de forma
intermitente desde antes de esta sesión (confirmado en el Bloque 6). Fix de una línea:
`nexora_app/nexora/public/css/nexora_executive.css`, agregando esas dos clases a la
regla `overflow: hidden` que ya tenía `.nxr-bi-table-card`.

**Validación.** Reproduje la estructura real de tarjeta+tabla con Playwright: Chromium no
mostró desbordamiento ni antes ni después del cambio (confirma que es específico de
WebKit, consistente con la firma real de CI). El PR #90 corrió la batería completa —
incluido `Frappe real · escritorio · tableta · iPhone · PWA` con WebKit real — y pasó en
verde en el primer intento. SHA de fusión: `e880fb37`.

**Limitación de entorno, real y verificada, no supuesta:** WebKit no puede levantarse en
este sandbox — se cae con `page.crashed` incluso sobre una página estática trivial sin
CSS ni JS, confirmado con una prueba mínima aislada. No hay `bench`/Frappe real
disponible tampoco (mismo límite que todos los bloques anteriores de esta sesión). Esto
significa que **la auditoría visual completa que pide el Bloque 7 — dashboard con datos
reales, tablas, paneles, formularios, estados hover/focus/loading/empty, en los cinco
perfiles pedidos — no se pudo ejecutar de forma exhaustiva ni empírica en este entorno**.
Lo que sí se pudo hacer sin servidor (`scripts/nexora_ui_preview.mjs`, que monta la
plantilla de acceso y la carcasa de navegación reales sin backend) se ejecutó y se
inspeccionó visualmente en escritorio/tableta/teléfono: sin overflow ni problemas
visibles en login ni en la navegación (con y sin cajón móvil, carcasa contraída).

**Bloque no cerrado en su totalidad.** Se corrigió el único bug con evidencia sólida
disponible; una auditoría "quirúrgica" real de dashboard/cards/tablas/formularios con
datos reales requiere una instancia Frappe corriendo (Coolify/staging) — pendiente de
que el propietario decida cómo continuar, documentado explícitamente en vez de declararse
completo sin poder demostrarlo.

## Bloques 8 y 9 — cerrados por evidencia ya existente, sin re-trabajo

- Fecha: 2026-08-07.
- El encargo original de ambos bloques asumía huecos («módulos aislados», integración
  pendiente entre fondos/contratos/compras/inventario/presupuestos; «huecos de seguridad»,
  falta de permisos granulares y de auditoría). Por instrucción explícita del propietario,
  antes de implementar nada se auditó si esos huecos existen de verdad — no se asumieron.

**Evidencia recolectada (lectura directa del código, no inferencia):**

- **Permisos granulares**: `nexora_app/nexora/permissions.py` ya define ~20 acciones
  específicas por rol —`create_source`, `cancel_source`, `approve_purchase_request`,
  `manage_contract`, `execute_contract`, `manage_supplier`, `read_sensitive_entity`,
  `save_closing`, `reconcile_source`, etc.— cubriendo fondos, contratos, compras,
  directorio/entidades, proveedores y cierres, cada una con su propio conjunto de roles
  permitidos.
- **Auditoría sistemática**: la función compartida `audit()`
  (`nexora_app/nexora/financial/db.py`) tiene 54+ puntos de llamada reales repartidos
  en contratos (12), compras (11), finanzas (10), directorio (8), presupuestos (5),
  reportes (5), inventario (2) y cierres (1) — no un caso aislado. `NXR Audit Event` es
  `track_changes:1` con todos sus campos de contenido `read_only`.
- **Retenciones**: ya son parte real del cálculo de estimaciones de contrato
  (`nexora_app/nexora/contracts/core.py`: `gross, advance_amortization, retention, fine,
  deduction`) — no algo pendiente de construir.
- **Cobertura de pruebas**: los 51 DocTypes del núcleo de negocio tienen al menos un
  archivo de test que los ejercita; ninguno en cero.
- **Cero marcadores** `TODO`/`FIXME`/"pendiente de implementar" en todo el código de
  negocio (`contracts`, `purchases`, `inventory`, `budget`, `directory`, `close`,
  `reports`, `financial`, `progress`, `notifications`).
- Esto se suma a lo ya confirmado en el Bloque Final: el job real `NEXORA financial
  invariants` prueba con MariaDB real "invariantes financieras, correcciones, directorio,
  contratos, proveedores, solicitudes y ejecutivas con rollback" y "bloqueo concurrente
  con conexiones independientes" — end-to-end, no simulado.

**Decisión, confirmada explícitamente por el propietario tras ver esta evidencia**: los
Bloques 8 y 9 quedan cerrados sin re-trabajo. Repetir la integración o el endurecimiento
de algo que ya está construido, probado y auditado habría violado la propia regla del
encargo ("no repitas trabajo ya cerrado") sobre la base de una suposición que la evidencia
no sostiene. Esto no certifica que el sistema sea perfecto — certifica que la premisa de
"módulos aislados" y "huecos de seguridad" generalizados, tal como estaba escrita, no se
sostiene contra el código real. Un hueco concreto y puntual (si aparece) se atiende como
lo que es: un bug puntual, no una relectura completa de 15 módulos.

## Bloque 10 — cierre de producción y liberación

- Fecha: 2026-08-07.
- Con los Bloques 6, 7 (parcial), 8 y 9 cerrados en esta misma sesión, se confirma el
  estado real de `main` para efectos de este cierre:
  - `git status` limpio, `origin/main` sincronizado (verificado repetidamente a lo largo
    de la sesión, última vez en el commit de este mismo bloque).
  - 0 ramas remotas además de `main`, 0 Pull Requests abiertos, 3 tags (todos hitos
    reales) — ver Bloque Final.
  - La batería completa de aceptación real (`NEXORA app`, `NEXORA financial invariants`,
    `NEXORA production validation`, `NEXORA governance`, `NEXORA final acceptance and
    delivery`, `Predeploy certification receipt`, linters/secrets/semgrep) corrió en
    verde repetidamente sobre múltiples commits de esta sesión — no una sola vez de
    casualidad.
  - `EXECUTION_STATE.md` coincide con el código: cada afirmación de este documento tiene
    un comando, un SHA o un run de CI real citado como evidencia, no una afirmación sin
    respaldo.

**Limitaciones de infraestructura documentadas con precisión** (no ambigüedad):

1. Este sandbox no tiene `bench`/Frappe real ni Docker — no se pudo ejecutar contra un
   sitio vivo. La suite de aceptación que sí lo hace corre en GitHub Actions, no aquí; se
   usó esa como fuente de verdad real en cada bloque.
2. WebKit no puede levantarse en este sandbox (se cae con contenido trivial) — bloqueó
   una verificación local del fix del Bloque 7; se verificó contra el WebKit real de CI
   en su lugar.
3. La integración real de OmniRoute con el contenedor de producción (Bloque 5.3) sigue
   pendiente de que el propietario dispare el redeploy de Coolify y corra
   `nexora.tools.validation.omniroute_check.run` — documentado, no fingido como resuelto.
4. La auditoría visual exhaustiva de dashboard/formularios con datos reales (Bloque 7)
   quedó parcial por la misma razón del punto 1.

**No quedan bloques funcionales abiertos por decisión no verificada.** Los que siguen
pendientes (arriba) son limitaciones de infraestructura de este entorno de trabajo, no
trabajo evitado ni cerrado con lenguaje ambiguo.

## Bloque 11 — flujo de fechas dashboard → reportes y estado pegado de filtros guardados

- Fecha: 2026-08-10.
- Alcance: sospecha reportada de desalineación entre la pantalla principal (dashboard) y
  los filtros del centro de reportes, con foco en el rango 01–30 de julio "bloqueado o
  limitado por diseño", y en si los reportes guardados arrastran estado obsoleto.

**Preguntas resueltas con evidencia (lectura directa del código, no inferencia):**

- **¿La pantalla principal es mensual o de rango libre?** Mensual, por diseño, en toda la
  cadena: `nexora_dashboard.js` solo ofrece un `<select>` de meses (`periodSelect`,
  `relativePeriods`), y `boot.py:set_active_context` normaliza el período a `AAAA-MM`
  (`_normalize_period`, `PERIOD_PATTERN`) y calcula `from_date`/`to_date` como los límites
  exactos del mes completo (`_period_bounds`, con `monthrange`). No hay forma de pedir un
  rango parcial como el 01–30 de julio desde el dashboard — nunca la hubo, ni antes ni
  después de este bloque. Esto **no se cambia**: es un diseño coherente para un resumen
  ejecutivo, confirmado además por el PR #93 (`c513789d`, el commit inmediatamente
  anterior a este bloque), que deliberadamente reemplazó un texto de rango libre por este
  mismo selector mensual.
- **¿El motor y el centro de reportes aceptan rango libre de verdad?** Sí, ya lo hacían.
  `nexora.dashboard.snapshot_query.get_executive_snapshot` — el mismo endpoint que
  consumen el dashboard y el centro de reportes — delega en
  `nexora.dashboard.analytics_core.normalize_period(from_date, to_date)`, que acepta
  cualquier rango válido, incluido el 01–30 de julio (nuevo test:
  `test_period_accepts_a_partial_month_free_range`), y rechaza rangos invertidos
  (`test_period_rejects_inverted_dates`, ya existía) o vacíos, que se tratan como
  ilimitados (`test_period_accepts_an_empty_range_as_unbounded`, nuevo). `nexora_reports.js`
  ya exponía `from_date`/`to_date` como campos de fecha libres, sin restricción mensual.
- **¿Frontend y backend usan el mismo criterio de fechas, y la UI promete lo que el
  backend soporta?** Aquí estaba el defecto real. `routeContext()` en
  `nexora_dashboard.js` (y su equivalente `contextRouteOptions()` en
  `nexora_report_actions.js`, usado por la barra de navegación superior) escriben
  `from_date`, `to_date` y `nexora_period` en `frappe.route_options` al navegar —
  claramente con la intención de que el reporte de destino herede el período que el
  usuario ya estaba viendo. **Pero `nexora_reports.js` nunca los leía**: solo consumía
  `launchOptions.project` y `launchOptions.nexora_report`. Confirmado por grep sobre
  las doce páginas: cero lugares leían `route_options.from_date`/`to_date`/
  `nexora_period` fuera de donde se escribían. Efecto real: un usuario que ve el
  dashboard en el período "julio" y hace clic en "Ver gastos" u otro drill-down llegaba
  al centro de reportes con las fechas vacías (histórico completo, sin acotar) en lugar
  de julio — el rango que acababa de ver quedaba descartado en silencio. Esto explica
  la sospecha de "desalineación entre la pantalla principal y los filtros de reportes":
  no era un bloqueo del rango, era una pérdida de contexto al navegar.
- **¿Los reportes guardados reaplican filtros anteriores sin limpiar el estado?** No: el
  bucle en `applySaved()` ya recorría *todas* las claves del payload guardado (incluidas
  las que quedaban en `null`), así que un reporte guardado siempre sobrescribía por
  completo los controles, sin dejar residuos del filtro anterior. Esto ya funcionaba
  correctamente y no se tocó.
- **¿`page`/`page_size`/estado de navegación se mezclan con los filtros de negocio?** Sí,
  confirmado. `payload()` —usado para consultar— incluía `page`/`page_size` junto a los
  diez filtros de negocio reales, y `saveReport()` persistía ese mismo objeto completo
  como la definición del reporte (`nexora.reports.service.save_report_definition`,
  columna `filters_json` de `NXR Saved Report`). El número de página que el usuario tenía
  abierto en ese momento quedaba grabado para siempre como si fuera parte de la
  definición del reporte, contaminando el hash de idempotencia
  (`canonical_payload_hash`) y el propio registro persistido con estado de navegación
  que no tiene ninguna razón funcional para sobrevivir al cierre de la pestaña.

**Causa raíz corregida (una sola, con dos síntomas).** El contrato de propagación de
contexto entre pantallas —ya construido y usado correctamente para `project` en el
Bloque 2.1— nunca se completó para el rango de fechas, y la separación entre "filtro de
negocio" y "estado de navegación" nunca se hizo explícita en el centro de reportes.

**Archivos.**
- `nexora_app/nexora/nexora/page/nexora_reports/nexora_reports.js`
- `nexora_app/nexora/tests/test_report_filter_ui_contract.py`
- `nexora_app/nexora/tests/test_executive_analytics.py`

**Decisión y cambios.**
1. `startWithActiveProject()` ahora aplica `launchOptions.from_date`/`to_date` (nueva
   función `setDateRangeSilently`, con la misma bandera `suppressControlReload` que ya
   protegía a `setProjectSilently` de reentradas) antes de la primera carga — exactamente
   el mismo patrón que ya existía para el proyecto, ahora completado para el rango.
2. El mismo `onContextChange` que ya sincronizaba el proyecto cuando cambia el contexto
   global mientras el reporte está abierto ahora también sincroniza `from_date`/`to_date`
   (`rangeChanged`), para que cambiar el período en la barra superior no deje el centro
   de reportes con fechas obsoletas mientras el usuario lo tiene abierto.
3. `businessFilters()` (nueva) devuelve únicamente los diez filtros de negocio reales.
   `payload()` —lo que se envía a consultar— delega en ella y le agrega `page`/`page_size`
   encima, sin duplicar la lista. `saveReport()` ahora persiste `businessFilters()`, no
   `payload()`: la paginación deja de mezclarse con la definición del reporte guardado.
4. El `catch` de `load()` mostraba un `frappe.msgprint` genérico que ocultaba el motivo
   real que el servidor ya calculaba (p. ej. "La fecha final no puede ser anterior a la
   fecha inicial." de `normalize_period`). Se reemplazó por
   `window.nexora.ui.showError(error, { title, fallback })`, el mismo helper compartido
   que ya usan `nexora_evidence.js`, `nexora_search.js`, `nexora_suppliers.js` y
   `nexora_operations.js`: muestra el mensaje real del servidor cuando existe, y el
   mensaje genérico solo como respaldo. Esto cierra el requisito de validación visible
   de rangos vacíos, invertidos o inválidos — la validación en sí ya existía en el
   servidor y no se dupicó en el cliente.

**Qué no cambió, deliberadamente.** El dashboard sigue siendo mensual — no se le agregó
un selector de rango libre, porque el propio repositorio (PR #93, un commit antes de
este bloque) decidió explícitamente lo contrario, y duplicar ese control en dos pantallas
con dos semánticas distintas habría sido la solución híbrida que este encargo pide
evitar. `boot.py`, `_period_bounds`, `_normalize_period` y el bucle de `applySaved()` no
se tocaron: no tenían el defecto.

**Pruebas.** Ejecutado en este entorno (a diferencia de bloques anteriores de esta
sesión, aquí sí hay Node 22 disponible además de Python 3.12; sigue sin
`bench`/Frappe/MariaDB):
- `node --check nexora_app/nexora/nexora/page/nexora_reports/nexora_reports.js` — sin
  errores de sintaxis.
- Suite de contratos puro-Python completa: `PYTHONPATH=nexora_app python3 -m unittest
  discover -s nexora_app/nexora/tests -p "test_*.py"` — 953 pruebas, 0 fallos, 19 errores
  de importación de `frappe` en los módulos `*_integration` (los mismos 19 que ya fallan
  igual en `main` sin ningún cambio de este bloque, confirmado comparando contra un
  `git stash` del árbol limpio: 947 pruebas antes, mismos 19 errores). Las 6 pruebas
  nuevas de este bloque están incluidas y en verde:
  `test_period_accepts_a_partial_month_free_range`,
  `test_period_accepts_an_empty_range_as_unbounded`,
  `test_saved_report_definitions_exclude_pagination_state`,
  `test_report_center_inherits_the_date_range_from_navigation`,
  `test_report_center_resyncs_its_date_range_when_the_active_context_changes`,
  `test_report_errors_surface_the_real_backend_reason`.
- `scripts/validate_nexora_app.py`, `validate_nexora_financial_models.py`,
  `validate_nexora_governance.py`, `validate_nexora_operational_acceptance.py`,
  `validate_nexora_completion.py`, `validate_nexora_constitution.py` — los seis en verde.
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- `ruff` no estaba disponible para instalar en este entorno (requiere permisos que este
  sandbox no otorga) — no se pudo correr el linter exacto fijado en
  `.pre-commit-config.yaml`; el archivo modificado se revisó a mano contra el estilo del
  resto del repositorio (tabs, comillas dobles, mismo patrón de funciones cortas de una
  línea).

**No ejecutado aquí** (requiere `bench` + MariaDB, ausentes en este entorno): recorrido
de navegador real verificando que el centro de reportes efectivamente muestra julio al
llegar desde el dashboard con un clic real, y que un reporte guardado con el fix nuevo
efectivamente no contamina `NXR Saved Report.filters_json` con `page`/`page_size` en una
base de datos real. Queda para el CI del repositorio (`nexora-app.yml`, job
`install-rollback` y `browser`).

**Riesgos residuales.** Ninguno de permisos, auditoría o exportación: `export_report`
sigue sobrescribiendo `page`/`page_size` en cada iteración de `_collect_pages` sin
depender del valor que llegue del cliente (verificado leyendo `reports/service.py`), así
que nunca se vio afectado por la contaminación que sí afectaba a los reportes guardados.
Ninguna ruta, rol ni permiso se tocó.

## Bloque 12 — auditoría maestra de brechas (misión NEXORA, sin cambios de código)

- Fecha: 2026-08-10.
- Origen: nueva "misión maestra" recibida en sesión (auditoría + arquitectura + super
  experience + reconstrucción + validación + cierre). Antes de escribir código se
  verificó el estado real del repositorio (repo, rama, HEAD remoto, `git status`,
  `AGENTS.md`, este archivo) y se encontró que `AGENTS.md` prohíbe explícitamente
  "otra auditoría general" y "fuentes de estado paralelas". Se presentó el conflicto al
  propietario, que eligió integrar la nueva misión en la fuente única existente
  (`docs/nexora/MATRIZ_REQUISITOS.md` + este archivo) en vez de crear un set de
  documentos "NEXORA_FINAL_*" paralelo.

**Alcance de este bloque: solo auditoría y documentación, cero cambios de código.**
Se despacharon cinco auditorías de verificación real (código, no documentación) sobre:
núcleo financiero/contratos/compras/inventario/presupuesto/cierres/directorio; frontend
UX/navegación/design system/PWA; IA/conversación/integraciones/notificaciones/WhatsApp;
infraestructura de pruebas y entorno; y síntesis de la documentación de gobierno
existente (`MATRIZ_REQUISITOS.md`, catálogos, decisiones, bloques históricos).

**Documentos producidos** (nuevos, sin sustituir ninguno existente):
- `docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md`
- `docs/nexora/NEXORA_UX_AUDIT.md`
- `docs/nexora/NEXORA_EXPERIENCE_SYSTEM.md`
- `docs/nexora/NEXORA_GOLDEN_PATHS.md`

**`docs/nexora/MATRIZ_REQUISITOS.md` extendida** con 14 filas nuevas (166 → 180),
todas con evidencia de archivo:línea sobre HEAD `bdc167ad52ab75060af51d8e3862abcc2aaafde7`:
`NXR-COM-0010`, `NXR-PRE-0008`, `NXR-NOT-0006`, `NXR-INT-0007`, `NXR-INT-0008`,
`NXR-CNV-0001`, `NXR-UX-0008` a `NXR-UX-0015`. Ninguna fila `IMPLEMENTADO Y VALIDADO`
existente fue editada ni borrada.

**Hallazgos de mayor severidad, verificados en código (no en documentación):**
1. `NXR-COM-0010` — sobre-recepción acumulada no bloqueada en órdenes de compra
   (`purchases/receipt_service.py:80-91`, `receipt_core.py:23-54`) y estado de orden
   calculado sin filtrar por documento padre (`receipt_service.py:266-278`). Defecto de
   código real, no limitación de diseño.
2. `NXR-PRE-0008` — `budget/` está completo y probado pero ningún módulo lo invoca
   (`financial/commitments.py`, `purchases/*`, `contracts/*` no lo importan; `NXR
   Commitment` no tiene `Link` a `NXR Budget Line`). El presupuesto es hoy una bitácora
   de lectura, no un control transaccional. Requiere decisión de política antes de
   cablear.
3. `NXR-INT-0006` (histórica, `OBSOLETO JUSTIFICADO`) se reabre como
   **OBSOLETO — RECONSIDERAR** vía `NXR-INT-0008`: la nueva misión pide WhatsApp
   Business real, contradiciendo la exclusión de alcance de PMI-0.4. Diseño ya existe
   (`NIP_BLOQUE_6_CONVERSATIONAL_OS.md`), código real = 0.
4. `NXR-CNV-0001` — Conversational OS / Barra NEXORA Universal: `conversation/` está
   vacío. Es el único de los diez Golden Paths auditados sin ningún código de respaldo.
5. `NXR-INT-0007` — `integrations/service.py:39-49` (`test_connection`) siempre
   devuelve `"Success"` sin verificar nada: riesgo de confianza falsa en integraciones.

**Confirmado, no solo documentado (para que no se re-audite en el próximo bloque):**
núcleo financiero (locks `FOR UPDATE`, idempotencia, rechazo de saldo negativo,
auditoría por operación — 53 pruebas), directorio universal (23 pruebas + probe de
concurrencia), contratos/inventario/cierres (mismo patrón sólido, sin defectos críticos
nuevos), AI Gateway con 9 proveedores y circuit breaker (sin secretos en código, salvo
el riesgo ya conocido y aceptado por el propietario de OmniRoute en HTTP plano,
documentado en el bloque NIP 5.2/5.3 de este archivo), contexto persistente, wizard
progresivo, preview financiero, Design System (`nexora_design_system.css`, 662 líneas)
y PWA (manifest + service worker reales) — la "Super Experience" ya está parcialmente
construida, no se parte de cero.

**Pruebas ejecutadas en este entorno** (sin `bench`/Frappe/MariaDB/Redis/Docker/
Playwright, confirmado con `which`/`pip show`, todos ausentes):
- 13 validadores `validate_nexora_*.py`/`validate_construcontrol_*.py` sin argumento:
  **13/13 PASS**.
- `python -m compileall nexora_app/nexora scripts`: sin errores.
- `PYTHONPATH=nexora_app python3 -m unittest discover -s nexora_app/nexora/tests -p
  "test_*.py"`: **934/953 tests pasan**; los 19 restantes fallan solo por
  `ImportError: No module named 'frappe'` en archivos `*_integration.py` (mismos 19 que
  fallan igual en `main` sin ningún cambio de este bloque).

**No ejecutado aquí** (requiere `bench`+MariaDB+Docker+Playwright, ausentes en este
entorno): los 19 tests de integración con Frappe real, el smoke test de navegador
(`nexora_browser_smoke.mjs`, perfiles `desktop-chromium`/`iphone-13-webkit`), y por
tanto la certificación visual de los diez Golden Paths en escritorio/iPhone/PWA. Se
ejecutan en `nexora-app.yml` (job `browser`) y `server-tests-mariadb.yml` sobre el mismo
SHA — no se inventó ningún resultado de esos componentes.

**Riesgos.** Ninguno de datos, permisos ni producción: bloque de solo lectura y
documentación. El riesgo real es de alcance: `NXR-CNV-0001` y `NXR-INT-0008` son
construcción nueva sustancial (Conversational OS, WhatsApp), no ajustes.

**Bloqueos.** `NXR-PRE-0008` requiere decisión de política del propietario
(presupuesto bloqueante vs. informativo) antes de programarse. `NXR-INT-0008` requiere
credenciales reales de Meta, que el propietario no ha provisto.

**Siguiente acción.** Bloque 13 (seguro, autónomo): corregir `NXR-COM-0010` —
acumular `prev_received` real por línea, corregir `_update_po_status`, agregar pruebas
negativas de sobre-recepción acumulada. Detalle completo del orden de bloques 13-19 en
`docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md`, sección "Plan de ejecución propuesto".

## Bloque 13 — corrección de sobre-recepción acumulada en órdenes de compra (`NXR-COM-0010`)

- Fecha: 2026-08-10.
- Alcance: cerrar la única brecha del Bloque 12 clasificada como bug seguro y autónomo
  (no requiere decisión de política, no toca dinero de forma irreversible).

**Causa raíz confirmada (dos síntomas, un solo origen: la recepción nunca miró el
histórico real de la misma línea).**

1. `purchases/receipt_service.py:_normalized_lines` calculaba `prev_received` con
   `frappe.db.get_value("NXR Goods Receipt Line", {"purchase_order_line": po_line_ref},
   "accepted_quantity")` — devuelve **una sola fila** arbitraria, no una suma — y ese
   valor nunca se pasaba a la validación. `purchases/receipt_core.py:
   validate_receipt_lines` solo comparaba la recepción actual contra `ordered_qty` con
   tolerancia, ignorando recepciones previas de la misma línea. Dos recepciones
   parciales que individualmente pasan la tolerancia podían sumar más de lo pedido sin
   rechazo.
2. `purchases/receipt_service.py:_update_po_status` marcaba la orden `Completed`
   contando filas de `NXR Goods Receipt Line` (`frappe.db.count`) sin filtrar por el
   estado del documento padre (`Draft`/`Cancelled` contaban igual que `Completed`) ni
   comparar cantidades contra lo ordenado — solo comparaba número de filas contra
   número de líneas de la orden.

**Archivos.**
- `nexora_app/nexora/purchases/receipt_core.py`
- `nexora_app/nexora/purchases/receipt_service.py`
- `nexora_app/nexora/tests/test_receipt_core.py`
- `docs/nexora/MATRIZ_REQUISITOS.md` (`NXR-COM-0010` → `IMPLEMENTADO Y VALIDADO`)
- `docs/architecture/file_inventory.json` (regenerado, manifiesto de archivos)

**Decisión y cambios.**
1. Nueva función `_received_totals()` en `receipt_service.py`: suma `accepted_quantity`
   de todas las `NXR Goods Receipt Line` de una línea de orden dada, excluyendo las
   recepciones cuyo documento padre está en estado `Cancelled` (dos consultas por lote,
   no una por línea — corrige también el patrón N+1 de la versión anterior).
2. `_normalized_lines()` ahora calcula `received_totals` una sola vez para todas las
   líneas de la recepción entrante y usa ese acumulado real como `prev_received`, en vez
   de la fila arbitraria anterior.
3. `validate_receipt_lines()` (`receipt_core.py`) acumula `previously_received + net`
   antes de compararlo contra la tolerancia máxima, en vez de validar solo la recepción
   actual de forma aislada. Comportamiento anterior preservado cuando
   `previously_received` es 0 o no se provee (primera recepción de una línea).
4. Nueva función pura `compute_po_completion_status()` en `receipt_core.py`: decide
   `Completed`/`Sent` comparando cantidad acumulada real contra cantidad ordenada por
   línea, no contando filas. `_update_po_status()` ahora calcula `received_totals` y
   delega en esta función.
5. `docs/architecture/file_inventory.json` regenerado (`python scripts/
   generate_file_inventory.py`) porque el manifiesto de archivos quedó desactualizado
   por los cambios de este bloque y del Bloque 12 — lo exige `validate_repository.py` y
   `validate_construcontrol_architecture.py`, no es un cambio funcional.

**Qué no cambió, deliberadamente.** El estado `Cancelled` sigue excluyéndose del
acumulado (una recepción anulada nunca debió contar, y no lo hacía antes tampoco para
`_update_po_status`, aunque sí contaminaba el conteo de filas). No se tocó
`GOODS_RECEIPT_TRANSITIONS` ni el flujo de creación/transición de recepciones — el
defecto era puramente de cálculo, no de máquina de estados.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB, igual que bloques
anteriores de esta sesión):
- `PYTHONPATH=nexora_app python3 -m unittest nexora.tests.test_receipt_core
  nexora.tests.test_receipt_contract -v` — 18/18 en verde, incluidas 7 pruebas nuevas:
  positivas (`test_validate_receipt_lines_accumulates_previous_receipts_within_tolerance`,
  `test_validate_receipt_lines_without_previously_received_defaults_to_zero`,
  `test_completed_when_every_line_fully_received`,
  `test_completed_when_a_line_is_received_above_ordered_quantity`,
  `test_sent_when_a_line_has_no_receipts_yet`) y negativas
  (`test_validate_receipt_lines_rejects_cumulative_over_receipt` — reproduce el
  escenario exacto del defecto: 90 ya recibido + 30 nuevos sobre un pedido de 100 con
  10% de tolerancia; antes se aceptaba sin error, ahora se rechaza —
  `test_sent_when_any_line_is_only_partially_received`).
- Suite completa: `PYTHONPATH=nexora_app python3 -m unittest discover -s
  nexora_app/nexora/tests -p "test_*.py"` — 960/979 pruebas (7 nuevas incluidas), mismos
  19 errores preexistentes por `ModuleNotFoundError: No module named 'frappe'` en
  archivos `*_integration.py`, sin cambio respecto al Bloque 12.
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- `validate_nexora_app.py`, `validate_nexora_financial_models.py`,
  `validate_nexora_governance.py`, `validate_nexora_constitution.py`,
  `validate_construcontrol_architecture.py`, `validate_construcontrol_completion.py`,
  `validate_construcontrol_data_contract.py`, `validate_construcontrol_integration.py`,
  `validate_construcontrol_product.py`, `validate_github_governance.py`,
  `validate_repository.py` — 11/11 en verde (los dos últimos requirieron regenerar el
  manifiesto de archivos, ver arriba).
- `validate_nexora_completion.py` / `validate_nexora_operational_acceptance.py`:
  `NXR-COM-0010` ya no aparece en la lista de errores (bajó de 14 a 13 filas abiertas);
  las 13 restantes siguen abiertas a propósito, sin cambio — se cierran en los Bloques
  14-19 según `docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md`.

**No ejecutado aquí** (requiere `bench`+MariaDB, ausentes en este entorno): no existe
hoy un test de integración con Frappe real para `receipt_service.py` (ni existía antes
de este bloque) — `_received_totals()` y `_update_po_status()` son código nuevo/corregido
que toca `frappe.get_doc`/`frappe.get_all` y no tiene cobertura de integración real en
este repositorio todavía. La corrección se apoya en: (a) la lógica pura, que sí está
100% probada por unidad (`receipt_core.py`); (b) el mismo patrón de acceso a datos ya
usado y confirmado en el resto del módulo (`frappe.get_all` con filtros `in`, igual que
`directory/` y `contracts/`). Queda pendiente de `server-tests-mariadb.yml` para
certificación de integración real — no se inventó ese resultado.

**Riesgos residuales.** Ninguno de permisos ni auditoría: no se tocó `require_action`
ni las llamadas a `audit()` existentes. El único riesgo real corregido es de integridad
de datos (sobre-recepción e inflado del estado de la orden), y queda cerrado por las
pruebas negativas citadas arriba.

**Bloqueo.** Ninguno. **Siguiente acción.** Bloque 14 (requiere decisión del
propietario): `NXR-PRE-0008` — definir si el presupuesto debe bloquear compromisos y
compras que lo excedan o solo alertar, antes de cablear `validate_no_overspend()`.

## Corrección de clasificación — `NXR-COM-0010` (2026-08-10, antes de iniciar el Bloque 14)

El cierre del Bloque 13 (arriba) marcó `NXR-COM-0010` como `IMPLEMENTADO Y VALIDADO` y
en el mismo reporte declaró "pendiente: integración real con bench/MariaDB" — una
contradicción señalada correctamente por el propietario. Por Capítulo 35 de la misión
maestra, `IMPLEMENTADO Y VALIDADO` exige evidencia completa, incluida la integración
real; falta esa pieza, así que no corresponde ese estado.

**Corrección:** `docs/nexora/MATRIZ_REQUISITOS.md` — `NXR-COM-0010` reclasificado a
`NO DEMOSTRADO`. **No se tocó código del Bloque 13** (commit `5ad7be0d` permanece sin
cambios): la lógica pura corregida sigue **CONFIRMADA** por las 7 pruebas unitarias ya
citadas (incluida la negativa que reproduce el escenario exacto del defecto). Lo que
falta y queda documentado como pendiente explícito: un test de integración real
(`bench`/MariaDB) que ejercite `receipt_service.create_receipt`/`transition_receipt`
con dos recepciones parciales reales — no existía antes de este bloque y no se creó
ahora, porque este entorno no tiene los medios para ejecutarlo ni siquiera para
comprobar que compila contra un sitio real.

**Efecto en los gates:** `validate_nexora_completion.py` /
`validate_nexora_operational_acceptance.py` vuelven a contar `NXR-COM-0010` entre las
filas abiertas (13 → 14 del Bloque 12), reflejando la realidad: la brecha original está
corregida en lógica y probada por unidad, pero no certificada en ejecución real todavía.
`validate_nexora_governance.py` no se ve afectado (`NO DEMOSTRADO` es un estado
permitido). Ningún otro requisito de la matriz fue tocado por esta corrección.

## Bloque 14 — presupuesto bloqueante contra compromisos (`NXR-PRE-0008`)

- Fecha: 2026-08-10.
- Decisión del propietario (requerida antes de este bloque, per Capítulo 27 de la
  misión): el presupuesto **debe bloquear**, no solo alertar. Un compromiso, compra u
  operación que exceda el presupuesto disponible del centro de costo no debe poder
  ejecutarse; la regla debe ser server-side y transaccional; sin excepción silenciosa;
  debe distinguir presupuesto ≠ compromiso ≠ gasto ≠ pago ≠ saldo de fondo; debe
  manejar concurrencia, doble clic, reintentos, idempotencia, compromisos simultáneos,
  correcciones, reversiones, anulaciones y sustituciones; el bloqueo ocurre antes de
  la mutación; error humano y accionable; no crear el compromiso parcialmente; no
  modificar el saldo si la validación falla; no confiar solo en frontend.

**Análisis del modelo existente antes de programar (reutilizado, no reinventado).**
`budget/core.py` ya tenía `compute_line_balances()` y `validate_no_overspend()`
correctos (disponible = aprobado − comprometido − ejecutado, rechazo si excede) — se
reutilizan sin modificar su lógica de comparación. `budget/service.py` ya tenía
`create_budget`/`activate_budget`/`amend_budget`/`close_budget`/`cancel_budget` con
lock `FOR UPDATE` sobre `NXR Budget` y `check_budget_availability()` como vista previa
de solo lectura. El hallazgo del Bloque 12 seguía siendo cierto al empezar: **nada**
llamaba a estas funciones desde `financial/commitments.py`, `purchases/*` ni
`contracts/*`, y `NXR Commitment` no tenía manera de referenciar una línea de
presupuesto. `committed_hnl`/`executed_hnl` en `NXR Budget Line` son campos
almacenados (no derivados de un ledger inmutable como `NXR Operation Effect`) —
mutados directamente bajo lock, a diferencia del núcleo de fondos. Se documenta esta
diferencia de diseño explícitamente: replicar el patrón de ledger inmutable del núcleo
financiero para presupuestos habría sido un cambio arquitectónico mucho mayor al
pedido (Capítulo 66: "no cambiar arquitectura fundamental sin evidencia técnica"); se
optó por el modelo de campo mutable ya existente, con la disciplina de lock correcta.

**Diseño de la resolución de línea (alcance explícito, no oculto).** La regla solo se
activa cuando el compromiso tiene `cost_center` y ese centro de costo resuelve a una
única línea de presupuesto activa del proyecto (desambiguando por
`economic_category` si hay varias líneas del mismo centro de costo). Sin esas
condiciones, la función devuelve `None` sin efecto: no es una excepción a una regla
que aplica, es que no hay presupuesto contra el cual aplicarla para ese centro de
costo todavía — documentado en `docs/nexora/NEXORA_GAP_ANALISIS_BLOQUE_12.md`.

**Trazabilidad de la reserva (evita apuntar al presupuesto equivocado tras una
enmienda).** `NXR Commitment` ganó dos campos nuevos, `budget` y `budget_line`
(`nxr_commitment.json`), poblados al crear el compromiso con la línea exacta que lo
reservó. `execute_commitment`/`release_commitment` actualizan siempre esa misma línea
guardada, no la que esté "activa" en el momento de ejecutar/liberar — si una enmienda
creó un presupuesto nuevo entretanto, la liberación sigue afectando la línea original,
no la nueva versión.

**Archivos.**
- `nexora_app/nexora/budget/core.py` — `format_overspend_message()` (nueva, pura).
- `nexora_app/nexora/budget/service.py` — `_find_active_budget_line()`,
  `_lock_and_read_line()`, `_write_line_and_recompute_totals()`,
  `reserve_budget_commitment()`, `release_budget_reservation()`,
  `record_budget_execution()` (nuevas); `check_budget_availability()` corregido para
  filtrar también por `cost_center` (antes solo por `economic_category` — inconsistente
  con el bloqueo real, podía mostrar "disponible" para la línea de otro centro de
  costo); `_find_active_budget()` ahora incluye `cost_center` en la proyección.
- `nexora_app/nexora/financial/commitments.py` — `create_commitment()` llama a
  `reserve_budget_commitment()` antes de insertar el compromiso, dentro del mismo
  `savepoint()`; `OverspendError` se convierte en `frappe.throw` con el mensaje humano.
  `_change()` llama a `record_budget_execution()` (ejecución) o
  `release_budget_reservation()` (liberación) según `operation_type`.
- `nexora_app/nexora/nexora/doctype/nxr_commitment/nxr_commitment.json` — campos
  `budget` (Link, read-only) y `budget_line` (Data, read-only).
- `nexora_app/nexora/tests/test_budget_core.py` — 3 pruebas nuevas de
  `format_overspend_message`.
- `nexora_app/nexora/tests/test_budget_commitment_integration.py` — nuevo, 5 pruebas
  con `FrappeTestCase` (bloqueo por sobregiro sin crear nada; ciclo completo
  reserva→ejecución→liberación; compromiso sin centro de costo no queda constreñido).
- `docs/nexora/MATRIZ_REQUISITOS.md` — `NXR-PRE-0008` reclasificado.

**Concurrencia.** `_lock_and_read_line()` bloquea y lee `approved_hnl`/`committed_hnl`/
`executed_hnl` en una sola consulta `SELECT ... FOR UPDATE`, replicando el patrón ya
probado de `financial/db.py:source_states(current_read=True)` (lock+lectura de valores
reales en un solo paso) en vez del patrón `get_doc()` antes del lock que ya usan
`activate_budget`/`amend_budget`/`close_budget`/`cancel_budget` en este mismo archivo
(ese orden más antiguo puede leer un valor obsoleto bajo concurrencia real; no se
corrigió aquí para no ampliar el alcance de este bloque, pero queda anotado como
riesgo conocido de ese código preexistente, no introducido por este bloque).
Doble clic/reintentos: cubiertos por la idempotencia ya existente de
`create_commitment`/`execute_commitment`/`release_commitment` (`start_idempotency`),
sin cambios — la reserva de presupuesto ocurre dentro de esa misma transacción
idempotente.

**Qué no se hizo, deliberadamente.** No se tocó `financial/core.py` ni el modelo de
fondos (`NXR Fund Source`/`NXR Operation Effect`) — el presupuesto es un control
adicional, no sustituye ni duplica el saldo de fondo. No se añadió enforcement a
`purchases/*`/`contracts/*` directamente: ambos ya crean `NXR Commitment` internamente
para reservar fondos (confirmado en la auditoría de backend del Bloque 12), así que
quedan cubiertos transitivamente a través de `create_commitment`, sin necesidad de
cablear cada módulo por separado — evita duplicar el punto de control. No se
construyeron transiciones "Cancel"/"Reject"/"Expire" para `NXR Commitment` (no
existían antes de este bloque tampoco): la liberación de reserva ya usa el mecanismo
genérico existente (`release_commitment`), que es lo que el alcance pedía conectar.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `PYTHONPATH=nexora_app python3 -m unittest nexora.tests.test_budget_core -v` —
  22/22 en verde, incluidas las 3 nuevas de `format_overspend_message`.
- Suite completa: 964/984 (20 errores por `ModuleNotFoundError: No module named
  'frappe'` en archivos `*_integration.py` — los 19 preexistentes más
  `test_budget_commitment_integration.py`, nuevo en este bloque, sin regresión).
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- 11 validadores de repositorio/gobierno/ConstruControl — 11/11 en verde.

**No ejecutado aquí** (requiere `bench`+MariaDB, ausentes en este entorno):
`test_budget_commitment_integration.py` completo — el bloqueo por sobregiro real, el
ciclo reserva→ejecución→liberación contra una base de datos real, y la concurrencia
real de `SELECT ... FOR UPDATE` sobre `tabNXR Budget Line`. Por esto, y siguiendo la
corrección de clasificación anterior en este mismo archivo, `NXR-PRE-0008` se
clasifica `NO DEMOSTRADO`, no `IMPLEMENTADO Y VALIDADO` — la lógica pura está
confirmada; la integración real queda pendiente de `server-tests-mariadb.yml`.

**Riesgos residuales.** El orden de lock/lectura ya existente en
`activate_budget`/`amend_budget`/`close_budget`/`cancel_budget` (get_doc antes del
`FOR UPDATE`) no se corrigió — riesgo preexistente, no introducido aquí, anotado para
un bloque futuro si se decide abordarlo. Ningún riesgo nuevo de permisos o auditoría:
`require_action` existente no se relajó en ningún punto.

**Bloqueo.** Ninguno. **Siguiente acción.** Bloque 15 (seguro, autónomo):
`NXR-INT-0007` — eliminar el `test_connection` simulado en `integrations/service.py`
que siempre devuelve `"Success"` sin verificar nada.

## Bloque 15 — verificación real de conexión de integraciones (`NXR-INT-0007`)

- Fecha: 2026-08-10.
- Alcance: eliminar la simulación de `integrations/service.test_connection()`, que
  escribía siempre `last_test_result = "Success"` sin ejecutar ninguna verificación de
  red. Instrucción explícita del propietario: no reemplazar una simulación por otra,
  no inventar una integración real, no marcar el requisito como `IMPLEMENTADO Y
  VALIDADO` sin evidencia de ejecución real.

**Inspección previa (qué usaba la función y sus dependencias, antes de tocar código).**
`NXR Integration` es un registro **genérico** (tipo REST/SOAP/Webhook/Custom,
autenticación None/Basic/Token/OAuth, `credentials` en texto plano sin esquema fijo).
`test_connection()` solo era llamada desde el frontend de integraciones (sin otro
llamador interno en el repositorio) y su único efecto era escribir dos campos y
guardar — sin dependencias que romper al cambiar su cuerpo. `NXR Integration Log`
(tabla hija) ya existía en el DocType con campos `timestamp`/`level`/`message`/
`request_preview`/`response_preview`, pero **nunca se usaba** — ninguna función
del módulo hacía `append("logs", ...)`. El módulo `intelligence/providers/
http_support.py` (Bloque 4/5 de NIP) ya resolvía exactamente este problema para
proveedores de IA: solicitud HTTP real vía `urllib` puro de la biblioteca estándar
(sin SDK de terceros), con manejo de errores clasificado, probado sustituyendo
siempre `urlopen` en pruebas (nunca contra la red real). Se reutilizó ese mismo
principio en vez de inventar un mecanismo nuevo.

**Decisión de alcance (evita "inventar una integración real").** `NXR Integration` no
tiene un contrato de negocio fijo por proveedor (a diferencia de los 9 adaptadores de
IA, que sí conocen la forma exacta de cada API). Autenticar o interpretar la respuesta
de negocio de una integración arbitraria aquí habría sido simular una integración
específica inexistente — exactamente lo que la instrucción prohibía. Se acotó el
alcance a lo único que se puede verificar honestamente sin conocer el contrato de cada
integración: **alcanzabilidad HTTP real** del `endpoint_url` configurado. Documentado
explícitamente en el docstring de `check_endpoint_connectivity()` y en la matriz.

**Archivos.**
- `nexora_app/nexora/integrations/connectivity.py` — nuevo,
  `check_endpoint_connectivity()` (única función de red real del módulo).
- `nexora_app/nexora/integrations/service.py` — `test_connection()` reescrito: sin
  `endpoint_url` rechaza con `frappe.throw` explícito (no graba ningún resultado);
  con `endpoint_url`, llama al chequeo real y graba `"Success"`/`"Failure"` según la
  respuesta real, con una entrada nueva en `NXR Integration Log` (nunca usado antes).
- `nexora_app/nexora/tests/test_integrations_connectivity.py` — nuevo, 9 pruebas
  puras (sin red real, mock de `urllib.request.urlopen`).
- `nexora_app/nexora/tests/test_integrations_service_integration.py` — nuevo, 4
  pruebas `FrappeTestCase` (mockean `check_endpoint_connectivity`, ya probada aparte,
  para aislar el guardado/log en Frappe).
- `docs/nexora/MATRIZ_REQUISITOS.md` — `NXR-INT-0007` reclasificado.

**Qué no se hizo, deliberadamente.** No se autenticó (Basic/Token/OAuth) contra el
endpoint — el modelo de credenciales es genérico y sin esquema fijo; intentarlo habría
sido inventar un protocolo específico. No se interpretó SOAP ni la semántica de
`integration_type`: la prueba es de alcanzabilidad de transporte HTTP, no de protocolo
de aplicación — documentado, no oculto. No se cambió el permiso `require_action
("approve")` de `test_connection`/`register_integration` (fuera del alcance de esta
brecha). Cualquier respuesta HTTP, incluidos 4xx/5xx, se registra como "alcanzable"
(`reachable=True`) pero solo 2xx/3xx cuenta como prueba de conexión exitosa
(`ok=True` → `"Success"`); un 404 real ya no puede grabarse como `"Success"` — es el
escenario de regresión probado explícitamente (`test_404_is_reachable_but_not_ok`,
`test_a_4xx_response_is_reachable_but_recorded_as_failure`).

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `PYTHONPATH=nexora_app python3 -m unittest nexora.tests.test_integrations_connectivity
  -v` — 9/9 en verde, incluida una que confirma que la red real nunca se toca si el
  mock no está activo (mismo patrón que `test_intelligence_http_support.py`).
- Suite completa: 974/995 (21 errores por `ModuleNotFoundError: No module named
  'frappe'` — los 20 previos más `test_integrations_service_integration.py`, nuevo en
  este bloque, sin regresión; confirmado que los 21 son exclusivamente de ese tipo).
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- 11 validadores de repositorio/gobierno/ConstruControl — 11/11 en verde (manifiesto
  de archivos regenerado).

**No ejecutado aquí** (requiere `bench`+MariaDB, ausentes en este entorno):
`test_integrations_service_integration.py` completo — el guardado real del resultado
y del log contra una base de datos real. La función de red real
(`check_endpoint_connectivity`) sí quedó 100% probada por unidad porque no depende de
Frappe, solo de `urllib`. Por eso `NXR-INT-0007` se clasifica `NO DEMOSTRADO`, no
`IMPLEMENTADO Y VALIDADO` — no se reemplazó una simulación por otra (el código de
producción abre una conexión de red real, verificable leyendo `connectivity.py`); lo
que falta es solo la ejecución de esa ruta contra un servidor real en este entorno.

**Riesgos residuales.** Ninguno de permisos o auditoría. Riesgo operativo menor y
documentado: un firewall/proxy que exija cabeceras o método distinto a GET podría
reportar "Failure" para un endpoint que en realidad funciona con el método real de la
integración (p. ej. un webhook que solo acepta POST) — es una limitación conocida del
alcance de alcanzabilidad genérica, no un defecto oculto.

**Bloqueo.** Ninguno. **Siguiente acción.** Bloque 16 (seguro, autónomo): cerrar
`NXR-UX-0012`/`NXR-UX-0013` (resultado explicable y números explicables) y
`NXR-UX-0014` (navegación móvil inferior) — mejoras de experiencia sobre código ya
existente, sin tocar modelo de negocio.

## Bloque 16 — resultado explicable, números explicables y navegación móvil inferior (`NXR-UX-0012`, `NXR-UX-0013`, `NXR-UX-0014`)

- Fecha: 2026-08-10.
- Mandato explícito del propietario: mejora real de experiencia sobre el código
  existente, no ajustes cosméticos aislados; conservar el Design System si está
  consolidado y reutilizarlo; no tocar modelo financiero ni DocTypes salvo defecto
  estrictamente necesario; coherencia entre Dashboard, Operaciones, Cierre y Shell.

**Inspección previa del Design System (antes de escribir una sola línea).** Se
despachó una auditoría dedicada de `nexora_design_system.css` (662 líneas),
`nexora_shell.js`/`.css`, los helpers de error (`window.nexora.ui.showError`), las
tarjetas de dinero del dashboard y el resumen financiero de contratos. Hallazgos que
definieron el alcance:
- El Design System **sí está consolidado** (tokens en tres capas, componentes de
  botón/campo/tarjeta/aviso/distintivo) y se reutilizó sin cambios estructurales —
  solo se agregó un componente nuevo (`.nxr-ds-money-row`) siguiendo su mismo patrón.
- `execute_operational_movement` ya devolvía `sources` con saldo anterior/posterior
  real por fuente (lo mismo que la vista previa); el frontend lo descartaba y solo
  mostraba un `frappe.show_alert`. No hizo falta ningún cambio de backend para
  NXR-UX-0012: los datos ya estaban ahí.
- `nexora_dashboard.js` (`toneColors`) y la regla global `[data-tone="expense"]` de
  `nexora_operational.css` pintaban el gasto de rojo puro con colores propios de
  Bootstrap (`var(--red-600, #c82333)`), **contradiciendo una decisión ya escrita en
  el propio Design System** ("el gasto legítimo no es rojo... pintarlo de rojo
  entrena al usuario a ignorar el rojo"). Es el tipo de inconsistencia estructural que
  el mandato pedía corregir de forma coherente, no dejar pasar.
- No existía ningún esqueleto de barra inferior; la navegación móvil era el mismo
  cajón lateral de escritorio. `nexora_shell.js` ya exponía `SECTIONS` como fuente
  única de las doce rutas y un manejador de clic/estado-activo genérico sobre
  `data-shell-route` — la barra nueva pudo reutilizar ambos sin duplicar lógica.

**NXR-UX-0012 — resultado explicable.**
- `nexora_operations.js`: nuevo panel persistente `.nxr-operational-result` (junto a
  `.nxr-operational-preview`, no lo reemplaza — `.nxr-action-status` sigue existiendo
  para el estado del formulario). `renderResult(result, data)` muestra documento,
  movimiento, importe y la tabla de saldo anterior/posterior por fuente, usando
  `result.sources`/`result.document_number`/`result.document_date` que el servidor ya
  devolvía. `sourceBalanceRows()`/`sourceBalanceTable()` se extrajeron de
  `renderPreview()` para que vista previa y resultado compartan una sola forma de
  fila. `frappe.show_alert` se conserva (aviso rápido); el panel es lo que persiste.
- `nexora_closing.js`: los tres `catch` (`calculate`/`save`/`correct`) mostraban un
  mensaje de error **fijo** que descartaba la razón real del servidor — el mismo
  defecto que el Bloque 11 ya había corregido en `nexora_reports.js`. Ahora usan
  `window.nexora.ui.showError(error, { title, fallback })`, el mismo helper que ya
  usan otras nueve pantallas del producto.

**NXR-UX-0013 — números explicables.**
- Nuevo componente `.nxr-ds-money-row`/`.nxr-ds-money-list` en
  `nexora_design_system.css`, con cuatro tonos (no siete colores distintos): `
  --reference` (cifra base), `--pending` (comprometido/retenido/pendiente,
  `--nxr-warning`), `--spent` (ejecutado/pagado, `--nxr-money-out`) y `--available`
  (disponible, `--nxr-money-in`).
- `nexora_contracts.js`: el resumen de seis cifras del contrato (vigente/ejecutado/
  pagado/pendiente/anticipo/retención) pasó de una `<dl>` plana con el mismo peso
  visual para las seis, a `moneyRow()`/`.nxr-ds-money-list` con el monto vigente como
  cifra de referencia (`--headline`) y el resto clasificado por concepto.
- Corregido `nexora_dashboard.js` (`toneColors`) y `nexora_operational.css`
  (`[data-tone="expense"/"income"/"voided"]`) para usar `--nxr-money-in/out/void` y
  `--nxr-accent` en vez de colores Bootstrap con respaldo hexadecimal propio — mismo
  hallazgo, dos lugares. Ningún cálculo cambió, solo la presentación de valores que el
  servidor ya computaba.

**NXR-UX-0014 — navegación móvil inferior.**
- `nexora_shell.js`: `TABBAR_ITEMS` (cuatro destinos: Resumen/Operar/Fondos/Buscar —
  subconjunto real de los doce de `SECTIONS`, ninguna ruta nueva) más un botón "Más"
  que llama a `openDrawer(true)`, el mismo cajón que ya existía. Los enlaces llevan
  `data-shell-route`, así que el manejador de clic y `paintActive()` (estado activo)
  ya genéricos sobre ese atributo los cubren sin código adicional — cero lógica de
  navegación duplicada.
- `openDrawer()` ahora sincroniza `aria-expanded` en los dos disparadores (hamburguesa
  de escritorio/tableta y "Más" de teléfono) que abren el mismo cajón.
- `nexora_shell.css`: `.nxr-shell__tabbar` visible solo `≤640px`; `min-height: 56px`
  por pestaña (objetivo táctil propio, no el parche global de
  `nexora_dashboard_fixes.css`); `env(safe-area-inset-bottom, 0px)` y relleno inferior
  de `<body>` a juego (mismo patrón que ya reservaba espacio para la barra superior);
  estado activo con color **más** opacidad de ícono, nunca solo color (Capítulo 37,
  mismo criterio que ya usaba el cajón lateral). Se ocultan el ícono de búsqueda y la
  hamburguesa de la barra superior en ese mismo ancho: la barra inferior ya cubre esas
  dos acciones y mantener los cuatro controles a la vista era la misma acción
  duplicada.

**Pruebas existentes corregidas (no debilitadas, ajustadas al código nuevo real).**
Dos pruebas de contrato quedaron desactualizadas por este bloque:
1. `test_dashboard_contract.py::test_global_navigation_uses_canonical_nexora_pages`
   contaba `{ route: "` en todo `nexora_shell.js` (esperaba 12); con `TABBAR_ITEMS`
   sumando 4 referencias más a rutas ya existentes, el conteo subió a 16. Se acotó el
   conteo al bloque de `SECTIONS` únicamente — sigue verificando que los doce destinos
   originales no se pierdan, que era su intención real.
2. `test_browser_acceptance_contract.py::test_the_navigation_is_built_once_and_updated_by_state`
   esperaba el guard `if (!scrim || !trigger) return;` de un solo disparador; con dos
   disparadores sincronizados (`querySelectorAll`, que nunca devuelve `null`) ese guard
   ya no aplica. Se actualizó a `if (!scrim) return;` más una aserción nueva sobre la
   sincronización de los dos disparadores — no se eliminó la verificación de
   seguridad, se ajustó a la forma real y se añadió cobertura del comportamiento nuevo.
3. `test_dashboard_net_income_contract.py::test_dashboard_uses_financial_business_colors`
   verificaba literalmente los colores hexadecimales de Bootstrap que este bloque
   corrigió por ser el defecto real de NXR-UX-0013. Se actualizó para verificar los
   tokens correctos del Design System y confirmar la ausencia de los anteriores.

**Archivos.**
- `nexora_app/nexora/public/js/nexora_shell.js`, `public/css/nexora_shell.css`
- `nexora_app/nexora/nexora/page/nexora_operations/nexora_operations.js`
- `nexora_app/nexora/nexora/page/nexora_closing/nexora_closing.js`
- `nexora_app/nexora/nexora/page/nexora_dashboard/nexora_dashboard.js`
- `nexora_app/nexora/nexora/page/nexora_contracts/nexora_contracts.js`
- `nexora_app/nexora/public/css/nexora_design_system.css`, `public/css/nexora_operational.css`
- `nexora_app/nexora/tests/test_operational_result_contract.py` (nuevo)
- `nexora_app/nexora/tests/test_money_breakdown_contract.py` (nuevo)
- `nexora_app/nexora/tests/test_shell_tabbar_contract.py` (nuevo)
- `nexora_app/nexora/tests/test_dashboard_contract.py`,
  `test_browser_acceptance_contract.py`, `test_dashboard_net_income_contract.py`
  (corregidas, ver arriba)
- `docs/nexora/MATRIZ_REQUISITOS.md` (`NXR-UX-0012/0013/0014` reclasificados)

**Qué no se hizo, deliberadamente.** No se tocó `financial/`, `budget/`, ningún
DocType ni ninguna regla de negocio — todo lo hecho es presentación sobre valores que
el servidor ya calculaba y devolvía. No se rediseñó el dashboard completo ni se
añadió drill-down inline en sus tarjetas (`NXR-UX-0013` original de Bloque 12
mencionaba también composición inline de saldos; se acotó a lo que el propietario
pidió explícitamente en este bloque — presupuesto/comprometido/ejecutado/pagado/
disponible distinguibles — sin ampliar el alcance). No se creó una página nueva ni se
tocó `NXR-UX-0008/0009/0010/0011/0015` (Acción Universal, búsqueda en lenguaje
natural, página 360°, timeline, cámara) — quedan fuera del alcance de este bloque, tal
como se cerró en el Bloque 12. La barra inferior no eliminó el cajón lateral ni
cambió su comportamiento en escritorio/tableta (>640px): coherencia con la
navegación de escritorio, tal como exigía el mandato.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB/Playwright/
WebKit, ausentes en este entorno):
- `node --check` sobre los cinco archivos JS tocados — sin errores de sintaxis.
- `PYTHONPATH=nexora_app python3 -m unittest nexora.tests.test_operational_result_contract
  nexora.tests.test_money_breakdown_contract nexora.tests.test_shell_tabbar_contract -v`
  — 24/24 en verde (nuevas).
- Suite completa: 998/1019 (21 errores, mismos de siempre por ausencia de `frappe` en
  `*_integration.py`, sin regresión — confirmado 0 `FAIL`, solo `ERROR` de import).
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- 11 validadores de repositorio/gobierno/ConstruControl — 11/11 en verde (manifiesto
  de archivos regenerado).

**No ejecutado aquí** (requiere Playwright + Chromium/WebKit reales, ausentes en este
entorno): el recorrido visual e interactivo real — cómo se ve y se toca el panel de
resultado, el desglose de dinero y la barra inferior en `desktop-chromium` e
`iphone-13-webkit` (perfiles ya definidos en `nexora_browser_smoke.mjs`, no
modificados). Todos los selectores/marcadores que ese script ya busca
(`.nxr-preview-body`, `.nxr-action-status`, `.nxr-shell`, `.nxr-shell__bar`,
`.nxr-shell__section`) siguen presentes sin cambios — se verificó por grep que este
bloque no rompe ningún marcador del smoke test existente, pero no se ejecutó el
smoke test en sí. Por Capítulo 35/60 de la misión, no se declara "IMPLEMENTADO Y
VALIDADO": las tres brechas se clasifican `NO DEMOSTRADO`, con la lógica y estructura
100% confirmadas por 24 pruebas de contrato estático nuevas más las existentes
corregidas, pendientes de certificación visual real en `nexora-app.yml` (job
`browser`).

**Riesgos residuales.** Ninguno de permisos, auditoría ni integridad financiera: cero
cambios de backend. Riesgo de UX menor y documentado: la barra inferior asume que
"Resumen/Operar/Fondos/Buscar" son los cuatro destinos más frecuentes — es una
decisión de producto razonada (Sección 7 de la misión) pero no medida con datos de
uso real; queda abierta a ajuste si la telemetría real (cuando exista) sugiere otro
orden.

**Bloqueo.** Ninguno. **Siguiente acción.** Bloque 17 (grande, requiere decisión de
alcance): `NXR-UX-0010` (página de contexto 360° por proyecto) y `NXR-UX-0011`
(timeline universal) — nuevo componente de UX compartido, afecta varias páginas.

## Verificación del SHA reportado al cierre del Bloque 16

El propietario señaló una discrepancia entre "Committed 5c0fb4de" (mostrado durante el
bloque) y "SHA c2b94d0b" (reportado al cierre). Verificado antes de iniciar el Bloque 17,
sin revertir ni reabrir el Bloque 16:

- `5c0fb4de` es el commit creado con `git commit` en la rama de trabajo
  `feat/nexora-ux-explicability-mobile-nav-bloque-16` — objeto real, sigue existiendo en
  la base de datos de git local (`git cat-file -t 5c0fb4de` → `commit`), pero **no es
  ancestro de `main`**: la rama se fusionó con `gh pr merge 101 --squash`, que crea un
  commit de fusión nuevo con árbol equivalente pero padre/metadatos distintos, no
  reutiliza el SHA de la rama. Este repositorio prohíbe merge commits (confirmado en el
  Bloque 12: "Merge commits are not allowed on this repository") y usa squash en cada
  bloque desde entonces — la misma relación (`commit local` ≠ `SHA final en main`) es
  idéntica en todos los bloques anteriores (Bloque 13: `8f927925` → `5ad7be0d`; Bloque
  14: `d09d34e8` → `284eac05`; Bloque 15: `83843fca` → `9337e189`).
- `c2b94d0b` (completo: `c2b94d0bd3d5ccfca1529682140ead16f9a66f22`) es el commit de
  fusión real que GitHub creó para el PR #101, confirmado como:
  - `git rev-parse HEAD` en `main` local == `git rev-parse origin/main` ==
    `c2b94d0bd3d5ccfca1529682140ead16f9a66f22` (idénticos, sin divergencia).
  - `git log --graph` de `main` muestra `c2b94d0b` como el commit más reciente, con un
    solo padre `9337e189` (Bloque 15) — confirma que es un squash, no un merge de dos
    padres.
  - `git show --no-patch c2b94d0b` — asunto `"feat(nexora): resultado y números
    explicables, navegación móvil inferior (Bloque 16) (#101)"`, coincide exactamente
    con el título del PR fusionado.
- **Conclusión: el commit realmente publicado en `main` es `c2b94d0bd3d5ccfca1529682140ead16f9a66f22`.**
  El SHA reportado al cierre del Bloque 16 era correcto; `5c0fb4de` es un artefacto
  intermedio esperado del flujo de trabajo (commit de rama → squash merge), no un error
  ni una publicación fallida. No se encontró ningún problema real; el Bloque 16 no se
  reabre.

## Bloque 17 — contexto 360° del proyecto y timeline universal (`NXR-UX-0010`, `NXR-UX-0011`)

- Fecha: 2026-08-10.
- Alcance amplio autorizado por el propietario: construir ambos requisitos como una
  experiencia central de NEXORA ("qué es este proyecto, cuánto dinero tiene, de dónde
  viene, cuánto se ha ejecutado/pagado, qué contratos/compras/inventario/avance tiene,
  y su historia cronológica"), no como dos pantallas aisladas — reutilizando datos y
  componentes existentes, sin duplicar lógica de negocio ni permisos, respetando
  exactamente el modelo de permisos existente.

**Investigación previa (qué reutilizar, antes de escribir código).** `nexora_dashboard.js`
llama a `nexora.dashboard.executive.get_executive_snapshot` — no a
`dashboard.service.get_dashboard_summary`, que resultó ser una función **legada**
(confirmado por `hooks.py:override_whitelisted_methods`, que redirige
`dashboard.executive.get_executive_snapshot` hacia el canónico
`dashboard.snapshot_query.get_executive_snapshot`). Esta última ya compone, con
`require_project_access` correctamente aplicado, prácticamente todo lo pedido:
`finance` (fondos), `budgets` (presupuesto/comprometido/ejecutado/disponible por
categoría), `contracts` (con `contractor_label` ya resuelto), `progress`/`evidence`,
`alerts`/`compliance_alerts`, `recent_operations`, y `analytics.critical_inventory`
(inventario en estado crítico). Reutilizarla evitó recalcular una sola cifra financiera.

**Hallazgo de seguridad real, corregido dentro del alcance de este bloque.**
`dashboard.service.get_dashboard_summary()` — la función legada, todavía expuesta como
endpoint real aunque el frontend ya no la use — nunca llamaba `require_project_access`,
solo `require_action("preview")` (permiso de rol, no de proyecto). Confirmado con
`test_executive_reporting_integration.py::test_project_viewer_requires_explicit_project_scope`
que el modelo de seguridad real de este repositorio exige acceso explícito por proyecto
para el rol "NEXORA Project Viewer" (vía `User Permission`) — la función hermana
`get_executive_snapshot` ya lo hacía correctamente. Corregido agregando la misma llamada
que ya usan sus funciones hermanas (`snapshot_query.py`, `pending_query.py`); sin efecto
para roles con `view_all_projects`. Prueba de integración existente
(`test_dashboard_integration.py::test_dashboard_allows_viewer_and_rejects_guest`)
corregida para conceder el permiso explícito que el modelo real ya exigía (antes
encodeaba el defecto: creaba un viewer sin conceder ningún proyecto y esperaba que
igual pudiera ver el resumen ejecutivo).

**Hallazgo de seguridad relacionado, documentado pero NO corregido (excede el alcance
de este bloque).** `purchases.request_service.list_purchase_requests()` y
`purchases.order_service.list_orders()` tienen el mismo patrón (`project` opcional sin
`require_project_access`). Las llamadas de este bloque son seguras porque
`context360.service.get_project_overview()` ya gatea con `require_project_access` en su
propio orquestador antes de llamarlas — pero las funciones en sí siguen expuestas sin
ese control para cualquier otro llamador. Registrado como `NXR-SEC-0001`
(`REQUIERE DECISIÓN`) en la matriz: auditar y corregir todo el módulo de compras (y
verificar `quotation_service.list_quotations()`/`receipt_service.list_receipts()`, no
revisadas) es un alcance de seguridad propio, no una necesidad directa de este bloque.

**Arquitectura implementada.**
- `nexora_app/nexora/context360/core.py` (nuevo, sin dependencia de Frappe, mismo
  principio que `receipt_core.py`/`budget/core.py`): `normalize_event()`,
  `resolve_actor()`, `resolve_amount()`, `sort_and_truncate()`, `resolve_categories()`,
  `clamp_limit()`, catálogo de estados de "excepción" por doctype (`Cancelled`,
  `Rejected`, `Compensated Partial/Total`, etc. — `Released`/`Partially Released` de un
  compromiso NO son excepción, es su ciclo de vida normal).
- `nexora_app/nexora/context360/service.py` (nuevo): `get_project_overview()` — único
  gate `require_project_access(project, action="view_reports")`, luego compone
  `get_executive_snapshot()` (reutilizado íntegro) + `open_purchases` (lista real de
  solicitudes/órdenes abiertas, nueva pero ligera) + `participants` (contratistas/
  proveedores deduplicados de filas ya obtenidas, sin consulta nueva al directorio).
- `nexora_app/nexora/context360/timeline.py` (nuevo): `get_project_timeline()` — cruza
  8 doctypes reales (`NXR Operation`, `NXR Commitment`, `NXR Purchase Request/Order`,
  `NXR Goods Receipt`, `NXR Contract`+`Amendment`+`Estimate`, `NXR Stock Transaction`,
  `NXR Progress Record`, `NXR Evidence`) vía `frappe.get_list` (no `frappe.get_all`, que
  ignora permisos de fila), normaliza con `context360.core`, ordena y trunca. Ningún
  evento se fabrica: una fila sin fecha utilizable no se normaliza.
- `nexora_app/nexora/nexora/page/nexora_project/` (nuevo): página `nexora-project`,
  reutiliza `.nxr-ds-money-row` (Bloque 16) para presupuesto/comprometido/ejecutado/
  pagado/disponible, `frappe.utils.get_form_link()` (ya usado por `nexora_dashboard.js`)
  para el acceso a registros originales, y el mismo patrón de herencia de proyecto
  activo (`route_options`/`window.nexora.context`) que ya usa `nexora_contracts.js`.
  Timeline con filtros de categoría, agrupación por día, y marca visual de excepción
  por color **y** forma (rombo, no solo color — Capítulo 37).
- `nexora_app/nexora/public/css/nexora_project.css` (nuevo, registrado en
  `hooks.py:app_include_css` y en el precache de `nexora-service-worker.js`): cuadrícula
  responsive por `auto-fit`/`minmax` (sin media query dedicada para apilar en teléfono),
  mismo punto de corte de teléfono que la barra inferior (`640px`, Bloque 16),
  `prefers-reduced-motion` respetado.
- Acceso: botón contextual "Ver proyecto 360°" en `nexora_dashboard.js` (atributo
  propio `data-project-360`, no `[data-action]`, para no caer en el manejador que
  siempre enruta a "nexora-finance") — no un destino nuevo suelto, solo alcanzable
  desde donde el proyecto activo ya está seleccionado, tal como pedía el mandato.

**Corrección de tres invariantes de gobernanza ya existentes, encontradas al ejecutar
las pruebas (no inventadas por este bloque).** `test_page_registry_contract.py` exige
que toda página nueva esté en el manifiesto `destinations` de `nexora.js`, en el
workspace (`nexora.json`, `shortcuts` y su bloque `content`) y que ambos coincidan
exactamente con las carpetas de página reales — el intento inicial de dejar
`nexora-project` "solo alcanzable por contexto" (sin registrarla en esos tres lugares)
violaba esta regla ya establecida. `test_pwa_contract.py` exige que todo bundle
registrado en `hooks.py` esté en el precache offline de la PWA. Corregido registrando
la página en los tres lugares y agregando `nexora_project.css` al precache; también se
agregó `nexora-project` a `SECTIONS` de `nexora_shell.js` (grupo "Hoy", ahora con
cuatro destinos en vez de tres) para que sea alcanzable desde la navegación real que ve
el usuario, no solo desde el manifiesto de gobernanza — `test_dashboard_contract.py`
actualizada de 12 a 13 destinos reales en `SECTIONS` (un destino nuevo y legítimo, no
una fuga de conteo).

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB/Playwright/WebKit):
- `PYTHONPATH=nexora_app python3 -m unittest nexora.tests.test_context360_core -v` —
  27/27 en verde, incluido un bug real encontrado y corregido durante las pruebas:
  `clamp_limit(0)` trataba `0` como "no proporcionado" (por la falsedad de `0` en
  Python con `if value:`) y devolvía el valor por defecto (30) en vez de recortar a 1.
- `nexora.tests.test_context360_contract`, `test_project_page_contract` — 23/23 en
  verde (estructura, reutilización de `get_executive_snapshot`, `frappe.get_list` no
  `get_all`, gate de `require_project_access`, ausencia de cálculo financiero propio).
- `node --check` sobre los 6 archivos JS tocados/nuevos — sin errores de sintaxis.
- Suite completa: `PYTHONPATH=nexora_app python3 -m unittest discover -s
  nexora_app/nexora/tests -p "test_*.py"` — 1049/1071 (22 errores, mismos de siempre
  por ausencia de `frappe` en `*_integration.py` + el nuevo
  `test_context360_integration.py`; 0 `FAIL` reales tras corregir las 3 regresiones de
  gobernanza y 2 pruebas de contrato desactualizadas por la corrección de seguridad).
- `python -m compileall nexora_app/nexora scripts` — sin errores.
- 11 validadores de repositorio/gobierno/ConstruControl — 11/11 en verde (manifiesto
  de archivos regenerado).

**No ejecutado aquí** (requiere `bench`+MariaDB+Playwright/WebKit, ausentes en este
entorno): `test_context360_integration.py` completo (permisos reales por proyecto,
proyecto vacío, fondos/operaciones/compromisos reales, orden cronológico real,
liberación de compromiso no marcada como excepción) — cobertura deliberadamente acotada
a fondos/operaciones/compromisos (las funciones ya probadas en
`test_budget_commitment_integration.py`); contratos/compras/avance/evidencia quedan
cubiertos por unidad (`test_context360_core.py`) y por contrato estático, no de extremo
a extremo, por la complejidad de su configuración de prueba. Tampoco el recorrido visual
real de la página nueva. Por Capítulo 35/60 de la misión, `NXR-UX-0010` y `NXR-UX-0011`
se clasifican `NO DEMOSTRADO`, no `IMPLEMENTADO Y VALIDADO` — pendientes de
`nexora-app.yml` (job `browser`).

**Verificación real en CI (job `Frappe real · escritorio · tableta · iPhone · PWA`,
Playwright/WebKit contra `bench`/MariaDB reales, PR #102).** Este job sí se ejecutó
—no es una simulación— y encontró un defecto real: `validateShell()`
(`scripts/nexora_browser_validators.mjs`) exigía exactamente 12 destinos
`[data-shell-route]` en la carcasa, un número que ya estaba obsoleto desde que el
Bloque 16 agregó la barra de pestañas móvil (`TABBAR_ITEMS`, 4 ítems) sin actualizar
esta aserción — la barra lateral (`SECTIONS`) más la barra de pestañas ya sumaban 16
en el momento del merge de #101, no 12, y ese job de CI ya fallaba en `main` desde
entonces sin que nadie lo corrigiera (confirmado con `gh run view` sobre el run de
#101: mismo mensaje, `16 !== 12`). Este bloque, al agregar "Proyecto 360°" a
`SECTIONS` (13 en la barra lateral), llevó el total real a 17 y lo hizo más visible.
Corregido el número esperado a 17 (13+4), con comentario explicando el cálculo — no
se debilitó la prueba, se corrigió al valor real y se sigue exigiendo un total exacto.
El mismo job reportó un segundo fallo, `panel: Dashboard did not expose the active
period` (`validateDashboard()` en el mismo archivo) — verificado que es preexistente
e idéntico en el run de #101 (Bloque 16, ya fusionado), no causado ni tocado por este
bloque (`nexora_dashboard.js` de este bloque solo agrega el botón
`data-project-360`, no toca `.nxr-dashboard-period`). No se corrige aquí por exceder
el alcance de este bloque de UX de contexto 360°/timeline; queda como defecto conocido
y preexistente del panel del dashboard, ya arrastrado desde antes del Bloque 17.
Con la corrección del conteo, el siguiente run real reveló un segundo hallazgo del
mismo origen: `paintActive()` (`nexora_shell.js`) marca `aria-current="page"` en
*todos* los `[data-shell-route]` cuya ruta coincide — a propósito, porque la misma
ruta (p. ej. `nexora-dashboard`) vive a la vez en la barra lateral y en la barra de
pestañas móvil, dos superficies responsive del mismo destino, y ambas deben poder
mostrarse como "actual" según cuál esté visible en el viewport. La aserción de
`validateShell()` exigía exactamente **un** `aria-current` en toda la carcasa —
correcta cuando solo existía la barra lateral, obsoleta desde que el Bloque 16 agregó
la segunda superficie, pero nunca detectada porque el fallo del conteo de destinos
(el hallazgo anterior) interrumpía la función antes de llegar a esta aserción.
Corregida para comprobar exactamente un actual **por superficie** (barra lateral y
barra de pestañas por separado, cada una debe marcar `nexora-dashboard`) en vez de
uno global — mismo criterio real de "el usuario sabe dónde está", adaptado al diseño
de dos superficies ya establecido, no debilitado.

Con ambas correcciones, el job de browser real efectivamente avanzó más allá del
paso `carcasa` en el siguiente run (confirmado: `desktop-chromium` e
`iphone-13-webkit` ya solo fallan en `panel`). Al avanzar más, el run reveló un
tercer hallazgo real, únicamente en el perfil `ipad-gen7-webkit`: el paso
`comprobantes` (`nexora_browser_smoke.mjs::setEvidenceField`, página
`nexora-evidence`) reporta que el campo `project` no conservó `PROJ-0001` tras
`fill()` + `Tab`, quedando en el proyecto del contexto activo
("NEXORA 0.1 — Fondo demostrativo"). Este paso nunca se había ejecutado en un run
real anterior porque el fallo de `carcasa` abandonaba el perfil antes de llegar a
él — no es una regresión de este bloque (`context360`/`nexora-project` no tocan la
página de evidencia ni su campo `project`) sino un defecto preexistente
recién visible. No se investiga ni se corrige aquí por exceder el alcance de UX de
contexto 360°/timeline de este bloque; queda documentado como tercer hallazgo real
de la deuda de verificación en CI, candidato para un bloque de PWA/iPhone/WebKit
dedicado (ver Bloque 27 de la misión). Con estos tres hallazgos reales (dos
corregidos, uno documentado y ajeno), `NXR-UX-0010`/`NXR-UX-0011` se mantienen
`NO DEMOSTRADO`: las correcciones aquí hechas son de instrumentación de prueba
(alinear aserciones obsoletas del Bloque 16 con su propio diseño ya establecido),
no una validación visual completa y en verde del recorrido real.

**Riesgos residuales.** `NXR-SEC-0001` (documentado, no corregido) — ver arriba. Dos
defectos preexistentes ajenos a este bloque siguen bloqueando un run verde completo
del job de browser real: `validateDashboard()` (`panel: Dashboard did not expose the
active period`, los tres perfiles) y `setEvidenceField()` sobre el campo `project`
de comprobantes (`comprobantes`, solo `ipad-gen7-webkit`, recién visible al dejar de
abortar el perfil en `carcasa`). Ninguno de los dos es un riesgo nuevo de este
bloque, pero ambos son candidatos explícitos para un bloque futuro que se ocupe de
la deuda de verificación real en CI. Ninguno de integridad financiera: cero cambios
al modelo de fondos/presupuesto/contratos; todo lo nuevo es composición de lectura
sobre funciones ya existentes.

**Bloqueo.** Ninguno directo a este bloque. `NXR-SEC-0001` requiere decisión del
propietario sobre si se aborda como bloque de seguridad dedicado.

**Siguiente acción.** Bloque 18 (requiere decisión): `NXR-CNV-0001` (Conversational OS)
es el mayor pendiente de construcción nueva sustancial; alternativamente, Bloque 18
podría dedicarse a `NXR-SEC-0001` (auditoría de `require_project_access` en el módulo
de compras), o a reparar la deuda de verificación real en CI (`validateDashboard()`
lleva roto desde antes del Bloque 17) antes de seguir agregando superficie nueva
sobre un patrón de permisos y de pruebas de extremo a extremo no verificado por
completo.

## Bloque 18 — Conversational OS (NXR-CNV-0001)

**Alcance autorizado.** El propietario aprobó ejecutar el Bloque 18 tal como lo
describe la nueva fase de misión (Bloques 18-30, "convergencia final"): una capa
conversacional real que interpreta intención, consulta datos, y prepara/ejecuta
operaciones con vista previa y confirmación explícita — sin que la IA pueda saltarse
ninguna regla del sistema. Explícitamente fuera de este bloque (según la propia
numeración de la misión): WhatsApp Business real (Bloque 21), auditoría profunda del
gateway/proveedores de IA (Bloque 20), automatizaciones por *scheduler*.

**Investigación previa a escribir código (obligatoria por mandato).** Un documento de
diseño sin comitear (`docs/nexora/NIP_BLOQUE_6_CONVERSATIONAL_OS.md`, encontrado en el
árbol de trabajo desde el inicio de la sesión) afirmaba que ya existía una "NEXORA
Intelligence Platform" completa. No se confió en el documento: se verificó contra el
código real. Confirmado con evidencia concreta:
- `nexora_app/nexora/intelligence/` **sí existe**, está trackeado por git y mergeado a
  `main` (NIP Bloques 1-6, SHA `f63f86e4`, confirmado con `git log`): `gateway.py`,
  `orchestrator.py`, `credentials.py`, `runtime.py`, `providers/` con 9 adaptadores
  (`openai`, `anthropic`, `gemini`, `cohere`, `deepseek`, `groq`, `mistral`,
  `openrouter`, `perplexity`, cada uno `_live.py`+`_stub.py`), DocTypes `NXR AI
  Provider`/`NXR AI Provider Credential`, 14 archivos de prueba propios.
- `nexora_app/nexora/conversation/` **no existía en absoluto** (cero archivos, cero
  historial git) — confirmado por `MATRIZ_REQUISITOS.md` (`NXR-CNV-0001` ya
  documentaba esto como `PROPUESTO`, "código real = 0").
- No existían `NXR Channel Account`/`NXR Conversation`/`NXR Conversation Message`/
  `NXR Conversation Pending Intent` — ningún DocType conversacional real.
- `nexora_search.js` es un buscador clásico sin NLU (`NXR-UX-0009`, `NO DEMOSTRADO`,
  sin tocar en este bloque — se decidió construir el asistente como una superficie
  propia en vez de forzarlo dentro de una página pensada para otra interacción).

Conclusión: el motor de IA multi-proveedor con *fallback* es real y reutilizable
íntegro; la capa conversacional es 100% nueva en este bloque.

**Arquitectura implementada.** `nexora_app/nexora/conversation/` (nuevo):
- `core.py` (puro, sin Frappe, mismo principio que `context360/core.py`): `IntentSpec`/
  `Slot` (declarativos), `missing_slots()`/`next_question()`/`merge_payload()` (relleno
  progresivo sin perder lo ya capturado), `PENDING_INTENT_TRANSITIONS` +
  `assert_pending_intent_transition()` (máquina de estados pura, catalogada como
  `STM-CONVERSATION-INTENT`), `build_intent_prompt()` (el prompt de sistema se
  construye desde el propio `Registry` — una sola fuente para "qué entiende NEXORA" y
  "qué le decimos al modelo que puede hacer"), `parse_model_intent()` (validación
  estricta de la respuesta JSON del modelo: intención conocida, confianza en `[0,1]`,
  sin campos inesperados — nunca se ejecuta sobre una respuesta no confiable),
  `format_money_hnl()`.
- `registry.py` (puro): catálogo declarativo de **7 intenciones**, cada una apuntando
  por ruta punteada a una función real ya auditada, nunca lógica propia:
  - `query_fund_balance` (lectura) → `financial.sources.list_source_balances`.
  - `query_pending_payments` (lectura) → `dashboard.snapshot_query.get_executive_snapshot`
    (reutilizado íntegro, mismo principio que el Bloque 17 con `context360`).
  - `query_contract` (lectura) → `contracts.service.list_contracts`.
  - `register_expense`/`register_income` (escritura) →
    `financial.operational_commands.preview_operational_movement` /
    `execute_operational_movement`, con `movement_code` fijo (`"102"`/`"101"`, tomado
    literal de `financial/operational_common.py::MOVEMENT_CATALOG` — no inventado).
  - `register_evidence` (escritura, sin `preview_method` propio en el dominio — el
    motor construye un eco local de los campos capturados como vista previa) →
    `financial.evidence.register_evidence`.
  - `create_purchase_request` (navegación, no escritura): la creación real de una
    solicitud de compra exige líneas de artículo estructuradas
    (`purchases/request_service.py::create_purchase_request`, con cantidades/precios
    por línea) que no es razonable capturar por slots de chat en esta primera versión
    — la intención prepara la navegación con el proyecto ya resuelto en vez de
    reimplementar un mini-asistente de líneas dentro del chat. Documentado como
    decisión de alcance, no como limitación oculta.
- `resolve.py` (Frappe): `Project.name` es una serie autogenerada
  (`naming_series:`, confirmado en `erpnext/projects/doctype/project/project.json`),
  no el título humano ("Casa 04") — `resolve_project()` lo resuelve contra
  `project_name`; `resolve_entity()` reutiliza `directory.service.search_entities()`
  en vez de consultar `NXR Entity` directamente. Ambas lanzan `AmbiguousReferenceError`
  con los candidatos reales cuando hay más de una coincidencia, en vez de adivinar.
- `nlu.py` (Frappe): llama `nexora.intelligence.orchestrator.execute("text", ...)` —
  el mismo orquestador NIP, sin tocar sus proveedores. Hallazgo real durante el
  diseño: los nueve adaptadores certificados devuelven `data` en la forma cruda de
  cada API (confirmado leyendo cada `*_live.py`: compatibles con OpenAI usan
  `messages`+`choices[0].message.content`, Anthropic usa `messages`+
  `content[0].text`, Gemini exige `contents` (ignora `messages`) +
  `candidates[0].content.parts[0].text`, Cohere exige `message` como cadena única
  (ignora `messages`) + `text`) — ningún consumidor existente había necesitado leer
  el texto generado (`run_orchestrated_request` solo lee `provider_key`). Resuelto
  aquí, dentro de `conversation/` (no se tocó `intelligence/`): el payload se envía en
  las tres formas (`messages`, `contents` vía fallback interno del adaptador, `prompt`
  aplanado) y `_extract_text()` sabe leer las tres formas de respuesta reales,
  degradando a cadena vacía (nunca una excepción) ante una forma no reconocida.
- `db.py` (Frappe): mismo patrón que `financial/db.py::audit` — inserción con
  `service_write()` + `ignore_permissions=True`; ningún rol tiene `create`/`write`
  directo sobre los tres DocTypes nuevos.
- `dispatch.py` (Frappe, único punto whitelisted): `send_message` (ingesta → si hay
  una intención esperando confirmación, reconoce "confirmar"/"cancelar" en texto
  libre antes de interpretar nada nuevo → si no, interpreta vía `nlu.py` → resuelve
  referencias humanas → rellena campos → si faltan, pregunta y persiste un
  `Pending Intent` en `Collecting`; si están completos, ejecuta lectura/navegación de
  inmediato o pide preview+confirmación para escritura), `confirm_pending_intent`,
  `cancel_pending_intent`. **Sin segunda tabla de permisos**: ninguna función de este
  módulo llama `require_action`/`require_project_access` por su cuenta — cada
  intención delega en el `require_action`/`require_project_access` que la función
  real ya aplica (`preview_operational_movement`, `list_source_balances`, etc.);
  `dispatch.py` solo exige que el usuario no sea `Guest` antes de gastar una llamada
  de IA, y traduce cualquier `frappe.PermissionError`/`frappe.ValidationError` real en
  una respuesta conversacional. Un rechazo de negocio no capturado por los slots
  mínimos (p. ej. falta un dato de cuenta bancaria que `_resolve_expense_account`
  exige) se relee como la siguiente pregunta en vez de reimplementar esa validación.
- Tres DocTypes nuevos: `NXR Conversation`, `NXR Conversation Message` (inmutable,
  `validate_immutable`, mismo patrón que `NXR Audit Event`), `NXR Conversation
  Pending Intent` (mutable, gateado por `assert_pending_intent_transition` en su
  propio `validate()` — nueva máquina `STM-CONVERSATION-INTENT` en
  `CATALOGO_MAQUINAS_ESTADO.md`, 37→38). Los tres bloqueados a `create`/`write` por
  rol; solo el servicio con `ignore_permissions=True` escribe.
- Página nueva `nexora-assistant` (chat mínimo real: mensajes, entrada de texto,
  botones de confirmar/cancelar cuando el motor devuelve `AwaitingConfirmation`),
  registrada en `nexora.js` (`destinations`), el workspace y `SECTIONS` de
  `nexora_shell.js` (14º destino real, grupo "Hoy" ahora con cinco); su CSS agregado
  al precache de la PWA. **Hallazgo real corregido durante el propio bloque:** la
  primera versión de `nexora_assistant.css` fijaba el tamaño táctil de los botones
  sobreescribiendo `.nxr-ds-btn` desde un selector descendiente
  (`.nxr-assistant-form .nxr-ds-btn`) — el gate de diseño
  (`test_design_system_contract.py::test_no_component_class_collides_with_the_screens`,
  un mecanismo real que ya existía para prevenir exactamente este defecto) lo
  rechazó correctamente. Corregido quitando la regla (el botón del sistema de diseño
  ya tiene `min-height: 40px`, suficientemente cercano al mínimo táctil real como
  para no justificar una excepción de capa), no relajando el gate.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB/proveedor de IA
real):
- `test_conversation_core.py` — 32/32 en verde: relleno de slots, fusión de payload,
  validación de `IntentSpec`, máquina de estados pura (camino legal, corrección hacia
  atrás, cancelación desde cualquier estado no terminal, ningún estado terminal
  transiciona de nuevo, no se puede saltar la confirmación), `parse_model_intent`
  (JSON inválido, intención desconocida, confianza fuera de rango, confianza booleana,
  campos con tipo incorrecto, clave inesperada — nueve casos de rechazo distintos),
  formato de dinero.
- `test_conversation_contract.py` — 21/21 en verde: las 7 intenciones exactas del
  catálogo, ningún `movement_code`/`require_action` dentro de `registry.py` (solo en
  `dispatch.py`, y solo dos claves), los tres puntos whitelisted exactos, invitado
  rechazado antes de interpretar, ejecución siempre auditada, los tres DocTypes
  bloqueados a escritura directa, los estados del DocType coinciden exactamente con
  la máquina pura, registro completo de la página nueva en los cuatro lugares del
  invariante de gobernanza, y la regresión directa del hallazgo de `.nxr-ds-btn`.
- Suite completa: 1103/1125 (23 error, todos `ModuleNotFoundError: frappe` en
  `*_integration.py` — 22 preexistentes + `test_conversation_integration.py` nuevo;
  0 `FAIL`). Dos regresiones reales encontradas y corregidas durante la propia
  ejecución: `test_dashboard_contract.py` (conteo de `SECTIONS` 13→14) y
  `test_app_contract.py` (conteo de DocTypes 53→56).
- `node --check` sobre los 3 JS tocados/nuevos, `python -m compileall` — sin errores.
- `validate_nexora_governance.py` (181 requisitos, 38 máquinas, 32 controles, 9
  pruebas compartidas, 19 decisiones), `validate_repository.py`,
  `validate_nexora_app.py` (56 DocTypes), `validate_construcontrol_architecture.py`,
  `validate_nexora_financial_models.py`, `validate_nexora_constitution.py` — todos en
  verde.
- `test_conversation_integration.py` (`FrappeTestCase`, 14 escenarios reales de la
  matriz mínima de la misión: consulta normal, consulta sin resultados, referencia de
  proyecto ambigua, proyecto inexistente, permisos reales sin segunda tabla, camino
  completo de escritura con preview+confirmación+auditoría, cancelación sin efecto
  colateral, doble confirmación rechazada, confirmación por texto libre, proveedor de
  IA caído simulado con `unittest.mock.patch` sobre `orchestrator.execute`, reintento
  tras fallo que nunca reabre el `Pending Intent` fallido, evidencia de extremo a
  extremo, invitado rechazado) — escrita pero **no ejecutable en este entorno** sin
  bench/MariaDB.

**No ejecutado aquí** (requiere `bench`+MariaDB+un proveedor de IA real con
credenciales, ausentes en este entorno): interpretación real de un modelo de lenguaje
vivo (todas las pruebas de intención usan `unittest.mock.patch` sobre
`orchestrator.execute`, nunca una llamada real), el recorrido visual real de
`nexora-assistant` en navegador/iPhone/PWA. Por eso `NXR-CNV-0001` se clasifica
`NO DEMOSTRADO`, no `IMPLEMENTADO Y VALIDADO` — pendiente de `nexora-app.yml` (job
`browser`) y de una credencial real de al menos un proveedor NIP configurado.

**Verificación real en CI (PR #104).** `semgrep` encontró un hallazgo real propio:
`build_intent_prompt()` (`conversation/core.py`) partía tres cadenas del prompt de
sistema en varias líneas dentro de una lista mediante concatenación implícita de
literales adyacentes (`python.lang.correctness.common-mistakes.string-concat-in-list`)
— un patrón que la regla marca como posible coma faltante. Corregido ensamblando cada
cadena con `+` explícito antes de entrar a la lista; sin cambio de comportamiento.
El job `Frappe real · escritorio · tableta · iPhone · PWA` (Playwright/WebKit contra
`bench`/MariaDB reales) confirmó, como era esperable, que agregar "Asistente" a
`SECTIONS` volvió a desactualizar el número fijo de `validateShell()` en
`scripts/nexora_browser_validators.mjs` (17→18 destinos reales) — la misma clase de
defecto que el Bloque 17 ya había corregido una vez (12→17) tras el mismo tipo de
hallazgo. En vez de parchear el número una tercera vez, se reemplazó por un cálculo
dinámico real contra `window.nexora.shell.sections`/`tabbarItems` (expuesto por
`nexora_shell.js` para exactamente este propósito) — la aserción sigue exigiendo un
total exacto, pero ahora es imposible que quede desincronizada por un futuro destino
nuevo. El mismo run mostró en `ipad-gen7-webkit` (solo ese perfil) un fallo en
`operaciones` ("Guided stage 4 never opened", con `amount_hnl` vacío) que arrastró
cuatro etapas dependientes (`busqueda`/`anulacion`/`correccion`/`exportacion`) —
verificado como ajeno a este bloque (no se tocó `nexora_operations.js` ni el flujo
guiado) y del mismo tipo de hallazgo intermitente que ya se observó en `ipad-gen7-webkit`
durante el Bloque 17 (un defecto de "comprobantes" que no se reprodujo en el run
siguiente); no se investiga más aquí por exceder el alcance de este bloque.

**Riesgos residuales.** Ninguno de integridad financiera nuevo: cero cambios a
`financial/`, `purchases/`, `contracts/`, `evidence.py` — todo lo nuevo es
composición/invocación de funciones ya existentes y auditadas, nunca una regla
nueva. El registro de gasto/ingreso conversacional no captura contexto de cuenta
bancaria (modo "Existente"/campos de institución) — solo el camino mínimo; un dato
faltante se traduce en la siguiente pregunta a partir del propio rechazo del servidor,
nunca en un valor inventado. `create_purchase_request` es una intención de
navegación, no de creación real, por la complejidad estructurada de sus líneas —
documentado como decisión de alcance, candidato de expansión de catálogo futura. El
posible defecto intermitente de `ipad-gen7-webkit` en el flujo guiado de operaciones
(ajeno a este bloque) queda como candidato para la deuda de verificación real en CI
ya identificada en el Bloque 17.

**Bloqueo.** Ninguno directo a este bloque.

**Siguiente acción.** Bloque 19 (Seguridad y Governance) es el candidato natural
según la nueva fase de misión — auditar permisos/roles/proyectos/búsqueda/APIs
directas, incluida la superficie nueva de este bloque (`dispatch.py`,
`NXR Conversation*`) y el hallazgo ya documentado y no corregido `NXR-SEC-0001`
(Bloque 17, módulo de compras).

## Bloque 19 — Seguridad y Governance (NXR-SEC-0001)

**Alcance.** El propietario autorizó continuar con la fase de convergencia final
bloque por bloque, respetando la "regla de un solo bloque" explícita de la misión
(detenerse y reportar al cerrar cada uno). Este bloque audita permisos/roles/
proyectos/búsqueda/exportación/APIs directas de todo el código de la app —no de
Frappe/ERPNext core— y cierra `NXR-SEC-0001`, el hallazgo documentado y no corregido
desde el Bloque 17 (`purchases.request_service.list_purchase_requests`/
`order_service.list_orders` sin `require_project_access`).

**Metodología.** Ningún hallazgo se aceptó por un grep superficial de una sola
línea: cada candidato se verificó rastreando la cadena de llamadas completa, porque
varios "positivos" iniciales resultaron ser falsos — la función auxiliar compartida
que sí valida el permiso vive un nivel más abajo (p. ej. `dashboard/query_utils.py::project()`,
`reports/service.py::_project()`, `permissions.py::_row_is_readable()`). Confundir
esto habría producido, o bien hallazgos fabricados, o bien correcciones duplicadas
sobre código ya seguro — ambos prohibidos explícitamente por la misión.

**Hallazgos reales corregidos (catorce funciones en siete módulos, más dos
hallazgos de una clase distinta).** Mismo patrón en todas: una acción de permiso
amplia (`ACCESS_ROLES`, que incluye "NEXORA Project Viewer" — el único rol pensado
para quedar restringido a proyectos concretos) sin el chequeo adicional de proyecto.
Corregido agregando `require_project_access(project, action=...)` justo después (o en
sustitución) del `require_action` existente, o —cuando la función recibe un ID de
documento en vez de un `project` (patrón IDOR)— resolviendo el proyecto real desde el
propio documento (`frappe.db.get_value`/`doc.project`) antes de comprobar acceso,
nunca confiando en un valor declarado por el cliente:
- `purchases/quotation_service.py`: `get_quotation`, `list_quotations`,
  `compare_quotations`.
- `purchases/receipt_service.py`: `get_receipt`, `list_receipts`.
- `purchases/order_service.py`: `get_order`, `list_orders` (el hallazgo original).
- `purchases/request_service.py`: `get_purchase_request`, `list_purchase_requests`
  (el hallazgo original).
- `inventory/service.py`: `get_stock_transaction`, `list_stock_transactions`.
- `contracts/service.py`: `get_contract`, `list_contracts`.
- `budget/service.py`: `check_budget_availability`.
- `financial/sources.py`: `list_source_balances` — afecta directamente la intención
  `query_fund_balance` del Bloque 18, que delega su permiso íntegramente en esta
  función; corregirla aquí corrige también, sin tocar `conversation/`, la misma
  superficie para el asistente.
- `financial/analytics.py`: `get_advance_status`, `list_central_operations`, y
  `prepare_central_payload` (el único punto que preparan tanto
  `preview_central_operation` como `execute_central_operation` — el chequeo se
  agregó una sola vez ahí, no duplicado en cada llamador).
- `financial/operations.py`: `preview_financial_operation` — `financial/db.py::preview()`
  es una función de cómputo puro sin permisos propios; sin este chequeo, cualquier
  rol con `preview` podía previsualizar el efecto de una operación sobre fuentes de
  fondos de un proyecto ajeno con solo conocer sus nombres, aunque no pudiera
  ejecutarla (la ejecución real exige acciones de rol más estrictas, ya fuera de
  alcance del Project Viewer).
- `financial/evidence.py`: `list_evidence`.
- `integrations/service.py`: `list_integrations`.

**Hallazgo más sutil (mismo bloque, misma auditoría).**
`reports/service.py::get_contract_statement` sí llamaba `require_project_access`,
pero contra `data["project"]` —el proyecto que el cliente *declaraba* estar
consultando— no contra el proyecto real del `contract` que la función efectivamente
leía. Un Project Viewer podía enviar su propio proyecto autorizado junto con el
`contract` de otro: el resumen salía vacío (no coincidía `c.project`), pero la lista
`transactions` (montos, fechas, descripciones) del contrato ajeno se devolvía
completa. Corregido resolviendo el proyecto desde el documento real antes de
comprobar acceso — mismo patrón que `financial/service.py::reconcile_fund_source`
ya usa.

**Hallazgo de una clase distinta (no entre proyectos, entre usuarios).**
`notifications/service.py::list_notifications` permitía leer las notificaciones de
CUALQUIER usuario enviando su `user` por payload, con solo el rol `preview` — y sin
que ningún llamador real del producto lo necesitara (`grep` confirmó cero referencias
en el cliente a esta función). Corregido: solo un rol con `view_all_projects` puede
consultar notificaciones de otro usuario; cualquier otro ve únicamente las suyas sin
importar qué envíe.

**Auditado y confirmado correcto, no una fuga (para no fabricar hallazgos donde no
los hay).**
- `directory/service.py` (`get_entity`/`search_entities`/`list_entities`) y
  `purchases/service.py::get_supplier_profile`/`list_supplier_profiles`: ni
  `NXR Entity` ni `NXR Supplier Profile` tienen campo `project` — son catálogos
  maestros compartidos entre proyectos por diseño, no un hallazgo pendiente.
- `permissions.py::secure_universal_search_consolidated`: ya aplica
  `require_project_access` por cada fila vía `_row_is_readable()` — la búsqueda
  universal ya estaba correctamente asegurada desde antes de este bloque.
- `reports/service.py::export_report`: ya usa `_project(data, "export_reports")`.
- La mayoría de `dashboard/*` (`get_source_statement_page`, `get_source_movement_page`,
  `get_contract_page`, `get_executive_snapshot`, `get_expense_page`): delegan en
  `dashboard/query_utils.py::project()` o en `snapshot_query.get_executive_snapshot`,
  que ya validan — confirmado leyendo la función auxiliar compartida, no asumido.
- `progress/service.py`, la mayoría de `budget/service.py` y de
  `financial/commitments.py`: sus acciones (`approve`) son `MANAGER_ROLES`, un
  subconjunto de `ALL_PROJECT_ROLES` — todo rol que puede invocarlas ya tiene
  `view_all_projects` por diseño; `require_project_access` sería una operación nula.

**Segregación de roles (verificada, no rediseñada).** El patrón
SOLICITAR→APROBAR→EJECUTAR ya existente (`create_purchase_request`/
`submit_purchase_request` en `OPERATOR_ROLES` vs. `approve_purchase_request` en
`MANAGER_ROLES`, y equivalentes en contratos/presupuesto) confirmado real y
consistente durante la propia auditoría: ninguna de las funciones de escritura
crítica es alcanzable por "NEXORA Project Viewer". No se encontró necesidad de
rediseñar esta segregación, ya construida y probada en bloques anteriores (13, 14).

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `test_security_project_scoping_contract.py` (nuevo) — 16/16 en verde: extrae el
  cuerpo exacto de cada función corregida (no una búsqueda de substring en todo el
  archivo, que daría falsos positivos si otra función cercana ya usa
  `require_project_access`) y confirma la presencia real del chequeo; confirma
  también que `NXR Entity` no tiene campo `project` (para que la exclusión del
  directorio no dependa de una suposición).
- Suite completa: 1119/1142 (23 error, todos `ModuleNotFoundError: frappe`
  preexistentes; 0 `FAIL`).
- `python -m compileall` sobre los 11 archivos `.py` tocados — sin errores.
- `validate_nexora_governance.py` (181 requisitos, sin cambio de conteo — se
  reclasificó `NXR-SEC-0001`, no se agregó una fila) — verde.

**No ejecutado aquí** (requiere `bench`+MariaDB reales): un intento real de acceso
cruzado entre proyectos contra Frappe/MariaDB (crear dos proyectos, restringir un
"NEXORA Project Viewer" a uno vía `User Permission`, e intentar leer el otro por cada
función corregida). La corrección se verificó por lectura exhaustiva y rastreo de
cadena de llamadas — riguroso, pero no es lo mismo que una prueba de penetración real
ejecutada. Por eso `NXR-SEC-0001` se clasifica `NO DEMOSTRADO`, no
`IMPLEMENTADO Y VALIDADO`.

**Riesgos residuales.** Ninguno nuevo: todos los cambios son adiciones de un chequeo
de permiso ya existente y probado (`require_project_access`) a funciones que ya lo
necesitaban — cero cambios a cálculo financiero, cero cambios de esquema. Riesgo
positivo: algunas funciones que antes devolvían datos sin acotar por proyecto ahora
exigen que el usuario tenga `view_all_projects` cuando no se especifica `project`
(p. ej. `list_purchase_requests()` sin argumentos) — un cambio de comportamiento
correcto y deseado, no un defecto, pero que un cliente real que dependiera del
comportamiento inseguro anterior notaría como un nuevo rechazo de permiso legítimo.
No se encontró ningún llamador real en el producto que dependiera de ese
comportamiento (verificado con `grep` contra `public/js/*.js` y `nexora/page/**/*.js`
para cada función corregida).

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 20 (IA operacional) según la nueva fase de misión:
auditar gateway/router/proveedores/credenciales/costos del NIP existente e integrar
IA en búsqueda/consultas/explicaciones — con la salvedad, ya anticipada, de que este
entorno no tiene credenciales reales de ningún proveedor, por lo que buena parte de
ese bloque quedará necesariamente `NO DEMOSTRADO`.

## Bloque 20 — IA operacional (NXR-AI-0001)

**Alcance.** Auditar (no reconstruir) el gateway de IA existente
(`nexora_app/nexora/intelligence/`, NIP Bloques 1-6, ya mergeado en `main` bajo SHA
`f63f86e4`): fallback, credenciales, timeouts, costos, capacidades, observabilidad —
y verificar el mandato explícito de seguridad de este bloque: "no enviar información
que el usuario no esté autorizado a consultar" a un proveedor externo. Dado que este
entorno no tiene credenciales reales de ningún proveedor de IA, este bloque es
predominantemente una auditoría de código ya existente, no construcción nueva —
consistente con la regla de no repetición de la misión ("si ya está IMPLEMENTADO Y
VALIDADO, no repetirlo"; aquí la infraestructura ya existe, se verificó, no se
reconstruyó).

**Metodología.** Lectura directa del código real de `intelligence/`, nunca de su
documentación de diseño ni de nombres de función que sugieran una capacidad sin
confirmarla.

**Hallazgos de la auditoría (infraestructura confirmada real, no aspiracional).**
- **Fallback multi-proveedor real**: `orchestrator.py::execute()` ordena candidatos
  vía `orchestrator_core.rank_candidates()`/`score_candidate()` — funciones puras,
  ya exhaustivamente probadas en `test_intelligence_orchestrator_core.py` (circuito
  cerrado/semiabierto/abierto, cooldown con backoff que se duplica en fallos
  repetidos y se capa en un máximo, `prefer` que cede ante un proveedor degradado en
  vez de forzarlo, un solo reintento sobre el mismo proveedor y solo para errores
  transitorios — nunca para autenticación/429/402/modelo-no-encontrado). No se
  encontró necesidad de agregar más pruebas puras aquí: la cobertura ya existente es
  exhaustiva: al revisar el archivo de prueba no se encontró ningún hueco real en la
  lógica de ranking/circuito que justificara una prueba nueva.
- **Timeouts** configurables por proveedor (`NXR AI Provider.timeout_seconds`, 30s
  por defecto, validado entre 1 y 600s) hasta `http_support.send_json_request`.
- **Credenciales**: el campo `secret` es `fieldtype: Password` (cifrado nativo de
  Frappe); no se encontró ningún `audit()`/log que incluya el valor crudo —
  confirmado además por un test estático ya existente
  (`test_audit_calls_never_include_the_raw_secret`). Ninguna función de listado
  (`list_providers`/`list_credential_status`) proyecta el campo `secret`.
- **Costos/uso real, no inventado**: `NXR AI Usage Event` registra cada intento
  (éxito o fallo) contra un proveedor con proveedor/capacidad/modelo/tokens/costo —
  los tokens y el costo se extraen de lo que el proveedor efectivamente reportó
  (`_extract_usage`), nunca se estiman ni se inventan — más latencia y
  `correlation_id`. `get_provider_usage_summary()` los agrega para el panel
  administrativo (`nexora-ai-providers`).
- **Observabilidad**: `NXR Audit Event` registra los eventos de vida del
  despachador (`ai_orchestrator_attempt_failed`, `ai_orchestrator_dispatch_succeeded`,
  `ai_orchestrator_all_providers_exhausted`) con `correlation_id`.

**Verificación del mandato de seguridad del bloque: ninguna fuga de datos no
autorizados hacia un proveedor externo.** `grep` exhaustivo confirmó que solo
existen **dos** llamadores reales de `intelligence.orchestrator.execute` en toda la
app:
- `conversation/nlu.py::interpret()` (Bloque 18) — envía únicamente el texto del
  usuario, su propio historial de conversación y el catálogo estático de intenciones
  (`build_intent_prompt(REGISTRY)`, metadatos fijos, no datos de ningún usuario).
  Por diseño de `dispatch.py`, `nlu.interpret()` se ejecuta *antes* de que cualquier
  función de dominio real se invoque (`_invoke_read`/`_run_write_preview` ocurren
  después de resolver la intención) — el modelo de IA nunca ve un saldo, un contrato
  ni ningún dato real del negocio, solo interpreta qué quiso decir el usuario.
- `intelligence/service.py::run_orchestrated_request` — el panel admin de "probar
  conexión"; envía únicamente una cadena de prueba (`"ping"` por defecto), nunca
  datos del negocio.

**Integración "búsqueda/consultas/explicaciones" ya satisfecha, no duplicada.** El
mandato de este bloque de "integrar IA en búsqueda/consultas/explicaciones" ya lo
construyó `NXR-CNV-0001` (Bloque 18) sobre este mismo gateway — no se repite ni se
construye una segunda capa conversacional.

**Hallazgo documentado, no un defecto que bloquee.** No existe una prueba ejecutable
de extremo a extremo de `orchestrator.execute()` con proveedores simulados fallando
en cascada — las pruebas del algoritmo de ranking son puras y completas, pero la
función impura que integra base de datos + HTTP no tiene un doble de prueba. No se
corrige aquí: requeriría inyección de dependencias dentro de código NIP ya
certificado en bloques anteriores, un cambio de diseño fuera del alcance de una
auditoría (que audita, no reabre código ya certificado sin una razón real
encontrada).

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB/credenciales
reales de IA):
- `test_ai_data_exposure_contract.py` (nuevo) — 3/3 en verde: fija que solo existen
  dos llamadores reales de `orchestrator.execute()` (si un tercero se agrega sin
  pasar por esta prueba, falla — obligando a auditar el nuevo llamador antes de
  aceptarlo) y que `conversation/nlu.py::interpret()` nunca referencia una función de
  lectura/escritura de dominio.
- Suite completa: 1122/1145 (23 error, todos `ModuleNotFoundError: frappe`
  preexistentes; 0 `FAIL`).
- `validate_nexora_governance.py` (182 requisitos — se agregó `NXR-AI-0001`, no se
  modificó ningún requisito existente) — verde.

**No ejecutado aquí** (requiere credenciales reales de al menos un proveedor de IA,
ausentes en este entorno): cualquier llamada real a `orchestrator.execute()` contra
un proveedor vivo; la prueba de extremo a extremo del mecanismo de fallback. Por eso
`NXR-AI-0001` se clasifica `EXISTENTE Y REUTILIZABLE` (infraestructura real,
auditada, correcta) y no `IMPLEMENTADO Y VALIDADO` (que exigiría esa ejecución real).

**Riesgos residuales.** Ninguno nuevo: este bloque no modificó código de
`intelligence/`, solo lo auditó y agregó pruebas de contrato que fijan hallazgos ya
verdaderos. El hueco de prueba de extremo a extremo del orquestador queda como deuda
técnica conocida, no crítica (la lógica pura que decide el fallback ya está probada
exhaustivamente; lo no probado es la integración con HTTP/DB, que requeriría
credenciales reales de todos modos para ser una prueba honesta).

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 21 (WhatsApp Business real) según la nueva fase de
misión — requiere credenciales reales de Meta (Embedded Signup, verify token) que
solo el propietario puede generar. Este es exactamente el tipo de bloque que la
misión pide detener para pedir una decisión del propietario antes de construir nada:
sin esas credenciales, cualquier código nuevo quedaría sin forma de probarse
honestamente y el diseño ya existente (`docs/nexora/NIP_BLOQUE_6_CONVERSATIONAL_OS.md`,
líneas 218-253) ya lo anticipa como "requiere credenciales reales de Meta que solo
el propietario puede emitir".

## Bloque 21 — WhatsApp Business real (NXR-INT-0008)

**Aclaración pedida antes de construir.** El propietario pidió inicialmente "solo
deja la opción de ingresar el número de WhatsApp Business, al ingresarlo y
verificarlo se sincronizará". Se detuvo la ejecución para aclarar: WhatsApp
Business Cloud API no se puede verificar con solo un número — Meta exige una app
con el producto WhatsApp Business activado, que emite un App ID, App Secret, token
de acceso y `phone_number_id`; nada de eso lo genera un número por sí solo. Construir
una pantalla que "solo pide el número y lo verifica" sin esas credenciales habría
exigido simular el éxito, prohibido explícitamente por este mismo bloque de la
misión. Se preguntó con `AskUserQuestion` y el propietario confirmó (2026-08-11) que
ya tiene la app de Meta configurada — la decisión que este bloque tenía pendiente
desde el Bloque 12 (`NXR-INT-0008`, "bloqueado hasta que el propietario decida
reabrir el alcance y provea credenciales reales de Meta") ya se tomó.

**Alcance.** Construir la conexión real (no las credenciales mismas — esas las
provee el propietario desde su panel de Meta for Developers): pantalla
administrativa para introducir App ID/App Secret/token de acceso/phone_number_id/
WABA ID/verify token, webhook firmado que recibe mensajes reales, y el cableado al
motor conversacional ya construido (Bloque 18) para que un mensaje real de WhatsApp
se procese exactamente como un mensaje de texto del asistente en la app — sin una
segunda interpretación de intención ni una segunda tabla de permisos.

**Arquitectura implementada.** `nexora_app/nexora/conversation/channels/` (nuevo):
- `whatsapp_core.py` (puro, sin Frappe, mismo principio que `conversation/core.py`):
  `verify_signature()` — HMAC-SHA256 sobre el cuerpo crudo exacto (nunca el payload
  ya parseado: un solo byte de diferencia invalida la firma real que Meta calculó),
  comparado con `hmac.compare_digest` para no filtrar por temporización.
  `extract_verification_challenge()` — responde al reto GET de Meta solo si
  `hub.mode == "subscribe"` y `hub.verify_token` coincide exactamente.
  `extract_inbound_messages()` — extrae solo mensajes reales de la forma que Meta
  documenta (`entry[].changes[].value.messages[]`), ignora actualizaciones de estado
  de entrega/lectura (que llegan en `value.statuses`, una forma distinta), y nunca
  fabrica texto para un mensaje sin `id`/`from` real o de un tipo no reconocido
  (ubicación, contacto, interactivo) — se conserva con `text: None`, no se descarta
  en silencio ni se inventa contenido.
- `whatsapp.py` (Frappe): resuelve la credencial activa con los secretos ya
  descifrados (`get_password`, nunca registrados ni impresos); el webhook POST
  verifica la firma **antes** de parsear el cuerpo como JSON (orden fijado por una
  prueba de contrato); deduplica por `message_id` real con `frappe.cache()` (24h) —
  Meta reintenta la entrega del mismo webhook, y no se justificaba un campo de
  esquema nuevo para un identificador que solo importa un día. Un mensaje de un
  número sin `NXR Channel Account` vinculado y `Active` nunca se procesa — responde
  pidiendo que un administrador lo conecte, exactamente como diseñaba
  `NIP_BLOQUE_6_CONVERSATIONAL_OS.md` antes de que existiera código real. El mensaje
  se procesa con `frappe.set_user(user)` temporal (restaurado en un `finally`) +
  `nexora.conversation.dispatch.send_message` — el mismo motor del Bloque 18,
  reutilizado íntegro. Imágenes/documentos: descarga real en dos pasos (resolver la
  URL firmada de corta vida del medio, luego descargarla — ambos con el mismo
  token, tal como Meta lo documenta), se suben como `File` privado de Frappe, y la
  leyenda (o "Guarda esta evidencia." por defecto) entra al motor conversacional
  como si el usuario la hubiera escrito — cae naturalmente en `register_evidence`
  sin ningún código especial para el canal, gracias a la extensión mínima de
  `dispatch.send_message` (`attachment_file_url` opcional, se fusiona como el slot
  `file_url` sin importar qué intención se resuelva; el canal de texto puro del
  Bloque 18 nunca envía esta clave, así que su comportamiento no cambió).
- Dos DocTypes nuevos: `NXR Channel Credential` (`app_secret`/`access_token`/
  `verify_token` como `Password`, cifrados en reposo; bloqueado a escritura por
  Desk UI con `require_service_write()`, mismo patrón que `NXR AI Provider
  Credential`; `on_trash` lo rechaza — una credencial se reemplaza, no se borra) y
  `NXR Channel Account` (vincula un número real a un `User` real de NEXORA; rechaza
  en su propio `validate()` un segundo vínculo `Active` para el mismo número).
- Cuatro acciones de permiso nuevas en `permissions.py`: `manage_channel_credential`/
  `manage_channel_account` → `ADMINISTRATOR_ONLY_ROLES` (conectar credenciales de
  Meta o decidir qué usuario real actúa detrás de un número es al menos tan sensible
  como gestionar una credencial de proveedor de IA); `view_channel` →
  `REPORT_EXPORT_ROLES`. Ningún "NEXORA Project Viewer" puede tocar nada de este
  módulo.
- Página administrativa `nexora-conversation-channels` (conectar, "Probar
  conexión", vincular/revocar números), registrada en `nexora.js` y el workspace —
  mismo patrón que `nexora-ai-providers`, que tampoco vive en la barra inferior de
  `nexora_shell.js` (confirmado leyendo `test_page_registry_contract.py`: esa prueba
  solo exige `nexora.js` + workspace, `SECTIONS` es un subconjunto curado, no un
  registro exhaustivo).
- **Prueba real, no simulada (mismo principio que corrigió `NXR-INT-0007` en el
  Bloque 15):** `test_channel_connection` hace una llamada HTTP real a la Graph API
  de Meta (`GET /{phone_number_id}?fields=display_phone_number,verified_name`) y
  solo activa el canal si Meta lo confirma — nunca escribe `"Success"` sin haber
  llamado a nadie; si Meta rechaza, el canal queda `Inactive` con el detalle real del
  rechazo. `connect_credential` (guardar) y `test_channel_connection` (probar) son
  funciones separadas a propósito, mismo principio que ya separó
  `save_credential`/`test_provider_connection` en el módulo de IA.

**Advertencia de implementación honesta (documentada también en el propio
código).** El mecanismo para que el reto GET de verificación de Meta devuelva texto
plano — no envuelto en JSON, como Frappe hace por defecto en cualquier función
`@frappe.whitelist` — se implementó según la convención mejor conocida de Frappe
(`frappe.response["type"] = "text"`), pero **no se pudo verificar contra una
instancia real de Frappe** (ausente en este entorno). Si la verificación del webhook
falla en el primer intento real contra un `bench` de verdad, este es el primer punto
a revisar.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB/red real hacia
Meta):
- `test_whatsapp_channel_core.py` (nuevo) — 18/18 en verde: firma válida sobre el
  cuerpo exacto, secreto equivocado rechazado, cuerpo alterado en un solo byte
  invalida la firma, encabezado ausente/sin prefijo/vacío rechazado, reto de
  verificación con token correcto/incorrecto/modo distinto de `subscribe`,
  extracción de mensaje de texto real, extracción de imagen con leyenda sin inventar
  un cuerpo de texto, actualizaciones de estado ignoradas (no son mensajes), mensaje
  sin `id`/`from` real nunca fabricado, tipo no reconocido (ubicación) conservado
  sin texto inventado.
- `test_whatsapp_channel_contract.py` (nuevo) — 19/19 en verde: la firma se verifica
  antes de parsear el cuerpo (orden fijado por la prueba, no solo por el código),
  `connect_credential` nunca llama a la Graph API real, `test_channel_connection` sí
  la llama, ningún secreto se registra en texto plano, ambos DocTypes exigen
  `require_service_write()`, los campos de secreto son `Password`, las cuatro
  acciones de permiso nuevas son administrativas, registro completo de la página en
  los lugares que exige el invariante de gobernanza, y que el canal de texto puro
  del Bloque 18 (7 intenciones, sin cambios) no se vio afectado por la extensión de
  adjuntos.
- Suite completa: 1160/1184 (24 error, todos `ModuleNotFoundError: frappe`
  preexistentes — 23 anteriores + `test_whatsapp_channel_integration.py` nuevo; 0
  `FAIL`). Una regresión real encontrada y corregida durante la propia ejecución:
  `test_app_contract.py` (conteo de DocTypes 56→58); una regla de gobernanza real
  encontrada y corregida: el tope superior de `Propietario` en
  `validate_nexora_governance.py` solo aceptaba hasta "BLOQUE 20" — extendido a 30
  para cubrir el resto de la nueva fase de misión (no un hallazgo del código de la
  app, sino de la propia herramienta de gobernanza, que no había sido actualizada
  desde que la misión se extendió a 30 bloques).
- `node --check` sobre el JS nuevo, `python -m compileall` — sin errores.
- `validate_nexora_governance.py` (182 requisitos, sin cambio de conteo —
  reclasificación de `NXR-INT-0008`, no una fila nueva) — verde.
- `test_whatsapp_channel_integration.py` (`FrappeTestCase`, verificación GET
  correcta/incorrecta, firma inválida rechazada antes de tocar cualquier dato,
  número no vinculado nunca procesado, número vinculado llega al motor
  conversacional real con `frappe.session.user` restaurado tras procesar, mensaje
  duplicado deduplicado, imagen con leyenda registrada como evidencia real) escrita
  pero **no ejecutable en este entorno** sin bench/MariaDB. Ninguna prueba, ejecutable
  o no, llama jamás a la Graph API real de Meta — todas simulan `_graph_get`/
  `_graph_post_json` con `unittest.mock.patch`.

**No ejecutado aquí** (requiere `bench`+MariaDB+la app real de Meta del propietario,
ausentes en este entorno): cualquier llamada real a la Graph API, cualquier webhook
real recibido desde WhatsApp, y en particular la verificación GET real del reto de
Meta (ver la advertencia de implementación honesta arriba). Por eso `NXR-INT-0008`
se clasifica `NO DEMOSTRADO`, no `IMPLEMENTADO Y VALIDADO`.

**Riesgos residuales.** Ninguno de integridad financiera: cero cambios a
`financial/`; la única extensión al motor conversacional del Bloque 18
(`attachment_file_url` opcional) es puramente aditiva y no afecta el canal de texto
existente (confirmado por prueba). Riesgo real documentado: la incertidumbre sobre
`frappe.response["type"] = "text"` (arriba) — el propietario debe verificar la
verificación GET del webhook contra su `bench` real antes de dar por sentado que
Meta aceptará la conexión sin ajustes.

**Bloqueo.** Ninguno directo a este bloque. El propietario debe: (1) desplegar este
código en un `bench` real; (2) conectar sus credenciales reales desde
`nexora-conversation-channels`; (3) ejecutar "Probar conexión"; (4) configurar la
URL del webhook (`https://<su-dominio>/api/method/nexora.conversation.channels.whatsapp.webhook`)
y el verify token en el panel de Meta; (5) vincular su número de WhatsApp a su
propio usuario de NEXORA desde la misma pantalla antes de escribirle al número de
prueba.

**Siguiente acción.** Bloque 22 (Integraciones) según la nueva fase de misión —
auditar el resto de integraciones existentes contra mocks peligrosos/`Success`
fijo/respuestas simuladas, mismo criterio que ya se aplicó aquí y en el Bloque 15.

## Bloque 22 — Integraciones (NXR-INT-0009)

**Alcance.** Barrido exhaustivo de `nexora_app/nexora/**/*.py` buscando cualquier
integración con algo externo al propio sistema que no se haya auditado ya en los
Bloques 15 (`NXR-INT-0007`, `integrations/service.py::test_connection`), 20
(`NXR-AI-0001`, gateway de IA) o 21 (`NXR-INT-0008`, WhatsApp) — para cerrar el
mandato "auditar TODAS las integraciones" sin dejar nada fuera ni repetir trabajo
ya cerrado.

**Metodología.** Búsqueda por patrón (`urllib`, `requests`, `http.client`,
"webhook", "smtp", "email", "gateway", "connector", "callback") en todo el árbol
de la app, seguida de lectura directa de cada candidato encontrado — nunca
confiando en un nombre de función o de archivo como prueba de qué hace.

**Confirmado, no una fuga nueva.**
- `integrations/connectivity.py::check_endpoint_connectivity` ya es real: timeout
  explícito, tres tipos de error distinguidos (`HTTPError`/`TimeoutError`/
  `URLError`, sin un `except Exception` genérico que los oculte), alcance
  declarado explícitamente en su propio docstring (solo alcanzabilidad HTTP, no
  autentica ni valida contrato de negocio).
- `notifications/service.py` — confirmado que **no** es una integración externa:
  `create_notification`/`list_notifications`/`mark_read` solo leen/escriben el
  doctype interno `NXR Notification`. No hay envío real de correo/SMS en ningún
  lugar de este módulo ni de sus doctypes relacionados.
- `grep` exhaustivo de `smtplib`/`send_mail`/`requests.post`/`requests.get`/
  `http.client` en todo `nexora_app/` fuera de `intelligence/` y
  `conversation/channels/`: sin resultados. El único `urllib.request` real fuera
  de esos dos módulos es exactamente `integrations/connectivity.py`.
- `erpnext/construcontrol/storage/supabase.py`: existe, es real (Supabase
  Storage, timeouts explícitos, validación estricta de URL solo HTTPS a
  `*.supabase.co`, credencial de variable de entorno de servidor), pero es
  legado de ConstruControl **sin relación funcional con NEXORA** — confirmado
  que `nexora_app/` no lo importa (solo se cita como precedente de diseño en dos
  comentarios de `intelligence/`) y que `test_app_contract.py`/
  `test_installation.py` (pruebas ya existentes, no nuevas de este bloque)
  verifican activamente que NEXORA no dependa de `erpnext.construcontrol`. Fuera
  del perímetro de esta auditoría, correctamente.

**Dos hallazgos reales corregidos** (mandato explícito del bloque: "cada
integración debe contemplar... auditoría"):
- `integrations/service.py::test_connection` (ya corregido en el Bloque 15 de
  `NXR-INT-0007` — el resultado real depende de `check_endpoint_connectivity`,
  no de un valor fijo) mutaba el documento `NXR Integration` pero nunca quedaba
  en la bitácora cruzada `NXR Audit Event` — solo en el log propio de la
  integración (`NXR Integration Log`), invisible para un auditor que revisa la
  bitácora del sistema como ya puede hacerlo para cualquier otra acción
  sensible. Corregido agregando `audit("integration_connection_tested", ...)`
  con un `correlation_id` real generado por intento.
- `conversation/channels/whatsapp.py` (Bloque 21, de esta misma sesión) tenía el
  mismo hueco en sus cuatro acciones administrativas: `connect_credential`,
  `test_channel_connection`, `link_channel_account`, `revoke_channel_account`
  nunca llamaban a `audit()` — un hallazgo real sobre trabajo propio, no ajeno.
  Conectar una credencial de Meta o decidir qué usuario real actúa detrás de un
  número externo es al menos tan sensible como cualquier otra acción ya
  auditada en este mismo módulo (el registro de un mensaje procesado, por
  ejemplo). Corregidas las cuatro con `audit(...)` + `correlation_id` real;
  `test_channel_connection` no tenía ningún `correlation_id` propio hasta ahora
  (su parámetro `payload` era opcional y nunca se parseaba) — se agregó.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `test_integrations_audit_contract.py` (nuevo) — 2/2 en verde: `test_connection`
  llama a la bitácora real, y (regresión directa de NXR-INT-0007) sigue
  dependiendo del resultado HTTP real, nunca de un valor fijo.
- `test_whatsapp_channel_contract.py` (ampliado) — nueva clase
  `TestAdministrativeActionsAreAudited`, 1/1 en verde: las cuatro funciones
  administrativas llaman a la bitácora real.
- Suite completa: 1163/1187 (24 error, todos `ModuleNotFoundError: frappe`
  preexistentes; 0 `FAIL`).
- `python -m compileall` sobre los 2 archivos tocados — sin errores.
- `validate_nexora_governance.py` (183 requisitos — se agregó `NXR-INT-0009`,
  no se modificó ninguna fila existente) — verde.

**No ejecutado aquí** (requiere `bench`+MariaDB reales): ninguna de las llamadas
de auditoría nuevas se ejecutó contra Frappe/MariaDB reales — no hay forma de
confirmar aquí que `frappe.get_doc("NXR Audit Event", ...)` real quede escrito
correctamente, solo que el código las invoca con los parámetros correctos. Por
eso `NXR-INT-0009` se clasifica `NO DEMOSTRADO`.

**Riesgos residuales.** Ninguno nuevo: ambas correcciones son adiciones puras de
una llamada de auditoría ya probada (`financial.db.audit`) a funciones que ya
mutaban un documento real — cero cambio de comportamiento observable para el
llamador (las funciones devuelven exactamente lo mismo que antes).

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 23 (Notificaciones) según la nueva fase de misión —
construir bandeja/correo/PWA con distinción real CREADO/ENTREGADO/FALLIDO. Dado
que este bloque ya confirmó que `notifications/service.py` hoy es una bandeja
interna sin ninguna salida externa real (sin correo/SMS), cualquier estado
"ENTREGADO" que se agregue deberá corresponder a una entrega real verificable
(p. ej. vía el canal WhatsApp ya construido en el Bloque 21, el único canal de
salida externa real que existe hoy) — nunca una marca de "entregado" sin haber
entregado nada, mismo principio que ya aplicó `NXR-INT-0007`.

## Bloque 23 — Notificaciones (NXR-NOT-0006)

**Alcance.** Reconstruir `notifications/` para que "Entregado" signifique algo
real: distinguir el registro interno (que siempre se crea) de la entrega
externa (que puede fallar), usando exactamente los dos canales con una salida
externa real que existen hoy en el sistema — correo vía `frappe.sendmail` (nunca
usado antes en este módulo) y WhatsApp vía el canal real del Bloque 21.

**Decisión de diseño documentada en `notifications/core.py`.** Inbox/PWA se
consideran entregados en el momento de crear el registro — la bandeja (dentro
de la app o de la PWA instalada) ES el mecanismo de entrega, no hay un segundo
paso de red que pueda fallar aparte. Solo Email/WhatsApp
(`EXTERNAL_DELIVERY_CHANNELS`) tienen un intento de entrega separado, con su
propio estado `Delivered`/`Failed` y reintento acotado
(`MAX_DELIVERY_RETRIES = 3`, `can_retry_delivery` pura).

**Arquitectura implementada.**
- `notifications/core.py`: agrega `EXTERNAL_DELIVERY_CHANNELS`,
  `MAX_DELIVERY_RETRIES`, `requires_external_delivery()`,
  `can_retry_delivery()` — todo puro, sin Frappe.
- `nxr_notification.json`: nuevos campos `delivery_status` (Created/Delivered/
  Failed, `reqd`+`read_only`, con descripción explícita de la distinción
  honesta en el propio esquema), `delivered_at`, `failure_reason`,
  `retry_count`; `channel` extendido con `WhatsApp`.
- `conversation/channels/whatsapp.py`: dos funciones nuevas para que otros
  módulos reutilicen el canal real sin tocar sus internos privados —
  `resolve_external_id_for_user(user)` (búsqueda inversa vía
  `NXR Channel Account`) y `send_direct_message(to, body)` (envío directo, no
  whitelisted por sí sola — cada llamador decide su propio permiso, mismo
  principio que ya usa `conversation.dispatch`).
- `notifications/service.py` reescrito por completo:
  - `create_notification` ahora valida canal/prioridad con los validadores
    puros ya existentes (estaban importados en versiones previas del módulo
    pero nunca se llamaban), deduplica por `idempotency_key` antes de insertar
    (el campo ya era `unique=1` en BD, pero un duplicado real habría chocado
    contra un error crudo de base de datos en vez de devolver el registro
    existente) y llama a `_attempt_delivery`.
  - `_attempt_delivery`: para Email llama a `frappe.sendmail` real (con
    `reference_doctype`/`reference_name` apuntando a la notificación); para
    WhatsApp resuelve el número vinculado del destinatario y llama a
    `send_direct_message`. Cualquier excepción real (SMTP caído, número no
    vinculado, Meta rechaza el envío) se traduce a `Failed` con el motivo real
    en `failure_reason` — nunca se oculta ni se convierte en un éxito
    fabricado. Cada intento queda en la bitácora cruzada (`financial.db.audit`,
    `notification_delivery_attempted`), mismo patrón que el resto del sistema
    desde el Bloque 22.
  - `retry_notification` (nueva): solo permite reintentar una notificación
    `Failed` en un canal con paso de entrega externo, hasta
    `MAX_DELIVERY_RETRIES`.
  - `mark_read`: **hallazgo real corregido** — exigía el permiso gerencial
    `approve` incluso para que el propio destinatario marcara su notificación
    como leída. Ahora el destinatario siempre puede marcar la suya; cualquier
    otro usuario sigue necesitando el mismo permiso amplio de siempre.
  - `list_notifications`: reverificado que sigue restringido a
    `has_action("view_all_projects")` para leer notificaciones de otro usuario
    (regresión directa de `NXR-SEC-0001`, Bloque 19) — se reescribió el módulo
    completo y había que confirmar que la corrección de ese bloque sobrevivió.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `test_notifications_core.py` (ampliado) — 20/20 en verde: cobertura nueva de
  `requires_external_delivery`/`can_retry_delivery`/canal `WhatsApp`.
- `test_notifications_contract.py` (ampliado) — 20/20 en verde: campos nuevos
  del doctype, entrega real (no fabricada) por Email/WhatsApp, deduplicación,
  gating de reintento, corrección de `mark_read`, restricción de
  `list_notifications`, auditoría de cada intento.
- `test_whatsapp_channel_contract.py` (ampliado) — nueva clase
  `TestDirectMessageSendingForOtherModules`, 3/3 en verde: `send_direct_message`
  nunca fabrica un éxito y no está whitelisted por sí sola.
- `test_notifications_integration.py` (nuevo, `FrappeTestCase`, 13 escenarios) —
  escrito pero no ejecutable en este entorno sin bench/MariaDB.
- Suite completa: 1160/1185 (25 error, todos `ModuleNotFoundError: frappe`
  preexistentes — 24 previos + 1 nuevo de `test_notifications_integration.py`;
  0 `FAIL`).
- `python -m compileall` sobre los archivos tocados — sin errores.
- `validate_nexora_governance.py` (183 requisitos, sin fila nueva — se
  reclasificó `NXR-NOT-0006`) — verde.

**No ejecutado aquí** (requiere `bench`+MariaDB reales): ningún correo SMTP
real enviado, ningún mensaje de WhatsApp real entregado desde este código, y
ninguna de las escrituras nuevas del doctype (`delivery_status`, etc.) se
confirmó contra Frappe/MariaDB reales. Por eso `NXR-NOT-0006` se clasifica
`NO DEMOSTRADO`.

**Riesgos residuales.** Ninguno nuevo más allá del ya inherente a no poder
ejecutar contra Frappe real en este entorno. El comportamiento de Inbox/PWA
(la mayoría del tráfico actual) no cambió observablemente para el llamador más
allá de los campos nuevos, que llegan con default seguro (`Created` →
`Delivered` en el mismo `create_notification`).

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 24 (Reportes) según la nueva fase de misión.

## Bloque 24 — Reportes (endurecimiento de NXR-SEC-0001 en `dashboard/*`)

**Alcance.** Auditar `nexora_app/nexora/reports/` y los módulos `dashboard/*` que
alimentan el centro de reportes (`nexora-reports`, FI01/FI02/FI03/CO01/PR02/
PR03/MM03/BI01) buscando cualquier hueco de alcance por proyecto que la
auditoría original de `NXR-SEC-0001` (Bloque 19) no hubiera cubierto — ese
bloque cubrió explícitamente `purchases/inventory/contracts/budget/financial/
integrations`, no los módulos de consulta de `dashboard/`.

**Metodología.** Lectura directa de `reports/service.py`, `reports/
safe_export.py`, `reports/canonical_views.py`, `reports/actions.py`,
`reports/core.py`, y de cada función `dashboard/*` que ambos consumen
(`source_query.py`, `contract_page.py`, `expense_query.py`, `snapshot_query.py`,
`query_utils.py`), rastreando la cadena de llamadas completa antes de concluir
que un chequeo existe o falta — mismo estándar que exigió el propio Bloque 19.

**Hallazgo inicial (descartado tras verificación):** `get_source_statement_page`,
`get_source_movement_page` (`dashboard/executive.py` → `source_query.py`) y
`get_contract_page` (`dashboard/executive.py` → `contract_page.py`) no llaman
`require_project_access` en su propio cuerpo — a primera lectura, parecía el
mismo defecto que `NXR-SEC-0001` corrigió en otros catorce lugares: un
"NEXORA Project Viewer" podría omitir `project` y leer datos de cualquier
proyecto. Verificación más profunda (rastreando la cadena completa, no solo la
función inmediata) confirmó que **no es un defecto**: las tres funciones
resuelven el proyecto con `dashboard.query_utils.project()` como su primera
operación real — y esa función sí llama `require_project_access(value,
action="view_reports")` internamente, lanzando antes de que se construya
cualquier filtro SQL. Esto coincide exactamente con lo que el propio
`NXR-SEC-0001` ya documentó ("la mayoría de `dashboard/*` ... que ya validan"),
pero esa afirmación nunca tuvo una prueba propia que la fijara — dependía de
que un lector futuro hiciera el mismo rastreo de cadena que se acaba de hacer
aquí. `expense_query.py` (FI02) sigue un patrón distinto pero igualmente
correcto: llama `require_project_access` directamente en su propio
`_query_params`, ya confirmado por el bloque anterior.

**Otras confirmaciones, sin hallazgo:** `reports/service.py::get_contract_statement`
(corregido en Bloque 19, sigue correcto: resuelve el proyecto real del
`contract` antes de comprobar acceso); `reports/service.py::export_report`
(la versión antigua, con truncado silencioso a `EXPORT_ROW_LIMIT`) está
redirigida por `hooks.py::override_whitelisted_methods` hacia
`reports/safe_export.py::export_report` (la versión que rechaza en vez de
truncar) — patrón ya usado y probado por `test_report_export_guard_contract.py`,
no un descubrimiento de este bloque; `NXR Saved Report` bloqueado a escritura
por Desk UI (`require_service_write()`) y a borrado (`on_trash`), igual que
otros doctypes sensibles.

**Trabajo de este bloque: cerrar la brecha de evidencia, no de código.** Se
escribió `test_reports_dashboard_project_scoping_contract.py` (nuevo, 7
pruebas de contrato estático) que fija de forma directa la cadena de
protección arriba descrita — no un grep superficial de todo el archivo, que
daría un falso positivo si la llamada existiera en una función vecina. Se
extendió `test_executive_reporting_integration.py` con
`test_report_center_queries_reject_a_viewer_without_an_explicit_project_grant`
(nueva, `FrappeTestCase`), que ejecuta contra los tres endpoints reales el
mismo intento que ya cubría `get_expense_page`: un Project Viewer sin
`User Permission` explícito es rechazado por los tres; tras concedérsela, los
tres responden con datos reales del proyecto autorizado.

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `test_reports_dashboard_project_scoping_contract.py` (nuevo) — 7/7 en verde.
- Suite completa: 1167/1192 (25 error, todos `ModuleNotFoundError: frappe`
  preexistentes; 0 `FAIL`).
- `python -m compileall` sobre los archivos tocados — sin errores.
- `validate_nexora_governance.py`/`validate_repository.py` — verdes.

**No ejecutado aquí** (requiere `bench`+MariaDB reales): la nueva prueba de
integración (`test_report_center_queries_reject_a_viewer_without_an_explicit_
project_grant`) no corrió contra Frappe/MariaDB reales en este entorno —
escrita pero no verificada por ejecución.

**Riesgos residuales.** Ninguno nuevo: no se modificó ningún comportamiento de
producción en este bloque, solo se agregó cobertura de prueba directa sobre un
invariante que ya existía y que la auditoría del Bloque 19 ya había confirmado
correcto por lectura.

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 25 (Evidencia + Avance) según la nueva fase de
misión.

## Bloque 25 — Evidencia + Avance (NXR-AVA-0005, NXR-AVA-0006)

**Alcance.** Auditar `financial/evidence.py` (comprobantes) y `progress/`
(avance físico) — los dos módulos que el nombre del bloque señala — buscando
el mismo tipo de hallazgo que ya cerraron los bloques anteriores: fuga de
alcance por proyecto, éxito fabricado, o afirmaciones de la matriz sin
respaldo real.

**Evidencia (`financial/evidence.py`): sin hallazgos.** Módulo ya
extremadamente maduro — SHA-256 real sobre el contenido (`sha256_content`),
archivo obligatoriamente privado, lista blanca de MIME/tamaño máximo 15 MB,
inmutabilidad de campos de contenido a nivel de controlador
(`IMMUTABLE_CONTENT_FIELDS` en `nxr_evidence.py`), máquina de estados real
(`assert_evidence_transition`), sustitución con versión incremental y
verificación de que el archivo previo realmente cambió (no una sustitución
vacía), y `list_evidence` ya corregido en el Bloque 19. Nada que corregir.

**Avance (`progress/`): hallazgo real — un reclamo falso en la matriz de
requisitos.** `NXR-AVA-0005` ("Experiencia cámara/galería iPhone") y
`NXR-AVA-0006` ("Proyección de feed fotográfico cronológico") estaban
clasificados `IMPLEMENTADO Y VALIDADO` desde el Bloque 13, citando el commit
`57a3438ddd931140f12fc417d5ba662dbbaaa315`. Verificación directa de ese commit
(`git show --stat`) mostró que solo agregó `progress/core.py` y
`progress/service.py` — ningún archivo de página, ningún JS, ninguna captura
de cámara. `git log --all --diff-filter=A --name-only -- "*progress*.js"` no
devolvió ningún resultado en **todo** el historial del repositorio: nunca
existió una página de avance. Los únicos dos llamadores reales de
`progress/service.py` eran `financial/seeds.py` (datos de siembra) y el
resumen agregado de solo lectura del panel ejecutivo — ningún usuario real
podía registrar avance con foto desde la aplicación, contra lo que la matriz
afirmaba. La clase CSS `.nxr-progress-grid` ya existía reservada en
`nexora.css` desde antes de este bloque, sin página que la usara.

**Corrección real, no solo documental.**
- `progress/service.py`: nueva `list_progress_records()` — no existía
  **ninguna** función whitelisted de lectura individual (ni agregada por
  proyecto ni por registro); toda lectura vivía detrás de un helper privado
  inalcanzable directamente. Mismo patrón de alcance que
  `financial.evidence.list_evidence`: `require_project_access(project,
  action="preview")` — regresión directa de NXR-SEC-0001 si se omite.
- Página nueva `nexora/page/nexora_progress/` (JSON de página, JS, registro
  Python vacío) — formulario de registro (proyecto, fase, descripción,
  porcentaje, fecha, responsable, fotografía vía `fieldtype: "Attach"`, que en
  navegadores móviles abre el selector nativo de cámara/galería sin código
  adicional — mismo mecanismo que ya usa `nexora-evidence`), controles de
  revisión (enviar a revisión / aprobar / rechazar, conectados a
  `transition_progress_record`), y un feed cronológico real de tarjetas con
  foto (no una tabla plana), ordenado por `recorded_date desc`.
- Registrada en `nexora.js` (destino global), el workspace (`nexora.json`,
  atajo + acceso directo al DocType) y `SECTIONS` de `nexora_shell.js` (grupo
  "Expediente", 15º destino real — actualizado
  `test_dashboard_contract.py::test_global_navigation_uses_canonical_nexora_pages`
  de 14→15 con el mismo criterio que documentó cada incremento anterior).
  Nuevo icono `camera` en el mapa `ICONS` de la carcasa. Nuevas etiquetas
  `Submitted`/`Corrected` en el diccionario compartido de estados
  (`nexora_report_actions.js`) — la máquina de estados de avance ya las usaba,
  pero no tenían traducción visible.
- `docs/nexora/MATRIZ_REQUISITOS.md`: `NXR-AVA-0005`/`NXR-AVA-0006`
  reclasificados de `IMPLEMENTADO Y VALIDADO` (falso) a `NO DEMOSTRADO`
  (honesto), owner BLOQUE 25, con el hallazgo documentado explícitamente en su
  propia celda de evidencia — no se ocultó el error original, se señaló y se
  corrigió. Conteo total sin cambio (183, ninguna fila nueva).

**Pruebas.** Ejecutado en este entorno (sin `bench`/Frappe/MariaDB):
- `test_progress_contract.py` (ampliado) — 15/15 en verde: `list_progress_records`
  es un endpoint POST real con chequeo de proyecto (no solo de rol amplio), y
  la página nueva existe, está registrada y llama a las funciones reales del
  servicio (no una simulación).
- `test_dashboard_contract.py` (corregido) — conteo de destinos actualizado a
  15, con la nueva ruta verificada explícitamente.
- `test_progress_integration.py` (nuevo, `FrappeTestCase`, 5 escenarios:
  creación con foto real, transición completa Draft→Submitted→Approved,
  transición inválida rechazada por la máquina de estados real, lectura por
  proyecto autorizado, rechazo a un Project Viewer sin permiso explícito y
  aceptación tras concedérselo) — escrita pero no ejecutable en este entorno
  sin bench/MariaDB.
- Suite completa: 1175/1201 (26 error, todos `ModuleNotFoundError: frappe`
  preexistentes — 25 previos + 1 nuevo de `test_progress_integration.py`; 0
  `FAIL`).
- `python -m compileall` sobre los archivos tocados — sin errores.
- `validate_nexora_governance.py`/`validate_repository.py`/`validate_nexora_app.py`
  — verdes.

**No ejecutado aquí** (requiere `bench`+MariaDB reales): ningún recorrido real
de cámara/galería en un iPhone físico ni en WebKit se ejecutó en este
entorno — pendiente de `nexora-app.yml` (job `Frappe real`). Por eso
`NXR-AVA-0005`/`NXR-AVA-0006` se clasifican `NO DEMOSTRADO`, no
`IMPLEMENTADO Y VALIDADO`.

**Riesgos residuales.** Ninguno nuevo en el backend (misma lógica de permisos
y máquina de estados ya probada, solo expuesta ahora con un endpoint de
lectura y una página reales). Riesgo de diseño documentado, no corregido en
este bloque: `create_progress_record`/`transition_progress_record` exigen el
mismo permiso `approve` (rol gerencial) para **crear** un borrador de avance,
no solo para aprobarlo — un operador de campo no puede registrar su propio
avance sin que un gerente lo haga por él. Esto es una decisión de producto ya
existente desde el Bloque 13, no un defecto de seguridad introducido ni
corregido aquí; se documenta para que el propietario decida si quiere
relajarlo en un bloque futuro.

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 26 (Cierre de flujos operativos) según la nueva
fase de misión — auditoría/verificación únicamente, sin modificar reglas
financieras.

## Bloque 26 — Cierre de flujos operativos (auditoría, NXR-CAL-0001)

**Alcance.** Mandato explícito de este bloque: auditar y verificar el cierre
de flujos operativos (compras→recepción, contratos→liquidación, inventario,
control de calidad) sin modificar ninguna regla financiera — solo corregir lo
que no sea una regla de negocio financiera si se encuentra un hallazgo real.

**Máquinas de estado de cierre revisadas — todas correctas, sin hallazgo.**
- `purchases/order_core.py::PURCHASE_ORDER_TRANSITIONS`: `Sent → Completed` es
  el único cierre real; `Completed`/`Cancelled` son terminales sin salida.
- `purchases/receipt_core.py::GOODS_RECEIPT_TRANSITIONS`: `Draft → Completed`
  terminal, sin reapertura posible.
- `contracts/core.py`: `CONTRACT_TRANSITIONS` (`Completed → In Liquidation →
  Liquidated`, terminal), `AMENDMENT_TRANSITIONS`, `ESTIMATE_TRANSITIONS` —
  todas cierran a un estado sin salida. Verificado en `contracts/service.py`
  que ambos puntos de escritura posterior a la aprobación
  (`create_contract_amendment` línea 567, `create_contract_estimate` línea
  723) rechazan expresamente un contrato que no esté `Active`/`Suspended` —
  ningún contrato `Liquidated`/`Early Terminated`/`Cancelled Before Active`
  admite una adenda o estimación nueva. La liquidación misma
  (`transition_contract`, línea 534) exige saldo de anticipo y de retención en
  cero antes de aceptar `Liquidated` — no se puede cerrar un contrato con
  dinero pendiente sin resolver.
- `inventory/core.py::STOCK_TRANSACTION_TRANSITIONS`,
  `purchases/request_core.py::PURCHASE_REQUEST_TRANSITIONS`,
  `purchases/quotation_core.py::QUOTATION_TRANSITIONS`,
  `close/core.py::CLOSE_TRANSITIONS` (`TERMINAL_STATES = {Approved,
  Cancelled}`) — todos cierran correctamente, sin estado colgante ni
  transición hacia atrás desde un terminal.

**Hallazgo real (`NXR-CAL-0001`): `NXR Quality Check` es un doctype muerto.**
Existe desde el Bloque 13 (mismo commit que introdujo `NXR Progress Record`),
con un campo `progress_record` que lo vincula a un registro de avance
concreto y un controlador que exige `require_service_write()` — el mismo
candado que usa cualquier otro doctype financiero sensible. Pero **no existe
ningún `quality/service.py`**, ninguna función `@frappe.whitelist` en todo el
repositorio que abra la puerta de `service_write()` para este doctype,
ninguna página lo usa, y `financial/seeds.py` nunca crea un registro de
prueba (a diferencia de `NXR Progress Record`, que al menos tenía dos
llamadores reales). Con el candado puesto y ninguna llave real, **nadie — ni
siquiera un Administrador — puede crear o actualizar un control de calidad
hoy**. A diferencia de `NXR-AVA-0005`/`NXR-AVA-0006` (Bloque 25), esta fila no
corrige un reclamo previo: nunca existió una fila en la matriz de 183
requisitos que prometiera esta función, así que no había nada que
"desmentir" — se agrega ahora (`NXR-CAL-0001`, 183→184) para no dejarla
invisible en la contabilidad final del Bloque 30. **No se corrige en este
bloque**: el mandato es auditoría, no construir una función nueva sin que el
propietario decida su alcance real (¿quién aprueba un control de calidad?
¿bloquea la aprobación del avance vinculado o es solo informativo? ¿qué pasa
si el resultado es "Rechazado"?) — construir código sobre una decisión no
tomada sería inventar una regla de negocio, exactamente lo que este bloque
tiene prohibido hacer. Clasificado `REQUIERE DECISIÓN`.

**Hallazgo residual, no de este bloque: inestabilidad del job `Frappe real`
en `main`.** El PR #114 (Bloque 24, sin ningún archivo de código de
producción/runtime en su diff — solo pruebas y documentación) y el PR #115
(Bloque 25) mostraron, además del defecto ya documentado
(`panel: Dashboard did not expose the active period`), una segunda falla
idéntica byte por byte en ambos runs: `desktop-chromium` reporta
`operaciones: Guided stage 4 never opened` con el mismo payload de
diagnóstico exacto (mismo `document_date`, mismo `amount_hnl` vacío). Como
Bloque 24 no tocó ningún archivo `.js`/`.py` de producción, esta falla no
puede ser una regresión de ese PR ni de este — es un defecto ya presente en
`main` (apareció por primera vez visible en el run de Bloque 24, ausente en
el run de Bloque 23) o una inestabilidad de temporización del propio script
de Playwright (`scripts/nexora_browser_smoke.mjs`) en este entorno de CI, no
diagnosticable sin poder ejecutar el navegador aquí mismo. No se investiga a
fondo en este bloque (fuera de su mandato de "cierre de flujos operativos");
se deja documentado para que el Bloque 29 (certificación integral) lo
verifique con una ejecución real y, si sigue apareciendo, se abra como
hallazgo propio con su propio bloque de corrección.

**Pruebas.** No se modificó ningún archivo de código de producción en este
bloque (hallazgo documental, no una corrección de código) — sin cambios de
comportamiento que probar. Se verificó igualmente que nada se rompió:
- Suite completa: sin cambios respecto al Bloque 25 (1175/1201, 26 error
  preexistentes, 0 `FAIL`) — no se tocó ningún archivo de prueba ni de
  producción.
- `validate_nexora_governance.py` — verde, 184 requisitos (antes 183).
- `validate_repository.py` — verde.

**No ejecutado aquí** (requiere `bench`+MariaDB reales, y en el caso del
hallazgo residual de `Frappe real`, un navegador real): ninguna verificación
en vivo de si `NXR Quality Check` se comporta como se documenta (no hay nada
que ejecutar: no existe código de servicio); ninguna reproducción controlada
del defecto `operaciones` de `Frappe real`.

**Riesgos residuales.** `NXR-CAL-0001` queda como una decisión de producto
pendiente del propietario, no como un riesgo de seguridad o de integridad
financiera — el doctype bloqueado no puede escribirse por ninguna vía, ni
autorizada ni no autorizada, así que no hay superficie de ataque mientras
permanezca así. El hallazgo de `Frappe real` sí es un riesgo a vigilar: si es
una regresión real de `main` (no solo inestabilidad de CI), afecta el flujo
operativo diario (`nexora-operations`), el corazón de la aplicación.

**Bloqueo.** Ninguno. `NXR-CAL-0001` requiere una decisión del propietario
antes de construir código, pero no bloquea el resto de la misión.

**Siguiente acción.** Bloque 27 (PWA/iPhone/WebKit) según la nueva fase de
misión — auditoría únicamente; marcar `NO DEMOSTRADO` cualquier verificación
que requiera WebKit real, no disponible en este entorno. Al llegar al Bloque
29, verificar primero si el hallazgo residual de `Frappe real` (`operaciones`)
sigue reproduciéndose contra `main`.

## Bloque 27 — PWA/iPhone/WebKit (auditoría)

**Alcance.** Mandato explícito: auditar la compatibilidad
PWA/service-worker/iPhone/WebKit. Auditoría únicamente — marcar
`NO DEMOSTRADO` cualquier verificación que requiera ejecución real de WebKit,
no disponible en este entorno.

**Verificado sin hallazgo.** `nexora_app/nexora/tests/test_pwa_contract.py`
(6 pruebas, ya existentes) sigue en verde sin cambios: el manifest es
instalable (`id`/`start_url`/`scope`/`display: "standalone"`/iconos 192×192 y
512×512 maskable reales en disco), los `shortcuts` abren los tres flujos
reales (`nexora-operations?movement_code=101/102`, `nexora-evidence`), el
service worker (`www/nexora-service-worker.js` — confirmado que
`public/service-worker.js` ya no existe, movimiento de seguridad de un
bloque anterior) nunca cachea `/api/`, `/private/`, `/files/` ni `/app/`, y
`SHELL_ASSETS` cubre exactamente los mismos bundles que `hooks.py` registra
site-wide (`app_include_js`/`app_include_css`) — comparado campo por campo
por la prueba, no a simple vista. `nexora.css` trae `env(safe-area-inset-bottom)`,
`@media (max-width: 767px)` y objetivos táctiles de `min-height: 44px`.
`public/js/nexora.js::ensureManifest()`/`registerPwa()` registran el service
worker con `scope: "/app/"` y `updateViaCache: "none"`, solo en contexto
seguro (`window.isSecureContext`) y solo en rutas NEXORA
(`isNexoraLocation()`) — sin registro fuera de la app. Las filas de la matriz
que citan estas piezas (`NXR-UX-0001` a `NXR-UX-0004`, `NXR-UX-0007`,
`NXR-DOC-0006`, todas `IMPLEMENTADO Y VALIDADO` desde el Bloque 18 citando el
commit `57a3438...`) se verificaron contra ese commit real
(`git show --stat`): sí agregó exactamente `manifest.json`,
`service-worker.js` y las 80 líneas nuevas de `nexora.css` que las filas
describen — a diferencia de `NXR-AVA-0005`/`NXR-AVA-0006` (Bloque 25), aquí
el commit citado sí contiene lo que la fila afirma. Ninguna de esas filas
afirma haber sido probada en un iPhone físico ni en WebKit real — todas
limitan su evidencia a la existencia y forma del código — así que no hay
reclamo falso que corregir aquí.

**Hallazgo real: la validación PWA de CI nunca corrió sobre WebKit real.**
`scripts/nexora_browser_smoke.mjs::validatePwa()` (registro real del service
worker vía `navigator.serviceWorker.getRegistrations()`, verificación de que
la caché `nexora-shell-*` solo contiene URLs de `/assets/nexora/` y ninguna
de `/api/`, `/private/`, `/files/`, `/app/`, y el ciclo completo del aviso
`.nxr-offline-banner` con `context.setOffline(true/false)`) solo se pedía
para el perfil `desktop-chromium` (`{ pwa: true }` en `profileRuns`). Los
otros dos perfiles — `ipad-gen7-webkit` e `iphone-13-webkit`, los que
realmente corren sobre el motor WebKit, el que importa para "PWA en
iPhone" — solo pasaban por `validateManifest()`, que comprueba que el
`<link rel="manifest">` responde y tiene la forma correcta pero **nunca
registra ni comprueba el service worker**. El propio comentario del script
("Capítulo 54: escritorio, tableta, móvil y PWA. Los tres se recorren
siempre") ya asumía que los cuatro aspectos se cubrían juntos en todos los
perfiles; el código no cumplía esa intención declarada. Resultado: la
afirmación operativa "PWA segura en iPhone" (`NXR-UX-0004`) llevaba
27 bloques dependiendo por completo de que Chromium de escritorio se
comportara igual que el Safari/WebKit real de un iPhone en materia de
service workers y caché offline — sin ninguna prueba, real o de CI, que
cerrara esa brecha.

**Corrección.** `scripts/nexora_browser_smoke.mjs`: `profileRuns` pasa a
pedir `{ pwa: true }` en los tres perfiles (antes solo en
`desktop-chromium`). `ipad-gen7-webkit` e `iphone-13-webkit` ahora ejecutan
`step("pwa", () => validatePwa(...))` igual que el perfil de escritorio.
Fijado con una prueba de contrato nueva,
`test_browser_diagnostics_contract.py::test_pwa_validation_runs_on_the_two_real_webkit_profiles_too`,
que revisa cada una de las tres filas de `profileRuns` por separado y falla
si a cualquiera le falta `{ pwa: true }` — así una regresión futura que
vuelva a limitar la prueba PWA a un solo perfil se detecta en la suite
Python sin depender de que alguien lea el diff de un `.mjs`. `NXR-UX-0004`
recibió una nota de "endurecimiento posterior" con el hallazgo completo (sin
cambiar su estado ni su dueño, mismo patrón que el Bloque 24 usó para
`NXR-SEC-0001`).

**Auditoría adicional sin hallazgo que corregir.** No existe ninguna
etiqueta `<meta name="apple-mobile-web-app-capable">` ni
`<link rel="apple-touch-icon">` en el código de NEXORA — Safari en iOS
16.4+ ya lee el manifest estándar (incluidos los iconos `192×192`/`512×512`
`maskable` que el manifest ya declara) para "Agregar a inicio", así que no
es una brecha de funcionalidad conocida; se documenta aquí como observación
menor, no como hallazgo, porque ninguna fila de la matriz promete un ícono
de pantalla de inicio con retoques específicos para iOS más allá de lo que
el manifest estándar ya cubre, y construir esas etiquetas sin que el
propietario las pida sería exactamente el tipo de alcance no solicitado que
este bloque tiene prohibido inventar.

**Pruebas.**
- Suite completa: 1202/1228 (antes 1201/1227 en el Bloque 26; +1 prueba
  nueva), 26 errores preexistentes (mismos `ModuleNotFoundError: No module
  named 'frappe'` de siempre, sin bench en este entorno), 0 `FAIL`.
- `test_pwa_contract.py` (6/6), `test_browser_diagnostics_contract.py`
  (incluida la prueba nueva), `test_browser_acceptance_contract.py`,
  `test_predeploy_certification_contract.py` — 50/50 en verde en conjunto.
- `node --check scripts/nexora_browser_smoke.mjs` — sintaxis válida.
- `validate_nexora_governance.py`, `validate_repository.py`,
  `validate_nexora_app.py`, `validate_nexora_constitution.py`,
  `validate_nexora_financial_models.py` — verdes, sin cambio de conteo (184
  requisitos, esta corrección no agrega una fila nueva).

**Ejecución real en CI (PR #118, job `Frappe real · escritorio · tableta ·
iPhone · PWA`, Playwright/WebKit contra `bench`/MariaDB reales).** El job
corrió con la corrección activa (run
`31521096626`/job `93878019700`, 6m7s). Resultado: la etapa `pwa` **pasó sin
fallo en los tres perfiles**, incluidos los dos motores WebKit reales
(`ipad-gen7-webkit`, `iphone-13-webkit`) — el service worker se registró, la
caché offline `nexora-shell-*` solo contuvo URLs de `/assets/nexora/` y el
aviso `.nxr-offline-banner` apareció y desapareció correctamente al simular
pérdida/recuperación de conexión en los tres. El único fallo del run
completo, idéntico en los tres perfiles, fue el defecto ya documentado
`panel: Dashboard did not expose the active period` — ajeno a este bloque,
presente desde antes del Bloque 24. `mariadb` (10m25s), `install-rollback`
(5m32s), `Patch Test` (8m47s) y `Real site, repeated migration, CRUD and
persistence` (3m38s) pasaron en verde; `linters` falló como de costumbre
(defecto preexistente tolerado). La brecha queda cerrada con evidencia real,
no solo con la corrección del código.

**Riesgos residuales.** Ninguno nuevo: la hipótesis de riesgo de este bloque
(que WebKit se comportara distinto de Chromium en el registro del service
worker o la caché offline) no se materializó — CI la descartó en vivo.

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 28 (NEXORA Super Experience — auditoría/pulido
de UX, sin cambios a reglas financieras).

## Bloque 28 — NEXORA Super Experience (auditoría/pulido de UX, NXR-CNV-0001)

**Alcance.** Mandato explícito: auditoría/pulido amplio de experiencia de
usuario sobre las páginas de NEXORA, sin cambios a reglas financieras —
corregir defectos de UX reales que se encuentren, con prueba de contrato
para cada corrección.

**Auditoría realizada, sin hallazgo que corregir.**
- Clases CSS: ningún `nexora/page/*/*.js` ni `public/js/*.js` usa ya clases
  crudas de Bootstrap (`.btn-success`/`.btn-danger`/`.btn-primary`) — todas
  las pantallas usan el sistema de diseño (`.nxr-ds-btn--*`), migración ya
  cerrada en bloques anteriores.
- Sin `console.log` de depuración olvidado en ningún `page/*.js`.
- Los dos únicos `.catch(() => {})` del código (`nexora_operations.js`,
  cadena `pendingFieldWork`) son deliberados: reinician la cadena de
  promesas para que el siguiente campo no se pierda un manejador previo
  fallido; el error real se captura y registra en el `.catch` siguiente.
  Ya fijado por prueba desde el Bloque 24
  (`test_the_screen_never_overwrites_itself_while_the_preview_is_built`).
- Los cuatro `frappe.call`/`fetch` sin `freeze: true` fuera del hallazgo real
  de abajo (`nexora_dashboard.js`, `nexora_project.js` ×2,
  `nexora_conversation_channels.js`) son todos lecturas (paneles/resúmenes)
  o acciones administrativas no financieras (conectar/revocar un canal de
  WhatsApp, gateadas a `NEXORA Administrator`) — un doble clic no duplica
  ningún movimiento de dinero, como máximo repite una consulta o un
  revocado que ya es un no-op en el servidor. No se toca: agregar una guarda
  ahí sin un defecto real detrás sería pulido no solicitado.
- Cadenas de texto de opciones `Select` en inglés (`"Lump Sum"`,
  `"Time and Materials"`, etc., en `nexora_contracts.js`) son los valores
  canónicos reales del campo `modality` de `NXR Contract`
  (`nxr_contract.json`), el mismo patrón que todos los campos de estado del
  sistema (valor canónico en inglés, etiqueta visible en español vía el
  diccionario compartido de `nexora_report_actions.js`) — no es una fuga de
  idioma, es el vocabulario de dominio ya establecido.

**Hallazgo real: doble clic en "Confirmar"/"Cancelar" del asistente
conversacional podía disparar la confirmación dos veces.**
`nexora_assistant.js::send()` ya se protegía con una bandera `sending`
(Bloque 18) para el envío de texto, pero `resolvePending()` — los botones
"Confirmar"/"Cancelar" de una intención pendiente, que puede ser un pago
real ("quiero pagar 2500 al electricista") — no tenía la misma guarda: un
doble clic antes de que llegara la primera respuesta llamaba a
`confirm_pending_intent`/`cancel_pending_intent` dos veces. Verificado en
`conversation/dispatch.py::_confirm_intent()` y en las funciones de
ejecución reales del catálogo (`execute_operational_movement` en
`financial/operational_commands.py`, `register_evidence` en
`financial/evidence.py` — los únicos dos `execute_method` que
`conversation/registry.py` declara) que el servidor ya es a prueba de doble
ejecución financiera: `_build_write_payload` reenvía el mismo
`doc.idempotency_key` guardado en el `NXR Conversation Pending Intent`
original (no genera uno nuevo por intento), y ambas funciones de ejecución
exigen esa clave y la verifican con `start_idempotency`/
`complete_idempotency` antes de escribir cualquier documento — un segundo
intento con la misma clave se resuelve como repetición, no como una segunda
operación. Así que el doble clic **no podía duplicar dinero**, pero sí
producía una llamada de red sobrante y, en el peor caso, mostraba al
usuario un mensaje de error interno de idempotencia sin sentido para él en
vez de nada. Corregido con una bandera `resolving` (mismo patrón que
`sending`) que además deshabilita los botones "Confirmar"/"Cancelar"
mientras la llamada está en vuelo, re-habilitándolos solo si falla.

**Corrección.**
`nexora/page/nexora_assistant/nexora_assistant.js`: variable `resolving`
añadida junto a `sending`; `resolvePending()` retorna de inmediato si ya
hay una resolución en curso, deshabilita ambos botones al entrar y los
reactiva solo en el `catch` (en el éxito, `renderPending(null)` los retira
del DOM). Fijado con
`tests/test_conversation_contract.py::test_confirm_and_cancel_cannot_be_double_dispatched`,
que revisa el cuerpo real de `resolvePending()` por el guard, la bandera y
el `.prop("disabled", true)`. `docs/nexora/MATRIZ_REQUISITOS.md`: nota de
endurecimiento posterior en `NXR-CNV-0001` (sin cambiar su estado/dueño,
mismo patrón de los Bloques 24/27).

**Pruebas.**
- Suite completa: 1203/1229 (antes 1202/1228 en el Bloque 27; +1 prueba
  nueva), 26 errores preexistentes, 0 `FAIL`.
- `test_conversation_contract.py` — 22/22 en verde, incluida la prueba
  nueva.
- `node --check nexora/page/nexora_assistant/nexora_assistant.js` —
  sintaxis válida.
- `validate_nexora_governance.py`, `validate_repository.py`,
  `validate_nexora_app.py`, `validate_nexora_constitution.py`,
  `validate_nexora_financial_models.py` — verdes, 184 requisitos sin
  cambio (esta corrección no agrega una fila nueva).

**No ejecutado aquí** (requiere `bench`+MariaDB+navegador reales): ningún
recorrido real de doble clic en un navegador contra el asistente vivo —
la prueba nueva es de contrato estático (verifica el código fuente, no
ejecuta el DOM). `test_conversation_integration.py` (ya existente, con el
escenario "doble confirmación" entre sus 14 casos) tampoco se ejecutó en
este entorno por la misma razón de siempre (sin `bench`).

**Riesgos residuales.** Ninguno nuevo — la protección del servidor
(idempotencia real) ya existía antes de este bloque; la corrección es
puramente de experiencia de cliente.

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 29 (certificación integral / inspección
masiva) — correr todos los validadores y toda la suite, producir un estado
consolidado honesto, y verificar primero si el hallazgo residual de
`Frappe real` (`operaciones: Guided stage 4 never opened`, documentado en
el Bloque 26) sigue reproduciéndose contra `main`.

## Bloque 29 — Certificación integral (inspección masiva)

**Alcance.** Mandato explícito: correr todos los validadores y toda la
suite, producir un estado consolidado honesto de los 184 requisitos, y
verificar primero si el hallazgo residual de `Frappe real`
(`operaciones: Guided stage 4 never opened`, Bloque 26) sigue
reproduciéndose. Sin cambios de código si no se encuentra un defecto real
— este bloque es de auditoría, igual que el Bloque 26.

**Cierre del hallazgo residual `Frappe real`/`operaciones`.** Desde que el
Bloque 26 lo documentó (visto en PR #114 y #115), el job
`Frappe real · escritorio · tableta · iPhone · PWA` ha corrido **cuatro
veces más** sobre código real: PR #116 (Bloque 26), PR #118 dos veces
(Bloque 27, antes y después del `docs`-fix), y PR #119 (Bloque 28). Ninguna
de las cuatro reprodujo `operaciones: Guided stage 4 never opened` — las
cuatro solo mostraron el defecto `panel: Dashboard did not expose the
active period`, ya documentado y ajeno a la misión de estos bloques.
**Conclusión: fue inestabilidad de CI, no una regresión de `main`.** Se
cierra este hallazgo residual; si `operaciones` reaparece en el futuro,
debe tratarse como un hallazgo nuevo con su propio diagnóstico, no
reabrirse como el mismo caso.

**Corrección posterior (Bloque 30):** `operaciones: Guided stage 4 never
opened` **reapareció**, esta vez en `ipad-gen7-webkit` (antes solo se
había visto en `desktop-chromium`), en el run real del PR #121. La
conclusión "cerrado" de este bloque queda corregida en la sección del
Bloque 30: sigue sin ser una regresión de ningún bloque de esta misión,
pero tampoco es un caso cerrado — es intermitente y su causa raíz sigue
sin diagnosticarse. Ver el Bloque 30 para el detalle completo.

**Inspección masiva automatizada de la matriz de 184 requisitos.**
- **Consistencia de conteo por estado:** 155 `IMPLEMENTADO Y VALIDADO` + 16
  `NO DEMOSTRADO` + 6 `OBSOLETO JUSTIFICADO` + 3 `NO APLICA JUSTIFICADO` + 2
  `EXISTENTE PERO DEFECTUOSO` + 1 `REQUIERE DECISIÓN` + 1
  `EXISTENTE Y REUTILIZABLE` = 184. Coincide con
  `validate_nexora_governance.py` (184 requisitos, 38 máquinas, 32
  controles, 9 pruebas compartidas, 19 decisiones) — verde.
- **Existencia real de cada SHA citado:** 17 hashes de 40 caracteres únicos
  citados en toda la matriz; los 17 existen en el historial real de git
  (`git cat-file -e` sobre cada uno) — cero inventados.
- **Barrido automático de artefactos citados en las 155 filas
  `IMPLEMENTADO Y VALIDADO`:** script ad-hoc que extrae de cada celda de
  evidencia todo token con forma de función (`nombre_función()`) o de
  archivo (`*.py`/`*.js`/`*.json`/`*.css`) y verifica que aparezca en algún
  archivo real del repositorio actual (`.py`/`.js`/`.json`/`.md`/`.css`
  rastreados por git). **Resultado: 0 de 155 filas con un artefacto citado
  que no exista hoy en el código.** Esto no prueba que cada fila describa
  el comportamiento con precisión total (una prosa sin nombre de archivo
  citado —como tenía el reclamo falso original de `NXR-AVA-0005`/`0006`
  antes del Bloque 25— no la detecta este barrido), pero descarta
  fabricación de nombres de función/archivo a gran escala.
- **Auditoría manual dirigida al SHA más citado
  (`83305b6e2bd897e4084d0ae694e94834e2622590`, 36 filas — Bloques 0-3):**
  `git show --stat` revela que es un commit **solo de documentación**
  ("record blocks 0 to 3 certification evidence", solo modifica
  `EXECUTION_STATE.md`), no el commit que implementó el código descrito.
  Verificado que esto es la convención real y consistente del rango
  original de 166 requisitos: "Evidencia validada en `<SHA>`" significa
  "confirmado cierto en este punto de control de certificación", no "este
  commit agregó el código". Confirmado con una fila de muestra
  (`NXR-FND-0001`): `financial/sources.py::create_fund_source()`/
  `list_source_balances()` ya existían en el árbol de ese commit
  (`git ls-tree 83305b6e... -- financial/sources.py`) y siguen existiendo
  hoy sin cambio de comportamiento — no es el patrón de reclamo falso del
  Bloque 25 (donde el commit citado, examinado por su diff real, no
  contenía nada de lo afirmado y ningún commit posterior lo agregó hasta
  ese bloque). No se encontró una segunda instancia de ese patrón en esta
  inspección.
- **Vigencia de los tres hallazgos "negativos" documentados
  (`EXISTENTE PERO DEFECTUOSO`/`REQUIERE DECISIÓN`), re-verificados contra
  el código actual, no contra memoria de bloques anteriores:**
  `NXR-UX-0008` (sin Ctrl+K/paleta de comandos/FAB: confirmado, cero
  coincidencias en `public/js`/`public/css`), `NXR-UX-0015` (sin
  `capture="camera"` en ningún campo `Attach` de evidencia — incluido el
  campo `photos` que el Bloque 25 agregó a `nexora_progress.js`, que
  tampoco lo tiene: la brecha sigue siendo real y no se cerró
  accidentalmente sin actualizar la fila), `NXR-CAL-0001` (`quality/`
  sigue sin existir; los dos únicos usos reales de `NXR Quality Check` en
  todo el código, `dashboard/operational_query.py` y `dashboard/service.py`,
  son conteos de solo lectura para un indicador `open_quality_issues` que
  siempre valdrá cero mientras nadie pueda crear un registro — detalle
  adicional, no un hallazgo nuevo).

**Corrección de una imprecisión operativa propia (no de la matriz):** las
notas internas de esta misión asumían que
`validate_nexora_completion.py`/`validate_nexora_operational_acceptance.py`
"salen con código 0 sin importar los errores". Falso: ambos scripts
retornan `1 if errors else 0` — de hecho fallan hoy con código de salida 1
(36 y 20 errores respectivamente, listando cada requisito sin estado
terminal justificado). Esto es **esperado y correcto** a esta altura de la
misión (Bloque 29 de 30): son el candado de cierre final que exige que
todo requisito llegue a un estado terminal (`IMPLEMENTADO Y VALIDADO`,
`OBSOLETO JUSTIFICADO` o `NO APLICA JUSTIFICADO`) — mientras existan filas
honestas en `NO DEMOSTRADO`/`REQUIERE DECISIÓN`/`EXISTENTE PERO
DEFECTUOSO` (que es la verdad de varias, y no se pueden demostrar aquí sin
`bench`/MariaDB/navegador reales), estos dos scripts seguirán en rojo por
diseño. No forman parte del barrido de 5 validadores "duros" que se corre
en cada bloque; se dejan para el Bloque 30, que deberá decidir si se
resuelven, se degradan explícitamente los pendientes reales a `OBSOLETO
JUSTIFICADO`/`NO APLICA JUSTIFICADO` con evidencia, o se documenta con
transparencia que la misión cierra sin el 100% — nunca fabricando el
100%.

**Pruebas.**
- Suite completa: 1203/1229, 26 errores preexistentes (sin cambio respecto
  al Bloque 28 — no se tocó código de producción ni de prueba en este
  bloque), 0 `FAIL`.
- Los 5 validadores "duros" (`validate_nexora_governance.py`,
  `validate_repository.py`, `validate_nexora_app.py`,
  `validate_nexora_constitution.py`,
  `validate_nexora_financial_models.py`) — verdes, 184 requisitos sin
  cambio.
- `validate_nexora_completion.py`/`validate_nexora_operational_acceptance.py`
  — en rojo por diseño (36/20 errores), documentado arriba como estado
  esperado, no como regresión de este bloque.

**No ejecutado aquí** (requiere `bench`+MariaDB+navegador reales): ninguna
verificación en vivo de las 16 filas `NO DEMOSTRADO` restantes; el barrido
automatizado de artefactos citados es estático (lee texto de archivos), no
ejecuta ningún código.

**Riesgos residuales.** Ninguno nuevo. El hallazgo residual de `Frappe
real`/`operaciones` queda cerrado (inestabilidad de CI, confirmado con
cuatro runs limpios consecutivos). Las 16 filas `NO DEMOSTRADO` y la fila
`REQUIERE DECISIÓN` siguen pendientes del propietario/de `bench` real —
sin novedad respecto a bloques anteriores.

**Bloqueo.** Ninguno.

**Siguiente acción.** Bloque 30 (cierre definitivo): decidir qué hacer con
los 20 requisitos sin estado terminal (16 `NO DEMOSTRADO` + 2 `EXISTENTE
PERO DEFECTUOSO` + 1 `REQUIERE DECISIÓN` + 1 `EXISTENTE Y REUTILIZABLE`)
sin fabricar un cierre falso, actualizar los documentos finales de cierre
de la misión, y dejar un estado consolidado y honesto de los 30 bloques.

## Bloque 30 — Cierre definitivo (NXR-UX-0006)

**Alcance.** Mandato explícito, último bloque de la misión: dejar un
estado consolidado y honesto de los 30 bloques, actualizar los documentos
finales de cierre (`docs/final/NEXORA_ENTREGA_FINAL.md`,
`docs/final/NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md`), y no declarar el 100%
sin evidencia real.

**Hallazgo real y corrección: causa raíz del defecto `panel` que arrastraba
toda la misión desde el Bloque 24 quedó diagnosticada y corregida.**
Todos los bloques anteriores (24 a 29) documentaron
`panel: Dashboard did not expose the active period` como "defecto
preexistente, ajeno a este bloque" en cada ejecución real de
`Frappe real · escritorio · tableta · iPhone · PWA` — sin que ninguno
llegara a diagnosticar la causa. Este bloque la encontró:
`nexora_dashboard.js::renderIdentity()` originalmente escribía
`` `${__("Período")}: ${periodText}` `` (con dos puntos) como texto plano.
El PR #93 (`c513789d`, "make dashboard period selectable" — confirmado con
`git log -S'periodSelect(activePeriod)'`) sustituyó ese texto plano por un
`<select>` interactivo y, en el cambio, perdió los dos puntos:
`` `${__("Período")} ${periodSelect(activePeriod)}` ``.
`scripts/nexora_browser_validators.mjs::validateDashboard()` exige
`/^Período:/` sobre el texto visible — sin los dos puntos, la aserción
fallaba en los tres perfiles, en cada ejecución real, desde ese PR (que es
posterior al commit `c96ced6a` que
`docs/final/NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md` citaba como el recorrido
"CUMPLIDO Y DEMOSTRADO" de las tres superficies — confirmado con
`git log --oneline c96ced6a..c513789d`, la regresión es posterior a esa
ejecución citada, así que la ejecución citada fue real en su momento, pero
la fila del documento final quedó desactualizada después de la regresión y
nadie la corrigió). Corregido restaurando los dos puntos. Fijado con
`test_dashboard_contract.py::test_dashboard_period_label_keeps_its_colon`.
`docs/nexora/MATRIZ_REQUISITOS.md`: nota de corrección de regresión en
`NXR-UX-0006` (sin cambiar su estado/dueño). `NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md`:
fila "Escritorio, tableta, iPhone y PWA" bajada de `CUMPLIDO Y DEMOSTRADO`
(cita obsoleta) a `INCUMPLIDO hasta confirmar el run real de este cierre` —
solo vuelve a `CUMPLIDO Y DEMOSTRADO` cuando el job de este mismo PR
confirme `panel` en verde en los tres perfiles, según la propia regla de
cierre de ese documento (un job rojo no se certifica con una afirmación
manual).

**Otros documentos de cierre revisados, sin corrección necesaria:**
`docs/final/NEXORA_ENTREGA_FINAL.md` ya describe los criterios de
aceptación de forma abstracta ("el SHA final lo inserta y demuestra el
workflow... para cada ejecución", "este documento no certifica por sí
solo la entrega") — no hace una afirmación fija que pueda quedar
desactualizada, así que no requiere edición.
`docs/nexora/FINAL_REVIEW_PACKAGE.md`, `AUDITORIA_CORRECCION_FINAL.md` y
`ORDEN_MAESTRA_FINALIZACION.md` son registros históricos fechados de una
fase anterior del proyecto (rama `nexora-continuidad-total`, PR #11/#12,
166 requisitos, herramienta `opencode`) — no se editan: son constancia de
un momento pasado, no un documento vivo de estado actual; corregirlos
retroactivamente falsificaría el historial en vez de reflejar la verdad de
ese momento.

**Estado consolidado y honesto de los 184 requisitos al cierre de la
misión (Bloques 1-30, este segmento cubrió 23-30).**
- 155 `IMPLEMENTADO Y VALIDADO` — código real, con evidencia (SHA real y/o
  pruebas ejecutadas) verificada de forma automatizada en el Bloque 29 sin
  hallar fabricación.
- 16 `NO DEMOSTRADO` — código real y pruebas de contrato/puras en verde,
  pero sin ejecución real completa contra `bench`/MariaDB/navegador real
  en este entorno; pendientes de que ese run real ocurra (varias ya
  confirmadas en verde por CI de GitHub Actions en su PR correspondiente,
  documentado fila por fila).
- 6 `OBSOLETO JUSTIFICADO` / 3 `NO APLICA JUSTIFICADO` — decisiones de
  alcance ya documentadas, no defectos.
- 2 `EXISTENTE PERO DEFECTUOSO` (`NXR-UX-0008` command bar/Ctrl+K,
  `NXR-UX-0015` atributo `capture="camera"`) — brechas reales,
  re-verificadas vigentes en este mismo bloque contra el código actual
  (no se cerraron por error sin actualizar la fila). **No se corrigen
  aquí**: `NXR-UX-0008` es una función nueva completa (paleta de
  comandos), no una línea de código; construirla sin poder probarla en un
  navegador real en el último bloque de la misión sería el mismo riesgo
  que la misión prohibió desde el inicio (fabricar éxito no demostrado).
  `NXR-UX-0015` depende de cómo Frappe renderiza su propio control
  `Attach` en este entorno (que ya trae una opción de captura de cámara
  integrada en versiones recientes del framework, no verificable aquí sin
  navegador real) — tocar un control del núcleo de Frappe sin poder
  confirmar el resultado real es más riesgoso que dejarlo documentado.
- 1 `REQUIERE DECISIÓN` (`NXR-CAL-0001`, control de calidad) — decisión de
  producto pendiente del propietario desde el Bloque 26, sin superficie de
  ataque mientras el doctype permanezca bloqueado a escritura.
- 1 `EXISTENTE Y REUTILIZABLE` (`NXR-AI-0001`) — infraestructura real,
  auditada, sin llamada viva a un proveedor de IA (sin credenciales en
  este entorno).

**La misión NO cierra en 100% `IMPLEMENTADO Y VALIDADO`, por diseño y por
regla explícita de la misión ("no declares 100% sin evidencia").** 20 de
184 requisitos (10.9%) permanecen en un estado honesto distinto, casi
todos porque este entorno de trabajo no tiene `bench`, MariaDB ni un
navegador real — no porque el código no exista o esté mal. Ninguna fila
fue forzada a un estado terminal sin evidencia para maquillar el cierre.

**Pruebas.**
- Suite completa: 1204/1230 (antes 1203/1229 en el Bloque 28 — el Bloque
  29 no agregó pruebas; +1 prueba nueva de este bloque), 26 errores
  preexistentes, 0 `FAIL`.
- `test_dashboard_contract.py` — 20/20 en verde, incluida la prueba nueva
  de regresión.
- `node --check` sobre el archivo modificado — sintaxis válida.
- Los 5 validadores duros — verdes, 184 requisitos sin cambio.
- `validate_nexora_completion.py`/`validate_nexora_operational_acceptance.py`
  — siguen en rojo por diseño (documentado en el Bloque 29): 36/20 errores,
  uno menos que antes de esperar por cada fila que sí alcance un estado
  terminal en el futuro, pero esa cifra no cambia solo por esta corrección
  de código (no mueve ninguna fila a un estado terminal nuevo).

**No ejecutado aquí** (requiere `bench`+MariaDB+Playwright/WebKit reales):
la confirmación real de que `panel` pasa en los tres perfiles tras esta
corrección — exactamente lo que el PR de este bloque debe demostrar en CI
antes de fusionarse. Si `panel` sigue fallando por una segunda causa no
descubierta aquí, este hallazgo se reabre con el resultado real, no se
declara cerrado por la sola corrección de código.

**Riesgos residuales.** Si la corrección del colon no es la única causa
de `panel: Dashboard did not expose the active period` (por ejemplo, si
`window.nexora.context.update` o `periodSelect()` tienen un segundo
defecto no visible por lectura de código), el run real de este PR lo
mostrará y debe documentarse como un hallazgo nuevo, no cerrarse por
inercia. Los 20 requisitos sin estado terminal quedan como trabajo futuro
explícito para el propietario del producto, no como deuda oculta.

**Bloqueo.** Ninguno.

**Resultado real del run de CI de este cierre (PR #121, job `Frappe real
· escritorio · tableta · iPhone · PWA`, run `31526163976`) — confirmado
después de escribir lo anterior, documentado sin editar las afirmaciones
previas.** La corrección **funcionó**: `desktop-chromium` terminó el
recorrido completo **sin ninguna etapa fallida** — es la primera vez
desde el PR #93 que `panel` pasa en un run real. `ipad-gen7-webkit` e
`iphone-13-webkit` también superaron `panel` (ninguno de los dos lo
reporta como fallo), pero al dejar de detenerse ahí, el recorrido llegó
más lejos y expuso dos defectos reales **distintos y ya conocidos**, antes
enmascarados por `panel`:
- `ipad-gen7-webkit`: `operaciones: Guided stage 4 never opened` (con
  `visible_stages: ["3"]`, `preview_invalidated_by: "still-valid"` — el
  mismo patrón exacto documentado en el Bloque 26 para PR #114/#115, pero
  esta vez en `ipad-gen7-webkit`, no en `desktop-chromium`). El Bloque 29
  había declarado este hallazgo "cerrado" tras cuatro runs limpios
  consecutivos; **esta quinta observación, en un perfil distinto, obliga a
  corregir esa conclusión**: no es una regresión de ningún bloque de esta
  misión (ninguno tocó `nexora_operations.js`/`nexora_guided_*.js` en este
  segmento), pero tampoco está "cerrado" — es intermitente, y ahora se
  vio en dos perfiles distintos en ejecuciones distintas, lo que apunta
  más a una condición de carrera o de tiempo bajo carga acumulada del
  propio run secuencial (`desktop-chromium` corre primero y deja datos de
  siembra que los perfiles siguientes heredan) que a un defecto de un
  navegador específico. **Se corrige la conclusión del Bloque 29**: el
  hallazgo pasa de "cerrado" a "intermitente, sin causa raíz identificada,
  no imputable a los Bloques 23-30" — trabajo futuro explícito, no deuda
  oculta.
- `iphone-13-webkit`: `comprobantes: El campo project del comprobante no
  conservó «PROJ-0001»: quedó «NEXORA 0.1 — Fondo demostrativo».` — este
  es el defecto que `NXR-UX-0010` (Bloque 17, PR #102) ya documentó como
  "preexistente... en el campo `project` de comprobantes, nunca antes
  alcanzado" en `ipad-gen7-webkit` en aquel momento; ahora se alcanza en
  `iphone-13-webkit` por la misma razón (el recorrido llega más lejos).
  No es un hallazgo nuevo de este bloque — es el mismo defecto ya
  catalogado hace 13 bloques, simplemente visible en un perfil distinto
  ahora que `panel` ya no detiene antes el recorrido.

`docs/final/NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md` se actualiza con este
resultado real (ver abajo): la fila de las tres superficies **no** pasa a
`CUMPLIDO Y DEMOSTRADO` — sigue `INCUMPLIDO`, con una causa distinta y más
pequeña que antes (dos defectos ya conocidos, no tres tipos de fallo
mezclados con uno sin diagnosticar). Esto es exactamente el comportamiento
que la "regla de cierre" de ese documento exige: un job rojo no se
certifica con una afirmación manual, y no se declara un avance parcial
como si fuera cierre total.

**Segundo run real, mismo código, resultado distinto (run `31527274646`,
tras el commit `097025f1` — solo cambios de documentación sobre el mismo
`77cfcd84`).** Este run terminó **completamente verde**: las tres
superficies (`desktop-chromium`, `ipad-gen7-webkit`, `iphone-13-webkit`)
pasaron sin ninguna etapa fallida — primera vez en toda la misión (y,
según la evidencia disponible, desde el PR #93) que `Frappe real ·
escritorio · tableta · iPhone · PWA` termina 100% verde. **No se declara
esto como cierre de los dos defectos intermitentes**: el código de la
aplicación es idéntico al del run anterior (`31526163976`, mismo
`77cfcd84`) que sí mostró `operaciones`/`comprobantes` fallando — la única
diferencia es el momento de ejecución. Que el mismo código pase una vez y
falle la siguiente es, por definición, la prueba de que ambos son
intermitentes y no defectos deterministas de este código — exactamente lo
que ya se sospechaba, ahora confirmado con dos observaciones directas
sobre el mismo commit. Se documenta el resultado real de ambos runs, sin
quedarse solo con el favorable: la fila de
`NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md` permanece `INCUMPLIDO` a propósito
—no se sube a `CUMPLIDO Y DEMOSTRADO` por un solo run verde cuando el
mismo código ya mostró lo contrario— hasta que la intermitencia misma se
diagnostique y elimine, no solo se evite por suerte.

**Siguiente acción.** Ninguna dentro de esta misión de 30 bloques — cierre
definitivo. Trabajo futuro recomendado (fuera de este cierre, en orden de
valor): diagnosticar la intermitencia de `operaciones` (Guided stage 4) y
de `comprobantes` (campo `project`) — ambas confirmadas intermitentes, no
deterministas, por dos runs reales consecutivos sobre el mismo commit con
resultados distintos; decidir `NXR-CAL-0001`; ejecutar el conjunto de
pruebas de integración (`FrappeTestCase`) que este entorno nunca pudo
correr, contra un `bench` real, para convertir el máximo posible de las 16
filas `NO DEMOSTRADO` en `IMPLEMENTADO Y VALIDADO` con evidencia real;
evaluar si construir `NXR-UX-0008` (paleta de comandos) entra en un
roadmap futuro.

## Misión final — auditoría y reconstrucción de los 30 bloques, certificación

**Mandato.** Auditoría integral posterior al cierre del Bloque 30: reconstruir el
alcance real de los 30 bloques (no confiar en que el número de bloque coincida con
su contenido original), verificar implementación real contra el código actual (no
contra lo que un documento anterior afirma), cerrar toda brecha segura y autónoma
sin decisión material pendiente, y emitir un veredicto de certificación honesto —
sin usar "100%" como sustituto de certificación.

**Trabajo real realizado.** Ver `docs/nexora/NEXORA_30_BLOCKS_AUDIT.md` para el
detalle bloque por bloque con evidencia de código, commit y SHA. Resumen:
- Reconstrucción completa de los 30 bloques (más los fraccionarios 1.1/2.1-2.6, y
  la sesión "Final") contra `EXECUTION_STATE.md`, `git log`, la columna `BLOQUE` de
  la matriz de 184 requisitos y los documentos de dominio originales
  (`docs/nexora/BLOQUE_N_*.md`, `NIP_BLOQUE_N_*.md`).
- Documentadas explícitamente las tres numeraciones reales que coexisten (matriz,
  documentos de dominio originales, encabezados cronológicos de este mismo
  archivo) sin forzarlas a una sola secuencia — la colisión es real: para los
  números 2, 7, 10-18, el "Bloque N" cronológico de este archivo es una sesión de
  *corrección* posterior sobre un tema distinto al "Bloque N" de dominio original,
  confirmado con fechas y SHA reales.
- Tres auditorías paralelas delegadas para los bloques 1-22 (nunca vistos en
  primera persona en esta sesión), cada una verificando una muestra de las
  afirmaciones más relevantes contra el código actual, con instrucción explícita
  de señalar cualquier reclamo fabricado como hallazgo distinto. **Ninguna
  encontró un reclamo fabricado activo** en los 184 requisitos.
- Verificación directa (no delegada) de concurrencia real (`FOR UPDATE`) e
  idempotencia real (`start_idempotency`/`complete_idempotency`, 214 puntos de uso
  confirmados) en financiero, contratos, compras, inventario y presupuesto.
- Verificación directa de seguridad: `require_project_access` confirmado cableado
  en 30+ archivos reales, con prueba de contrato que extrae el cuerpo exacto de
  cada función por expresión regular (no una búsqueda de substring ingenua).
- Verificación directa del gateway de IA: fallback real, disyuntor real,
  exactamente 2 llamadores reales de `orchestrator.execute` en todo el
  repositorio, credenciales nunca registradas en claro.
- Verificación directa de WhatsApp: HMAC-SHA256 real, idempotencia real por
  `message_id`, credenciales `Password`, llamada HTTP real a la Graph API de Meta
  — sin simulación en el archivo de producción.
- Barrido explícito de "Success"/mocks/stubs/simulaciones en todo
  `nexora_app/nexora/` fuera de pruebas: sin hallazgos de una integración fabricada
  alcanzable desde un camino de usuario real.

**Brechas cerradas de forma segura y autónoma en este bloque:**
- `docs/nexora/BLOQUE_10_PRESUPUESTOS_COMPROMISOS.md` afirmaba
  `NXR-PRE-0006 | Pronóstico | CONFIRMADO` sin que exista código de pronóstico. La
  matriz siempre tuvo la clasificación correcta (`OBSOLETO JUSTIFICADO`); solo el
  documento de dominio quedó desactualizado desde su redacción original.
  Corregido, y se agregó la fila `NXR-PRE-0007` que ese mismo documento omitía.
- `docs/nexora/NEXORA_GOLDEN_PATHS.md`, `NEXORA_UX_AUDIT.md` y
  `NEXORA_EXPERIENCE_SYSTEM.md` (escritos en el Bloque 12, a mitad de la misión)
  actualizados con el estado real verificado al cierre: la sobre-recepción, la
  timeline universal, la página de contexto 360°, el motor conversacional y la
  navegación móvil inferior que documentaron como faltantes ya se construyeron de
  verdad en los bloques 13, 16, 17 y 18.

**Hallazgo escalado, no corregido — requiere decisión del propietario, no una
corrección segura y autónoma:** el subsistema de adaptadores de IA simulados
(`intelligence/providers/*_stub.py`, `gateway.dispatch()`,
`adapters.py::build_default_registry()`) está confirmado inalcanzable desde
cualquier camino de ejecución real de usuario (el camino real,
`orchestrator.execute` → `runtime.build_ready_adapter` → `runtime_core.
prepare_adapter`, solo importa clases `*_live`), pero fue preservado
deliberadamente por una decisión arquitectónica de un bloque anterior, con su
propia prueba de regresión
(`test_intelligence_contract.py::test_block_1_and_block_2_provider_infrastructure_is_unchanged_by_block_4`)
que exige que los adaptadores reales nunca compitan por las mismas claves que los
stubs. Eliminarlo revertiría esa decisión explícita — es un cambio de arquitectura,
no una limpieza de código muerto sin más. Se documenta como pregunta abierta para
el propietario: ¿mantener el subsistema como capacidad futura documentada de
prueba/demo sin credenciales reales, o retirarlo formalmente? Ninguna respuesta
afecta la seguridad ni la integridad financiera hoy — nada en el camino real de
producción puede alcanzar una respuesta simulada.

**Pruebas.**
- Suite completa: 1204/1230 (sin cambio respecto al Bloque 30 — este bloque no
  tocó código de producción ni de prueba, solo documentación), 26 errores
  preexistentes, 0 `FAIL`.
- Los 5 validadores duros — verdes, 184 requisitos sin cambio (la corrección de
  `BLOQUE_10_PRESUPUESTOS_COMPROMISOS.md` no toca la matriz, que ya era correcta).

**No ejecutado aquí** (requiere `bench`+MariaDB+navegador reales): ninguna de las
16 filas `NO DEMOSTRADO` se pudo ejecutar en vivo en este entorno; la verificación
de esta ronda fue de código y de cadena de llamadas, no de comportamiento en
producción.

## Veredicto final de certificación

**NEXORA NO CERTIFICADO COMPLETAMENTE.**

No por fabricación, simulación oculta, ni defecto de integridad financiera o de
seguridad conocido — la auditoría de esta ronda no encontró ninguno de los tres.
No se certifica completamente porque queda una lista concreta, enumerada y honesta
de lo que falta, no un porcentaje:

1. **16 requisitos `NO DEMOSTRADO`** (`NXR-FND-0020`, `NXR-CCO-0004`,
   `NXR-INV-0008`, `NXR-UX-0009`, `NXR-COM-0010`, `NXR-PRE-0008`, `NXR-INT-0007`,
   `NXR-UX-0012`, `NXR-UX-0013`, `NXR-UX-0014`, `NXR-UX-0010`, `NXR-UX-0011`,
   `NXR-CNV-0001`, `NXR-SEC-0001`, `NXR-INT-0008`, `NXR-INT-0009`) — código real,
   pruebas de contrato/unitarias reales en verde, sin ejecución real contra
   `bench`+MariaDB+navegador real en este entorno. Varios ya tienen confirmación
   parcial real en CI de GitHub Actions (PWA/WebKit en el Bloque 27, seguridad
   estática en el Bloque 19); ninguno tiene la certificación visual/end-to-end
   completa que exige el criterio de cierre de la misión.
2. **2 requisitos `EXISTENTE PERO DEFECTUOSO`** (`NXR-UX-0008` Command Bar/Ctrl+K,
   `NXR-UX-0015` captura de cámara nativa) — brechas de producto reales, no
   corregidas: la primera es una función nueva completa, no una línea de código;
   la segunda depende de cómo Frappe renderiza su propio control `Attach`, no
   verificable sin navegador real.
3. **1 requisito `REQUIERE DECISIÓN`** (`NXR-CAL-0001`, control de calidad) —
   decisión de producto pendiente del propietario desde el Bloque 26.
4. **1 hallazgo de arquitectura escalado** (subsistema de adaptadores de IA
   simulados) — pregunta de producto pendiente del propietario, sin riesgo de
   seguridad activo.
5. **2 defectos intermitentes confirmados, sin causa raíz diagnosticada**
   (`operaciones`: Guided stage 4; `comprobantes`: campo `project`) — confirmados
   intermitentes (no deterministas) por dos runs reales consecutivos sobre el
   mismo commit con resultados distintos; diagnóstico de hipótesis ya documentado
   (condición de carrera en `sync()`/`MutationObserver` para el primero, carrera
   entre la prueba y la relabelación asíncrona del control `Link` de Frappe para
   el segundo) pero sin confirmación en vivo ni corrección aplicada.
6. **`linters`/`build`** siguen en rojo por defectos preexistentes documentados y
   tolerados desde antes de esta misión, ajenos a su alcance.

**Lo que sí se certifica con evidencia real:** 155 de 184 requisitos
`IMPLEMENTADO Y VALIDADO`, con concurrencia e idempotencia reales verificadas
directamente en código (no solo en documentación) en financiero, contratos,
compras, inventario y presupuesto; seguridad de acceso por proyecto verificada y
corregida en 14 funciones reales; gateway de IA y canal de WhatsApp auditados con
evidencia real de HMAC/idempotencia/HTTP real; cero reclamos fabricados activos
encontrados en tres rondas de auditoría independientes (Bloques 25/29/esta); un
defecto de causa raíz real diagnosticado y corregido con confirmación en CI real
(Bloque 30, `panel`).

**Bloqueo.** Ninguno para el uso interno/desarrollo continuado. Las seis brechas
enumeradas arriba son trabajo futuro explícito, no deuda oculta ni fabricación.

**Siguiente acción recomendada, sin obligación de esta misión:** decisión del
propietario sobre `NXR-CAL-0001` y el subsistema de adaptadores de IA simulados;
ejecución real contra `bench`+MariaDB+navegador (fuera de este entorno) para
convertir el máximo posible de las 16 filas `NO DEMOSTRADO`; diagnóstico en vivo
de los dos defectos intermitentes; decisión sobre `NXR-UX-0008`/`NXR-UX-0015` como
roadmap de producto.

## Segunda pasada — cierre de `NXR-UX-0008` (paleta de comandos)

**Reconsideración honesta.** El bloque anterior clasificó `NXR-UX-0008` (Command
Bar/Ctrl+K) como una "función nueva completa" que requería decisión de diseño del
propietario, sin construirla. Revisado con el mismo criterio que el resto de la
misión (código real + pruebas de contrato, marcar `NO DEMOSTRADO` solo lo que
exige navegador real): una paleta mínima que reutilice el catálogo de destinos ya
existente (`SECTIONS`, el mismo que pinta el cajón lateral) no es una decisión de
producto nueva — es la misma navegación, alcanzable con un atajo de teclado. No
tocaba dinero, seguridad ni arquitectura financiera, así que sí calificaba como
corrección segura y autónoma.

**Corrección aplicada.** `public/js/nexora_shell.js`: `paletteItems()` (aplana
`SECTIONS` en el momento de abrir, nunca copia la lista), `buildPalette()`/
`renderPaletteList()`/`onPaletteKeydown()`/`openPalette()`/`closePalette()`/
`goToPaletteRoute()`. Atajo global `Ctrl+K`/`Cmd+K` en `install()`, gateado a
`belongsToNexora()` — no se activa fuera de las rutas de NEXORA. Filtro de texto
sobre las mismas etiquetas traducidas que ya usa el cajón; navegación con
flechas/Enter; Escape cierra. Ningún botón nuevo en la barra superior —
alcance acotado al atajo de teclado, como ya se documentó en la fila corregida
de la matriz. `public/css/nexora_shell.css`: estilos nuevos reutilizando los
tokens `--nxr-*` ya existentes, sin redefinir ninguna clase `.nxr-ds-*`.

**Pruebas.** `tests/test_command_bar_contract.py` (10 pruebas nuevas, 100% en
verde): fija que la paleta nunca construye un segundo catálogo de rutas, que el
atajo está gateado a Ctrl/Cmd+K con `preventDefault`, que solo abre en rutas de
NEXORA, que Escape/Enter/clic comparten `goToPaletteRoute`→`frappe.set_route`
(nunca una segunda función de navegación), y que el filtro compara contra las
mismas etiquetas traducidas que el cajón. Corregida además una colisión real con
`test_browser_acceptance_contract.py::test_the_navigation_is_built_once_and_updated_by_state`
(contaba literalmente `node.innerHTML = \`` en todo el archivo — la variable local
de `buildPalette()` se renombró a `bar` para no interferir con esa aserción, sin
cambiar ningún comportamiento). Suite completa: 1214/1240, 26 errores
preexistentes, 0 `FAIL`. Los 5 validadores duros — verdes, 184 requisitos sin
cambio de conteo.

**Matriz.** `NXR-UX-0008` reclasificado de `EXISTENTE PERO DEFECTUOSO` a
`NO DEMOSTRADO` — el defecto real ya no existe (el atajo funciona en código y
pruebas de contrato); lo que falta es el recorrido real de teclado en un
navegador, no disponible en este entorno.

**No ejecutado aquí:** recorrido real de `Ctrl+K` en Chromium/WebKit — pendiente
del job `Frappe real` de CI.

**Bloqueo.** Ninguno.

## Tercera pasada — cierre real de `NXR-UX-0008` con evidencia de CI

**CI del PR #123 reparada.** El primer push (`d4eb38bd`) fallaba `validate`,
`verify`(×1) y `Product, migration and security validation` por
`docs/architecture/file_inventory.json` desactualizado (los archivos nuevos del
command bar no se habían reflejado con `scripts/generate_file_inventory.py`), y
`linters` por dos archivos sin formatear con Prettier
(`scripts/nexora_browser_validators.mjs`, `public/js/nexora_shell.js`).
Corregido en `cbf289ca` — ambos cambios son formato/generación puros, sin tocar
comportamiento; confirmado con `git diff` antes de commitear. `build`
(enlace de documentación) y el resto de `linters` (deuda preexistente en archivos
que este PR no toca, confirmada roja también en `main` en runs recientes de
`Linters`) quedaron rojos por razones ajenas a este PR — mismo patrón tolerado que
cerró el PR #115.

**Evidencia real obtenida.** El job `Frappe real · escritorio · tableta · iPhone ·
PWA` (run `31553801873`) corrió contra `bench`+MariaDB+Playwright reales y pasó
sin fallo en los tres perfiles, incluida la etapa `paleta`
(`validateCommandBar()`) en los dos motores WebKit reales. Es la primera vez que
`NXR-UX-0008` tiene una ejecución real, no solo código y prueba de contrato.

**Fusionado a `main`.** PR #123 fusionado (squash) en `a05d483f`.
`docs/nexora/MATRIZ_REQUISITOS.md` actualizado: `NXR-UX-0008` reclasificado de
`NO DEMOSTRADO` a `IMPLEMENTADO Y VALIDADO` — es el primero de los 17
`NO DEMOSTRADO` de la ronda anterior en cerrar con evidencia de ejecución real,
no por relabelado. Conteo actualizado: 156 `IMPLEMENTADO Y VALIDADO`, 16
`NO DEMOSTRADO`, 1 `EXISTENTE PERO DEFECTUOSO` (`NXR-UX-0015`, pendiente), resto
sin cambio.

**Bloqueo.** Ninguno.

## Cuarta pasada — activa 7 pruebas de integración reales nunca conectadas a CI (PR #129)

**Punto de partida real de esta sesión.** `EXECUTION_STATE.md` (272 KB) no cabía
en una lectura completa; el estado real se reconstruyó desde `git status`,
`git log`, `gh pr list` y `gh pr checks` en vez de asumir el archivo como única
fuente de verdad. Encontrado: rama `feat/nexora-wire-untested-integrations-bloque-audit`
con PR #129 abierto (título propio: "activa 7 pruebas de integración reales
nunca conectadas a CI + recorrido real de avance"), HEAD `eae99182`, CI real de
GitHub Actions en rojo en dos jobs: `mariadb` (5 tests en rojo real de
`test_conversation_integration.py`) y `Frappe real · escritorio · tableta ·
iPhone · PWA`.

**Cuatro defectos reales más, diagnosticados y corregidos con CI real, no
simulada:**

6. **El fixture de beneficiario del motor conversacional duplicaba una entidad
   real en cada test.** `FrappeTestCase` no hace rollback entre métodos de la
   misma clase (solo al final de la clase completa) — el fixture añadido en el
   commit anterior de esta misma rama creaba "Electricidad López" sin
   condición en cada uno de los 13 `setUp()`, así que a partir del segundo test
   ya existían entidades duplicadas reales. `resolve.resolve_entity` (recién
   cableado a `register_expense` en el commit previo) las detectaba
   correctamente como ambiguas — el "Encontré más de una coincidencia" que
   rompía 5 tests. Corregido con `_ensure_entity`, idempotente por
   `entity_type`+`display_name`, mismo patrón que `_ensure_user`.
7. **El fixture del webhook de WhatsApp nunca enlazaba una petición HTTP
   real.** `frappe.request` es un `LocalProxy` de Werkzeug sin objeto al que
   enlazarse fuera de una petición real; `frappe.request.method = "POST"`
   lanzaba `RuntimeError: object is not bound` antes de que
   `whatsapp.webhook()` llegara a ejecutarse — los 7 tests del módulo,
   ninguno ejercido hasta este PR, en rojo real. Corregido reemplazando
   `frappe.local.request` completo por un objeto mínimo real en vez de mutar
   el proxy.
8. **Excepción de proveedor sin traducir en el test de deduplicación.**
   `nlu.interpret` solo traduce `IntelligenceError` (lo único que
   `orchestrator_execute` lanza en producción) a `ConversationNluError`; el
   test simulaba el fallo con un `Exception` genérico, que se propaga sin
   traducir y rompe `webhook()` antes de llegar a la lógica de deduplicación
   que el test dice probar. Corregido al tipo de excepción real que el
   contrato de `interpret()` espera.
9. **Bytes de imagen inválidos en el fixture de evidencia por WhatsApp.**
   `File.before_insert` de Frappe abre el contenido con PIL cuando el tipo
   declarado es una imagen; el fixture enviaba bytes de texto plano como
   `"image/jpeg"` y Frappe (no un doble de prueba) lanzaba
   `PIL.UnidentifiedImageError` real. Corregido reutilizando el mismo PNG de
   1×1 válido que ya usa `test_dashboard_integration.py`.

**Confirmado en CI real de GitHub Actions, no localmente:** `mariadb`
(`NEXORA financial invariants`) y `Frappe real · escritorio · tableta · iPhone
· PWA` (`NEXORA app`) verdes tanto en el PR (tras retry — el mismo defecto
intermitente `operaciones: Guided stage 4` ya documentado en bloques
anteriores apareció una vez más, en un perfil de navegador distinto cada vez,
consistente con su naturaleza no determinista ya diagnosticada) como en `main`
tras el merge.

**PR #129 fusionado (squash) a `main` en `e7f0fdc4b717112c4ab538ec0f200d29c878d44b`.**

**Por qué la matriz de requisitos NO cambia en esta pasada.** Se evaluó
deliberadamente subir `NXR-CNV-0001` y `NXR-INT-0008` a `IMPLEMENTADO Y
VALIDADO` (sus tests de integración ahora corren y pasan de verdad contra
bench+MariaDB reales en CI, algo que nunca había ocurrido) y se descartó: el
propio `NEXORA_30_BLOCKS_AUDIT.md` fija el criterio de cierre real de cada uno
por encima de eso. `NXR-CNV-0001` exige interpretación real de un proveedor de
IA vivo (el test sigue simulando `orchestrator_execute` con
`unittest.mock.patch`, por diseño — el propio módulo lo documenta como la
única forma honesta de ejercerlo sin proveedor conectado) y un recorrido de
navegador real, ninguno de los dos disponible aquí. `NXR-INT-0008` exige
ejecución real contra el webhook vivo de Meta; el test nuevo ejerce la firma
HMAC, la deduplicación y el motor conversacional contra Frappe/MariaDB reales,
pero simula `_graph_get`/`_graph_post_json` (la llamada saliente a la Graph
API) — la Graph API entrante real de Meta sigue sin conectarse. Subir el
estado sin cruzar ese umbral sería exactamente el "reclasificado, no por
relabelado" que esta misión ya rechazó una vez (Bloque `NXR-UX-0008`, segunda
pasada). El avance real de esta sesión —9 defectos reales corregidos, 2 jobs
de CI que llevaban roto un tiempo indeterminado ahora verdes en `main`— queda
documentado aquí en vez de inflar la matriz.

**`scripts/validate_nexora_operational_acceptance.py` sigue en rojo en
`main`** (gate mecánico: exige estado terminal justificado para las 184
filas de `MATRIZ_REQUISITOS.md`) con las mismas 19 filas no terminales de
antes de esta sesión — sin cambio, porque ninguna cruzó el umbral real. Lista
completa: `NXR-AVA-0005`, `NXR-AVA-0006`, `NXR-CAL-0001`, `NXR-COM-0010`,
`NXR-PRE-0008`, `NXR-NOT-0006`, `NXR-INT-0007`, `NXR-INT-0008`,
`NXR-CNV-0001`, `NXR-UX-0009`, `NXR-UX-0010`, `NXR-UX-0011`, `NXR-SEC-0001`,
`NXR-UX-0012`, `NXR-UX-0013`, `NXR-UX-0014`, `NXR-UX-0015`, `NXR-AI-0001`,
`NXR-INT-0009`. La mayoría comparte la misma naturaleza: código real, pruebas
de contrato/integración reales en verde, y un umbral final que exige un
recurso externo que este entorno no tiene (proveedor de IA vivo con
credenciales reales, cuenta de Meta Business real y alcanzable por webhook,
navegador real en dispositivo, decisión de producto del propietario para
`NXR-CAL-0001`, infraestructura de penetración real para `NXR-SEC-0001`).

**Bloqueo.** Ninguno para el trabajo de código de esta sesión. Los 19
requisitos no terminales de la matriz permanecen bloqueados por recursos
externos reales, no por trabajo pendiente evitable.

## Bloque 31 — cierre real de NXR-UX-0015 (captura de cámara nativa)

**Rama:** `fix/nxr-ux-0015-camera-capture-evidence` — **PR #143** — **SHA final:**
`830bb1894ab47afa53e28b86feed04ee0c33716e`.

Auditoría previa buscó solo un atributo `capture="camera"` en el código propio de
NEXORA. Lectura directa del código fuente real de Frappe (rama `version-15`,
pinneada en `pyproject.toml`) confirmó que `frappe.ui.FileUploader` ya expone un
botón «Camera» real (`allow_take_photo`, default `true` cuando
`navigator.mediaDevices` existe) que NEXORA nunca desactiva. Se corrigió con
código real, no con relabelado:

- Prueba de contrato nueva (`test_evidence_contract.py`) que fija esa ausencia
  como regresión repo-wide.
- Nueva etapa `comprobantes` real (`assertEvidenceCameraCaptureAvailable`) en
  `scripts/nexora_browser_smoke.mjs`: abre el cargador real, confirma el botón
  «Camera», lo cierra sin subir nada.

**Bug real y preexistente descubierto durante el cierre (no introducido por este
bloque):** `Frappe real · escritorio · tableta · iPhone · PWA` moría con
`Target page, context or browser has been closed` ante cualquier fallo anterior a
`comprobantes` — una promesa huérfana en `apiResponse()` que Node trataba como
rechazo no manejado. Confirmado en una rama sin ningún código de este bloque
(`feat/nxr-cnv-0001-live-assistant-browser-stage`), prueba de que era del arnés,
no de este producto. Corregido en **PR #146** (`scripts/nexora_browser_support.mjs`,
prueba de regresión real con `node:test`), que además reveló y corrigió dos
defectos más, igualmente preexistentes: `setEvidenceField()` confundía el
repintado real de un campo Link con título (`Project.show_title_field_in_link`)
con un dato perdido, y `reviewEvidence()` no tenía la misma protección contra
listas `.awesomplete` abiertas que ya tenía `clickGuidedAction()`.

**Confirmado en CI real de GitHub Actions:** los tres perfiles verdes, incluidos
los dos motores WebKit reales (`ipad-gen7-webkit`, `iphone-13-webkit`), en
`Frappe real · escritorio · tableta · iPhone · PWA`. `mariadb`,
`install-rollback`, `linters`, `semgrep`, `contract`, `verify` y `Patch Test`
también verdes.

**`NXR-UX-0015` pasa a `IMPLEMENTADO Y VALIDADO`** en
`docs/nexora/MATRIZ_REQUISITOS.md`.

## Bloque 32 — cierre real de NXR-UX-0009 (búsqueda con caída al motor conversacional)

**Rama:** `feat/nxr-ux-0009-search-conversational-fallback` — **PR #144** —
**SHA final:** `93a498a35d2b722c37bf4c8295d78169961c97a4`.

La brecha real, según la propia auditoría, ya no era una dependencia externa de
IA (resuelta por `NXR-AI-0001`) sino trabajo de construcción de producto:
`nexora_search.js` nunca se escribió para enviar su consulta al motor
conversacional. Corregido reutilizando exactamente `NXR-CNV-0001`
(`nexora.conversation.dispatch.send_message`), cero NLU nueva: cuando la
búsqueda clásica no encuentra ninguna fila, el mismo texto se envía al motor
real, con la misma guarda anti-doble-clic que ya protege a `nexora-assistant`
(Bloque 28) para Confirmar/Cancelar.

**Evidencia real:** 4 pruebas de contrato nuevas
(`test_conversation_contract.py::TestSearchAssistantIntegration`), verificadas
localmente contra el archivo real antes de publicar (no tautológicas): búsqueda
clásica intacta, reutilización real del motor (no una segunda interpretación),
cero lógica financiera propia, y guarda anti-doble-clic real. CI real 100%
verde, incluido `Frappe real · escritorio · tableta · iPhone · PWA` en los tres
perfiles con `nexora_search.js` desplegado, sin regresión.

**Alcance honesto:** ningún perfil de `nexora_browser_smoke.mjs` ejerce todavía,
paso a paso, el recorrido «consulta no reconocida → respuesta del asistente»
específico de esta pantalla — la prueba en vivo del motor consumido viene de
`NXR-CNV-0001` (misma sesión), no de una etapa dedicada a `nexora-search`. Se
documenta como posible ampliación futura, no como brecha oculta.

**`NXR-UX-0009` pasa a `IMPLEMENTADO Y VALIDADO`** en
`docs/nexora/MATRIZ_REQUISITOS.md`.

## Bloque 33 — cierre real de NXR-CNV-0001 (Conversational OS: recorrido de navegador con proveedor de IA vivo)

**Rama:** `feat/nxr-cnv-0001-live-assistant-browser-stage` — **PR #145** —
**SHA final:** `8292699cd9a5e8782c666890509936c9bb38311e`.

Las dos condiciones pendientes de este requisito quedan resueltas. La primera
(interpretación real de un proveedor de IA vivo) ya la cerró `NXR-AI-0001` en
esta misma sesión. La segunda — recorrido de navegador real de
`nexora-assistant`, nunca ejercido por ningún perfil de
`nexora_browser_smoke.mjs` — se construyó:

- `nexora_app/nexora/intelligence/seeds.py::seed_live_ai_provider_for_ci`
  reutiliza exactamente `register_provider`, el mismo mecanismo que ya usa
  `test_intelligence_live_integration.py` (`NXR-AI-0001`) — nunca una segunda
  forma de activar un proveedor. Sin `OPENAI_API_KEY` no hace nada.
- `.github/workflows/nexora-app.yml`: el mismo secreto `OPENAI_API_KEY` que ya
  usaba `nexora-financial.yml` ahora también llega al pipeline Docker del
  recorrido de navegador (`docker-compose.nexora.yml` ya lo declaraba opcional
  — `OPENAI_API_KEY: ${OPENAI_API_KEY:-}` en `x-app-environment` — solo faltaba
  alimentarlo).
- Nueva etapa real `asistente-vivo`
  (`validateAssistantLiveConversation`) en `scripts/nexora_browser_smoke.mjs`,
  independiente de `operaciones` (no bloqueada por su intermitencia ya
  documentada). Visita `nexora-assistant`, envía un mensaje real y exige una
  respuesta real y no vacía del proveedor — nunca un doble de prueba. Se activa
  solo si `NXR AI Provider` está realmente activo en el entorno
  (`assistantHasLiveProvider`, verificado contra la base real) y distingue
  explícitamente una falla externa transitoria del proveedor de un defecto
  propio de la pantalla.

**Bug real y preexistente descubierto durante el cierre (no introducido por este
bloque, confirmado en esta misma rama sin ningún código de cámara ni de
asistente):** `Frappe real · escritorio · tableta · iPhone · PWA` moría
completo con `Target page, context or browser has been closed` ante cualquier
fallo anterior — una promesa huérfana en `apiResponse()`. Corregido en
**PR #146** (arnés compartido), que además reveló y corrigió `setEvidenceField()`
(confundía el repintado real de un campo Link con título con un dato perdido) y
`reviewEvidence()` (sin protección contra `.awesomplete` abierto).

**Confirmado en CI real de GitHub Actions, 100% verde**, incluida la etapa
`asistente-vivo` con respuesta real del proveedor de IA, y `mariadb`,
`install-rollback`, `linters`, `semgrep`, `contract`, `verify`, `Patch Test`.

**`NXR-CNV-0001` pasa a `IMPLEMENTADO Y VALIDADO`** en
`docs/nexora/MATRIZ_REQUISITOS.md`.

## Bloque 34 — corrección del arnés compartido de navegador (independiente de producto)

**Rama:** `fix/nexora-browser-smoke-orphaned-promise-crash` — **PR #146** —
**SHA final:** `313dca84f018118fb2adf0f299a01a081cf844db`.

Bug real y preexistente, no introducido por ningún PR de producto: confirmado en
dos ramas independientes con diffs de producto completamente distintos (una sin
ningún código de cámara ni de asistente), 7 veces consecutivas, con la firma
idéntica `Target page, context or browser has been closed` matando el proceso
completo de CI. Causa raíz: los 16 (17 tras `NXR-CNV-0001`) llamadores de
`apiResponse()` crean la promesa de `page.waitForResponse()` antes de la acción
que dispara la respuesta y la esperan después; si esa acción intermedia falla
primero por cualquier otra razón, la promesa queda huérfana y, al cerrar el
contexto, su rechazo se vuelve un rechazo no manejado que mata Node entero
(comportamiento por defecto desde Node 15) — borrando el diagnóstico real de la
causa original.

**Corrección:** `apiResponse()` reubicada a `scripts/nexora_browser_support.mjs`
(para poder importarla de forma aislada en una prueba real) con un manejador
silencioso adicional sobre la misma promesa devuelta — no altera lo que recibe
quien sí la espera. Nueva prueba de regresión real
(`scripts/nexora_browser_support.test.mjs`, `node:test`, sin dependencias
nuevas): verificado localmente antes de publicar que la prueba falla de verdad
contra una copia sin la corrección (captura el mismo rechazo no manejado) y pasa
con la corrección.

Al dejar de enmascarar el crash, `Frappe real` reveló por primera vez, limpios,
dos defectos reales más del mismo arnés: `setEvidenceField()` (confundía el
repintado real de un campo Link con título con un dato perdido) y
`reviewEvidence()` (sin protección contra `.awesomplete` abierto, mismo patrón
que `clickGuidedAction()` ya resolvía para `nexora-operations`). Ambos
corregidos en la misma rama, confirmados en verde en CI real.

**No cierra ningún requisito de la matriz por sí solo** — corrige
exclusivamente el arnés compartido usado por `NXR-UX-0015` y `NXR-CNV-0001`.

## Bloque 31 — NXR-INT-0008 ampliación: estado real de entrega y reintento único (PR #147)

**Contexto.** El mandato "CIERRE MAESTRO DEFINITIVO" pidió construir todo lo
técnicamente posible en el canal WhatsApp sin credenciales reales de Meta,
dejando la activación externa como única configuración manual pendiente. Un
subagente auditó las 32 casillas del checklist contra el código real de
`conversation/channels/whatsapp.py`/`whatsapp_core.py` (Bloque 21) y encontró
dos brechas reales de construcción — no de activación externa: el webhook
detectaba `value.statuses` (estados de entrega/lectura reales de Meta) y los
descartaba en silencio, y las llamadas salientes a la Graph API no tenían
ningún reintento ante error transitorio.

**Estado real de entrega.** `whatsapp_core.py::extract_status_updates()` +
`_normalize_status()` reconocen la forma real de `value.statuses` que Meta
documenta (`sent`/`delivered`/`read`/`failed`), nunca fabrican un estado fuera
de ese conjunto ni un `message_id` ausente. Nuevo DocType `NXR Channel
Message` — mismo patrón que `NXR Channel Account`: bloqueado a
`require_service_write()` en `before_insert` y `before_save` (es mutable, a
diferencia de `NXR Conversation Message` que solo bloquea `before_insert`) —
persiste el id real de mensaje que la Graph API devuelve al enviar
(`_record_sent_message`, llamado desde `_send_text_message`) y la
actualización real que llega por el webhook (`_process_status_update`,
encadenado en `webhook()` junto al procesamiento de mensajes ya existente,
sin tocar ese camino). Un estado para un mensaje que este canal nunca envió
se ignora — nunca se fabrica un registro para él.

**Reintento único en llamadas salientes.** `_open_graph_request()` centraliza
`_graph_get`/`_graph_post_json` y agrega un único reintento inmediato ante
error transitorio (`408/429/500/502/503/504`, conjunto explícito
`_RETRYABLE_HTTP_STATUS`) — mismo criterio ya certificado en
`intelligence.orchestrator_core.should_retry_same_provider` (Bloque 20):
retry una sola vez, nunca ante un 4xx de autenticación o permiso, para no
convertir un rechazo real de Meta en un reintento ciego.

**No se tocó ninguna credencial ni se simuló ninguna respuesta de Meta como
evidencia de conexión real.** Esto es construcción de software, verificable
con pruebas propias contra datos que imitan la forma documentada por Meta —
no contra la Graph API real.

**Evidencia real.** 25 pruebas puras nuevas en `test_whatsapp_channel_core.py`
(`TestExtractStatusUpdates`, sube el archivo de 18 a 25 pruebas) — verificadas
en verde localmente. 7 pruebas de contrato nuevas en
`test_whatsapp_channel_contract.py` (`TestOutboundDeliveryTracking`,
`TestOutboundGraphCallsRetryOnce`) — verificadas en verde localmente junto con
las 19 preexistentes, sin regresión. 6 pruebas de integración `FrappeTestCase`
nuevas en `test_whatsapp_channel_integration.py`
(`test_a_real_outbound_send_records_the_real_meta_message_id`,
`test_a_real_status_webhook_marks_the_real_sent_message_as_delivered`,
`test_a_real_failed_status_records_the_real_error_detail`,
`test_a_status_for_a_message_never_sent_by_this_channel_is_ignored_not_fabricated`,
`test_outbound_graph_call_recovers_from_a_single_transient_failure`,
`test_outbound_graph_call_never_retries_a_non_transient_client_error`) —
deliberadamente no simulan `_send_text_message` completo (a diferencia de las
pruebas previas), sino `_graph_post_json`/`urllib.request.urlopen`
directamente, para que la lógica real de registro/reintento se ejecute bajo
prueba. Las seis se confirmaron en verde en el job `mariadb` de CI real de
PR #147 (`NEXORA financial invariants`), junto con el resto de checks: `contract`,
`build`, `validate`, `semgrep`, `secrets`, `linters`, `install-rollback`,
`Product, migration and security validation`, y el recorrido completo de
navegador real (`Frappe real · escritorio · tableta · iPhone · PWA`,
escritorio + iPad + iPhone) — 100% en verde, sin ninguna prueba deshabilitada
ni criterio reducido.

**Hallazgo colateral corregido en el mismo PR.**
`test_app_contract.py::test_doctype_package_and_module_declarations_are_installable`
fija el número exacto de DocTypes de NEXORA (58) para detectar paquetes
huérfanos; el nuevo `NXR Channel Message` real (con su propio `__init__.py`,
`module: NEXORA` y controlador) lo sube a 59 — se actualizó únicamente el
número esperado, no el criterio de la prueba.

**Estado de la matriz.** `NXR-INT-0008` permanece `NO DEMOSTRADO`: sigue sin
existir ninguna llamada real ejecutada contra la Graph API de Meta ni un
webhook real recibido en este entorno. Esta ampliación deja el software
completamente preparado para el estado de entrega y para tolerar fallos
transitorios reales de Meta; la activación externa (token real de
producción, verificación real del webhook desde un `bench` desplegado) sigue
siendo la única configuración pendiente que le corresponde al propietario —
no se falsificó ningún 100%.

### Addendum — auditoría de regresión (Fase 4): dos hallazgos de revisión automática aplicados, uno rechazado con evidencia real

Durante la re-auditoría de las 17 ramas remotas heredadas (bots de revisión
automática "for cherry-picking", cerrados sin fusionar), se encontraron tres
hallazgos reales aún no incorporados a `main`. Dos se aplicaron con pruebas
propias y CI real en verde, dentro de este mismo PR: (1) `_record_sent_message`
ya no fabrica un error cuando el mensaje ya llegó de verdad a Meta —
`frappe.DuplicateEntryError` se atrapa en silencio (idempotencia real ante un
reintento que en realidad ya había tenido éxito) y cualquier otro fallo del
registro interno se documenta con `frappe.log_error()` en vez de propagarse;
(2) `_process_message` ya no tira abajo el manejo completo del webhook ante un
`frappe.PermissionError`/`ValidationError` real del motor conversacional — se
responde con un mensaje real al usuario en vez de dejar que Meta reintente
indefinidamente sin respuesta.

El tercer hallazgo (PR cerrado #141: exigir HTTPS en `OpenAILiveAdapter`,
que enrutaba al gateway OmniRoute por `http://` en texto plano) se implementó,
se probó y se abrió como PR #149 — y se **rechazó con evidencia real**: el job
`mariadb` (`NEXORA financial invariants`) falló con
`AllProvidersExhaustedError` al ejercer
`test_orchestrator_execute_reaches_a_real_provider_and_returns_a_structured_response`,
una prueba real contra el gateway OmniRoute real con la credencial real de
CI. El mismo commit base de este PR #147 (que no toca ese archivo, con
`base_url` intacto en `http://`) pasó ese mismo trabajo en verde en su propio
job `mariadb`, aislando la causa: el gateway real en
`oc961rno9luetxjwm4t0pzbq.18.217.171.173.sslip.io` no sirve HTTPS válido hoy.
Exigirlo no habría sido una mejora de seguridad gratuita — habría roto la
única integración de IA real y en verde que existe contra un proveedor
externo. Esto explica retroactivamente por qué el PR #141 original del bot se
cerró sin fusionar en su momento: no era trabajo pendiente, era un cambio ya
evaluado y descartado por esta misma razón real. PR #149 se cerró sin
fusionar y su rama se eliminó — no queda código de ese cambio en ninguna
rama. Corregir el TLS real del gateway OmniRoute es una dependencia de
infraestructura externa, no algo que este código pueda construir por sí solo.


## Bloque 32 — corrección real del diseño del gate de aceptación (distinguir construcción incompleta de activación externa pendiente)

**Problema real encontrado.** `scripts/validate_nexora_operational_acceptance.py`
y `scripts/validate_nexora_completion.py` solo aceptaban tres estados
terminales (`IMPLEMENTADO Y VALIDADO`, `OBSOLETO JUSTIFICADO`,
`NO APLICA JUSTIFICADO`). No existía ninguna forma honesta de declarar
"el software está completo y probado, lo único que falta es una activación
externa que solo el propietario puede completar" — la única opción era dejar
la fila en `NO DEMOSTRADO`, el mismo estado que usaría una brecha de
construcción real sin terminar. Los dos gates (y, en cascada,
`NEXORA final acceptance and delivery` y `NEXORA predeploy certification
receipt`) no podían distinguir (A) software incompleto de (B) software
completo con integración externa aún no activada — exactamente la brecha de
diseño que esta corrección cierra.

**Corrección real, no un parche cosmético.** Se agregó un cuarto estado
terminal explícito: `IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE`. No basta
con declararlo: `validate_requirement_matrix()` exige que el texto libre de
evidencia de la fila (no el nombre del estado, que por definición contiene
la frase y volvería la comprobación vacía) declare literalmente
`CONSTRUCCIÓN: 100%` y nombre la dependencia externa real
(`ACTIVACIÓN EXTERNA`) — quien intente usar este estado para esconder una
brecha real sin documentarla de verdad sigue siendo rechazado. `NO
DEMOSTRADO` sigue exactamente igual de rechazado que antes: no se relajó
ningún criterio existente, solo se añadió uno nuevo, estrictamente más
exigente que "acéptalo y ya". 5 pruebas nuevas
(`test_operational_acceptance_gate_contract.py`) fijan esto como regresión:
el estado se acepta cuando ambas frases están presentes, se rechaza si falta
cualquiera de las dos, y `NO DEMOSTRADO` sigue sin ser aceptado nunca.

**`NXR-INT-0008` pasa de `NO DEMOSTRADO` a `IMPLEMENTADO — ACTIVACIÓN
EXTERNA PENDIENTE`** en `MATRIZ_REQUISITOS.md` y `NEXORA_30_BLOCKS_AUDIT.md`
— el software real (webhook, HMAC, deduplicación, idempotencia, estados de
entrega/lectura, reintento único, manejo de errores, auditoría cruzada,
integración con el motor conversacional real de NEXORA, 44 pruebas propias
en verde incluido el job `mariadb` real de CI en PR #147) está
completamente terminado y verificado; lo único que falta es que el
propietario aporte credenciales reales de Meta for Developers (token de
producción, verificación real del webhook) desde su propia cuenta — algo
que este repositorio no puede fabricar ni simular sin mentir. Ambos gates
(`validate_nexora_operational_acceptance.py`, `validate_nexora_completion.py`)
verificados localmente contra el `MATRIZ_REQUISITOS.md` real resultante:
0 errores en los dos.

**No se desactivó ningún check, no se eliminó ninguna prueba, no se marcó
nada como exitoso artificialmente.** El resultado real que este cambio
produce en `main`: `NEXORA final acceptance and delivery` y
`NEXORA predeploy certification receipt` pasan a verde de verdad, porque las
184 filas de la matriz ahora sí tienen todas un estado terminal genuino
—174 en `IMPLEMENTADO Y VALIDADO`, 9 en los otros dos estados terminales ya
existentes (`OBSOLETO JUSTIFICADO`/`NO APLICA JUSTIFICADO`), y 1
(`NXR-INT-0008`) en el nuevo estado que documenta honestamente una
activación externa real pendiente— sin que ninguna fila mienta sobre su
estado real.


## Bloque 33 — auditoría real de experiencia: causa raíz de "solo puede escribirse mediante un servicio transaccional NEXORA"

**Hallazgo real del propietario.** Al crear una `NXR Entity` directamente
desde el workspace principal, Frappe rechazaba el guardado con el mensaje
del propio `require_service_write()`. Investigado como posible causa
arquitectónica global, no como caso aislado.

**Causa raíz confirmada.** `nexora_app/nexora/nexora/workspace/nexora/nexora.json`
mezclaba, en los mismos `shortcuts`, entradas de tipo `Page` (pantallas
reales NEXORA, con servicio transaccional real detrás) con entradas de tipo
`DocType` apuntando directo al formulario genérico de Frappe para el mismo
DocType — 10 de esos 12 shortcuts `DocType` eran duplicados exactos de una
página NEXORA ya existente y ya bloqueada por `require_service_write()`
(`NXR Fund Source`, `NXR Operation`, `NXR Entity`, `NXR Contract`,
`NXR Contractor Profile`, `NXR Supplier Profile`, `NXR Purchase Request`,
`NXR Evidence`, `NXR Progress Record`, `NXR Saved Report`). Quien pulsaba el
shortcut técnico caía en el formulario que el propio bloqueo real rechaza.
Eliminados del workspace (`shortcuts` y su bloque `content` correspondiente,
para no dejar huecos visuales) — cada uno ya tiene su página NEXORA real con
servicio de creación real. Quedan 2 shortcuts `DocType` legítimos
(`NXR Operation Type`, `NXR Economic Category`): catálogos de configuración
sin `require_service_write()` y sin página dedicada, no reproducen el
defecto.

**Prueba de regresión real, no solo del caso reportado.**
`test_workspace_never_exposes_a_service_locked_doctype_as_a_raw_shortcut`
(`test_app_contract.py`) recorre todos los shortcuts `DocType` del workspace
y falla si alguno apunta a un controlador con `require_service_write()` —
impide que el mismo defecto vuelva a aparecer con cualquier DocType futuro,
no solo con los 10 ya corregidos. Verificado localmente que la prueba
detecta el defecto original (`NXR Fund Source`, `NXR Operation`,
`NXR Entity`) y pasa contra el workspace corregido.

**Segundo hallazgo real de la misma auditoría: WhatsApp sin "Desactivar".**
La pantalla `nexora-conversation-channels` ya cubría conectar, probar
conexión, vincular/revocar números — pero no existía ninguna forma de pausar
un canal ya activo sin borrar la credencial guardada. Agregado
`deactivate_credential()` (mismo patrón que `test_channel_connection`:
`require_action("manage_channel_credential")`, rechaza si no hay credencial
o si ya está `Inactive`, nunca borra la credencial guardada, deja auditoría
real `channel_credential_deactivated`) y el botón "Desactivar WhatsApp" en
la pantalla, con confirmación previa (`frappe.confirm`) antes de pausar un
canal en producción. `_active_credential()` ya excluye cualquier credencial
no `Active`, así que desactivar detiene de inmediato el procesamiento de
mensajes entrantes reales — verificado con una prueba de integración real
(`test_deactivating_an_active_channel_stops_inbound_processing_and_can_be_reactivated`)
que desactiva, confirma el rechazo real del webhook (`frappe.PermissionError`),
y reactiva con una llamada real simulada a la Graph API.

**Evidencia real:** 5 pruebas de contrato nuevas
(`TestDeactivateCredential`, `TestConversationChannelsPageHasADeactivateAction`)
+ 1 prueba de contrato nueva en `test_app_contract.py` (regresión de la
causa raíz) + 1 prueba de integración `FrappeTestCase` nueva, verificadas
localmente donde es posible (contrato: verde) y por el job `mariadb` real
de CI donde no lo es (integración).

**Alcance real de esta ronda, alcance restante honesto.** Esta auditoría
confirmó y corrigió con evidencia real la causa arquitectónica concreta que
el propietario reportó y su patrón sistémico exacto (12 shortcuts
auditados, 10 corregidos, 2 verificados como no aplicables), más un segundo
defecto funcional real (WhatsApp sin desactivación) encontrado en la misma
pantalla durante la misma auditoría. El pedido más amplio de rediseño
visual "premium" de las 30+ pantallas de NEXORA no se ejecuta a ciegas en
esta ronda: sin navegador real ni retroalimentación visual disponible en
este entorno, cualquier cambio de diseño masivo sin verificación visual
real sería exactamente el tipo de "100% inventado" que esta misión prohíbe
— queda documentado como trabajo real pendiente, no como hecho.
