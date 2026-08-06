# NEXORA — Memoria técnica de reconstrucción

Documento maestro entre sesiones (Guía Maestra v2.0, Fase 4). Registra decisiones,
hallazgos y plan. **No se reescribe: se actualiza.** El detalle histórico del Bloque 2
vive en `EXECUTION_STATE.md`.

- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales: **sin tocar**

## Línea base verificada

| Verificación | Estado en `main` (`080dc670`) |
|---|---|
| `validate_nexora_app` | ✅ |
| `validate_repository` | ✅ |
| `validate_construcontrol_architecture` | ✅ |
| `validate_nexora_completion` | ✅ 166 requisitos |
| `validate_nexora_governance` | ✅ |
| `validate_nexora_financial_models` | ✅ 10 DocTypes |
| Suite de contrato | ✅ 275 pruebas |
| Recorrido de navegador (`browser`) | ❌ **único rojo** |

Los dos rojos documentales heredados (`validate_repository`,
`validate_construcontrol_architecture`) se cerraron en el PR #60.

## Bloque 3 — Diagnosticabilidad del recorrido de navegador

### Problema

El recorrido de navegador es la única verificación en rojo y **no se podía
diagnosticar**. Al rechazar el servidor la vista previa del gasto, el log solo decía:

```text
AssertionError: Expense preview request failed.
false !== true
```

Tres ejecuciones de CI se gastaron en eso. El motivo real viaja en
`_server_messages` —un JSON dentro de otro JSON— y la sonda lo descartaba. Esto
incumple la Constitución §21: todo error debe ser reproducible y con causa
identificable.

### Causa técnica

`assert.equal(response.ok(), true, "…")` compara un booleano y tira el cuerpo de la
respuesta, que es exactamente donde Frappe pone la regla de negocio incumplida.
Ocurría en las 8 comprobaciones de respuesta del recorrido.

### Hipótesis descartadas leyendo código (no por ensayo y error)

| Hipótesis | Por qué se descarta |
|---|---|
| Falta la moneda del gasto | `_normalize_expense_currency` usa `HNL` por defecto (`operational_commands.py:46`), y el cliente ya la fija en `set_value("HNL")` |
| Falta la cuenta financiera del beneficiario | Sin `financial_account` ni `save_financial_account`, `normalize_account_mode` devuelve `Manual`, que no exige cuenta |
| Segregación de funciones | `CONSTRUCTION_PAYMENT` no está en `SEGREGATED_OPERATION_CODES` |

### Corregido

- `scripts/nexora_browser_support.mjs`: `serverReason()` desempaqueta
  `_server_messages` y `exc_type`; `assertResponseOk()` falla nombrando el estado
  HTTP y el mensaje del servidor. Solo construye el mensaje cuando falla.
- Las 8 comprobaciones del recorrido pasan por el helper.
- `tests/test_browser_diagnostics_contract.py`: prohíbe volver a
  `assert.equal(x.ok(), true, …)` en cualquier script del recorrido.

### Hallazgo mayor: una suite de runtime que nadie ejecutaba

`nexora_app/nexora/tests/test_operational_integration.py` cubre ingreso, gasto,
correcciones y libro contra MariaDB real — y **ningún workflow la invocaba**. Daba
falsa confianza (Constitución §24).

- Conectada al job `install-rollback`, que ya levanta bench real y siembra dos veces.
- Añadido `test_guided_expense_102_accepts_the_payload_the_console_really_sends`:
  reproduce **el payload exacto de la consola guiada** —`beneficiary_doctype: "NXR
  Entity"`, efectivo, modo `Manual`, sin solicitante ni aprobador explícitos—, la
  combinación que ningún caso cubría (los existentes usan un `User` como beneficiario
  y nombran dos actores distintos) y que es justo donde cae el navegador.

Con esto el rechazo del servidor se reproduce en un job de ~5 min con traza de Python
completa, en vez de en un recorrido de navegador de ~10 min sin mensaje.

### También corregido en este bloque

- `nexora_operations.js`: el `catch` de `initialize()` usaba
  `window.nexora.ui?.showError?.()` sin respaldo; si ese bundle no cargó, la pantalla
  quedaba «lista» y muda. Ahora cae en `frappe.msgprint`, igual que el panel principal.
- `test_reference_rules.py`: el camino «falta un actor» de `validate_segregation` no
  tenía prueba; solo se cubría el actor repetido.

## Cómo verificar localmente igual que CI

`ruff` en el PATH de esta máquina es 0.15.8; **CI fija 0.16.0** en
`.pre-commit-config.yaml`. Las dos versiones no coinciden en las reglas activas por
defecto: 0.15.8 no señalaba `SIM117` (dos `with` anidados) y sí señalaba `E402` en
`test_operational_integration.py`, mientras 0.16.0 hace lo contrario. Un `linters` rojo
salió de esa diferencia, no del código.

Usar siempre la versión de CI:

```bash
python -m ruff check nexora_app/      # 0.16.0, la misma que pre-commit
python -m ruff format --check nexora_app/
npx --yes prettier@2.7.1 --check <archivos>
```

**Dos validadores exigen argumentos y por eso es fácil darlos por buenos sin
ejecutarlos.** Lanzarlos sin ellos devuelve el `usage:` de `argparse`, que se lee como
un fallo del entorno y no como una comprobación pendiente. `Check Commit Titles` se
puso rojo justamente así: un título en imperativo llano, fuera de la convención.

```bash
python scripts/validate_commit_titles.py --from origin/main --to HEAD
python scripts/validate_construcontrol_backup.py <ruta-de-respaldo>
```

Los títulos aceptados son conventional commits, `[B01]`…`[B12]` o `[CERT]`.

**Añadir o borrar cualquier archivo obliga a regenerar el inventario.**
`docs/architecture/file_inventory.json` lleva conteos por categoría y un hash canónico
que cinco workflows comparan; no regenerarlo los pone a todos en rojo aunque el código
esté bien.

```bash
git add nexora_app scripts docs   # las rutas del cambio, revisadas antes
git status && git diff --cached   # qué se va a confirmar, no lo que quedó suelto
python scripts/generate_file_inventory.py
```

El generador solo cuenta archivos **ya rastreados**: regenerarlo antes de preparar los
archivos deja fuera los nuevos y CI vuelve a ponerse rojo con el mismo hash de antes. Ese
es el único motivo del orden. Prepare rutas explícitas en lugar de `git add -A`: un
comodín arrastra lo que haya en el árbol —un volcado, una credencial de prueba— y una vez
confirmado ya está en la historia.

## Deuda registrada (no corregida aquí)

| Elemento | Motivo de no corregirlo ahora |
|---|---|
| `BANK_CHANNELS` duplicado entre `nexora.js` y `nexora_guided_model.js` | Intentado y revertido: el modelo guiado se ejecuta también fuera del navegador —`test_guided_account_progressive_contract.py` lo carga con Node a secas— y leerlo de `window.nexora.rules` lo deja con el conjunto vacío. Unificarlo exige decidir quién es la fuente y en qué orden se cargan los paquetes; es rediseño, no un ajuste |
| `test_operational_integration.py:13` parece violar `E402` | Falsa alarma de ruff 0.15.8: con la 0.16.0 que usa CI el árbol pasa limpio. El orden es deliberado — Frappe exige `test_dependencies` antes de importar módulos que tocan esos DocTypes |
| `cr-gpt[bot]` comenta en cada PR que falta `OPENAI_API_KEY` | Configuración del repositorio: o se configura o se desinstala la app |
| La degradación del asistente se dispara con un parpadeo, no solo con un cambio real | `if (!valid && state.stage > 2) activate(state, 2, false)` mira un estado que la consola original refresca por su cuenta. Es el diseño original y la corrección de la etapa 3 no lo empeora, pero un parpadeo entre alcanzar el registro y pulsarlo devuelve al usuario a la etapa 2 sin que él haya cambiado nada. Requiere distinguir «datos invalidados» de «botones refrescándose», que es rediseño del asistente, no un ajuste |
| Cobertura de docstrings 14,91% según CodeRabbit | No es puerta del repositorio; documentar por umbral no mejora el producto |

## Bloque 4 — El comprobante que la pantalla no pedía y el servidor sí exigía

### Problema (encontrado persiguiendo el rojo del navegador)

`evaluate_evidence_policy` (`financial/evidence_core.py`) obliga a comprobante en
**depósitos y transferencias**, y en **efectivo por encima de L2,000**. Ninguna de las
dos pantallas de gasto lo pedía:

- La consola operativa marcaba `evidence` como obligatorio **solo para el código 304**
  (`toggle("evidence", expense || correction, code === "304")`).
- El gasto rápido de `nexora.js` nace con medio de pago **«Transferencia»** por defecto
  —que siempre exige comprobante— y el campo no era obligatorio.

El usuario llenaba proyecto, beneficiario, importe, medio de pago, categoría, centro de
costo y distribución, pulsaba «Vista previa» y recién ahí el servidor lo rechazaba. En
el gasto rápido, el camino por defecto estaba condenado. Es trabajo perdido y un error
inducido por la interfaz (Constitución §6, §15, §19).

### Corregido

- `nexora.js` publica `window.nexora.rules.evidencePolicy(medio, importe)`: espejo
  exacto de la regla del servidor, en el primer bundle que carga NEXORA, **en un solo
  lugar del cliente** (§18).
- El gasto rápido aplica la política al abrir el diálogo y al cambiar medio de pago o
  importe: el campo se marca obligatorio y explica por qué.
- La consola operativa consulta la misma regla —sin reimplementarla—, la reevalúa al
  cambiar `payment_method` o `amount_hnl`, y bloquea la vista previa con un error de
  campo en vez de dejar que el servidor la rechace.
- `tests/test_evidence_policy_parity_contract.py`: los medios y el umbral del cliente
  se comparan contra `PAYMENT_EVIDENCE_METHODS` y `CASH_EVIDENCE_THRESHOLD_HNL`
  importados del servidor, así que no pueden separarse; y se prohíbe volver a declarar
  la regla dentro de la página.

### Descartado como causa del rojo del navegador

El recorrido usa efectivo de L75.25: por debajo del umbral, la política no exige
comprobante. La causa del rechazo sigue sin nombre y la entregará la instrumentación
del Bloque 3. Este defecto se encontró **buscando** esa causa y es independiente de
ella: afecta al usuario real en cuanto paga por transferencia o en efectivo por encima
de L2,000.

## Bloque 5 — Causa raíz del rojo: ningún gasto podía registrarse

Persiguiendo el mismo patrón —reglas del servidor sin espejo en la pantalla— apareció
la causa del rechazo, verificada leyendo la cadena completa:

1. `nexora_operations.js` inicializa `controls.account_mode.set_value("New")`.
2. `account_mode` está **oculto** en el gasto (`toggle("account_mode", income, income)`),
   así que conserva ese «New».
3. `payload()` enviaba `account_mode: "New"`, `save_financial_account: 1` y
   `account_name: ""` — el campo del nombre también está oculto en el gasto.
4. El servidor, con modo `New`, ejecuta
   `_validate_account_payload(_expense_account_payload(...), required_direction="Destination")`,
   cuyo primer requisito es
   `_required(account_name, "Escriba un nombre para reconocer la cuenta.")`.

**Resultado: la vista previa de todo gasto se rechazaba, para cualquier usuario y en
cualquier sitio.** No era un fallo del recorrido: el recorrido estaba reportando un
producto roto.

Segundo defecto de la misma familia, encontrado en la misma cadena:
`_resolve_expense_account` exige **banco y referencia de cuenta** para todo gasto
pagado por un canal bancario (`BANK_CHANNELS`), y la pantalla ocultaba ambos campos en
el gasto. Un pago por depósito o transferencia era imposible de completar aunque el
modo de cuenta fuera correcto.

### Corregido

- `payload()` deriva el modo de cuenta del movimiento: el control solo se muestra en el
  ingreso, así que el gasto envía `Manual`, que es lo que la pantalla realmente ofrece.
- `applyBankVisibility()` gana una rama para el gasto: muestra y exige banco y
  referencia cuando el medio de pago es un canal bancario, y se reevalúa al cambiarlo.
- `window.nexora.rules.BANK_CHANNELS` / `requiresBankAccountDetails()` junto a la regla
  de evidencia: un solo lugar para las reglas compartidas del cliente.
- El contrato compara los canales del cliente contra `BANK_CHANNELS` leído de
  `operational_common.py`, y exige que el gasto nunca declare un modo de cuenta que la
  pantalla esconde.

## Bloque 6 — Paridad en los códigos de corrección

Auditados 303, 304 y 501 contra sus perfiles del servidor:

| Código | Perfil | Exige el servidor | Exigía la consola |
|---|---|---|---|
| 303 · Anulación financiera | `REVERSAL_NO_CASH` | referencia, **segregación** | referencia, motivo ≥10 |
| 304 · Corrección documental | `DOCUMENT_SUBSTITUTION` | referencia, **segregación**, **evidencia** | referencia, motivo ≥10 |
| 501 · Cancelación total | `REVERSAL_NO_CASH` | referencia, **segregación** | referencia, motivo ≥10 |

La consola marcaba `requester`, `approved_by` y `evidence` con `reqd` en el control,
pero su propia función `validate()` —la que arma los errores y bloquea la vista previa—
nunca los comprobaba. Elegirse a uno mismo como solicitante, que es lo natural porque es
quien llena el formulario, se rechazaba recién en el servidor.

La regla de segregación **ya existía** en `nexora_quick_flows.js` (`correctionActors`),
local a ese archivo: la superficie principal de correcciones no la usaba. Dos
superficies que registran lo mismo aplicando reglas distintas es la duplicidad que la
Constitución §16 y §18 prohíben.

### Corregido

- `window.nexora.rules.segregationError(requester, approvedBy)` en `nexora.js`: espejo
  de `validate_segregation`, devuelve el error sin renderizarlo, para que cada
  superficie lo muestre a su manera (diálogo con `msgprint`, consola con error de campo).
- `nexora_quick_flows.js` y la consola operativa consumen la misma función.
- La consola valida ahora segregación en los tres códigos y evidencia en el 304.
- El contrato de correcciones exige que ninguna superficie reimplemente el conjunto de
  actores (`new Set([requester, approvedBy, executor])`).

## Bloque 7 — Ingreso auditado y la carrera real del asistente guiado

### Ingreso (101): sin brechas

Único flujo cuya paridad ya era correcta. `resolve_income` exige proyecto, cuenta
—guardada o nueva con nombre—, importe > 0, tasa > 0, remitente y, para canales
bancarios, banco, cuenta destino y referencia. La rama `101` de `validate()` pide
exactamente eso. **No se cambió nada**: inventar trabajo donde no hay defecto
contradice §27 y §33.

### La etapa 3 del asistente se cerraba sola

Con el gasto ya corregido, el recorrido de navegador falló **en el ingreso**, en
`advanceValidatedGuidedReview`. No es un fallo de la sonda:

```js
if (valid && state.previewRequested) {
    state.previewRequested = false;   // ← se consumía aquí
    activate(state, 3);
}
if (!valid && state.stage > 2) activate(state, 2, false);
```

`previewRequested` se gastaba en la **primera** pasada de `sync()` que viera `valid`.
Si el estado parpadeaba a inválido justo después —cosa que la consola original hace al
refrescar botones—, la segunda regla devolvía el asistente a la etapa 2 con la bandera
ya consumida, y la revisión **no volvía a abrirse nunca**. El usuario pulsaba «Vista
previa», el servidor respondía correctamente, y el asistente retrocedía en silencio.

Corregido: la bandera ya no se consume al abrir la etapa 3. Se consume cuando la
revisión se usa de verdad —al avanzar al registro definitivo— o cuando
`nexora:data-changed` invalida los datos.

### Hallazgos de revisión atendidos

| Hallazgo | Origen | Resolución |
|---|---|---|
| `validate()` no comprobaba banco ni referencia en el gasto | Codex + CodeRabbit | Añadidos, con contrato |
| `showError(...) \|\| msgprint(...)` mostraba **dos** diálogos | CodeRabbit + Qodo | Rama explícita; corregido también en el panel principal, que tenía el mismo patrón |
| La matriz de actores ausentes solo variaba el solicitante | CodeRabbit | Nueve casos: tres actores × `""`, espacios y `None` |
| La prueba de integración no reproducía todo lo que `payload()` serializa | CodeRabbit | Incluye `channel`, `exchange_rate` y los demás campos ocultos —justo la clase de residuo que rompía el gasto |
| Bloque de código sin lenguaje (MD040) | CodeRabbit | Etiquetado |

## Bloque 8 — Fijar las correcciones con pruebas que fallan de verdad

Dos correcciones del bloque anterior quedaron sin guardia. Corregir sin fijar es dejar
la puerta abierta a repetir el defecto (§23, §28).

- `tests/test_guided_wizard_contract.py`: prohíbe volver a consumir `previewRequested`
  al abrir la etapa 3, exige que se consuma donde la revisión se usa de verdad —al
  avanzar al registro y al invalidarse los datos— y comprueba que la degradación a la
  etapa 2 sigue protegiendo de registrar sin vista previa válida.
- `test_dashboard_contract.py`: prohíbe encadenar el respaldo de error con `||` en las
  dos superficies que lo tenían, y ancla que `showError` no devuelve valor —si algún
  día lo devolviera, el contrato obliga a revisarlo.

**Ambas se verificaron reintroduciendo el defecto a propósito**: fallan con él y pasan
sin él. Un contrato que no se ha visto fallar no prueba nada.

## Bloque 9 — El runtime queda certificado; el navegador todavía no dice por qué falla

### Veredicto del paso 14 (lo que se pedía confirmar)

`install-rollback` terminó **verde en sus 15 pasos**, incluido el paso 14 «Exercise the
operational console against the real bench» (run `30971151724`, job `92195548939`,
03:08:42→03:09:19, SHA `13b81d89`). Es la primera vez que la suite operativa se ejecuta
contra un bench real: instalación, desinstalación, reinstalación, semilla idempotente y
recorrido operativo, todo sobre ERPNext v15 de verdad. Lo que hasta ayer estaba
«probado estáticamente» pasa a estar **certificado en runtime**.

### Lo que sigue rojo, dicho sin adornos

El recorrido de navegador (`Frappe real · escritorio · iPhone · PWA`) falla en el
**ingreso**, al esperar que la etapa 3 quede válida y estable:

```text
page.waitForFunction: Timeout 60000ms exceeded.
    at advanceValidatedGuidedReview (scripts/nexora_browser_smoke.mjs:183)
    at validateIncomeGuided (scripts/nexora_browser_smoke.mjs:340)
```

La vista previa del servidor **respondió 200** —`assertResponseOk` la dejó pasar—, así
que el rechazo no viene del negocio. Pero el log no dice más: la espera resume cinco
condiciones en un único booleano y, al expirar, no distingue entre causas que se
corrigen de formas distintas.

### Por qué no se corrigió a ciegas en este bloque

Se agotaron las dos vías de evidencia disponibles antes de escribir código:

| Vía | Resultado |
| --- | --- |
| Reproducir el stack localmente | Imposible: el entorno no tiene demonio Docker. |
| Descargar `nexora-ui-*.zip` (captura + informe JSON) | Imposible: el proxy responde 403 a la API de artefactos. |

Queda un solo canal legible: **el log de CI**. Proponer una corrección sin poder
nombrar la causa sería exactamente lo que §28 prohíbe («nunca asumirás que algo
funciona sin comprobarlo»). Se descartaron por lectura tres hipótesis —que el gasto
invalidara la vista previa al reescribir campos (todas las escrituras del asistente van
con `notify=false`), que `nexora:data-changed` apagara `previewRequested` durante la
petición (ninguno de sus emisores se dispara en una vista previa de ingreso, y
`$(document).trigger` no alcanza a los oyentes nativos) y que la firma de estabilidad
oscilara (sus seis componentes son estáticos tras el render)— sin llegar a una causa
demostrable.

### Corregido: el punto ciego, no un síntoma inventado

Mismo remedio que ya funcionó con las respuestas HTTP en el Bloque 3, aplicado ahora a
las esperas del asistente.

- `scripts/nexora_browser_smoke.mjs`: `guidedReviewDiagnostics()` devuelve, campo por
  campo, el estado que la espera comprimía en un booleano —etapas visibles, si la etapa
  3 sigue oculta, si «Continuar» y el botón de la consola siguen deshabilitados, si la
  revisión quedó vacía, y los textos de la vista previa, del resumen de validación y del
  estado de acción—. `waitForGuidedStage` y `advanceValidatedGuidedReview` fallan ahora
  nombrando ese estado en vez de «Timeout».
- `scripts/nexora_browser_support.mjs`: `describeSignals(profile)` resume los errores de
  página, de consola, 5xx y de autorización que la página venía emitiendo.
- `scripts/nexora_browser_validators.mjs`: `captureFailure` los **imprime en el log**.
  Antes solo se comprobaban al terminar el perfil, así que un fallo anterior los
  descartaba sin mostrarlos, y el informe JSON vive dentro de un zip que no siempre se
  puede descargar.

### Pruebas

`test_browser_diagnostics_contract.py` gana dos casos que exigen las siete señales del
diagnóstico y la impresión en el log. **Ambos se verificaron reintroduciendo el defecto**:
fallan al quitar `describeSignals` de las dos esperas y de `captureFailure`, y pasan al
devolverlo. Gate local completo en verde: 292 contratos, 43 casos de núcleo, los
validadores del repositorio, `python -m ruff` (0.16.0, la de CI), prettier 2.7.1 y
`node --check`.

### Riesgo asumido

Este bloque **no arregla el ingreso**: lo hace diagnosticable. La siguiente ejecución
dirá la causa con nombre en vez de un temporizador agotado.

## Bloque 10 — El diagnóstico habló: el ingreso pasa y el gasto se anula solo

### El ingreso quedó cerrado

En el run `30972014964` el ingreso recorrió **entero**: vista previa, revisión, registro
definitivo y replay idempotente con el mismo número documental. El rojo se movió al
gasto. La carrera de la etapa 3 corregida en el Bloque 7 era real.

### Lo que dijo el diagnóstico, literal

```json
{"visible_stages":["2"],"review_stage_hidden":true,"continue_button_disabled":true,
 "console_execute_disabled":true,"preview_still_empty":true,
 "preview_text":"La información cambió. Genere una nueva vista previa.",
 "validation_summary":"","action_status":"Genere una vista previa válida para contabilizar."}
— the page reported no errors.
```

Tres lecturas que cierran el caso a la mitad:

1. Los dos textos son **literalmente** los de `invalidatePreview()`. La vista previa se
   generó bien y **algo la anuló después**.
2. `validation_summary` vacío descarta el rechazo del servidor: el `catch` de
   `previewMovement` llena ese resumen con «No se pudo validar», y está vacío.
3. `visible_stages: ["2"]` es la degradación del asistente reaccionando a esa anulación,
   no la causa. El asistente hace lo correcto; la consola es la que se contradice.

Antes de esto, el mismo fallo se leía como `page.waitForFunction: Timeout 60000ms
exceeded` y consumió tres ejecuciones sin permitir elegir entre causas.

### Corregido: la consola ya no anula sin decir quién

`invalidatePreview()` no dejaba rastro. Sus cuatro llamantes son distinguibles y llevan
correcciones distintas —un campo editado por el usuario no es lo mismo que la pantalla
refrescándose sola—, así que cada uno deja su nombre en
`data-preview-invalidated-by` de la carcasa, el diagnóstico lo lee, y una vista previa
aceptada limpia la marca para no confundir el motivo anterior con el actual.

| Llamante | Motivo registrado |
| --- | --- |
| `input` en `.nxr-source-amount` | `allocation-amount` |
| `fieldChanged(fieldname)` | `field:<nombre>` |
| `catch` de `previewMovement` | `server-refused-preview` |
| `resetAfterExecution` | `after-execution` |

### Hallazgo de revisión atendido

Greptile detectó que `advanceValidatedGuidedReview` reenviaba `profile` al bloque de
diagnóstico pero **no** a su propio `waitForGuidedStage(page, 4)`: un fallo en la etapa 4
habría informado «the page reported no errors» sin haber mirado. Corregido, y el
contrato prohíbe ahora cualquier espera de etapa sin perfil —era un llamante colado
dentro de la misma función que arreglaba el problema.

### Pruebas

`test_browser_diagnostics_contract.py` sube a 6 casos: exige las ocho señales del
diagnóstico, prohíbe `invalidatePreview()` anónimo, exige los cuatro motivos y la
limpieza al aceptar, y prohíbe esperas de etapa sin perfil. **Verificados
reintroduciendo los dos defectos**: fallan con ellos, pasan sin ellos. Gate local
completo en verde: 293 contratos, 43 casos de núcleo, validadores, `python -m ruff`
0.16.0, prettier y `node --check`.

### Riesgo asumido

Sigue sin arreglar el gasto. La mitad que falta —**cuál** de los cuatro llamantes
dispara— la responde la próxima ejecución con una palabra.

## Bloque 11 — Constitución vinculante y el gasto que no se podía reintentar

### La Constitución no existía en el repositorio

El Capítulo 72 la declara vinculante para toda IA que participe en NEXORA. Vivía solo en el
historial de un chat: se perdía con la sesión y no gobernaba nada. Ahora reside en
`NEXORA_CONSTITUTION.md` con sus 5 partes y 74 capítulos; `AGENTS.md` se declara subordinado
y deja de reescribir por su cuenta la definición de «terminado» —que es del Capítulo 60—
para no tener dos definiciones que se separen (Capítulo 44).
`validate_nexora_constitution.py` exige que siga íntegra: partes, capítulos, títulos de los
siete capítulos que sostienen el proyecto, las trece comprobaciones del Capítulo 60 y la
subordinación de `AGENTS.md`. Corre en CI y se verificó degradando el documento a propósito.

### El gasto se registra; lo que fallaba era el reintento

El recorrido llegó hasta `replayExecution`: **el gasto se ejecuta de extremo a extremo** y
falla al repetir la petición idéntica, con `HTTP 417`.

Causa raíz, en `execute_operational_movement`: el envoltorio operativo recalculaba la vista
previa y exigía que el hash coincidiera **antes** de delegar en el núcleo. La propia
ejecución ya había movido los saldos, así que el hash recalculado difería siempre y el
reintento moría con «la vista previa está vencida». El núcleo sí es idempotente
—`start_idempotency` devuelve la respuesta original antes de recalcular nada—, pero nunca se
llegaba a él. El ingreso pasaba porque `execute_income` retorna antes de esa revalidación.

Impacto real: un doble clic, un corte de red o una reconexión del móvil se leían como fallo
y empujaban al usuario a capturar el gasto por segunda vez.

Corregido con `completed_idempotent_response()` en `db.py` —consulta, no reserva; la regla
de idempotencia sigue viviendo en un único lugar—: un reintento ya completado devuelve la
respuesta original sin revalidar precondiciones que la ejecución modificó. La anulación de
ingreso (303/501) tenía el mismo defecto y recibe la misma corrección (Capítulo 36).

### Cuatro comprobaciones ciegas más

`replayExecution` afirmaba `assert.equal(replay.ok, true, ...)`, que descarta el cuerpo de
la respuesta: por eso el 417 no dijo su motivo. El contrato solo vetaba la forma de función
(`x.ok()`), no la de propiedad (`x.ok`). Ampliado el veto, aparecieron cuatro llamadas
ciegas más —login, API ejecutiva, libro operativo y manifiesto—, todas convertidas a
`assertResponseOk`.

### Pruebas

`test_operational_integration.py` gana el reintento del gasto contra bench real: mismo
documento, misma operación, un único `NXR Operation`. 293 contratos, 43 casos de núcleo,
validadores (incluido el nuevo), `ruff check`, `ruff format` y prettier en verde.

## Bloque 12 — La vista previa del gasto se invalidaba por un cambio que no existió

### El diagnóstico dio el nombre

```json
{"visible_stages":["2"],"preview_still_empty":true,
 "preview_text":"La información cambió. Genere una nueva vista previa.",
 "validation_summary":"","preview_invalidated_by":"field:description"}
```

`field:description`: la consola **invalidaba la vista previa** del gasto —ya aprobada por
el servidor— porque llegaba un evento `change` de un campo que el usuario no volvía a
tocar. Nada persistido se revirtió: el gasto aún no se había registrado; lo que se perdía
era el trabajo previo del usuario.

### Causa

`fieldChanged` invalidaba la vista previa ante **cualquier** evento `change`. Frappe lo emite también cuando
la pantalla reescribe un control, cuando el asistente guiado mueve el campo de contenedor
y cuando el foco vuelve a él. Ninguno de esos casos es una edición del usuario, y los tres
destruían trabajo válido obligando a repetir la vista previa sin haber cambiado nada.

Corregido comparando el valor: solo un valor distinto anula. Ejecutar con una vista previa
obsoleta sigue siendo imposible —el servidor revalida su huella en `execute()`—, así que
la relajación del cliente no abre ningún hueco financiero.

### También en este bloque (revisión de CodeRabbit, cinco hallazgos válidos)

- **Reintento e identidad.** El atajo de idempotencia devolvía la respuesta guardada
  buscando solo la clave y luego le sobrescribía metadatos con la nueva solicitud. Ahora
  compara los datos que identifican la operación —proyecto, fecha, importe, beneficiario,
  código— contra el documento persistido, rechaza la reutilización si difieren y devuelve
  la respuesta tal como se guardó. `payload_hash` no sirve aquí: el núcleo lo calcula
  sobre su payload preparado, que incluye una huella de saldos previos y por eso nunca
  vuelve a coincidir en un reintento.
- **Anulación de ingreso.** Reconocía el reintento demasiado tarde: la vista previa valida
  que la fuente siga siendo anulable y tras la primera anulación ya no lo es. La consulta
  pasa delante.
- **Validador de la Constitución.** Contaba trece casillas sin mirar su contenido. Ahora
  exige los trece requisitos por texto y prohíbe que `AGENTS.md` reproduzca la lista en vez
  de referenciarla (Capítulo 44). Verificado degradando ambos documentos.
- **Contrato de diagnóstico.** Solo vetaba `assert.equal`; ampliado a `assert(x.ok())`,
  `assert.ok(...)` y `assert.strictEqual(...)`, y a esperas de etapa con variable.

### Pruebas

294 contratos —el nuevo verificado reintroduciendo el defecto—, validadores, `ruff`,
prettier y `node --check` en verde.

## Bloque 13 — Validación 1:1 de las Partes 2 y 3, y las tablas que no dejaban trabajar

### Cómo se validó

Capítulo por capítulo contra el repositorio, no por impresión. Lo mecánicamente
comprobable se comprobó con comandos; lo demás se contrastó con el código.

| Capítulo | Estado | Evidencia |
| --- | --- | --- |
| 12 Ciclo · 16 Causa raíz · 19 Validación | ✅ | Bloques 9–12: diagnóstico → causa → contrato verificado |
| 13 Priorización | ✅ | El recorrido roto (Nivel 1) se atendió antes que cualquier refactor |
| 20 Deuda · 21 Documentación | ✅ | Tabla de deuda viva; esta memoria explica qué, por qué y riesgos |
| 22 Commits | ✅ | `Check Commit Titles` en CI |
| **23 GitHub** | ⚠️ | **29 ramas remotas; ~27 abandonadas.** Ver abajo |
| 24 Prohibiciones · 25 Continuidad | ✅ | Sin auditorías eternas; cada bloque cierra con código publicado |
| 26 Producto único · 27 Dominio · 30 Identidad visual | ✅ | Una sola carcasa `nxr-product-shell`, un solo sistema de estilos |
| 28 Navegación · 29 Panel principal | ✅ | Diez rutas `nexora-*`; el panel muestra estado, actividad, alertas, indicadores, avance, documentos y acciones rápidas |
| **33 Tablas · 34 Componentes** | ❌→✅ | **Corregido en este bloque** |
| 35 Flujos · 39 Errores | ✅ | Ingreso y gasto de extremo a extremo; errores con causa y remedio |
| 36 Consistencia | ✅ | `window.nexora.rules` y ahora `window.nexora.tables`, una regla en un lugar |
| 37 Móvil y PWA | ✅ | Recorrido en escritorio, iPhone WebKit y PWA; contrato de precarga sin conexión |
| 38 Rendimiento percibido | ✅ | `freeze_message` en cada llamada larga, estados vacíos explicados |

### El hueco real: dieciséis tablas que solo se podían mirar

Diez pantallas, dieciséis tablas: **ninguna se podía ordenar y solo Reportes exportaba**.
El Capítulo 33 exige buscar, filtrar, ordenar, exportar, acciones, estado, indicadores y
resumen; el 34 prohíbe resolverlo pantalla por pantalla, que habría creado diez variantes
del mismo comportamiento.

`public/js/nexora_tables.js` mejora las tablas **elegibles** de NEXORA desde un único
lugar, sin que la pantalla tenga que pedirlo. Elegible es la que sirve para trabajar:
`isWorkSurface(table)` deja fuera las declaradas `data-nxr-table="plain"` y las que no
llegan a dos filas, porque ordenar o exportar una sola línea no significa nada.

- orden por columna, con tipo detectado —fecha ISO, fecha local, importe formateado,
  texto con acentos— y empate resuelto por el orden original;
- accesible con teclado y `aria-sort`, así que también se opera en móvil y con lector;
- exportación CSV con comillas escapadas y BOM, para que Excel no rompa los acentos;
- resumen de filas que sigue al repintado de la pantalla en vez de congelarse.

`test_tables_contract.py` fija las cuatro capacidades y prohíbe que una pantalla
reimplemente el orden por su cuenta. El contrato de PWA ya existente detectó por su cuenta
que el bundle nuevo faltaba en la precarga sin conexión: corregido.

### Hallazgos de revisión atendidos

- **Anulación de ingreso.** Su reintento devolvía la respuesta guardada sin comparar nada.
  Su huella canónica —fuente, proyecto, fecha, importe, motivo— no depende de saldos, así
  que un reintento legítimo la reproduce intacta: ahora se exige antes de reutilizar. La
  huella vive en `_income_cancellation_stable`, en un único lugar.
- **Gasto.** La comparación se amplía a centro de costo, categoría económica, medio de pago
  y la distribución de fondos, leída de los efectos que la operación dejó.
- **Validador de la Constitución.** Extrae el texto de cada casilla en vez de buscarlo en
  todo el capítulo: trece casillas arbitrarias con un párrafo enumerando los requisitos ya
  no pasan.

### Pendiente de autorización (Capítulo 5)

`git ls-remote` muestra **29 ramas**: `main`, la rama de trabajo y ~27 abandonadas
(`copilot/*`, `fix/remediation-*`, `codex/*`, `jules-*`, `Clopezgg-patch-*`,
`revert-35-*`). El Capítulo 23 prohíbe mantenerlas, pero borrarlas es irreversible y el
Capítulo 5 reserva esa decisión. Borrar una rama ya fusionada no destruye nada —sus
commits viven en `main`—; borrar una no fusionada sí. Falta autorización para proceder
con las fusionadas.

## Bloque 14 — El recorrido avanza dos etapas más: búsqueda y corrección

Cada corrección destapa el siguiente paso que nunca se había ejecutado. Dos en este
bloque, ambos con la causa impresa por el diagnóstico.

### Búsqueda universal: una excepción silenciaba el Enter

```text
[nexora] desktop-chromium failed — page errors:
TypeError: controls.query.get_input is not a function
```

`get_input()` no existe en los controles de Frappe. La excepción rompía el manejador de
teclado, así que pulsar Enter no lanzaba ninguna búsqueda y el recorrido esperaba 120 s
una petición que nunca salía. Sustituido por `$input`.

### Corrección auditada: una promesa sin elemento propio

```text
waiting for locator('.modal.show .modal-dialog').filter({ hasText: 'Anular operación' })
  .getByText('El original no será eliminado ni sobrescrito.', { exact: true })
— the page reported no errors.
```

La vista previa de la anulación respondía bien y el diálogo se pintaba, pero la frase
—que es **la promesa que sostiene toda la corrección auditada**: el usuario acepta anular
porque confía en que nada se pierde— era un nodo de texto suelto dentro del `alert`,
pegado al título. Sin elemento propio no se puede estilar, ni traducir como unidad, ni
comprobar: `exact: true` jamás podía encontrarla porque el contenedor incluye también el
título. Ahora vive en `<span class="nxr-correction-preserves">`.

No es un ajuste para complacer a la prueba: una afirmación de este peso merece ser un
elemento de primera clase de la interfaz (Capítulo 39). El contrato lo fija y se verificó
devolviendo la frase al nodo suelto.

### Estado del recorrido

Certificado hasta aquí: panel, ingreso completo, **gasto completo** —vista previa,
revisión, registro definitivo y reintento idempotente—, búsqueda universal, y ahora la
vista previa de la corrección auditada.

## Bloque 15 — El perfil de escritorio pasó entero; el móvil destapó dos defectos

### Escritorio: hasta reportes, con evidencia

`desktop-chromium` atravesó panel, ingreso, gasto, búsqueda universal, corrección auditada
y reportes: el libro del panel muestra la corrección ya contabilizada —`303 · Anulación
financiera · L 75.25` tachado, estado «Contabilizado»—. **El cierre semanal quedó fuera**:
es la etapa siguiente y todavía no ha pasado en ninguna ejecución de CI. El recorrido no
está certificado mientras esa etapa siga pendiente (Capítulo 41).

### Móvil: dos defectos que solo aparecen ahí

El perfil de iPhone nunca se había ejecutado, porque el de escritorio fallaba antes.

**1. La aserción del panel exigía un `<table>` visible.** En móvil la pantalla sustituye
la tabla por tarjetas y la oculta —diseño correcto, Capítulo 37—, así que el recorrido
fallaba sobre una interfaz que funciona. El requisito real es que el usuario vea los
movimientos recientes: ahora se acepta la tabla **o** sus tarjetas.

**2. Mi barra de tabla flotaba sobre una tabla oculta.** El componente del Bloque 13
inserta la barra encima de cada tabla; en móvil la tabla desaparece y la barra se quedaba
ofreciendo «Exportar CSV» y un recuento de algo que el usuario no tiene delante.
`syncToolbar` la oculta con su tabla, y el listener de `resize` la mantiene al día porque
girar el teléfono cambia la representación sin tocar el DOM.

### Sobre el contrato

La primera versión de la guardia comprobaba que `syncToolbar` **existiera**, no que se
**llamara**: al borrar la llamada seguía pasando. Corregida para inspeccionar el cuerpo
de `refresh`, y verificada de nuevo reintroduciendo el defecto. Un contrato que no se ha
visto fallar no prueba nada, y verlo fallar por el motivo correcto tampoco es automático.

## Bloque 16 — La tabla que no era tabla, y el cierre que se descartaba solo

### 1. Mi propio componente rompió el asistente

El recorrido dejó de poder pulsar «Continuar» en el asistente de operaciones: el botón
quedaba debajo de la barra fija de Frappe, que interceptaba el clic. La causa era mía. El
componente del Bloque 13 insertaba su barra encima de **toda** `table.table`, incluida
`.nxr-entry-table` —el resumen de la línea del movimiento, de una sola fila—, y esa altura
extra empujó el formulario. El Capítulo 34 pide un único componente reutilizable, no que
toda `<table>` se convierta en una rejilla de datos: ordenar y exportar una fila no
significan nada.

`isWorkSurface(table)` descarta las tablas declaradas `data-nxr-table="plain"` y las que no
llegan a dos filas, y `enhance` abandona **antes** de marcar la tabla, de modo que una que
empieza vacía y se llena después entra cuando de verdad tiene filas que ordenar. El
contrato comprueba las dos condiciones y que el abandono ocurra antes de insertar la barra;
verificado reintroduciendo cada defecto por separado.

### 2. El cierre semanal se descartaba a sí mismo

Con el asistente desbloqueado, el recorrido llegó por primera vez al cierre semanal y falló
allí: los KPI se pintaban, pero `.nxr-close-hash` quedaba vacío y la huella del motor
`nexora-analytics-v3` no aparecía. Nada en la página había fallado —el registro decía «the
page reported no errors»—, así que el cálculo se estaba borrando **después** de pintarse.

Sólo `calculationChanged()` vacía esa tarjeta, y sus disparadores eran los `change` de los
tres controles. Los controles de Frappe emiten `change` también al perder el foco, con el
mismo valor de siempre: pulsar «Calcular» quita el foco del proyecto, y el cálculo recién
pedido se descartaba solo. Es el mismo defecto del Bloque 12 en otra pantalla, y se resuelve
igual (Capítulo 36): `fieldChanged(fieldname)` compara contra el último valor conocido y
sólo entonces invalida.

Además, `calculationChanged(reason)` escribe `data-calculation-cleared-by` en la pantalla y
`renderCalculation()` lo borra, de modo que ninguna invalidación queda anónima; el validador
del navegador lee ese atributo y lo incluye en el fallo. Una tarjeta vacía sin motivo no
distingue «el motor no respondió» de «algo descartó el cálculo» (Capítulo 39).

### Sobre el contrato

Tres reintroducciones verificadas: quitar `fieldChanged` de un control, dejar una invalidación
sin motivo y quitar el atributo de diagnóstico. Un contrato preexistente exigía el literal
`calculationChanged()`; se ajustó a `calculationChanged(` porque la invariante real es que la
invalidación siga existiendo, no que sea anónima.

## Bloque 17 — El asistente que no avanza sin decir qué le falta

El recorrido retrocedió: la etapa 2 del asistente de ingresos, que en la ejecución
anterior había pasado, dejó de abrirse. El commit no tocó esa pantalla, así que no es una
regresión: es una carrera que unas veces muerde y otras no. El diagnóstico decía
`preview_invalidated_by: "field:channel"`, `visible_stages: ["1"]` — pero no decía **qué
dato principal faltaba**, que es lo único que explica por qué `validatePrimary` se negó a
avanzar.

Dos cosas, entonces:

**1. Que el asistente nombre lo que falta.** `validatePrimary` ya sabe exactamente qué
campos están vacíos; ahora lo escribe en `data-guided-missing`, y el recorrido lo publica
junto con el valor de cada campo principal. «La etapa 2 nunca se abrió» no distingue un
dato que el usuario no puso de un campo que la pantalla vació sola después de rellenarlo,
y esa diferencia es toda la diagnosis (Capítulo 39).

**2. Que la pantalla no se pise a sí misma.** Los manejadores de campo de la consola son
asíncronos y escriben en otros controles —cargar el proyecto, aplicar el modo de cuenta,
traer canal, moneda y referencia de una cuenta existente—. Se lanzaban sueltos: dos podían
solaparse y el último en terminar pisaba al anterior, y uno que terminara después de la
vista previa la anulaba recién nacida. Ahora se encadenan en el orden en que se piden y
`previewMovement()` espera a que la cadena termine antes de leer los valores.

No afirmo que esto sea la causa del fallo observado —el registro no la nombra, y por eso
el primer punto existe—. Afirmo que la carrera es real y que estaba ahí.

### Ciclo de vida de las tablas

Las pantallas repintan con `innerHTML`: la tabla mejorada se sustituye entera y varias
veces por sesión. Cada `enhance()` dejaba su `MutationObserver` y un listener de `resize`
propio, ambos reteniendo un nodo que ya no está en el documento. Ahora hay un registro de
tablas vivas, un único listener global, y `release()` desconecta y olvida las que dejaron
de estar conectadas —en cada pasada y al cambiar el tamaño—.

### Sobre el contrato

Tres reintroducciones verificadas: quitar la espera de `previewMovement`, romper la
cadena de trabajo pendiente y quitar el diagnóstico de campos faltantes. El contrato de
tablas exige además un único listener de `resize` y que `release()` se llame de verdad.

## Bloque 18 — Partes 4 y 5 de la Constitución: lo que faltaba de verdad

Validación 1:1 de los Capítulos 43 a 74 contra el repositorio. La mayoría ya tenía
respuesta con evidencia —validación en servidor, auditoría, errores que no se silencian,
puerta de commits, rollback, la lista de trece puntos del Capítulo 60—. Dos capítulos no
la tenían:

**Capítulo 54 — validación visual.** Exige escritorio, **tableta**, móvil y PWA. El
recorrido solo abría dos perfiles: `desktop-chromium` a 1440×900 y `iphone-13-webkit`. La
tableta no es un escritorio estrecho ni un teléfono grande: es el ancho donde las rejillas
cambian de columnas y donde la aplicación decide entre tabla y tarjetas. Se añadió
`ipad-gen7-webkit`, y el nombre del job pasa a decir lo que recorre —lo que obligó a
corregirlo también en la certificación previa al despliegue, en el validador de aceptación
operativa y en la matriz de cumplimiento, que lo daban por «cumplido y demostrado»—. De
paso, el mensaje de desbordamiento decía «iPhone» en cualquier perfil; ahora nombra el
real.

**Capítulo 63 — hoja de ruta permanente.** No existía. `EXECUTION_STATE.md` es histórico y
`PROJECT_RECONSTRUCTION.md` registra la deuda; ninguno dice qué falta ahora ni en qué
orden. `ROADMAP.md` lo dice, ordenado por el Capítulo 64, y **referencia** la deuda en vez
de copiarla: dos copias de la misma lista divergen (Capítulos 44 y 67).

La matriz de cumplimiento afirmaba «CUMPLIDO Y DEMOSTRADO» sobre las superficies. No lo
está: el cierre semanal no ha pasado en ninguna ejecución y la tableta acaba de entrar al
recorrido. Queda marcado como abierto.

### Sobre el contrato

`test_constitution_governance_contract.py` comprueba que la hoja de ruta existe, cita su
origen, ordena por prioridad y no reproduce la deuda; verificado desordenando las
prioridades, copiando una fila de deuda y borrando el archivo. El contrato del recorrido
exige las cuatro superficies del Capítulo 54; verificado quitando el perfil de tableta.

## Bloque 19 — Lo que tapaba el botón, por fin nombrado

El registro del recorrido nombró los dos interceptores del clic sobre «Continuar»:

```
<form role="search" …> from <div class="sticky-top">…</div> subtree intercepts pointer events
<p title="Create a new Currency">…</p> from <div class="nxr-guided-fields" …> subtree intercepts pointer events
```

La barra fija de la aplicación por arriba, y **la lista de sugerencias de un campo Link
por abajo**. Escribir «HNL» en Moneda abre el desplegable de Frappe con su «Create a new
Currency», que se dibuja justo sobre el botón; tabular no siempre lo cierra, porque la
validación del enlace va al servidor y puede reabrirlo al volver. Eso explica las tres
ejecuciones anteriores: unas veces el clic no llegaba, otras llegaba tarde y la etapa 2 se
quedaba cerrada sin que nada fallara en la página.

Tres correcciones, dos del recorrido y una del producto:

- `setField` cierra la lista con `Escape` y **espera** a que se haya ido, en vez de confiar
  en el tabulador.
- `clickGuidedAction` centra el botón antes de pulsarlo: es lo que hace una persona sin
  pensarlo, y quita de en medio tanto la barra fija como cualquier desplegable. Los seis
  clics del asistente pasan por ahí; el contrato prohíbe volver a pulsarlos directamente.
- `scroll-margin-top` en las acciones y el progreso del asistente: al desplazar hacia un
  botón —por ancla, por foco de teclado o porque el navegador lo centra— dejaba de quedar
  debajo de la barra fija. Esta sí es del producto: le pasa a cualquiera que navegue con
  el teclado.

### Sobre el contrato

Verificado reintroduciendo tres defectos: pulsar directamente sin el ayudante, quitar el
`Escape` de `setField` y quitar la declaración del CSS. La tercera guarda no fallaba al
principio —buscaba la palabra `scroll-margin-top`, que también aparece en el comentario
que la explica— y se corrigió para mirar dentro de la regla. Una guarda que no puede
fallar no prueba nada; es la tercera vez en este trabajo que me pasa y la tercera vez que
se detecta reintroduciendo el defecto en vez de leyendo el contrato.

## Bloque 20 — El diagnóstico funcionó, y señaló mi propia corrección

Primera vez que el registro nombra la causa sin que haya que interpretarla:

```
guided_missing: "original_amount"
primary_values: { original_amount: "", currency: "HNL", channel: "Cash", … }
preview_invalidated_by: "field:account_mode"
```

El asistente no avanzaba porque **faltaba el importe** —un campo que el recorrido había
rellenado con `125.50` dos líneas antes—. Y lo vació yo: el `Escape` que añadí en el
Bloque 19 se pulsaba **después** de tabular, y `press` de Playwright enfoca el elemento
antes de teclear. Es decir, volvía al campo ya confirmado y lo dejaba vacío.

Dos correcciones:

- `Escape` va **antes** de `Tab`, mientras el campo aún tiene el foco y el texto escrito:
  cierra la lista de sugerencias sin volver a tocar el valor.
- `setField` comprueba, sobre el propio campo y en el momento, que conservó lo que se
  escribió. Un dato que se pierde en silencio no se descubre hasta que el asistente se
  niega a avanzar, y para entonces ya no se sabe quién lo vació.

El `preview_invalidated_by: "field:account_mode"` del mismo registro confirma además que
la pantalla sigue escribiéndose a sí misma al cargar el proyecto: eso es lo que la cadena
`pendingFieldWork` del Bloque 17 ordena, y no volvió a impedir avanzar.

### Sobre el contrato

Verificado reintroduciendo los dos defectos: pulsar `Escape` después de `Tab` y quitar la
comprobación del valor. Ambos hacen fallar la guarda.

## Bloque 21 — Centrar el botón no bastaba: se pulsa con el teclado

El registro de `f53dbc6f` volvió a mostrar los dos interceptores sobre «Continuar», ya
centrado: el formulario de búsqueda de la barra fija y el `<p title="Create a new
Currency">` del desplegable de Frappe. Centrar aparta el botón de la barra pero puede
meterlo justo debajo de la lista de sugerencias, que flota bajo su campo.

`clickGuidedAction` hace ahora tres cosas antes de activar: quita el foco —lo que cierra
la lista—, **espera** a que ninguna lista quede visible, y centra el botón. Y lo activa
con `Enter` sobre el botón enfocado en vez de con el ratón: un clic lo puede tapar
cualquier cosa que se dibuje encima; una pulsación de teclado activa el mismo manejador
sin que nada pueda interponerse, y es como opera quien no usa ratón (Capítulo 37).

Lección que ya va por su tercera aparición en este trabajo: **una corrección plausible no
es una corrección verificada**. Centrar el botón parecía suficiente y no lo era; solo el
registro de la ejecución siguiente lo demostró.

### Sobre el contrato

Verificado reintroduciendo dos defectos: volver al clic de ratón y quitar el cierre de la
lista. Ambos hacen fallar la guarda.

## Bloque 22 — Escritorio y tableta pasaron enteros; el móvil se repinta encima

Primer hecho verificable en muchas ejecuciones: en `54a3844e` el recorrido falló en el
perfil **`iphone-13-webkit`**. Los perfiles corren en orden —escritorio, tableta, iPhone—
y el recorrido aborta al primer fallo, así que llegar al iPhone significa que
**`desktop-chromium` y `ipad-gen7-webkit` completaron su recorrido entero**: panel,
ingreso, gasto, búsqueda universal, corrección auditada, reportes, **cierre semanal**, las
diez rutas y —en escritorio— la PWA. El cierre semanal no se había atravesado nunca, y la
tableta acababa de incorporarse.

La activación por teclado del Bloque 21 era, entonces, la corrección correcta.

El fallo que queda lo nombra la propia comprobación que añadí en el Bloque 20:

```
El campo origin_or_sender no conservó lo que se escribió:
se puso «Ingreso navegador iphone-13-webkit» y quedó «».
```

En el ancho del teléfono el asistente reordena los campos entre contenedores al ajustar el
diseño, y un control de Frappe que se vuelve a pintar pierde lo escrito. `setField`
reescribe **una vez** —lo que hace cualquiera al ver el campo en blanco— y deja constancia
en el registro; si tampoco así se queda, el fallo lo dice explícitamente. Reescribir en
bucle escondería un defecto real; no reescribir convertía un repintado en un rojo.

Queda anotado como sospecha de producto, no como hecho: si el repintado ocurre mientras el
usuario escribe, le pasa lo mismo. La siguiente ejecución dirá si hubo que reescribir.

### Sobre el contrato

Verificado quitando la reescritura: la guarda falla. Y exige que sea **una sola**.

## Bloque 23 — El iPhone pasó las operaciones; la búsqueda pedía una tabla oculta

En `5ec4da81` el perfil de iPhone **superó las operaciones guiadas** —la reescritura del
campo repintado funcionó— y el recorrido avanzó hasta la búsqueda universal, donde falló
así:

```
waiting for … .nxr-search-results tbody tr … filter({ hasText: '000000000026' }) to be visible
124 × locator resolved to hidden <tr>…</tr>
```

La fila **existe y está oculta**. En el ancho del teléfono la pantalla oculta la tabla y
muestra tarjetas a propósito (Capítulo 37): `#page-nexora-search .nxr-search-results
table { display: none }` y `enhanceMobileOperationalLists` construye las tarjetas con el
`innerHTML` de cada celda, así que el enlace al detalle sigue dentro. El producto está
bien; la comprobación exigía la representación equivocada.

Es **el mismo defecto que ya corregí en el panel** (Bloque 15), en otra pantalla. El
Capítulo 36 dice que el mismo problema se resuelve igual, y esta vez el contrato lo fija
para las dos: ninguna comprobación puede exigir solo la tabla.

### Sobre el contrato

Verificado devolviendo el selector a `tbody tr`: la guarda falla.

## Bloque 24 — Ocho esperas anónimas

`b8b90c4d` falló así:

```
page.waitForResponse: Timeout 120000ms exceeded while waiting for event "response"
```

Y no dice **cuál**. El recorrido tiene ocho esperas de llamada —vista previa y registro de
ingreso, de gasto y de la corrección, búsqueda universal y detalle del resultado— y todas
eran anónimas. Un fallo así obliga a elegir entre «la pantalla no pidió la vista previa» y
«no pidió el detalle de la búsqueda», que son dos correcciones distintas.

`apiResponse(page, fragment, label)` envuelve las ocho y, al expirar, dice cuál faltó: «La
pantalla nunca pidió «detalle del resultado de búsqueda» (get_search_result_detail) en
120 s». El contrato exige que `page.waitForResponse` solo aparezca dentro del ayudante.

### Una hipótesis descartada leyendo, no ejecutando

Parecía razonable que las tarjetas móviles no fueran pulsables: se construyen copiando el
`innerHTML` de las celdas, y copiar HTML no copia los manejadores de eventos. Pero la
pantalla de búsqueda enlaza por delegación —`$(page.body).on("click",
"[data-search-doctype]", …)`— y `page.body` contiene también las tarjetas. La hipótesis era
falsa y se descartó leyendo el archivo, sin gastar una ejecución de CI en comprobarla.

### Sobre el contrato

Verificado devolviendo una de las ocho esperas a su forma anónima: la guarda falla.

## Bloque 25 — El botón mudo: lo que perdí al cambiar el ratón por el teclado

El nombre que faltaba llegó a la primera:

```
La pantalla nunca pidió «registro definitivo del movimiento» (execute_operational_movement) en 120 s.
```

Y la causa es el cambio del Bloque 21. Un clic de ratón de Playwright **espera a que el
botón esté habilitado**; `focus()` + `Enter` no espera nada, y sobre un botón
deshabilitado no hace absolutamente nada. El botón de registro definitivo nace
`disabled` y lo habilita `sync()` cuando la revisión es válida: pulsarlo antes de tiempo
no fallaba, simplemente no ocurría, y el rojo aparecía 120 segundos después en la llamada
que nunca se pidió —lejos del botón que no respondía—.

Cambiar el ratón por el teclado quitó una interceptación y, sin darme cuenta, quitó
también una espera. `clickGuidedAction` espera ahora a que el botón esté habilitado y, si
no lo está en 60 s, lo dice sobre el botón en vez de sobre la llamada.

Además, tres flujos piden el mismo método: cada uno nombra el suyo —«del ingreso», «del
gasto», «de la corrección»—, porque «el registro definitivo» a secas no distingue cuál de
los tres se quedó sin pedir.

### Sobre el contrato

Verificado quitando la espera de habilitación y devolviendo una etiqueta a su forma
genérica: las dos guardas fallan.

## Bloque 26 — El `Escape` que impedía elegir la opción, y un hueco en la puerta

`2c5cf4f5` falló en **escritorio** —una regresión respecto a `54a3844e`— y el diagnóstico
lo dijo entero:

```
guided_missing: "project"   ·   project: ""   ·   preview_invalidated_by: "field:original_amount"
```

`project` es el primer campo que escribe el recorrido, y la comprobación de retención no
saltó: al escribirlo **sí** estaba, y se vació después. En un campo Link de Frappe, cerrar
la lista con `Escape` impide que se seleccione la opción, y el control descarta al perder
el foco lo que no llegó a validarse contra el servidor.

Ese `Escape` lo añadí yo en el Bloque 20 para quitar la lista de encima del botón, y ya no
hacía falta: desde el Bloque 21 la lista la cierra `clickGuidedAction` antes de pulsar.
Sobraba y hacía daño. Escribir y tabular es lo que hace el usuario.

Se añade además `assertWrittenFieldsHeld`, que revisa antes de cada «Continuar» que siga
ahí lo que se escribió. Un campo puede conservar el valor al escribirlo y perderlo
después; comprobarlo al avanzar convierte «la etapa 2 nunca se abrió» en «el campo project
se vació entre que se escribió y el momento de continuar».

### Un hueco en la puerta, encontrado por CodeRabbit

El flujo `nexora-app.yml` se dispara por rutas y **no incluía** `NEXORA_CONSTITUTION.md`,
`AGENTS.md` ni `scripts/validate_nexora_constitution.py`. Un cambio que solo tocara el
documento rector no ejecutaba la validación que lo guarda: la puerta estaba abierta justo
donde más importa. Corregido, y fijado por contrato.

De las otras dos observaciones de la misma revisión: la de `payload()` es **falsa** —
`account_mode` solo se muestra en el ingreso, y forzar `Manual` en el gasto fue la
corrección deliberada del Bloque 4, documentada en el propio código—; la de
`BANK_CHANNELS` es cierta y está ahora en la deuda registrada, con el motivo real de no
corregirla hoy: se intentó, y leerla de `window.nexora.rules` deja el conjunto vacío
cuando el modelo guiado se ejecuta fuera del navegador.

## Bloque 27 — La corrección auditada, y dos huecos del propio diagnóstico

`40ff9dbd` avanzó otra etapa: operaciones guiadas y búsqueda universal pasaron, y el
recorrido llegó a la corrección auditada.

```
La pantalla nunca pidió «vista previa de la corrección» (preview_operational_movement) en 120 s.
```

Dos cosas faltaban en el propio diagnóstico, y las dos se arreglan aquí:

**1. El mensaje no dice en qué perfil ocurrió.** Escritorio, tableta y teléfono son tres
correcciones distintas; el perfil se perdía al subir el error desde `runProfile`. Ahora
cada fallo llega con su prefijo: `[iphone-13-webkit] La pantalla nunca pidió…`.

**2. El botón del diálogo se pulsaba sin esperar a que estuviera habilitado.** Es
exactamente el agujero del Bloque 25, en otro sitio: pulsar un botón deshabilitado no hace
nada y el fallo aparece 120 segundos después en la llamada que nunca se pidió, lejos del
botón mudo. `clickDialogPrimary` espera, y si el botón sigue deshabilitado lo dice sobre
el botón. El Capítulo 36 pide resolver igual el mismo problema; el contrato prohíbe ahora
pulsar directamente cualquier botón principal de diálogo.

No afirmo que el botón deshabilitado sea la causa del fallo observado: no tengo evidencia
de eso todavía. Afirmo que con el diagnóstico anterior era imposible distinguirlo de media
docena de causas, y que ahora se distingue.

### Sobre el contrato

Verificado devolviendo el `throw error;` que perdía el perfil y devolviendo un clic
directo al diálogo: las dos guardas fallan.

## Bloque 28 — Cambio de estrategia: el recorrido deja de esconder lo que queda

Nueve rondas seguidas con el mismo procedimiento: leer el fallo, corregirlo, empujar,
esperar ocho minutos, leer el siguiente. Cada ejecución de CI rendía **un solo dato**,
porque el recorrido abortaba en la primera avería y todo lo que venía detrás quedaba sin
ejecutar. Y como los tres perfiles corrían en cadena, un fallo en escritorio dejaba
tableta y teléfono sin recorrer: hacían falta tantas ejecuciones como perfiles rotos
hubiera.

El defecto no estaba en ninguna de las nueve correcciones. Estaba en el diseño del
recorrido, que usaba CI como un depurador de un paso cada ocho minutos.

**Rediseño:**

- Cada etapa —panel, operaciones, búsqueda, corrección, reportes, cierre, rutas,
  manifiesto, PWA, responsive, tiempo real, sesión, ausencia de errores— se ejecuta
  aunque la anterior haya fallado, y registra su resultado por separado.
- Las que dependen de datos de otra lo **declaran** (`needs`) y se saltan diciendo por
  qué, en vez de fallar por arrastre y ensuciar el diagnóstico con averías derivadas.
- Al terminar el perfil se reportan **todas** las etapas sin superar, juntas.
- Los tres perfiles se recorren siempre; los fallos de los tres se acumulan y se
  publican en un único mensaje.

Una ejecución pasa a rendir el mapa completo de lo que falta en vez de la primera piedra
del camino. Además `validateResponsiveLayout` deja de correr solo en iPhone: el
desbordamiento horizontal se comprueba en las cuatro superficies, que es lo que pide el
Capítulo 54.

### Sobre el contrato

Verificado quitando la dependencia declarada de la etapa de búsqueda: la guarda falla. Y
comprueba etapa por etapa, no que la palabra aparezca en algún sitio del archivo —una
guarda que busca una cadena suelta pasa aunque la etapa concreta la haya perdido—.

## Bloque 29 — Un solo defecto, y esta vez es del producto

El recorrido rediseñado rindió el mapa completo en su primera ejecución:

```
[iphone-13-webkit] 3 etapa(s) sin superar:
  · operaciones: El campo origin_or_sender no conservó lo que se escribió … incluso tras reescribirlo.
  · busqueda: depende de operaciones, que no llegó a completarse
  · correccion: depende de operaciones, que no llegó a completarse
```

**Escritorio y tableta pasaron las trece etapas.** Del teléfono, dos de los tres apuntes
son saltos declarados, no averías. Queda **un defecto**, y leyendo el código —no
adivinando— resulta ser del producto:

`loadProjectData()` ponía `account_mode = "Existing"` en cuanto el proyecto tenía cuentas
guardadas. `applyAccountMode()` entonces deja origen, canal, moneda y referencia en solo
lectura, y `control.refresh()` los repinta: lo que la persona acababa de escribir
desaparece y el campo queda bloqueado. Pero el asistente **sigue exigiendo el origen** para
avanzar de la primera etapa. La pantalla pedía un dato que ella misma impedía teclear
(Capítulo 46).

Por qué aparecía solo en el teléfono: los tres perfiles recorren el mismo sitio en cadena y
el teléfono va tercero, cuando el proyecto ya tiene cuentas. No es una particularidad de
iOS; es orden de ejecución. En escritorio el mismo defecto está latente y aparecería en
cuanto el proyecto tuviera una cuenta guardada — es decir, **le pasa a cualquier usuario
real desde su segunda operación**.

La corrección: el modo neutro es `Manual` —no guarda nada y deja escribir—, y usar una
cuenta existente vuelve a ser lo que siempre debió ser, una elección explícita que el
asistente ofrece en su segunda etapa. La pantalla deja de elegir por el usuario.

### Sobre el contrato

Verificado devolviendo la elección automática: la guarda falla. Comprueba además que el
bloqueo siga atado a «Existing», para que el modo neutro no acabe bloqueando por otra vía.

## Bloque 30 — La causa raíz real: la pantalla se repintaba encima del usuario

La corrección del bloque anterior movió el fallo a escritorio, y el informe consolidado lo
dijo entero —cuatro apuntes, dos de ellos saltos declarados—:

```
[desktop-chromium] 4 etapa(s) sin superar:
  · operaciones: El campo original_amount no conservó lo que se escribió … incluso tras reescribirlo.
  · sin-errores: desktop-chromium emitted page errors → ['undefined']
```

Eso obligó a mirar más abajo, y la causa raíz **no era el modo de cuenta**:

```js
function toggle(name, visible, required = false) { …; control.refresh(); }
function setReadOnly(name, readOnly)            { …; control.refresh(); }
```

`refresh()` repinta el control desde el modelo, y con él se va lo que la persona está
escribiendo y todavía no ha confirmado. La consola llama a `toggle` y `setReadOnly` **en
cascada** cada vez que cambia el proyecto, el modo de cuenta o el medio de pago —diecisiete
llamadas por pasada—, casi siempre para dejar el control **exactamente como estaba**. Un
repintado inútil que llega en mitad de la escritura vacía el campo.

Por eso el defecto parecía saltar de un campo a otro y de un perfil a otro: dependía de en
qué milisegundo caía la cascada. Y por eso mi cambio del Bloque 29 lo movió de sitio en vez
de resolverlo: convirtió un `set_value` que era no-op en un cambio real, y con ello adelantó
la cascada.

**La corrección:** `toggle` y `setReadOnly` solo repintan cuando algo cambió de verdad. No
es una optimización; es la diferencia entre poder escribir y no poder. El modo neutro
`Manual` del bloque anterior se mantiene —la pantalla no debe elegir por el usuario— y
ahora es seguro.

### Sobre el contrato

Verificado quitando cada una de las dos salidas tempranas: las guardas fallan por separado.
Comprueban además que la salida esté **antes** del repintado, no en cualquier sitio de la
función.

## Bloque 31 — Recorrido certificado en las tres superficies

Sobre `main` en `c96ced6a`, ejecución `31032214468`:

| Trabajo | Resultado |
|---|---|
| `Frappe real · escritorio · tableta · iPhone · PWA` | **success** |
| `install-rollback` (15 pasos, incluido el 14 contra el bench real) | success |
| `contract` | success |
| `Linters`, `NEXORA production validation`, `NEXORA financial invariants`, `NEXORA final acceptance and delivery` | success |
| `NEXORA predeploy certification receipt` | **success** |

El recibo de certificación previa al despliegue es el que más pesa: espera a los **nueve**
controles obligatorios —linters, semgrep, secrets, contract, install-rollback, el
recorrido, mariadb, la aceptación operativa de las fases 2 y 3 y el paquete final
verificado— y solo publica éxito si todos cierran. Cerró en verde.

Dentro del recorrido, el paso «Repetir la causa del fallo al final del registro» aparece
**omitido**: corre con `if: failure()`, así que su omisión es la prueba de que no hubo
avería. Las trece etapas pasaron en `desktop-chromium`, `ipad-gen7-webkit` e
`iphone-13-webkit`: panel, ingreso guiado, gasto guiado, búsqueda universal, corrección
auditada, reportes, **cierre semanal**, las diez rutas, manifiesto, PWA, responsive, tiempo
real y ausencia de errores de página, de consola, de servidor y de autorización.

### Lo que hizo falta para llegar aquí

Nueve rondas de corrección una-por-una no bastaron; el desbloqueo vino de dos decisiones de
diseño, no de más parches:

1. **Que el recorrido dejara de abortar** (Bloque 28). Mientras abortaba en la primera
   avería, cada ejecución de ocho minutos rendía un solo dato y escondía el resto. Al
   reportarlas todas, una ejecución dio el mapa completo.
2. **Bajar del síntoma a la causa común** (Bloque 30). El defecto parecía saltar de campo
   y de perfil porque `toggle` y `setReadOnly` repintaban el control aunque nada hubiera
   cambiado, y el repintado se llevaba lo que el usuario estaba escribiendo.

Y el último, el del Bloque 31 ya fusionado: el asistente decidía si podía avanzar mirando
`go.disabled` —estado de pintado, que parpadea— en vez de la validez real.

### Lo que sigue abierto, sin adornos

*(Estado en el momento del Bloque 31. Se conserva como registro histórico; lo que sigue
abierto hoy vive en [`ROADMAP.md`](ROADMAP.md), que es el documento vivo.)*

- ~~El Capítulo 53 pide recorrer ocho operaciones; el recorrido cubre **tres** (crear,
  consultar y anular). Editar, aprobar, rechazar, corregir y exportar no se recorren.~~
  **Cerrado en el Bloque 32.**
- No hay prueba negativa de permisos por rol en los cincuenta métodos expuestos.
- El módulo de inventario no tiene prueba de integración propia.
- La huella canónica versionada al reservar la clave de idempotencia sigue siendo deuda.
- Veintinueve ramas remotas llevan commits que no están en `main`. El recuento y el
  contenido de cada una viven en
  [`docs/architecture/BRANCH_ARCHIVE.md`](docs/architecture/BRANCH_ARCHIVE.md), que es la
  única fuente: dos documentos contando ramas por su cuenta terminan discrepando, y el
  borrado autorizado depende de esa cifra.

## Bloque 32 — Las ocho operaciones del Capítulo 53

El capítulo pide recorrer, «como mínimo: crear, editar, consultar, aprobar, rechazar,
anular, corregir y exportar». El recorrido ejercía tres. Las otras cinco se daban por
buenas, que es exactamente lo que el capítulo prohíbe: «no se asume que funciona: se
comprueba».

| Operación | Dónde se recorre ahora | Qué se afirma |
|---|---|---|
| Crear | Asistente 101 y 102 | Documento de doce dígitos y repetición idempotente |
| Editar | Formulario contabilizado + «Corregir fecha o datos» | La edición en sitio se rechaza **y** la corrección auditada cambia el dato de verdad |
| Consultar | Búsqueda universal y lista de comprobantes | El documento aparece en tabla o en tarjeta, según el ancho |
| Aprobar | Comprobantes → «Validar» | El comprobante queda `Validated` |
| Rechazar | Comprobantes → «Rechazar» | La versión sustituta queda `Rejected` |
| Anular | Formulario → «Anular operación» (303) | Compensación auditada; el original se conserva |
| Corregir | Diálogo «Corregir operación contabilizada» | Número de corrección distinto y dato efectivo releído del servidor |
| Exportar | Barra del libro operativo + impresión del documento | CSV descargado con BOM y con el número dentro; `printview` responde 200 |

Esta tabla dice **qué recorre el recorrido**, no que esté certificado. Los contratos leen
el guion y comprueban que cada operación tiene su etapa, su llamada y su afirmación; leer
un guion no es ejecutarlo. La certificación es la ejecución en verde del trabajo `Frappe
real · escritorio · tableta · iPhone · PWA`, y hasta que exista la fila del Capítulo 53
sigue abierta en [`ROADMAP.md`](ROADMAP.md) con su identificador pendiente de citar.

### Dos decisiones que conviene no enterrar en el código

**«Editar» no es editar.** Sobre un libro inmutable no existe modificar en sitio, y la
pantalla lo dice: campos de solo lectura, guardado desactivado y un aviso que remite a la
corrección. Recorrer «editar» comprobando solo la corrección habría dejado sin vigilar la
mitad que protege la auditoría —que el atajo esté cerrado—, así que la etapa afirma las
dos: la negativa y el camino que sí funciona.

**«Exportar» no puede exigir lo mismo en los tres perfiles.** En el ancho del teléfono la
pantalla sustituye la tabla por tarjetas y retira la barra con ella a propósito (Capítulo
37): ahí no hay CSV que pulsar, y exigirlo sería declarar roto un diseño correcto. La
etapa registra qué salida ejerció cada perfil y, al terminar los tres, exige que el CSV se
haya descargado **en alguno**. Sin esa última exigencia, una comprobación que se salta
sola en los tres perfiles pasaría sin comprobar nada, que es la clase de verde que este
proyecto ya pagó caro.

### Un cambio de enfoque, y por qué

El comprobante exige archivo privado real: el servidor verifica que el `File` existe, que
es privado y que su contenido no está vacío. La primera intención fue conducir el cargador
de ficheros de Frappe desde el navegador; se descartó antes de escribirlo. Ese cargador es
código del marco, su DOM no se puede verificar desde aquí, y cada suposición equivocada
habría costado una ejecución de ocho minutos —la misma trampa que costó nueve rondas en el
Bloque 28—. El archivo se sube ahora por el mismo `upload_file` que usa el cargador, con la
sesión viva del navegador; lo que el Capítulo 53 manda recorrer son las ocho operaciones
del producto, y esas se ejercen pulsando los botones de la pantalla.

### Lo que encontró el recorrido en su primera vuelta

Dos defectos, y los dos son **del producto**, no de la prueba. Para eso está.

**El diálogo de corrección se abría prometiendo cargar el documento y no cargaba nada.**
Falló en los tres perfiles, siempre igual: «la pantalla nunca pidió la carga del documento
a corregir». `set_value` de un diálogo de Frappe es asíncrono; llamar a la búsqueda en la
línea siguiente leía el campo todavía vacío, salía por `if (!number) return` y la petición
no llegaba a hacerse. El usuario veía el número escrito delante y un diálogo que no hacía
nada hasta pulsar «Buscar documento» sobre un campo que ya estaba relleno.

**En escritorio, una tabla perfectamente visible se quedaba sin su botón «Exportar CSV».**
El registro lo dijo con precisión: *124 × locator resolved to hidden*. Dos causas
encadenadas. `syncToolbar` decidía con `offsetParent`, que también vale nulo cuando un
ancestro está posicionado de forma fija, así que confunde «no se ve» con «se ve y cuelga de
algo fijo»; ahora decide con los rectángulos del elemento, que valen cero solo si no se
pinta. Y esa decisión se tomaba una vez y no se revisaba nunca: el observador del cuerpo
solo mira los datos, y mostrar una pantalla no cambia el tamaño de la ventana. Una tabla
mejorada mientras su pantalla aún no estaba pintada nacía con la barra oculta —correcto en
ese instante— y se quedaba así para siempre. La visibilidad se vuelve a decidir en cada
pasada, y el observador global escucha además los atributos con los que Frappe muestra y
esconde pantallas.

Las tres guardas nuevas se comprobaron reintroduciendo cada defecto: las tres fallan. Una
guarda que no falla cuando el defecto vuelve no es una guarda, y este proyecto ya escribió
tres de esas.

### Sobre el contrato

`test_browser_suite_walks_the_eight_operations_of_chapter_53` exige una etapa por
operación dentro del corredor que no aborta, las seis llamadas de servidor implicadas, las
dos decisiones de revisión por separado, el estado `Superseded` del comprobante original,
la descarga real del CSV y la exigencia de que algún perfil la ejerza. El contrato de
diagnóstico dejó de fijar en «ocho» el número de esperas nombradas —crecía con el
recorrido y solo garantizaba tener que actualizarlo— y ahora comprueba lo que no puede
cambiar: que ninguna espera de red quede sin nombre.

## Bloque 33 — Reconstrucción visual: identidad, acceso, carcasa y panel

Mandato explícito del responsable: dejar de parecer ERPNext modificado. Prioridad
absoluta sobre la deuda técnica pendiente (permisos por rol, huella canónica), que queda
registrada y espera su turno.

**Sistema de diseño propio** (`nexora_design_system.css`): tokens en tres capas
—primitivas, semántica, componentes—, escalas completas de espaciado, radio, tipografía
con interlineado por paso, elevación y movimiento. Tema oscuro que reasigna semántica y
nunca primitivas. Se carga primero de todas las hojas porque las demás consumen sus
variables. La paleta prestada de Google (`#1a73e8` y compañía) desapareció del CSS, del
manifiesto y del logotipo; las variables históricas de `nexora.css` pasaron a ser alias
del sistema nuevo, así que las diez pantallas existentes adoptan la identidad sin que se
tocara una sola de ellas.

**Acceso propio** (`www/login.py` + `www/login.html`): sustituye la pantalla del marco
por precedencia de aplicación. El contexto de autenticación —redirección saneada,
proveedores externos, LDAP, límite de intentos— lo sigue construyendo
`frappe.www.login.get_context`; reimplementarlo habría significado mantener una copia de
las reglas de acceso del marco en la superficie donde un error no se paga con una
pantalla fea sino con una puerta abierta.

**Carcasa** (`nexora_shell.js` + `nexora_shell.css`): navegación de doce destinos
agrupados en cuatro secciones por la pregunta que cada una responde, en vez de una tira
de enlaces inyectada y reconstruida seis veces por navegación. Se monta solo en rutas de
NEXORA y no toca nada del escritorio del marco fuera de ellas.

**Panel** (`nexora_command_center.css` + `renderAgenda` en `nexora_dashboard.js`): banda
«Qué requiere su atención hoy» antes que cualquier tarjeta, jerarquizada por lo que
cuesta no atenderlo. No pide datos nuevos al servidor; reúne lo que el panel ya recibía.

### El defecto de arquitectura que encontró el recorrido, y por qué la primera versión estaba mal

La primera versión de la carcasa **reparentaba `#body`**: el contenedor donde el
enrutador de Frappe construye cada pantalla se movía con `appendChild` dentro de un
`.nxr-shell__content` propio, para envolverlo con la barra y la navegación sin
duplicarlo. El razonamiento parecía sólido —mover un nodo conserva sus manejadores— pero
pasaba por alto que el enrutador no solo llena `#body`: en algún punto de su ciclo de
render asume que esa raíz permanece donde estaba cuando la resolvió, y moverla la dejó en
un estado del que no se recupera.

El recorrido real lo mostró en los tres perfiles, siempre igual:

```
nexora-dashboard did not reach a stable rendered state:
{"page_exists": false, "page_visible": false, "page_text": ""}
```

`#page-nexora-dashboard` no llegaba a existir. No se repintaba distinto: desaparecía. Tres
ejecuciones de CI se gastaron confirmando el mismo síntoma antes de que el diagnóstico
señalara la causa con precisión.

**La corrección no es un parche sobre `adopt()`: es no tener `adopt()`.** La carcasa no
mueve nada del marco. La navegación y la barra son elementos `position: fixed` que flotan
por encima del contenido; `.nxr-shell` en sí es `display: contents` —una agrupación sin
caja propia— para que sus hijos actúen como si colgaran directamente de `<body>`. El
contenido se queda exactamente donde el enrutador lo construyó, y lo único que la carcasa
le pide es espacio: `padding-left` y `padding-top` en `<body>`, reactivos al estado de
navegación contraída mediante un atributo espejado en `<html>` (`data-nxr-shell-collapsed`),
porque `<body>` no es descendiente de `.nxr-shell` y no hay otro ancestro común desde el
que una regla CSS pueda leer ese estado.

Es una arquitectura más simple que la que sustituye, no solo más segura: sin nodo que
mover, sin `release()` que deshacer al salir de NEXORA, sin la clase entera de fallos que
nace de reparentar la raíz de otra aplicación.

### Guardas nuevas, comprobadas contra su propio defecto

`test_the_shell_never_relocates_the_frameworks_content` prohíbe por nombre exacto
`getElementById("body")`, `appendChild(container)` y las funciones `adopt`/`release` en
`nexora_shell.js`, y exige `display: contents` en `.nxr-shell` y el relleno en
`.nxr-shell-active body`. Se comprobó reintroduciendo la función `adopt()` original: la
guarda falla, con las tres razones nombradas por separado.

`validateShell` en el recorrido real pasa de exigir que `#body` viviera dentro del marco
de contenido a exigir lo contrario: que `#page-nexora-dashboard` siga existiendo con la
carcasa montada, y que `#body` no aparezca dentro de `.nxr-shell__nav` ni de
`.nxr-shell__bar`. Su espera de visibilidad se movió de `.nxr-shell` —que ya no genera
caja propia, así que la comprobación de Playwright nunca habría resuelto sobre ella— a
`.nxr-shell__bar`, que es lo que de verdad se pinta.

### Estado de certificación

Código publicado, 343 contratos en verde, `ruff`, `prettier`, `node --check` limpios. La
captura visual (`scripts/nexora_ui_preview.mjs`) confirma que los tres estados —completa,
contraída, cajón en móvil— se ven idénticos a la versión que reparentaba el DOM, ahora sin
tocarlo. **Lo que falta, y no se sustituye por lo anterior:** la ejecución en verde del
trabajo `Frappe real · escritorio · tableta · iPhone · PWA` sobre el commit que contiene
esta corrección. Escrito y verificado por contrato no es lo mismo que certificado en
navegador real (Capítulo 53); hasta ese verde, el Bloque B sigue abierto en
[`ROADMAP.md`](ROADMAP.md).

### Segunda vuelta del recorrido: dos defectos nuevos, ninguno del `#body`

El recorrido sobre `5a34c00d` confirmó que la carcasa quedó bien —ningún perfil volvió a
mostrar `page_exists: false`— pero encontró dos defectos distintos, uno por perfil:

**iPhone, etapa `correccion`:** «la pantalla nunca pidió la aplicación de la corrección de
datos» en 120 s. Mismo defecto que ya se había corregido una vez en el diálogo hermano de
corrección rápida (`nexora_quick_flows.js`), vivo todavía en `openCorrectionDialog`
(`nexora_operational_ui.js`): nueve campos usaban `onchange: invalidate` a secas, sin línea
base ni comparación, así que cualquier blur —incluido el que provoca pulsar el botón del
pie del diálogo— anulaba la vista previa vigente y el botón volvía a decir «Vista previa» en
vez de ejecutar. Se aplicó el mismo patrón: un arreglo `TRACKED` con los doce campos, un
`Map` `seen` con el último valor visto de cada uno, y `remember()` fijando la línea base al
terminar de cargar el documento y al aceptar cada vista previa. `invalidate(fieldname)` solo
anula si el valor realmente cambió frente a esa línea base. Guarda:
`test_the_operational_correction_dialog_survives_the_blur_of_its_own_button`
(`test_browser_diagnostics_contract.py`), comprobada reintroduciendo el `onchange: invalidate`
sin nombrar campo: falla.

**Escritorio, etapa `operaciones`:** «Guided stage 4 never opened», con diagnósticos que no
mostraban nada roto —botón «Continuar» habilitado, vista previa vigente, consola original
habilitada—. La causa: el asistente guiado (`nexora_guided_operations.js`) ya sabía que
`reviewValidity(root)` parpadea —la consola original apaga y enciende sus botones al
refrescarse— y por eso `sync()` pinta el botón «Continuar» con un estado **asentado**
(`usable`, con margen `SETTLE_MS` de 400 ms) en vez del instantáneo. Pero el manejador del
clic sobre `data-guided-next="4"` seguía comprobando `reviewValidity(root)` en crudo: el
botón se veía habilitado —pintado con el estado asentado, más permisivo— y el clic caía
justo en el parpadeo del estado instantáneo, más estricto. El asistente rechazaba avanzar
con un aviso naranja que nadie llegaba a ver, y la etapa 4 no se abría nunca. La corrección
no añade una segunda tolerancia: guarda el `usable` que `sync()` ya calcula en
`state.reviewUsable` y hace que el manejador del clic lea exactamente ese valor, el mismo
que pinta el botón, en vez de recalcular una versión distinta y más estricta. Guarda:
`test_advancing_is_decided_by_the_settled_truth_not_by_a_blink`
(`test_guided_wizard_contract.py`, sustituye a la prueba anterior que fijaba el
comportamiento incompleto), comprobada reintroduciendo la lectura cruda en el manejador:
falla.

344 contratos en verde (343 más esta guarda), `ruff`, `node --check` limpios. Sigue
pendiente la misma condición: el Bloque B no cierra hasta que el recorrido real pase en
verde sobre el commit con ambas correcciones.

## Siguiente bloque

**Bloque 34 — el resto de la reconstrucción visual.** Zonas restantes del panel (Bloque
C), llevar los componentes `nxr-ds-` a las diez pantallas que aún usan `btn btn-xs` y
`table table-bordered` del marco (Bloque D), y reconstrucción progresiva del resto de
módulos (Bloque E). Después: permisos por rol —no hay prueba negativa sobre los cincuenta
métodos expuestos, hoy se comprueba que el autorizado puede, nunca que el no autorizado no
puede— y la huella canónica versionada en la reserva de idempotencia.
