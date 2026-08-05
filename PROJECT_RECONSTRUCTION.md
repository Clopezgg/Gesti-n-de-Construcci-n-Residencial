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

## Deuda registrada (no corregida aquí)

| Elemento | Motivo de no corregirlo ahora |
|---|---|
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

```
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

## Siguiente bloque

**Bloque 11 — cerrar el gasto.** Con el motivo nombrado, la corrección es directa: si es
`field:<nombre>`, la pantalla se está escribiendo a sí misma y hay que distinguir la
escritura programática de la edición del usuario; si es `allocation-amount`, el panel de
fondos se repinta después de la vista previa.
