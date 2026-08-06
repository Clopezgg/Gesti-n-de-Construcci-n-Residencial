# NEXORA Intelligence Platform — Bloque 1: AI Gateway + AI Provider Manager

> Subordinado a [`NEXORA_INTELLIGENCE_ARCHITECTURE.md`](../../NEXORA_INTELLIGENCE_ARCHITECTURE.md)
> (secciones 6 y 7) y a [`AGENTS.md`](../../AGENTS.md). Registra qué se construyó de ese
> diseño, qué se dejó fuera a propósito y con qué se probó.

## Problema

NEXORA no tenía ningún punto de entrada para inteligencia artificial. La arquitectura
aprobada exige que, cuando exista, ningún módulo del ERP dependa de un proveedor de IA
concreto. Este bloque construye la primera capa —resolución de proveedor— sin conectar
todavía ningún proveedor real.

## Alcance de este bloque

Incluido:

- Interfaz base (`AIProviderAdapter`) que todo adaptador de proveedor futuro deberá
  implementar.
- Provider Manager: registro de proveedores configurados (`ProviderRegistry`, DocType
  `NXR AI Provider`).
- Router interno determinista (`resolve_provider`): capacidad → proveedor activo, con
  *fallback* de prioridad y desempate estable.
- AI Gateway mínimo (`gateway.build_registry` / `gateway.resolve`, y
  `intelligence.service.resolve_capability`): decide qué proveedor atendería una
  solicitud, sin invocar a ninguno.
- Configuración inicial (`intelligence/config.py`): estado por defecto, prioridad por
  defecto, límite de proveedores.
- Validaciones de clave, nombre, estado, prioridad y capacidades
  (`intelligence/core.py`).
- Permisos nuevos y exclusivamente aditivos en `permissions.py`:
  `ai_manage_provider` (`MANAGER_ROLES`) y `ai_view_provider` (`REPORT_EXPORT_ROLES`).
  Ninguna entrada existente se modificó.
- Auditoría reutilizada: cada registro y cambio de estado de proveedor llama a
  `financial.db.audit(...)`, el mismo helper que usa el resto de NEXORA — no se creó un
  segundo sistema de auditoría.

Explícitamente fuera de alcance (siguiente bloque o posterior):

- API Key Manager: ningún campo de credencial existe en `NXR AI Provider` — verificado
  por prueba de contrato (`test_ai_provider_doctype_has_no_credential_field`).
- Model Router con criterios de costo/latencia/salud — el router de este bloque solo
  decide por capacidad + prioridad configurada.
- Prompt Manager, Conversation Engine, Memory Engine, Tool Engine, Automation Engine,
  OCR/Vision, Voice, Agentes — nada de esto se tocó.
- Cualquier UI. Nada en `nexora/page/`, `hooks.py` (`app_include_js`/`app_include_css`)
  ni el workspace cambió.
- Cualquier adaptador real de proveedor. `intelligence/` no importa ningún SDK de IA;
  verificado por prueba de contrato
  (`test_no_provider_adapter_is_shipped_yet`).
- Ningún módulo de negocio existente (`financial`, `contracts`, `directory`, …) fue
  modificado para consumir este subsistema.

## Archivos

Nuevos:

- `nexora_app/nexora/intelligence/__init__.py`
- `nexora_app/nexora/intelligence/core.py`
- `nexora_app/nexora/intelligence/config.py`
- `nexora_app/nexora/intelligence/registry.py`
- `nexora_app/nexora/intelligence/router.py`
- `nexora_app/nexora/intelligence/gateway.py`
- `nexora_app/nexora/intelligence/service.py`
- `nexora_app/nexora/nexora/doctype/nxr_ai_provider/{__init__.py,nxr_ai_provider.json,nxr_ai_provider.py}`
- `nexora_app/nexora/tests/test_intelligence_core.py`
- `nexora_app/nexora/tests/test_intelligence_registry.py`
- `nexora_app/nexora/tests/test_intelligence_router.py`
- `nexora_app/nexora/tests/test_intelligence_gateway.py`
- `nexora_app/nexora/tests/test_intelligence_contract.py`
- Este documento.

Modificados (mínimo necesario, ambos aditivos):

- `nexora_app/nexora/permissions.py` — dos claves nuevas en `ACTION_ROLES`.
- `nexora_app/nexora/tests/test_app_contract.py` — el conteo de DocTypes instalables
  pasa de 50 a 51 (`test_doctype_package_and_module_declarations_are_installable`),
  reflejando el DocType nuevo.

Nada más se tocó: ningún archivo de `erpnext/`, `deploy/`, `.github/workflows/`,
`docker-compose*.yml` ni ningún Dockerfile.

## Decisión de diseño relevante

`ProviderRecord` (config validada e inmutable: clave, nombre, estado, capacidades,
prioridad) es deliberadamente distinto de `AIProviderAdapter` (el contrato de ejecución
futuro). El primero es lo que hoy existe y se prueba; el segundo fija la forma que un
adaptador real deberá tener cuando se construya, sin que su existencia obligue a
implementar nada todavía. Esta separación es la que permite que
`test_no_provider_adapter_is_shipped_yet` verifique, de forma mecánica, que el bloque
cumple "no consumir ningún proveedor real".

## Pruebas

Todas ejecutables sin `bench`/MariaDB (lógica pura, sin `frappe`), con
`PYTHONPATH=nexora_app python3 -m unittest <módulo>`:

| Suite | Casos | Resultado |
|---|---|---|
| `test_intelligence_core` | 41 | OK |
| `test_intelligence_registry` | 11 | OK |
| `test_intelligence_router` | 13 | OK |
| `test_intelligence_gateway` | 9 | OK |
| `test_intelligence_contract` | 11 | OK |
| `test_app_contract` (actualizado) | 13 | OK |

Total 85 pruebas propias de este bloque + 13 de regresión de `test_app_contract` (98 en
conjunto), todas con casos positivos y negativos (p. ej. `NoProviderAvailableError` con
registro vacío, `ProviderConfigError` con clave/estado/capacidad inválida, desempate
determinista entre proveedores de igual prioridad).

Guards reales del repositorio, ejecutados sin modificación contra el árbol resultante:

| Validador | Resultado |
|---|---|
| `python -m compileall nexora_app/nexora scripts` | OK |
| `scripts/validate_nexora_app.py` | `exit 0` — imports locales, módulo `NEXORA`, controlador, sin importaciones legado |
| `scripts/validate_nexora_financial_models.py` | `exit 0` — 10 DocTypes financieros canónicos, sin cambios |
| `scripts/validate_nexora_governance.py` | `exit 0` — 166 requisitos, 37 máquinas, sin cambios |
| `scripts/validate_nexora_completion.py` | `exit 0` |
| `scripts/validate_nexora_operational_acceptance.py` | `exit 0` |
| `scripts/validate_github_governance.py` | `exit 0` |
| `scripts/validate_nexora_constitution.py` | `exit 0` |

No ejecutado en este entorno (requiere `bench` + MariaDB, no disponibles aquí): pruebas
de integración de `service.py` contra un sitio real, `install-rollback`, recorrido de
navegador. Queda para el pipeline de CI del PR (`nexora-app.yml`), tal como certifica
cualquier otro bloque de este repositorio.

## Limitaciones reales

- `resolve_capability` no tiene todavía ningún consumidor real: ningún módulo de negocio
  lo llama. Su único propósito en este bloque es dejar demostrado, con pruebas, que la
  decisión de enrutamiento es correcta antes de que el Bloque 2 la use.
- Con cero proveedores registrados (el estado de fábrica tras este bloque), cualquier
  llamada a `resolve_capability` responde `resolved: false` — comportamiento esperado,
  no un defecto: es la degradación segura descrita en la arquitectura.
- `docs/architecture/file_inventory.json` no se regeneró: `scripts/validate_repository.py
  --check` (heredado del guard de ConstruControl, no del guard `nexora-app.yml`) ya
  reportaba el inventario desactualizado **antes** de este bloque, por razones ajenas a
  este trabajo. No se tocó, para no mezclar una corrección no relacionada en este commit.
