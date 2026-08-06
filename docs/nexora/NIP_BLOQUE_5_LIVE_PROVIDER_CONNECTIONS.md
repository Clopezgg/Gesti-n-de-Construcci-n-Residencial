# NEXORA Intelligence Platform — Bloque 5: Live Provider Connections

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> y a [`AGENTS.md`](../../AGENTS.md). Continúa
> [`NIP_BLOQUE_4_PROVIDER_RUNTIME_CREDENTIAL_ACTIVATION.md`](NIP_BLOQUE_4_PROVIDER_RUNTIME_CREDENTIAL_ACTIVATION.md)
> sin crear código paralelo — este bloque completa el manejo de errores del Runtime del
> Bloque 4, reutilizando exactamente su mismo transporte HTTP compartido.

## Qué proveedores funcionan en modo real

**Ninguno todavía, y de forma deliberada.** Este bloque tenía como objetivo activar el
consumo real de los nueve proveedores, pero ese objetivo tiene una precondición que no
se puede fabricar: una credencial real. Siguiendo la instrucción explícita del encargo
("si es necesario configurar credenciales reales, detente... no inventes valores, no
utilices placeholders para validar llamadas reales"), se verificó primero que este
entorno **sí tiene salida de red real** —una solicitud de prueba sin credenciales a
`https://api.openai.com/v1/models` devolvió `HTTP 401`, no un error de conectividad—, y
después se preguntó explícitamente al propietario si quería aportar una credencial real
para una verificación en vivo. Su decisión fue cerrar el bloque sin verificación en vivo.
En consecuencia:

- **Cero llamadas de red reales se ejecutaron durante este bloque.**
- **Cero proveedores están confirmados contra su API real.**
- Los nueve adaptadores están completos, con el mismo contrato del Bloque 1 y el mismo
  manejo de errores exhaustivo que exige este bloque — lo único que falta para pasar de
  "listo" a "verificado" es que el propietario configure al menos una credencial real y
  llame a `test_provider_connection`.

## Qué añadió este bloque sobre el Bloque 4

El Runtime del Bloque 4 ya resolvía credencial, configuración, prioridad y disponibilidad,
y ya manejaba autenticación, timeout y errores de red genéricos. Este bloque completó
exactamente los dos tipos de error que el encargo pedía explícitamente y que el Bloque 4
todavía no distinguía:

- **Límite de tasa (HTTP 429) → `ProviderRateLimitError`.** Antes cualquier 429 caía en
  el error genérico `AdapterInvocationError`; ahora se clasifica aparte, e incluye el
  valor de la cabecera `Retry-After` en el mensaje cuando el proveedor la envía. No
  reintenta automáticamente — decidir cuántas veces y cuánto esperar es una política de
  quien invoque el Runtime, no del adaptador (mismo principio que ya regía timeout y
  autenticación en el Bloque 4).
- **Modelo inexistente (HTTP 404) → `ProviderModelNotFoundError`.** El Bloque 4 ya había
  declarado esta excepción pero no la usaba en ningún punto — quedó documentado
  explícitamente como pendiente. Ahora `http_support.send_json_request` la lanza ante
  cualquier 404, con la advertencia honesta de que es una heurística razonable (las URLs
  que este subsistema construye son fijas y ya validadas, así que un 404 real casi
  siempre señala el segmento del modelo), no un hecho confirmado contra las nueve APIs
  reales — ver "Limitaciones reales".

Ambas excepciones heredan de `AdapterInvocationError` (Bloque 2), así que cualquier
código existente que ya capturaba esa clase (`test_provider_connection`, Bloque 4) las
atrapa sin ningún cambio adicional.

No se creó ningún adaptador nuevo, ningún transporte HTTP paralelo ni ninguna ruta de
código alternativa: **toda la clasificación de errores vive en el único punto de
transporte real que ya existía** (`providers/http_support.py`), reutilizado sin cambios
de forma por los nueve adaptadores en vivo del Bloque 4.

## Cómo configurar las API Keys

Sin cambios respecto al Bloque 3/4: variable de entorno de servidor (prioridad) o
`save_credential` (registro cifrado). Ver
[`NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md`](NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md)
para el detalle completo, incluida la tabla de los nueve nombres oficiales de variable.

## Cómo validar una conexión

Sin cambios respecto al Bloque 4: `check_provider_readiness` (validación estática, sin
red) y `test_provider_connection` (llamada real mínima, gateada por
`ai_test_connection`, auditada). Este bloque no añadió ningún endpoint nuevo — solo hizo
que los errores que esos endpoints ya podían encontrar se clasifiquen con más precisión.

## Qué error devuelve cada proveedor

Los nueve comparten exactamente la misma clasificación, porque comparten el mismo
transporte (`http_support.send_json_request`):

| Situación | Excepción |
|---|---|
| Sin credencial configurada (ni entorno ni base de datos) | `CredentialNotConfiguredError` |
| Proveedor no registrado | `ProviderNotFoundError` |
| Proveedor registrado pero no `Active` | `ProviderDisabledError` |
| Capacidad no declarada por el proveedor | `AdapterInvocationError` |
| Sin modelo por defecto configurado | `ProviderConfigError` |
| HTTP 401 / 403 (credencial rechazada) | `ProviderAuthenticationError` |
| HTTP 429 (límite de tasa) | `ProviderRateLimitError` (con `Retry-After` si el proveedor lo envía) |
| HTTP 404 (modelo no reconocido) | `ProviderModelNotFoundError` |
| Tiempo de espera excedido | `ProviderTimeoutError` |
| Fallo de conexión (DNS, red) | `AdapterInvocationError` |
| Cualquier otro código HTTP | `AdapterInvocationError` |

Los nueve adaptadores no tienen manejo de errores propio: todos delegan en esta misma
tabla a través de `send_json_request`. Un proveedor con una forma de error genuinamente
distinta (por ejemplo, que use un código distinto de 404 para "modelo no encontrado")
solo se descubriría al probarlo contra la cuenta real — ver "Limitaciones reales".

## Cómo añadir futuros proveedores

Sin cambios de patrón respecto al Bloque 4:

1. Si la API es compatible con el formato de chat completions de OpenAI: una subclase de
   `OpenAICompatibleLiveAdapter` con `provider_key`, `capabilities` y `base_url` — nada
   más, hereda automáticamente la clasificación de errores de esta tabla.
2. Si no lo es: una clase que implemente `AIProviderAdapter.invoke()`, construya su
   propia solicitud y delegue el envío en `send_json_request` — obtiene la misma
   clasificación de errores sin reimplementarla.
3. Añadirla a `runtime_core.REAL_ADAPTER_CLASSES` (nunca a `@register_adapter`, que es
   exclusivo de los *stubs* simulados de los Bloques 2/2.1 — ver
   [`NIP_BLOQUE_4...md`](NIP_BLOQUE_4_PROVIDER_RUNTIME_CREDENTIAL_ACTIVATION.md), sección
   "Compatibilidad").
4. Añadir su variable de entorno oficial a `credentials.PROVIDER_ENV_VARS` y a
   `.env.nexora.example`.

Ningún paso requiere tocar `runtime.py`, `runtime_core.py` (salvo la entrada del mapeo),
`service.py` ni ningún endpoint administrativo — todos ya son genéricos por
`provider_key`.

## Archivos

Modificados (aditivos únicamente, sin excepción — verificado con `git diff` antes de
comitear: ninguna de las tres líneas eliminadas en todo el bloque pertenece a lógica
existente, todas son imports reformateados para caber en una lista más larga):

- `nexora_app/nexora/intelligence/core.py` — una excepción nueva, `ProviderRateLimitError`.
- `nexora_app/nexora/intelligence/providers/http_support.py` — dos ramas nuevas de
  clasificación de error (429, 404) más la actualización del docstring que las describe.
- `nexora_app/nexora/tests/test_intelligence_http_support.py` — seis pruebas nuevas.

Nuevo:

- Este documento.

Nada más se tocó: cero DocTypes nuevos o modificados, cero cambios en `permissions.py`,
cero endpoints nuevos, cero adaptador nuevo, cero archivo de los Bloques 1–4 alterado más
allá de lo descrito arriba.

## Pruebas

Ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`; transporte HTTP siempre
sustituido por un doble de prueba), con `PYTHONPATH=nexora_app python3 -m unittest`:

| Suite | Casos | Nuevo en este bloque | Resultado |
|---|---|---|---|
| `test_intelligence_http_support` | 14 | +6 | OK |
| Resto de `test_intelligence_*` (12 archivos) | 233 | 0 (sin cambios) | OK |
| `test_app_contract` | 13 | 0 (sin cambios) | OK |

271 pruebas en total (incluye `test_integrations_core` como control), todas en verde —
6 nuevas de este bloque, sin ninguna regresión de los Bloques 1–4 (265 previas intactas).
Cubren, con casos positivos y negativos, el checklist completo pedido:

| Caso pedido | Dónde se cubre |
|---|---|
| Credencial inexistente | `test_intelligence_runtime_core.py` (Bloque 4, sin cambios) |
| Credencial inválida (rechazada por el proveedor) | `test_intelligence_http_support.py`, 401/403 |
| Timeout | `test_intelligence_http_support.py` (Bloque 4, sin cambios) |
| Respuesta correcta | `test_intelligence_live_adapters.py` (Bloque 4, sin cambios) |
| Proveedor deshabilitado | `test_intelligence_runtime_core.py` (Bloque 4, sin cambios) |
| Proveedor no registrado | `test_intelligence_runtime_core.py` (Bloque 4, sin cambios) |
| Modelo inexistente | `test_intelligence_http_support.py`, **nuevo en este bloque** |
| Manejo de excepciones (límite de tasa incluido) | `test_intelligence_http_support.py`, **nuevo en este bloque** |

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

**No ejecutado, por decisión explícita del propietario**: cualquier llamada real contra
cualquiera de los nueve proveedores. Se confirmó que este entorno tiene salida de red
real (prueba sin credenciales a `api.openai.com` → `HTTP 401`, no un fallo de
conectividad), y se preguntó directamente si aportar una credencial real para verificar
al menos un proveedor en vivo; la respuesta fue cerrar el bloque sin esa verificación.
Queda disponible para cuando el propietario lo decida — no requiere ningún cambio de
código, solo configurar una credencial real y llamar a `test_provider_connection`.

## Limitaciones reales

- **La clasificación HTTP 404 → "modelo inexistente" es una heurística, no un hecho
  confirmado por proveedor.** Ninguna de las nueve APIs reales se consultó para
  verificar que efectivamente devuelven 404 (y no, por ejemplo, 400 con un cuerpo de
  error específico) cuando el modelo no existe. El primer intento real contra cada
  proveedor puede requerir ajustar este mapeo.
- **La respuesta exitosa (`ProviderResponse.data`) nunca se validó contra una respuesta
  real de ningún proveedor.** El cuerpo JSON se decodifica y se devuelve tal cual; su
  forma exacta (nombres de campo, estructura anidada) se construyó contra la
  documentación pública de cada API, no contra una respuesta real — misma limitación ya
  declarada en el Bloque 4, todavía sin resolver por la misma razón (cero credenciales
  reales disponibles).
- **`ProviderRateLimitError` no implementa reintento ni backoff.** Es una decisión de
  diseño explícita (ver sección "Qué añadió este bloque"), no una limitación por
  descuido — pero significa que, hoy, un límite de tasa detiene la solicitud en curso;
  reintentarla es responsabilidad de quien llame al Runtime.
- El resto de limitaciones del Bloque 4 (sin `bench`/MariaDB en este entorno, sin
  verificación de que `Password` cifre en runtime real) siguen aplicando sin cambios.
