# NEXORA Intelligence Platform — Bloque 5.2: AI Orchestrator + OmniRoute Integration

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> y a [`AGENTS.md`](../../AGENTS.md). Continúa
> [`NIP_BLOQUE_5_LIVE_PROVIDER_CONNECTIONS.md`](NIP_BLOQUE_5_LIVE_PROVIDER_CONNECTIONS.md)
> sin crear código paralelo: reutiliza `gateway.build_registry` (Bloque 1) y
> `runtime.build_ready_adapter` (Bloque 4) tal cual, y añade encima el bucle de
> reintento/fallback, el circuito de salud y el panel administrativo que faltaban.

## Qué construye este bloque

La "regla de oro" del encargo: si un proveedor falla o se queda sin cuota, NEXORA sigue
funcionando con otro proveedor capaz, sin detener la sesión del usuario, dejando el
cambio de proveedor únicamente en el registro de auditoría interno. Concretamente:

- **`orchestrator_core.py`** (puro, sin `frappe`): circuito de salud por proveedor
  (`Closed`/`Open`/`Half-Open`), puntuación de candidatos (`priority` + `cost_hint` +
  penalización si está en `Half-Open`) y `rank_candidates`, que ordena los proveedores
  capaces de una tarea excluyendo a los que están `Open` y aún en enfriamiento.
- **`orchestrator.py`** (con `frappe`): `execute(capability, payload, correlation_id)` —
  el bucle real de intento → fallo → siguiente candidato, construido enteramente sobre
  `gateway.build_registry` y `runtime.build_ready_adapter` ya existentes. Persiste el
  estado de salud en `NXR AI Provider`, registra cada intento (éxito o fallo) en la
  nueva `NXR AI Usage Event`, audita cada fallo y el agotamiento total, y notifica a los
  administradores solo si **todos** los proveedores capaces fallaron.
- **`prompt_optimizer.py`** (puro, sin `frappe`): compresión mecánica de prompts
  (normalización de espacios + truncado a un presupuesto de caracteres con marcador
  explícito). Construido por instrucción expresa del propietario aunque todavía no
  exista un consumidor real (chat/conversación) — ver "Limitaciones reales".
- **`NXR AI Usage Event`** (DocType nuevo, solo-append): latencia, éxito, tokens y costo
  reportado por cada intento, base del panel de "latencia" y "costo estimado" pedido.
- **Tres endpoints nuevos** en `service.py`: `run_orchestrated_request` (ejecuta la
  regla de oro), `preview_routing_decision` (qué proveedor se usaría ahora, sin invocar
  a nadie), `get_provider_usage_summary` (agregado de latencia/éxito/costo por
  proveedor).
- **Panel administrativo** (`nexora-ai-providers`, Page de Desk): tabla de proveedores
  con estado, circuito, credencial, prioridad, modelo, latencia y tasa de éxito;
  botones de probar conexión, activar/desactivar, fijar por defecto, configurar,
  registrar credencial; sección para ejecutar la regla de oro manualmente. Alcanzable
  desde el workspace y desde la barra de navegación superior, como exige el resto de la
  aplicación.

## Decisión sobre OmniRoute

Se analizó `diegosouzapw/OmniRoute` (MIT) como referencia arquitectónica, tal como pedía
el encargo. Hallazgos relevantes: gateway Node.js/TypeScript local (proceso aparte, no
librería), fallback en cuatro niveles, circuito + enfriamiento de conexión + bloqueo de
modelo, motor de puntuación de doce factores, credenciales en SQLite con AES-256-GCM,
OAuth+PKCE, compresión de tokens RTK+Caveman (15–95%), servidor MCP con 94–104
herramientas, endpoint único estilo OpenAI en `localhost:20128`.

**Estrategia elegida: referencia arquitectónica, sin dependencia en tiempo de
ejecución.** Reimplementación nativa en Python, dentro del mismo proceso Frappe, por
tres razones concretas:

1. **Runtime distinto.** NEXORA ya es una aplicación Frappe/Python; añadir un proceso
   Node.js separado como dependencia de arranque introduce un segundo runtime, un
   segundo despliegue y un segundo punto de fallo para una plataforma que hoy no lo
   necesita — los Bloques 1–5 ya resuelven credenciales, configuración y transporte
   HTTP en Python puro.
2. **Superficie ya cubierta con lo propio.** El fallback multi-nivel, el circuito y la
   puntuación de OmniRoute son el mismo problema que este bloque resuelve directamente
   en `orchestrator_core.py`, reutilizando el Registry (Bloque 1) y el Runtime
   (Bloque 4) que ya existen — no hay nada que un proceso externo añadiera que no se
   pueda expresar en las ~200 líneas de `orchestrator_core.py`.
3. **No hace falta mover ningún repositorio.** El repositorio de NEXORA ya pertenece a
   la cuenta del propietario; "mover OmniRoute a tu cuenta" no aplica porque no se
   integra en tiempo de ejecución, solo como referencia de diseño ya documentada aquí.

No se copió código de OmniRoute (aunque su licencia MIT lo habría permitido): la
compresión de prompts de este bloque es una reimplementación mecánica propia (normalizar
espacios + truncar a presupuesto), sin relación con RTK/Caveman, y el circuito de salud
sigue el patrón estándar de la industria (Closed/Open/Half-Open), no el código de
OmniRoute línea por línea.

## Cómo funciona la regla de oro

```
orchestrator.execute(capability, payload, correlation_id, prefer=None)
  → construye el registro de proveedores activos capaces de `capability`
    (gateway.build_registry, Bloque 1 — sin cambios)
  → calcula la salud de cada uno desde NXR AI Provider
    (circuit_state, consecutive_failures, degraded_until)
  → orchestrator_core.rank_candidates: ordena por prioridad + cost_hint,
    excluye a quien esté Open y aún en enfriamiento,
    reintegra a prueba (Half-Open) a quien ya cumplió su enfriamiento
  → si no hay ningún candidato: NoProviderAvailableError (Bloque 1, sin cambios;
    no se audita "nada que intentar" — mismo criterio ya usado en Bloques previos)
  → por cada candidato, en orden:
      construye el adaptador (runtime.build_ready_adapter, Bloque 4 — sin cambios)
      invoca
      éxito → record_success, persiste salud, registra NXR AI Usage Event,
              audita "ai_orchestrator_dispatch_succeeded", devuelve la respuesta
      fallo → record_failure (abre el circuito si toca), persiste salud,
              registra NXR AI Usage Event, audita "ai_orchestrator_attempt_failed"
              reintenta el mismo proveedor solo si el error es un timeout;
              cualquier otro error (auth, cuota, límite de tasa, modelo inexistente)
              pasa directamente al siguiente candidato
  → si todos fallaron: audita "ai_orchestrator_all_providers_exhausted",
    notifica a los administradores (NXR Notification), lanza AllProvidersExhaustedError
```

`should_retry_same_provider` decide qué errores merecen un segundo intento contra el
*mismo* proveedor antes de pasar al siguiente: solo `ProviderTimeoutError` (transitorio
por definición). `ProviderAuthenticationError`, `ProviderModelNotFoundError`,
`ProviderQuotaExhaustedError` y `ProviderRateLimitError` nunca se reintentan contra el
mismo proveedor — pasan directamente al siguiente candidato, exactamente el
comportamiento que pide la regla de oro.

El cambio de proveedor **nunca llega al usuario como error**: `run_orchestrated_request`
solo devuelve un fallo si `AllProvidersExhaustedError` se agotó de verdad; cualquier
fallo intermedio queda únicamente en `NXR Audit Event` y `NXR AI Usage Event`.

## Certificación real de los nueve proveedores

Por decisión explícita del propietario ("quiero darte una credencial real ahora"), se
certificó cada proveedor uno por uno con una API key real, aportada de forma transitoria
por variable de entorno de shell (nunca escrita a ningún archivo, commit, log o
documentación) y usada directamente contra la clase del adaptador correspondiente,
saltándose Frappe/DocTypes por completo porque este entorno no tiene `bench`/MariaDB.
Resultado agregado — **cero fragmentos de ninguna clave real aparecen a continuación,
solo el resultado observado**:

| Proveedor | Resultado | Detalle |
|---|---|---|
| OpenAI | **READY** | Autenticación, respuesta y latencia correctas |
| Gemini | **READY** | Ciclo completo correcto; hallazgo de "thinking tokens" — ver abajo |
| OpenRouter | **READY** | Autenticación, respuesta y latencia correctas |
| DeepSeek | **QUOTA_EXHAUSTED** | Credencial válida, `HTTP 402` — "Insufficient Balance" |
| Perplexity | **READY** | Autenticación, respuesta y latencia correctas |
| Groq | **READY** | Ver bug de Cloudflare/User-Agent corregido abajo; 287 ms tras el fix |
| Anthropic | **QUOTA_EXHAUSTED** | Credencial válida, `HTTP 400` — "credit balance is too low" |
| Mistral | **READY** | Autenticación, respuesta y latencia correctas |
| Cohere | **READY** | Autenticación, respuesta y latencia correctas |

**7 de 9 en `READY` confirmado contra su API real; 2 de 9 (DeepSeek, Anthropic) con
credencial válida confirmada pero sin saldo/cuota** — ambos casos genuinos, no simulados,
no maquillados: el sistema los reporta exactamente como lo que son.

### Dos bugs reales encontrados y corregidos por esta certificación

- **Groq / Cloudflare 403.** La solicitud real a Groq devolvía `HTTP 403` con
  `error code: 1010` — Cloudflare, que protege la API de Groq, bloquea peticiones sin
  cabecera `User-Agent` (el valor por defecto de `urllib` queda filtrado). Antes de este
  hallazgo, ese 403 se clasificaba como `ProviderAuthenticationError` — un falso
  "credencial inválida" contra una credencial en realidad correcta. Corregido añadiendo
  una cabecera `User-Agent: NEXORA-Intelligence-Platform/1.0` por defecto en
  `http_support.send_json_request` (una llamada que ya envíe su propio `User-Agent` lo
  conserva; el merge de diccionarios da prioridad al valor del llamador). Reverificado
  en vivo contra la API real de Groq tras el fix: éxito, 287 ms.
- **HTTP 402 sin clasificar.** DeepSeek respondía `HTTP 402` ante saldo agotado, y ese
  código caía en el `AdapterInvocationError` genérico — indistinguible de un fallo de
  red o de un error de servidor. Se añadió `ProviderQuotaExhaustedError`, clasificada
  únicamente sobre el código numérico 402 (confiable), nunca marcada como reintentable
  contra el mismo proveedor por `should_retry_same_provider`.

### Hallazgo documentado, no corregido: Anthropic con 400 en vez de 402

Anthropic reporta el mismo escenario ("saldo agotado, credencial válida") con
`HTTP 400` y un mensaje de texto ("credit balance is too low"), no con el 402 numérico
que sí clasifica `ProviderQuotaExhaustedError`. Se decidió **no** clasificarlo aparte:
distinguirlo requeriría inspeccionar el texto del mensaje, específico de cada proveedor
y frágil entre idiomas/versiones de API — el mismo criterio ya aplicado en el Bloque 5
para no clasificar heurísticas basadas en texto. Hoy, este caso concreto de Anthropic
cae en `AdapterInvocationError` genérico (reintentable contra el mismo proveedor una vez
por ser genérico, no por ser correcto) — limitación honesta, no oculta.

### Hallazgo documentado, no corregido: Gemini y "thinking tokens"

`gemini-flash-latest` consumió todo el presupuesto de `max_tokens` en tokens internos de
"pensamiento", devolviendo una respuesta visible vacía en una llamada que, por lo demás,
fue exitosa (autenticación, formato y ciclo de respuesta correctos — por eso Gemini
queda en `READY`). Un intento de fijar `thinkingBudget: 0` devolvió `HTTP 400`. No se
implementó soporte para `thinkingConfig` en este bloque — queda documentado como
limitación real, no oculta ni maquillada.

## Compatibilidad con los Bloques 1–5

Todos los archivos existentes se tocaron de forma exclusivamente aditiva:

- `core.py`: nuevas excepciones (`ProviderQuotaExhaustedError`,
  `AllProvidersExhaustedError`) y nuevo campo opcional `cost_hint` en `ProviderRecord`
  con valor por defecto — ningún consumidor previo de `ProviderRecord` se rompe.
- `gateway.py`: `build_registry` ahora también lee `cost_hint` de cada fila; sin cambio
  de comportamiento en `resolve`/`dispatch`.
- `providers/http_support.py`: `User-Agent` por defecto (el llamador lo puede
  sobrescribir) y clasificación del código 402 — ambos aditivos.
- `nxr_ai_provider.json`: cinco campos nuevos de solo lectura para el estado del
  circuito — el DocType sigue sin ningún campo de credencial (ver
  `test_ai_provider_doctype_has_no_credential_field`, sin tocar desde el Bloque 1).
- `service.py`: 100% inserciones — tres funciones nuevas, cero líneas existentes
  modificadas o eliminadas.
- Workspace y navegación: una entrada nueva en cada uno (`nexora.json`,
  `public/js/nexora.js`), siguiendo el mismo contrato que exige
  `test_page_registry_contract.py` para toda página nueva.

`gateway.dispatch()` y el Router del Bloque 1 siguen funcionando exactamente igual que
antes para cualquier código que no use el nuevo Orchestrator — el fallback automático es
una capa nueva por encima, no un reemplazo.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/orchestrator_core.py`
- `nexora_app/nexora/intelligence/orchestrator.py`
- `nexora_app/nexora/intelligence/prompt_optimizer.py`
- `nexora_app/nexora/nexora/doctype/nxr_ai_usage_event/` (`__init__.py`, `.json`, `.py`)
- `nexora_app/nexora/nexora/page/nexora_ai_providers/` (`__init__.py`, `.json`, `.js`)
- `nexora_app/nexora/tests/test_intelligence_orchestrator_core.py` (39 pruebas)
- `nexora_app/nexora/tests/test_intelligence_prompt_optimizer.py` (21 pruebas)
- Este documento.

Modificados (aditivos, verificado con `git diff` antes de comitear):

- `nexora_app/nexora/intelligence/core.py`
- `nexora_app/nexora/intelligence/gateway.py`
- `nexora_app/nexora/intelligence/providers/http_support.py`
- `nexora_app/nexora/intelligence/service.py` (100% inserciones)
- `nexora_app/nexora/nexora/doctype/nxr_ai_provider/nxr_ai_provider.json`
- `nexora_app/nexora/nexora/workspace/nexora/nexora.json`
- `nexora_app/nexora/public/js/nexora.js`
- `nexora_app/nexora/tests/test_app_contract.py` (conteo de DocTypes 52 → 53)
- `nexora_app/nexora/tests/test_intelligence_contract.py` (conteo de endpoints 13 → 16,
  más 8 pruebas nuevas de contrato para este bloque)
- `nexora_app/nexora/tests/test_intelligence_http_support.py` (+5 pruebas)

## Pruebas

Ejecutables sin `bench`/MariaDB, con `PYTHONPATH=nexora_app python3 -m unittest`:

| Suite | Casos | Resultado |
|---|---|---|
| `test_intelligence_*` (14 archivos) | 320 | OK |
| `test_app_contract` | 13 | OK |
| `test_page_registry_contract` | 9 | OK |
| `test_integrations_core` (control) | 11 | OK |

**353 pruebas en total, todas en verde.** 73 son nuevas de este bloque
(`test_intelligence_orchestrator_core`: 39; `test_intelligence_prompt_optimizer`: 21;
`test_intelligence_http_support`: +5; `test_intelligence_contract`: +8), sin ninguna
regresión de los Bloques 1–5.

Cobertura del checklist pedido, positivo y negativo:

| Caso pedido | Dónde se cubre |
|---|---|
| Proveedor válido | Certificación real (tabla arriba) + `test_intelligence_live_adapters` |
| Proveedor inválido / no registrado | `test_intelligence_runtime_core.py` (Bloque 4) |
| Credencial faltante | `test_intelligence_runtime_core.py` (Bloque 4) |
| Credencial incorrecta | `test_intelligence_http_support.py` (401/403) |
| Proveedor deshabilitado | `test_intelligence_runtime_core.py` (Bloque 4) |
| Timeout | `test_intelligence_orchestrator_core.py`, `should_retry_same_provider` |
| Límite de tasa | `test_intelligence_http_support.py` + `orchestrator_core` (no reintenta) |
| Fallback automático | `test_intelligence_orchestrator_core.py`, `rank_candidates` |
| Selección del siguiente mejor proveedor | `test_intelligence_orchestrator_core.py`, `score_candidate` |
| Health Monitor | `test_intelligence_orchestrator_core.py`, `record_success`/`record_failure` |
| Panel de configuración | `nexora_ai_providers.js`, verificado con `node --check` |
| Reemplazo de credencial | Sin cambios — `save_credential` (Bloque 3), reutilizado tal cual |
| Compatibilidad con Bloques 1–5 | Sección "Compatibilidad" arriba + `git diff` aditivo |

Guards reales del repositorio, ejecutados sin modificación contra el árbol resultante:

| Validador | Resultado |
|---|---|
| `python -m compileall nexora_app/nexora scripts` | OK |
| `scripts/validate_nexora_app.py` | `exit 0` |
| `scripts/validate_nexora_completion.py` | `exit 0` |
| `scripts/validate_nexora_constitution.py` | `exit 0` |
| `scripts/validate_nexora_financial_models.py` | `exit 0` |
| `scripts/validate_nexora_governance.py` | `exit 0` |
| `scripts/validate_nexora_operational_acceptance.py` | `exit 0` |
| `scripts/validate_github_governance.py` | `exit 0` |

**No ejecutado en este entorno** (requiere `bench` + MariaDB, ausente en este sandbox):
una cadena completa de fallback multi-proveedor en vivo a través de
`orchestrator.execute()` contra un sitio Frappe real. La lógica de decisión
(`orchestrator_core.rank_candidates`, `record_failure`, `should_retry_same_provider`) sí
tiene cobertura completa de 39 pruebas unitarias puras, y la clasificación de errores por
proveedor sí se verificó contra las nueve APIs reales (tabla de certificación arriba) —
lo que falta es específicamente la orquestación de *varios* proveedores encadenados
dentro de una sola llamada a `execute()`, que requiere el DocType `NXR AI Provider`
persistido en una base de datos real.

## Limitaciones reales

- **Sin cadena de fallback en vivo de extremo a extremo** (ver arriba) — bloqueada por
  la ausencia de `bench`/MariaDB en este entorno, no por diseño incompleto.
- **Anthropic con `HTTP 400` de saldo agotado no se clasifica como
  `ProviderQuotaExhaustedError`** (solo el 402 numérico lo hace) — decisión explícita
  para no depender de texto de mensaje frágil entre proveedores e idiomas.
- **Gemini y los "thinking tokens"**: una llamada puede ser técnicamente exitosa
  (`READY`) y aun así devolver una respuesta visible vacía si el modelo agota su
  presupuesto de tokens pensando — sin soporte de `thinkingConfig` todavía.
- **La compresión de prompts es mecánica, no semántica.** `prompt_optimizer.py` recorta
  por presupuesto de caracteres; no resume ni prioriza contenido por importancia (eso
  sería compresión semántica, fuera de alcance de este bloque) — y hoy no tiene ningún
  consumidor real dentro de NEXORA, construido por instrucción explícita del propietario
  para cuando exista uno (chat/conversación).
- El resto de limitaciones de los Bloques 1–5 (sin verificación de `Password` cifrado en
  runtime real, forma exacta de `ProviderResponse.data` no validada contra las nueve
  respuestas reales completas) siguen aplicando sin cambios.
