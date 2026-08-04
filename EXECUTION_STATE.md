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

- **Contexto activo en las 9 páginas restantes.** Se unificó en dashboard, operación
  diaria y reportes —las pantallas de trabajo con selector de proyecto propio—. Cierre
  semanal, contratos, proveedores, compras, cotizaciones, evidencias, entidades,
  fondos y buscador siguen recibiendo el proyecto solo por `route_options`. No es un
  defecto nuevo, pero conviene extender el mismo patrón.
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
