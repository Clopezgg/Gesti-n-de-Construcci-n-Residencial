# NEXORA Intelligence Platform — Bloque 2: AI Provider Adapters

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> (secciones 3 y 7) y a [`AGENTS.md`](../../AGENTS.md). Continúa
> [`NIP_BLOQUE_1_AI_GATEWAY_PROVIDER_MANAGER.md`](NIP_BLOQUE_1_AI_GATEWAY_PROVIDER_MANAGER.md)
> sin modificar su código, salvo dos correcciones puntuales documentadas abajo.

## Problema

El Bloque 1 dejó el Provider Manager y el Router capaces de decidir *qué* proveedor
configurado atendería una capacidad, pero nada podía ejecutarse: no existía ningún
adaptador de código, así que "resolver" un proveedor no producía ninguna respuesta. Este
bloque construye esa pieza — el contrato de adaptador ya definido en el Bloque 1
(`AIProviderAdapter`) cobra una primera implementación real, todavía simulada.

## Alcance de este bloque

Incluido:

- Tres adaptadores simulados que implementan exactamente la misma interfaz
  (`AIProviderAdapter`, definida en el Bloque 1): `OpenAIStubAdapter`,
  `AnthropicStubAdapter`, `GeminiStubAdapter`.
- Registro automático de adaptadores: decorador `@register_adapter` que da de alta una
  clase por su `provider_key` al importarse — añadir un proveedor nuevo es un archivo
  nuevo en `providers/` más una línea de import en `providers/__init__.py`; ni el
  Gateway, ni el Router, ni el Provider Manager cambian.
- `AdapterRegistry`: registro en memoria de *instancias* de adaptador — distinto del
  `ProviderRegistry` del Bloque 1, que registra *configuración* (`ProviderRecord`), no
  código.
- `gateway.dispatch(...)`: compone `resolve` (Bloque 1) con `AdapterRegistry` (Bloque 2)
  para invocar de verdad al adaptador elegido. Sigue sin tocar la red por sí mismo — la
  tocaría el adaptador, y los tres que existen hoy no la tocan.
- Validaciones: `register_adapter` rechaza una clase sin `provider_key` y rechaza que dos
  clases distintas reclamen la misma clave; cada adaptador rechaza una capacidad que no
  declaró.
- Manejo de errores: `AdapterInvocationError` (nueva, aditiva en `core.py`) para
  capacidad no soportada por el adaptador ya elegido — distinta de
  `NoProviderAvailableError` (Bloque 1: ningún candidato configurado) y de
  `ProviderNotFoundError` (reutilizada: proveedor configurado y activo, pero sin
  adaptador de código todavía — situación válida, no un error de configuración).

Explícitamente fuera de alcance (siguiente bloque o posterior):

- Ningún SDK real (`openai`, `anthropic`, `google-generativeai`) se instaló ni se
  importó. Ninguna API key. Ninguna llamada de red — verificado por prueba de contrato
  (`test_no_provider_file_imports_a_real_sdk_or_touches_the_network`).
- Ninguna interfaz gráfica, ningún chat, ninguna memoria.
- Ningún módulo de negocio del ERP fue modificado ni quedó conectado a `dispatch`.
- `service.py` (la capa `@frappe.whitelist` del Bloque 1) no se tocó: sigue
  exactamente con los mismos cuatro endpoints, sin ninguno nuevo — verificado por
  prueba de contrato (`test_service_was_not_touched_by_block_2`). No hay todavía ningún
  consumidor real de `dispatch`; exponerlo por red es trabajo del bloque que sí lo
  necesite.
- Model Router con criterios de costo/latencia/salud: el router del Bloque 1 sigue
  siendo el único, sin cambios de comportamiento.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/adapters.py`
- `nexora_app/nexora/intelligence/providers/__init__.py`
- `nexora_app/nexora/intelligence/providers/stub_support.py`
- `nexora_app/nexora/intelligence/providers/openai_stub.py`
- `nexora_app/nexora/intelligence/providers/anthropic_stub.py`
- `nexora_app/nexora/intelligence/providers/gemini_stub.py`
- `nexora_app/nexora/tests/test_intelligence_adapters.py`
- `nexora_app/nexora/tests/test_intelligence_provider_stubs.py`
- Este documento.

Modificados (Bloque 1, ambos cambios aditivos o correctivos — ver más abajo):

- `nexora_app/nexora/intelligence/core.py` — una clase nueva, `AdapterInvocationError`.
  Ninguna línea existente cambió.
- `nexora_app/nexora/intelligence/gateway.py` — una función nueva, `dispatch`, más los
  imports que necesita. `build_registry` no cambió. `resolve` conservó su
  comportamiento; solo se corrigió una frase de su docstring que, tras decidirse el
  alcance real de este bloque, había quedado desactualizada (mencionaba "Model Router
  del Bloque 2", cuando el Bloque 2 terminó siendo "AI Provider Adapters") — un defecto
  documental comprobado, no un cambio de diseño.
- `nexora_app/nexora/tests/test_intelligence_gateway.py` — se añadió la clase
  `TestGatewayDispatch` (6 casos) y se ampliaron los imports. Ningún caso existente del
  Bloque 1 se modificó ni se eliminó.
- `nexora_app/nexora/tests/test_intelligence_contract.py` — se añadieron dos métodos de
  prueba (existencia de los archivos de este bloque; `service.py` intacto). Ningún caso
  existente se modificó.

Nada más se tocó: `service.py`, `registry.py`, `router.py`, `config.py`, el DocType
`NXR AI Provider`, `permissions.py` y `test_app_contract.py` quedaron exactamente como
los dejó el Bloque 1.

## Decisión de diseño relevante

`AdapterRegistry` (código ejecutable) y `ProviderRegistry` (configuración) se mantienen
deliberadamente separados en vez de fusionarse en una sola estructura. Un
`ProviderRecord` activo en `NXR AI Provider` no obliga a que exista un adaptador de
código — `dispatch` lo maneja como un caso válido y distinguible
(`ProviderNotFoundError`, con mensaje propio), no como un error de configuración. Esta
separación es la que permite que el Provider Manager (administración) y los adaptadores
(implementación) evolucionen en bloques distintos sin acoplarse, tal como exige
`NEXORA_INTELLIGENCE_ARCHITECTURE.md` sección 3.

## Pruebas

Todas ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`), con
`PYTHONPATH=nexora_app python3 -m unittest <módulo>`:

| Suite | Casos | Nuevo en este bloque | Resultado |
|---|---|---|---|
| `test_intelligence_core` | 41 | 0 (sin cambios) | OK |
| `test_intelligence_registry` | 11 | 0 (sin cambios) | OK |
| `test_intelligence_router` | 13 | 0 (sin cambios) | OK |
| `test_intelligence_gateway` | 15 | +6 (`TestGatewayDispatch`) | OK |
| `test_intelligence_contract` | 13 | +2 | OK |
| `test_intelligence_adapters` | 12 | +12 (archivo nuevo) | OK |
| `test_intelligence_provider_stubs` | 11 | +11 (archivo nuevo) | OK |
| `test_app_contract` | 13 | 0 (sin cambios) | OK |

129 pruebas de `intelligence/` + `test_app_contract`, todas en verde, con casos
positivos y negativos: adaptador que rechaza una capacidad no declarada, registro que
rechaza una clave duplicada por otra clase, `dispatch` que propaga
`NoProviderAvailableError` sin configuración y `ProviderNotFoundError` cuando hay
configuración pero no adaptador, respuesta simulada determinista y sin mutar el payload
recibido.

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

No ejecutado en este entorno (requiere `bench` + MariaDB): igual que en el Bloque 1,
queda para el CI del PR.

## Limitaciones reales

- Los tres adaptadores son simulados. `invoke()` nunca contacta un proveedor real; la
  respuesta siempre trae `"simulated": True` para que sea imposible confundirla con una
  respuesta genuina en un log o en una prueba futura.
- `dispatch` no tiene consumidor real todavía, igual que `resolve_capability` en el
  Bloque 1. Su valor en este bloque es demostrar, con pruebas, que la cadena completa
  (configuración activa → resolución → adaptador de código → respuesta) funciona antes
  de que un bloque futuro lo exponga a algo que realmente lo use.
- Las capacidades asignadas a cada stub (`text`/`vision` para OpenAI y Anthropic;
  `text`/`vision`/`audio` para Gemini) son ilustrativas, elegidas para que las pruebas
  de enrutamiento tengan más de un proveedor entre el que elegir por capacidad — no son
  una afirmación certificada sobre las capacidades reales de esos proveedores.
