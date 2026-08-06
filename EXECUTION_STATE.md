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

SHA en `main`: pendiente de commit, push y Pull Request.
