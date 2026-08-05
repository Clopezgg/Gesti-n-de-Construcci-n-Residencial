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

## Deuda registrada (no corregida aquí)

| Elemento | Motivo de no corregirlo ahora |
|---|---|
| `test_operational_integration.py:13` parece violar `E402` | Falsa alarma de ruff 0.15.8: con la 0.16.0 que usa CI el árbol pasa limpio. El orden es deliberado — Frappe exige `test_dependencies` antes de importar módulos que tocan esos DocTypes |
| `cr-gpt[bot]` comenta en cada PR que falta `OPENAI_API_KEY` | Configuración del repositorio: o se configura o se desinstala la app |
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

## Siguiente bloque

**Bloque 8 — confirmar el recorrido completo.** Con la etapa 3 ya sin carrera y el
gasto reparado, el recorrido debería avanzar por ingreso y gasto hasta el registro
definitivo. Falta ver `install-rollback` ejecutar la suite operativa: es la primera vez
que corre y es quien da fe del runtime.
