# NEXORA Intelligence Platform — Bloque 4: AI Provider Runtime + Credential Activation

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> y a [`AGENTS.md`](../../AGENTS.md). Continúa
> [`NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md`](NIP_BLOQUE_3_PROVIDER_CONFIGURATION_CREDENTIAL_MANAGER.md)
> sin reescribir la arquitectura de los Bloques 1–3 — ver "Compatibilidad" más abajo.

## Qué hace este bloque

Convierte la configuración y las credenciales de los Bloques 1–3 en algo que de verdad
puede hablar con un proveedor de IA. Tres piezas nuevas:

1. **Nueve adaptadores en vivo** (`*_live.py`, uno por proveedor oficial), que
   implementan el mismo contrato `AIProviderAdapter` del Bloque 1 pero, a diferencia de
   los *stubs* del Bloque 2, sí construyen una solicitud HTTP real y sí la envían —
   usando únicamente `urllib` de la biblioteca estándar, sin ningún SDK de proveedor
   como dependencia nueva.
2. **Runtime Provider Manager** (`runtime_core.py` + `runtime.py`): resuelve proveedor,
   configuración, prioridad, credencial y disponibilidad, y devuelve un adaptador en
   vivo listo para invocarse — o el error más específico posible si algo falta.
3. **Cinco endpoints administrativos** en `service.py` para validar, consultar y probar
   proveedores sin exponer nunca una credencial.

## Qué no hace todavía

- **No ejecuta ninguna solicitud de producción durante este bloque.** Todo el código que
  toca la red existe y está probado (con el transporte HTTP sustituido por un doble de
  prueba, nunca contra un endpoint real), pero como no hay ninguna credencial real
  configurada en este entorno, `prepare_adapter` rechaza cualquier intento con
  `CredentialNotConfiguredError` antes de llegar a la red. La primera vez que alguien
  configure una API key real, la capacidad ya estará ahí — construida, no habilitada por
  un interruptor separado.
- **No implementa chat, memoria conversacional, herramientas del ERP, automatizaciones,
  OCR ni voz** — fuera de alcance explícito de este bloque.
- **No garantiza que el formato exacto de cada solicitud/respuesta coincida al 100% con
  la API real de cada proveedor.** Las nueve integraciones se construyeron contra la
  forma pública y documentada de cada API (chat completions estilo OpenAI para seis
  proveedores, Messages API de Anthropic, `generateContent` de Gemini, Chat/Embed de
  Cohere), pero nunca se ejercitaron contra una cuenta real — ver "Limitaciones reales".
- **No usa `is_default` para elegir proveedor.** `build_ready_adapter_for_capability`
  reutiliza el Router del Bloque 1 (prioridad + capacidad), que sigue sin leer ese campo
  — la misma limitación ya declarada en el Bloque 3.

## Cómo registrar API Keys

Sin cambios respecto al Bloque 3: `save_credential` (variable de entorno o registro
cifrado). Este bloque no añade una tercera forma de guardar una credencial — solo
consume las dos que ya existían.

## Cómo activar un proveedor

1. Registrarlo (`register_provider`, Bloque 1) con `capabilities` y `status: Active`.
2. Configurar `default_model` (`update_provider_config`, Bloque 3) — sin modelo, el
   Runtime Provider Manager rechaza construir el adaptador aunque todo lo demás esté
   correcto.
3. Guardar su credencial (`save_credential`, Bloque 3) o exportar la variable de entorno
   oficial correspondiente.
4. Confirmar con `check_provider_readiness` (Bloque 4) que `ready: true` — si no, el
   reporte dice exactamente qué falta.

## Cómo validar un proveedor

- `check_provider_readiness`: validación estática — configuración, capacidad y
  credencial presentes, sin tocar la red. Cubre "validar proveedor" y "consultar
  disponibilidad" del encargo de este bloque con una sola función, porque son la misma
  pregunta vista desde dos ángulos.
- `test_provider_connection`: única función de este bloque con efecto real fuera de
  NEXORA — construye el adaptador y le envía una solicitud mínima (`"ping"`, capacidad
  `text`). Si el proveedor no está listo, falla antes de tocar la red (mismo camino que
  `check_provider_readiness`); si está listo, sí hace una llamada real y puede consumir
  cuota — por eso queda auditada y gateada por una acción propia
  (`ai_test_connection`, `MANAGER_ROLES`), más estricta que la simple lectura.

## Qué queda listo para el siguiente bloque

- `build_ready_adapter_for_capability(capability)` ya es la función que un Tool Engine o
  Conversation Engine futuro llamaría para obtener un adaptador real listo para usar,
  elegido por prioridad — sin que ese bloque futuro tenga que repetir ninguna validación.
- Las nueve integraciones reales existen y están probadas en su construcción de
  solicitud; conectar un modelo de negocio del ERP a una de ellas ya no requiere escribir
  cliente HTTP nuevo.
- El patrón `check_readiness` (reporte, nunca excepción) queda disponible para
  cualquier pantalla de administración futura que quiera mostrar el estado de los nueve
  proveedores a la vez sin capturar nueve excepciones distintas.

## Compatibilidad con los Bloques 1–3

**`intelligence/service.py` no perdió ni modificó ninguna línea existente** —
verificado con `git diff` antes de comitear: el diff de este archivo es 100% inserciones,
cero eliminaciones. Los 8 endpoints de los Bloques 1 y 3 no cambiaron.

Dos pruebas existentes se actualizaron porque su premisa literal quedó superada por este
bloque exactamente como sus propios docstrings preveían — mismo patrón ya usado al pasar
del Bloque 2 al Bloque 3:

- `test_service_endpoint_count_is_intentional` (antes actualizada en el Bloque 3): de 8
  a 13, por los cinco endpoints nuevos.
- `test_no_provider_file_imports_a_real_sdk_or_touches_the_network` (Bloque 2), que
  escaneaba *todo* `providers/*.py` porque hasta el Bloque 3 ahí no vivía nada más que
  simulaciones. Se renombró a `test_no_stub_file_imports_a_real_sdk_or_touches_the_network`
  y se acotó a `*_stub.py` + `stub_support.py` — la garantía real ("los stubs simulados
  nunca tocan la red") sigue intacta y probada; lo que dejó de ser cierto fue la
  afirmación más amplia sobre todo el directorio, porque el propio Bloque 4 necesitaba
  añadir archivos que sí tocan la red **a propósito** en ese mismo directorio.

**El registro automático del Bloque 2 (`@register_adapter` / `_ADAPTER_CLASSES`) no se
tocó ni se usa para los adaptadores en vivo.** Los nueve `*_live.py` no llevan el
decorador — se resuelven mediante un mapeo explícito y separado,
`runtime_core.REAL_ADAPTER_CLASSES`, precisamente para no competir por las mismas claves
(`openai`, `anthropic`, …) que ya ocupan los *stubs* registrados desde los Bloques 2/2.1.
`gateway.dispatch()` (Bloque 2) sigue usando exclusivamente `build_default_registry()`
—los *stubs*— como antes; nada en este bloque cambia su comportamiento por defecto.
Verificado por prueba de contrato
(`test_block_1_and_block_2_provider_infrastructure_is_unchanged_by_block_4`).

`core.py` solo ganó seis excepciones nuevas (`CredentialNotConfiguredError`,
`ProviderDisabledError`, `ProviderAuthenticationError`, `ProviderTimeoutError`,
`ProviderModelNotFoundError`, más las tres primeras heredan `IntelligenceError` y las
otras dos heredan `AdapterInvocationError` del Bloque 2, sin alterarla). Ninguna línea
existente de `core.py` cambió.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/runtime_core.py`
- `nexora_app/nexora/intelligence/runtime.py`
- `nexora_app/nexora/intelligence/providers/http_support.py`
- `nexora_app/nexora/intelligence/providers/openai_compatible_live.py`
- `nexora_app/nexora/intelligence/providers/{openai,groq,deepseek,mistral,perplexity,openrouter}_live.py`
- `nexora_app/nexora/intelligence/providers/{anthropic,gemini,cohere}_live.py`
- `nexora_app/nexora/tests/test_intelligence_runtime_core.py`
- `nexora_app/nexora/tests/test_intelligence_http_support.py`
- `nexora_app/nexora/tests/test_intelligence_live_adapters.py`
- Este documento.

Modificados (aditivos, salvo lo descrito en "Compatibilidad"):

- `nexora_app/nexora/intelligence/core.py` — seis excepciones nuevas.
- `nexora_app/nexora/intelligence/service.py` — cinco funciones nuevas
  (`check_provider_readiness`, `get_provider_runtime_config`, `list_active_providers`,
  `get_provider_capabilities`, `test_provider_connection`). Cero líneas eliminadas.
- `nexora_app/nexora/permissions.py` — acción nueva `ai_test_connection`.
- `nexora_app/nexora/tests/test_intelligence_contract.py` — ocho pruebas nuevas más el
  conteo de endpoints actualizado.
- `nexora_app/nexora/tests/test_intelligence_provider_stubs.py` — una prueba renombrada
  y acotada (ver "Compatibilidad"); ninguna otra prueba del archivo cambió.

## Reglas de seguridad aplicadas

- **Ninguna API key hardcodeada, ningún secreto de ejemplo, ninguna credencial falsa.**
  Todas las pruebas usan valores sintéticos (`sk-synthetic-...`) que además fallarían la
  propia validación de plantilla del Bloque 3 si se intentaran usar como reales.
- **La credencial nunca sale del backend.** `runtime.resolve_active_credential` la
  entrega directamente al constructor del adaptador; ninguna función de este bloque la
  registra, la imprime ni la incluye en una respuesta — verificado por prueba de
  contrato (`test_runtime_never_logs_or_returns_the_secret_by_name`) y por las pruebas de
  `http_support` que confirman que ni siquiera un error de autenticación HTTP la
  incluye en su mensaje.
- **Gemini nunca lleva la credencial en la URL.** Usa la cabecera `x-goog-api-key` en vez
  del parámetro `?key=` que la documentación de Google también permite — una URL puede
  quedar en un log de proxy o de servidor web; una cabecera, no. Verificado por prueba de
  contrato.
- **Separación configuración/credencial preservada.** El Runtime Provider Manager lee
  `NXR AI Provider` (configuración) y `NXR AI Provider Credential` (secreto) por separado
  y solo los combina en memoria, dentro de la instancia del adaptador — nunca persiste
  la combinación.
- **Timeout siempre configurado.** Cada llamada real usa `timeout_seconds` de
  `NXR AI Provider` (Bloque 3); una llamada nunca puede colgarse indefinidamente.
- **Menor privilegio.** `test_provider_connection` (la única función con efecto de red
  real) exige `ai_test_connection` (`MANAGER_ROLES`) y queda auditada — más estricto que
  las funciones de solo lectura de este mismo bloque (`ai_view_provider`).

## Pruebas

Ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`; el transporte HTTP siempre
sustituido por un doble de prueba, nunca contra un endpoint real), con
`PYTHONPATH=nexora_app python3 -m unittest <módulo>`:

| Suite | Casos | Nuevo en este bloque | Resultado |
|---|---|---|---|
| `test_intelligence_core` | 41 | 0 (sin cambios) | OK |
| `test_intelligence_registry` | 11 | 0 (sin cambios) | OK |
| `test_intelligence_router` | 13 | 0 (sin cambios) | OK |
| `test_intelligence_gateway` | 15 | 0 (sin cambios) | OK |
| `test_intelligence_contract` | 32 | +8 | OK |
| `test_intelligence_adapters` | 14 | 0 (sin cambios) | OK |
| `test_intelligence_provider_stubs` | 15 | 0 (renombrada, mismo total) | OK |
| `test_intelligence_credentials` | 23 | 0 (sin cambios) | OK |
| `test_intelligence_provider_config` | 36 | 0 (sin cambios) | OK |
| `test_intelligence_runtime_core` | 21 | +21 (archivo nuevo) | OK |
| `test_intelligence_http_support` | 9 | +9 (archivo nuevo) | OK |
| `test_intelligence_live_adapters` | 12 | +12 (archivo nuevo) | OK |
| `test_app_contract` | 13 | 0 (sin cambios) | OK |

266 pruebas en total (incluye `test_integrations_core` como control), todas en verde —
50 nuevas de este bloque, sin ninguna regresión de los Bloques 1, 2, 2.1 y 3 (216
previas intactas). Cubren, con casos positivos y negativos, exactamente lo pedido:
carga desde variable de entorno vs. credencial cifrada (heredado del Bloque 3, sin
cambios), prioridad de resolución (reutiliza el Router del Bloque 1, probado ahí),
errores de autenticación (`ProviderAuthenticationError` en HTTP 401/403, distinguido de
un 500 genérico), timeout, proveedor inexistente, proveedor deshabilitado, capacidad no
soportada, modelo ausente, y construcción de solicitud correcta (URL, cabecera de
autenticación, cuerpo) para cada uno de los nueve proveedores — todo mockeando el
transporte HTTP, nunca contra la red real.

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

No ejecutado en este entorno (requiere `bench` + MariaDB, y una credencial real que no
existe en ningún entorno de este proyecto): la integración real de `runtime.py` contra
un sitio Frappe real, y por definición, cualquier llamada real de red contra un
proveedor de IA. Queda para cuando el propietario configure una credencial real y lo
decida explícitamente — este bloque no lo hace por sí solo.

## Limitaciones reales

- Las nueve integraciones nunca se ejercitaron contra una cuenta real de cada proveedor.
  Se construyeron contra la forma pública y documentada de cada API al momento de
  escribir este bloque; un proveedor puede cambiar su API sin aviso, y el primer intento
  real puede requerir un ajuste menor (nombre de campo, código de error no mapeado
  todavía). Esto es intrínseco a no haber podido probar contra la red real, no un defecto
  oculto.
- `test_provider_connection` es la única función de todo el subsistema con efecto real
  fuera de NEXORA — vale la pena que quien opere el sistema lo sepa antes de llamarla con
  una credencial real configurada: consume una unidad mínima de cuota del proveedor.
- La detección de "modelo inexistente" depende de que el proveedor responda con un
  código reconocible; hoy se clasifica como error genérico
  (`AdapterInvocationError`) salvo que sea un 401/403 (autenticación) — no hay mapeo
  específico por proveedor de "este modelo no existe" todavía, porque cada proveedor lo
  señala de forma distinta y confirmarlo requeriría probarlo contra la API real.
- `ProviderModelNotFoundError` está declarada en `core.py` para cuando un bloque futuro
  con acceso a pruebas contra proveedores reales pueda mapear cada código de error
  específico; hoy ningún adaptador la lanza todavía.
