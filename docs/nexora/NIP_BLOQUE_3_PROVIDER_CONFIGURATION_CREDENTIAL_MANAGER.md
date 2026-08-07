# NEXORA Intelligence Platform — Bloque 3: AI Provider Configuration & Credential Manager

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> (secciones 7 y 8) y a [`AGENTS.md`](../../AGENTS.md). Continúa
> [`NIP_BLOQUE_2.1_EXPANSION_PROVEEDORES.md`](NIP_BLOQUE_2.1_EXPANSION_PROVEEDORES.md)
> sin reescribir la arquitectura de los Bloques 1 y 2 — ver "Compatibilidad" más abajo.

## Qué hace este bloque

Cierra la pieza que los Bloques 1 y 2 dejaron explícitamente pendiente: hasta ahora,
`NXR AI Provider` podía registrar la *identidad* de un proveedor (clave, capacidades,
prioridad, estado) pero no había ningún lugar seguro donde guardar su credencial, ni
metadatos operativos (modelo por defecto, límites, costo relativo). Este bloque añade
ambas piezas — Provider Configuration y API Key Manager
(`NEXORA_INTELLIGENCE_ARCHITECTURE.md`, secciones 7 y 8) — sin tocar cómo Bloques 1 y 2
resuelven o despachan un proveedor.

## Qué no hace todavía

- **No conecta ningún proveedor real.** Guardar y validar el *formato* de una API key no
  es lo mismo que llamarla contra el proveedor — eso sigue sin ocurrir en todo el
  subsistema.
- **No hace ninguna llamada HTTP.** "Validar" una credencial en este bloque significa
  únicamente: no está vacía, no tiene espacios al borde, tiene una longitud razonable y
  no es un valor de plantilla obvio (`REEMPLAZAR_CON_...`, `changeme`, …). Por eso el
  estado resultante se llama `"Format Valid"`, nunca `"Valid"` a secas — no confirma que
  el proveedor vaya a aceptarla.
- **No crea ninguna interfaz gráfica.** La "interfaz mínima" que pide el requisito 13 del
  encargo es la propia API `@frappe.whitelist` (`save_credential`,
  `update_provider_config`, `set_default_provider`), invocable por un Administrator
  autenticado sin escribir ni desplegar código — exactamente el mismo patrón que ya usa
  el resto de funciones de servicio de NEXORA. No se creó ninguna página, componente ni
  formulario nuevo.
- **No hace que el Router use `is_default` todavía.** El campo se guarda, se valida y se
  expone; el Router del Bloque 1 sigue eligiendo únicamente por prioridad y capacidad, sin
  leer `is_default` — "preparar", no "usar" (requisito 12 del encargo).
- **No implementa chat, memoria, OCR, voz, canales externos ni automatización del ERP** —
  fuera de alcance explícito, ver la lista completa en la sección "No implementar
  todavía" del encargo de este bloque.

## Qué proveedores soporta

Los nueve oficiales, ya registrados como adaptadores simulados desde los Bloques 2 y 2.1
y ahora con su variable de entorno oficial documentada:

| Proveedor | `provider_key` | Variable de entorno |
|---|---|---|
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Perplexity | `perplexity` | `PERPLEXITY_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |
| Mistral | `mistral` | `MISTRAL_API_KEY` |
| Cohere | `cohere` | `COHERE_API_KEY` |

## Cómo se añade una API Key

Dos caminos, resueltos en este orden de prioridad (`list_credential_status` informa cuál
está activo para cada proveedor):

1. **Variable de entorno de servidor** (recomendado para el proveedor principal de la
   plataforma): defina `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc. en el entorno del
   contenedor backend — mismo mecanismo que ya usa `SUPABASE_SERVER_KEY`. Nunca se
   versiona un valor real; `.env.nexora.example` solo documenta el nombre, vacío.
2. **Base de datos, cifrada** (para overrides por proveedor sin redeploy): un
   Administrator llama a `nexora.intelligence.service.save_credential` con
   `{"provider_key": "openai", "secret": "..."}`. La credencial se guarda cifrada en
   `NXR AI Provider Credential` (fieldtype `Password` nativo de Frappe, misma clave de
   cifrado del sitio que ya protege otros secretos) y nunca vuelve a aparecer en texto
   plano en ninguna respuesta, log o evento de auditoría posterior.

Si ya existe una credencial guardada para ese proveedor, `save_credential` la reemplaza
— así se rota una clave sin necesitar un endpoint de borrado.

## Cómo se valida un proveedor

`save_credential` valida el **formato** de la credencial antes de guardarla
(`nexora.intelligence.credentials.validate_credential_format`): la rechaza si está vacía,
tiene espacios al borde, es demasiado corta o larga, o contiene un marcador de plantilla
obvio. Cada intento —aceptado o rechazado— actualiza `validation_state` y
`last_validated_at` en el `NXR AI Provider` correspondiente y queda en
`NXR Audit Event`. Ninguna llamada de red ocurre en este proceso — deliberado, ver "Qué
no hace todavía".

## Qué queda preparado para el siguiente bloque

- `NXR AI Provider` ya expone `default_model`, `timeout_seconds`, `temperature`,
  `max_tokens`, `cost_hint` e `is_default` — un Model Router futuro puede leerlos vía
  `list_providers`/`_provider_rows()` sin que este bloque haya adivinado su diseño.
- `list_credential_status` ya resuelve, por proveedor, si hay una credencial disponible y
  de dónde vendría (`environment` / `database` / `none`) — la pieza que le falta a un
  futuro `dispatch` real es solo leer ese valor y pasarlo al adaptador correspondiente.
- El patrón completo de credencial seguro (DocType separado, `Password` cifrado,
  validación de formato sin red, nunca expuesta en logs/auditoría) queda establecido y
  probado — cualquier subcomponente futuro que necesite guardar un secreto distinto
  puede replicarlo sin inventar uno nuevo.

## Compatibilidad con los Bloques 1 y 2

Ningún archivo de los Bloques 1 o 2 cambió de comportamiento. Dos excepciones, ambas
extensiones explícitamente autorizadas por este mismo bloque, documentadas aquí y no en
otro lugar:

- **`intelligence/service.py` — `_provider_rows()`.** Su lista de `fields` pasó de 5 a 13
  columnas (se añadieron las ocho nuevas de configuración). Es un *helper privado*, no un
  endpoint: `gateway.build_registry()` ya ignoraba cualquier clave de fila que no
  reconociera, así que esta extensión no cambia nada aguas abajo. Las cuatro funciones
  del Bloque 1 (`register_provider`, `set_provider_status`, `list_providers`,
  `resolve_capability`) no perdieron ni ganaron ninguna línea de lógica propia.
- **`tests/test_intelligence_contract.py` — `test_service_was_not_touched_by_block_2`.**
  Su aserción literal (`service.py` tiene exactamente 4 endpoints) dejó de ser cierta
  porque este bloque añade 4 más, exactamente lo que el propio Bloque 2 preveía
  ("ampliar la superficie de `@frappe.whitelist` queda para el bloque que sí lo
  necesite"). Se renombró a `test_service_endpoint_count_is_intentional` y se actualizó
  el número a 8, con un docstring que explica la historia de la cifra en vez de fingir
  que nunca cambió.

Todo lo demás (`core.py`, `registry.py`, `router.py`, `gateway.py`, `adapters.py`,
`providers/*.py`, los nueve adaptadores simulados, `NXR AI Provider`'s ocho campos
originales) permanece exactamente como lo dejó cada bloque anterior — confirmado con
`git diff` antes de comitear (ver tabla de pruebas más abajo).

`test_ai_provider_doctype_has_no_credential_field` (Bloque 1) sigue verde **sin
modificarse**: la credencial vive en `NXR AI Provider Credential`, un DocType nuevo y
separado — `NXR AI Provider` en sí mismo nunca tuvo ni tiene ningún campo de credencial.
Esa separación deliberada (Provider Manager ≠ API Key Manager,
`NEXORA_INTELLIGENCE_ARCHITECTURE.md` sección 8) es lo que evitó tener que tocar esa
prueba en absoluto.

## Reglas de seguridad aplicadas

- **Ninguna API key hardcodeada.** `credentials.py` solo declara *nombres* de variable de
  entorno; ningún valor real aparece en código, prueba ni documentación de este bloque.
  `test_intelligence_credentials.py` usa exclusivamente secretos sintéticos
  (`sk-synthetic-...`) que además fallarían la propia validación de plantilla si
  contuvieran palabras como "changeme" — se verificó a propósito que no las contengan.
- **Ningún secreto en logs, pruebas o documentación.** `save_credential` nunca pasa el
  valor crudo a `audit(...)`; la huella (`payload_hash`) se calcula sobre un resumen
  redactado con `nexora.integrations.core.redact_credentials` (reutilizado tal como pide
  la sección 7 de la arquitectura), nunca sobre el secreto en texto plano.
  `list_credential_status` y `list_providers` nunca solicitan el campo `secret` en
  ninguna consulta — verificado por prueba de contrato
  (`test_service_never_requests_the_secret_field_in_a_query`,
  `test_audit_calls_never_include_the_raw_secret`).
- **Cifrado en reposo, no un patrón nuevo.** `NXR AI Provider Credential.secret` usa el
  fieldtype `Password` nativo de Frappe — el mismo mecanismo de cifrado
  (`FRAPPE_ENCRYPTION_KEY`) que ya protege otros secretos en este sitio. No se inventó
  ningún cifrado propio.
- **Menor privilegio.** Guardar o reemplazar una credencial exige la acción nueva
  `ai_manage_credential`, restringida a `ADMINISTRATOR_ONLY_ROLES` (`System Manager`,
  `NEXORA Administrator`) — más estricta que `ai_manage_provider` (que además incluye
  `NEXORA Finance Manager`), porque configurar un secreto es más sensible que registrar
  un proveedor.
- **Nunca se elimina una credencial**, igual que `NXR Integration`/`NXR AI Provider`: se
  reemplaza guardando un valor nuevo. La razón de seguridad para permitir el reemplazo
  in-place (no exigir borrar-y-recrear) es que así se puede rotar una clave comprometida
  sin un endpoint de borrado adicional que auditar.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/credentials.py`
- `nexora_app/nexora/nexora/doctype/nxr_ai_provider_credential/{__init__.py,nxr_ai_provider_credential.json,nxr_ai_provider_credential.py}`
- `nexora_app/nexora/tests/test_intelligence_credentials.py`
- `nexora_app/nexora/tests/test_intelligence_provider_config.py`
- Este documento.

Modificados (aditivos, salvo lo descrito en "Compatibilidad"):

- `nexora_app/nexora/intelligence/core.py` — `CredentialFormatError` y ocho validadores
  de configuración operativa (`validate_default_model`, `validate_timeout_seconds`,
  `validate_temperature`, `validate_max_tokens`, `validate_cost_hint`,
  `validate_validation_state`, más `COST_HINTS`/`VALIDATION_STATES`).
- `nexora_app/nexora/intelligence/config.py` — cinco constantes de valores por defecto.
- `nexora_app/nexora/intelligence/service.py` — cuatro funciones nuevas
  (`update_provider_config`, `set_default_provider`, `save_credential`,
  `list_credential_status`) más dos helpers privados; `_provider_rows()` extendido (ver
  "Compatibilidad").
- `nexora_app/nexora/permissions.py` — `ADMINISTRATOR_ONLY_ROLES` y la acción
  `ai_manage_credential`.
- `nexora_app/nexora/nexora/doctype/nxr_ai_provider/nxr_ai_provider.json` — ocho campos
  nuevos; los ocho originales del Bloque 1 no cambiaron.
- `nexora_app/nexora/tests/test_intelligence_contract.py` — once pruebas nuevas más el
  renombrado descrito arriba.
- `nexora_app/nexora/tests/test_app_contract.py` — conteo de DocTypes de 51 a 52.
- `.env.nexora.example` — nueve variables de entorno documentadas, vacías.

## Pruebas

Ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`), con
`PYTHONPATH=nexora_app python3 -m unittest <módulo>`:

| Suite | Casos | Nuevo en este bloque | Resultado |
|---|---|---|---|
| `test_intelligence_core` | 41 | 0 (sin cambios) | OK |
| `test_intelligence_registry` | 11 | 0 (sin cambios) | OK |
| `test_intelligence_router` | 13 | 0 (sin cambios) | OK |
| `test_intelligence_gateway` | 15 | 0 (sin cambios) | OK |
| `test_intelligence_contract` | 24 | +11 (+1 renombrada) | OK |
| `test_intelligence_adapters` | 14 | 0 (sin cambios) | OK |
| `test_intelligence_provider_stubs` | 15 | 0 (sin cambios) | OK |
| `test_intelligence_credentials` | 23 | +23 (archivo nuevo) | OK |
| `test_intelligence_provider_config` | 36 | +36 (archivo nuevo) | OK |
| `test_app_contract` | 13 | 0 (sin cambios) | OK |

216 pruebas en total (incluye `test_integrations_core`, ajena a este subsistema, usada
como control), todas en verde — 70 nuevas de este bloque, sin ninguna regresión de los
Bloques 1, 2 y 2.1 (146 previas intactas). Cubren, con casos positivos y negativos, cada
punto pedido: registro y consulta de configuración (validadores de `default_model`,
`timeout_seconds`, `temperature`, `max_tokens`, `cost_hint`), carga y rechazo de
credenciales por formato (vacía, con espacios, corta, larga, valor de plantilla),
resolución de credencial por entorno vs. base de datos, y las pruebas de contrato que
verifican que ninguna ruta del código puede filtrar el secreto.

Guards reales del repositorio, ejecutados sin modificación contra el árbol resultante:

| Validador | Resultado |
|---|---|
| `python -m compileall nexora_app/nexora scripts` | OK |
| `scripts/validate_nexora_app.py` | `exit 0` |
| `scripts/validate_nexora_financial_models.py` | `exit 0` — sin cambios |
| `scripts/validate_nexora_governance.py` | `exit 0` — sin cambios |
| `scripts/validate_nexora_completion.py` | `exit 0` |
| `scripts/validate_nexora_operational_acceptance.py` | `exit 0` |
| `scripts/validate_github_governance.py` | `exit 0` |
| `scripts/validate_nexora_constitution.py` | `exit 0` |

No ejecutado en este entorno (requiere `bench` + MariaDB): igual que en los bloques
anteriores, las pruebas de integración reales de `save_credential`,
`update_provider_config`, `set_default_provider` y `list_credential_status` contra un
sitio Frappe real —incluyendo que `Password` cifra y enmascara correctamente en
runtime— quedan para el CI del PR (`nexora-app.yml`).

## Limitaciones reales

- La validación de credenciales es solo de formato. Una clave con el formato correcto
  pero revocada o incorrecta se guardaría como `"Format Valid"` — el nombre del estado
  es deliberadamente preciso sobre esto, pero sigue siendo una limitación real hasta que
  exista un bloque de despacho real que la ejercite contra el proveedor.
- `is_default` no tiene ningún efecto en el enrutamiento todavía; es dato preparado, no
  comportamiento nuevo.
- No existe endpoint de borrado de credencial ni de rotación con historial — reemplazar
  (`save_credential` de nuevo) es la única operación disponible, a propósito, para
  mantener el alcance mínimo pedido por este bloque.
- No se verificó en este entorno que Frappe realmente cifre y enmascare el campo
  `Password` en tiempo de ejecución real (requiere `bench`); se confía en el
  comportamiento documentado y ya usado en el resto del framework, y queda pendiente de
  la corrida de CI con MariaDB real.
