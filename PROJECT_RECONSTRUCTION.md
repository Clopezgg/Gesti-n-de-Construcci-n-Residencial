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

```
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

## Deuda registrada (no corregida aquí)

| Elemento | Motivo de no corregirlo ahora |
|---|---|
| `test_operational_integration.py:13` viola `E402` (import tras `test_dependencies`) | Preexistente y deliberado: Frappe exige `test_dependencies` antes de importar módulos que tocan esos DocTypes |
| `cr-gpt[bot]` comenta en cada PR que falta `OPENAI_API_KEY` | Configuración del repositorio: o se configura o se desinstala la app |
| Cobertura de docstrings 14,91% según CodeRabbit | No es puerta del repositorio; documentar por umbral no mejora el producto |

## Siguiente bloque

**Bloque 4 — cerrar el recorrido de navegador.** Con el nombre exacto de la regla que
rechaza la vista previa del gasto (que entregarán `install-rollback` y el propio
recorrido en la próxima ejecución), corregir la causa: o el flujo guiado no envía algo
que el servidor exige, o el servidor exige algo que la pantalla nunca pide —y en ese
segundo caso la corrección es de producto, no de la sonda.
