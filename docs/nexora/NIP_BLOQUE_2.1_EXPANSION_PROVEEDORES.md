# NEXORA Intelligence Platform — Bloque 2.1: expansión de proveedores IA

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> y a [`AGENTS.md`](../../AGENTS.md). Extiende
> [`NIP_BLOQUE_2_AI_PROVIDER_ADAPTERS.md`](NIP_BLOQUE_2_AI_PROVIDER_ADAPTERS.md) sin
> modificar su comportamiento — ver "Compatibilidad" más abajo.

## Problema

El Bloque 2 demostró el patrón de adaptador con tres proveedores (OpenAI, Anthropic,
Gemini). Faltaba comprobar que ese patrón realmente se sostiene sin tocar el núcleo al
añadir un proveedor nuevo — la promesa central del Provider Manager
(`NEXORA_INTELLIGENCE_ARCHITECTURE.md`, sección 3: "extensible sin romper lo
existente"). Este bloque la pone a prueba seis veces seguidas.

## Alcance de este bloque

Incluido — seis adaptadores simulados nuevos, todos con la misma forma exacta que los
tres del Bloque 2 (misma interfaz `AIProviderAdapter`, mismo decorador
`@register_adapter`, mismo helper compartido `simulated_invoke`):

| Adaptador | `provider_key` | Capacidades declaradas (ilustrativas) |
|---|---|---|
| `GroqAdapter` | `groq` | `text` |
| `DeepSeekAdapter` | `deepseek` | `text` |
| `MistralAdapter` | `mistral` | `text`, `vision` |
| `CohereAdapter` | `cohere` | `text`, `embedding` |
| `PerplexityAdapter` | `perplexity` | `text` |
| `OpenRouterAdapter` | `openrouter` | `text`, `vision` |

Explícitamente fuera de alcance (igual que el Bloque 2):

- Ningún SDK real, ninguna API key, ninguna llamada HTTP — verificado por la misma
  prueba de contrato del Bloque 2 (`test_no_provider_file_imports_a_real_sdk_or_touches_the_network`),
  que recorre `providers/*.py` y por tanto cubre los seis archivos nuevos sin
  modificarse.
- Ninguna interfaz gráfica, ningún chat, ninguna memoria.
- Ningún proveedor real conectado. Cero cambios en `service.py`, cero nuevo consumidor
  de `dispatch`.

## Compatibilidad con el Bloque 2

Ningún archivo del Bloque 1 ni del Bloque 2 cambió de comportamiento:

- `core.py`, `registry.py`, `router.py`, `config.py`, `service.py`,
  `adapters.py`: **sin tocar**.
- `openai_stub.py`, `anthropic_stub.py`, `gemini_stub.py`, `stub_support.py`: **sin
  tocar**.
- `providers/__init__.py`: se añadieron seis imports y sus seis entradas en `__all__`.
  Las tres entradas del Bloque 2 siguen exactamente igual.
- `test_intelligence_adapters.py`: se añadieron dos pruebas
  (`test_includes_the_six_block_2_1_stub_providers`,
  `test_default_registry_has_exactly_nine_providers_after_block_2_1`). La prueba del
  Bloque 2 (`test_includes_the_three_block_2_stub_providers`) no cambió una línea y
  sigue verde.
- `test_intelligence_provider_stubs.py`: los tres adaptadores del Bloque 2 mantienen sus
  pruebas dedicadas sin cambios (`test_invoke_returns_a_simulated_response_...`,
  `test_invoke_rejects_an_unsupported_capability`, etc.). Las pruebas que recorrían
  `STUB_ADAPTERS` en bucle (contrato genérico: es un `AIProviderAdapter`, declara su
  `provider_key`, declara sus capacidades, nunca finge ser real) ahora recorren
  `ALL_STUB_ADAPTERS` — la unión de `STUB_ADAPTERS` (Bloque 2, sin tocar) y
  `EXPANDED_STUB_ADAPTERS` (Bloque 2.1, nuevo) — así que las mismas aserciones que ya
  pasaban para los tres primeros siguen pasando exactamente igual, y ahora también
  corren para los seis nuevos.

`build_default_registry()` no cambió una línea: como en el Bloque 2, importa
`nexora.intelligence.providers` e instancia una clase por cada clave registrada.
Registrar seis clases más en `providers/__init__.py` basta para que aparezcan — es
exactamente la promesa que este bloque venía a comprobar.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/providers/groq_stub.py`
- `nexora_app/nexora/intelligence/providers/deepseek_stub.py`
- `nexora_app/nexora/intelligence/providers/mistral_stub.py`
- `nexora_app/nexora/intelligence/providers/cohere_stub.py`
- `nexora_app/nexora/intelligence/providers/perplexity_stub.py`
- `nexora_app/nexora/intelligence/providers/openrouter_stub.py`
- Este documento.

Modificados (aditivos únicamente):

- `nexora_app/nexora/intelligence/providers/__init__.py`
- `nexora_app/nexora/tests/test_intelligence_adapters.py`
- `nexora_app/nexora/tests/test_intelligence_provider_stubs.py`

Nada más se tocó.

## Pruebas

Ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`), con
`PYTHONPATH=nexora_app python3 -m unittest <módulo>`:

| Suite | Casos | Nuevo en este bloque | Resultado |
|---|---|---|---|
| `test_intelligence_core` | 41 | 0 (sin cambios) | OK |
| `test_intelligence_registry` | 11 | 0 (sin cambios) | OK |
| `test_intelligence_router` | 13 | 0 (sin cambios) | OK |
| `test_intelligence_gateway` | 15 | 0 (sin cambios) | OK |
| `test_intelligence_contract` | 13 | 0 (sin cambios) | OK |
| `test_intelligence_adapters` | 14 | +2 | OK |
| `test_intelligence_provider_stubs` | 15 | +4 (más 6 casos existentes ahora ejercitados también con los proveedores nuevos vía `ALL_STUB_ADAPTERS`) | OK |
| `test_app_contract` | 13 | 0 (sin cambios) | OK |

135 pruebas en total, todas en verde, sin ninguna regresión de los Bloques 1 y 2. Casos
positivos y negativos añadidos: `GroqAdapter` rechaza `vision` (nunca la declaró),
`CohereAdapter` acepta y simula `embedding`, `OpenRouterAdapter` rechaza `audio`, el
registro por defecto contiene exactamente 9 proveedores tras este bloque.

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
anteriores, queda para el CI del PR.

## Limitaciones reales

- Los nueve adaptadores son simulados; ninguno contacta un proveedor real.
- Las capacidades asignadas a los seis proveedores nuevos son ilustrativas, elegidas
  para variar el conjunto disponible en las pruebas de enrutamiento — no son una
  afirmación certificada sobre las capacidades reales de esos proveedores, todavía no
  conectados.
- Sigue sin existir ningún consumidor real de `dispatch`; este bloque prueba que el
  catálogo de proveedores escala, no que algo del ERP ya lo use.
