# NEXORA — Estado de ejecución

- Fecha de cierre técnico: 2026-08-02
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- Commit base de cierre de fase 1: `18f7219a3ae4d566c502090b2543c84e11d89768`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**
- Migración histórica de registros: **NO**

## Bloque 1.1 — cierre formal de fase 1

Este bloque cerró la fase documental e identidad sin tocar backend, frontend, DocTypes, permisos, servicios ni lógica de negocio.

### Cambios realizados

- Se alineó la superficie documental y operativa visible a **NEXORA**.
- Se conservó trazabilidad del legado donde sigue siendo útil o técnicamente necesario.
- Se evitó cualquier cambio en comportamiento funcional.
- Se verificó que la documentación modificada permaneciera coherente con el README y con la identidad oficial NEXORA.

### Archivos modificados en el Bloque 1

- `docs/CONSTRUCONTROL_ADMIN_GUIDE.md`
- `docs/final/NEXORA_ENTREGA_FINAL.md`
- `.github/workflows/apply-construcontrol-consolidation.yml`
- `.github/workflows/construcontrol-branch-cleanup.yml`
- `.github/workflows/construcontrol-container-receipt.yml`
- `.github/workflows/construcontrol-runtime-receipt.yml`
- `.github/workflows/construcontrol-validation.yml`
- `.github/workflows/construcontrol-verification-receipt.yml`
- `.github/workflows/forensic-audit-snapshot.yml`

### Riesgos pendientes

- Persisten nombres técnicos heredados en rutas, artefactos y contratos internos donde cambiarlos afectaría compatibilidad o trazabilidad.
- Este cierre no ejecuta ni valida runtime de Frappe/MariaDB, navegador, PWA ni linters.

### Estado real de NXR-CONS-001

- **Estado:** NO DEMOSTRADO como requisito trazable independiente en el árbol revisado.
- **Interpretación operativa:** el cierre de fase 1 deja la identidad documental alineada, pero no aporta evidencia funcional nueva para elevarlo a validado.

### Evidencia de publicación

- Commit del bloque 1 publicado en `main`: `18f7219a3ae4d566c502090b2543c84e11d89768`.
- Cierre formal de fase 1 publicado en `main` mediante este archivo.

## Base certificada anterior

- Fundación y consola: PR `#11` y `#26`; fusión `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.

## Bloque 2 — Auditoría real de `nexora_app` y correcciones (en revisión)

### Auditoría ejecutada (estática, sobre el árbol completo)

- Estructura de paquetes: 50 DocTypes revisados en `nexora_app/nexora/nexora/doctype/`; 18 carecían de `__init__.py`, rompiendo la convención Frappe y la cobertura de empaquetado (`flit_core.buildapi` + `MANIFEST.in`).
- Seguridad de endpoints: 135 métodos `@frappe.whitelist` revisados. Todos los flujos sensibles quedan cubiertos por `require_action` / `require_project_access`, de forma directa o transitiva (`dashboard/expense_query.py`, `dashboard/snapshot_query.py`, `contracts/service.py`, `close/canonical_weekly.py`, `directory/service.py`). `get_build_info` permanece abierto a usuarios autenticados de forma intencional (no expone datos sensibles).
- Duplicación de lógica: helpers `_payload`, `_text` y `_period` reimplementados en cuatro módulos de `dashboard/` pese a existir `dashboard/query_utils.py`.
- Linters: `ruff check` y `ruff format --check` en verde sobre `nexora_app` (307 archivos) antes y después de los cambios.

### Correcciones aplicadas

- Se crearon los 18 `__init__.py` ausentes en paquetes de DocType.
- `dashboard/query_utils.payload` acepta un mensaje opcional para conservar textos de error específicos por módulo.
- `dashboard/expense_query.py`, `dashboard/snapshot_query.py`, `dashboard/contract_query.py` y `dashboard/pending_query.py` delegan sus helpers a `query_utils` sin alterar comportamiento ni compatibilidad.
- Se conservó el `_period` propio de `snapshot_query.py` (usa `frappe.utils.today()` como cierre por omisión), por no ser equivalente al helper central.
- Detalle completo y evidencia de duplicación: `docs/BLOQUE_2_AUDITORIA.md`.

### Evidencia de publicación del Bloque 2

- Rama: `nexora/bloque-2-auditoria`.
- Pull Request: `#49` (abierto contra `main`).
- Alcance contenido al dominio `nexora_app/nexora/dashboard/` y a los paquetes de DocType; sin cambios en otros módulos.

### Riesgos pendientes del Bloque 2

- Sigue sin ejecutarse validación runtime de Frappe/MariaDB, navegador y PWA en este entorno; esa verificación depende del CI del repositorio.
- Las pruebas de contrato basadas en marcadores de código fuente permanecen intactas, pero solo el CI puede confirmarlo con Frappe instalado.

## Veredicto de esta fase

- **Bloque 1:** cerrado.
- **Bloque 1.1:** cerrado.
- **Bloque 2:** auditoría estática ejecutada y correcciones publicadas en PR `#49`; pendiente de revisión y fusión.
