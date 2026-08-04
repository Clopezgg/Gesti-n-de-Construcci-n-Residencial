# NEXORA — Estado de ejecución

- Fecha de cierre técnico: 2026-08-04
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- HEAD inicial de `main` verificado: `8ed7bd292c29fda0f57a41b3102f0f290bb8e90c`
- Rama de trabajo de este bloque: `claude/nexora-surgical-audit-lsxcuh`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**
- Migración histórica de registros: **NO**

## Bloque 2 — corrección quirúrgica de carga de páginas, permisos y navegación

Este bloque corrige defectos que impedían el uso real del sistema, retira el ruido
que rompía la propia puerta de calidad del repositorio y deja pruebas de regresión
que impiden que los mismos defectos vuelvan.

### Estado real encontrado

1. **`main` estaba rojo contra su propio contrato.** `scripts/validate_nexora_app.py`
   —el primer paso del job `contract` de `.github/workflows/nexora-app.yml`— salía con
   código 1 en `8ed7bd2` porque los últimos ocho commits habían añadido ocho workflows
   `nexora-*` que ese mismo guard declara no aprobados.

2. **Cuatro de las doce páginas NEXORA se servían en blanco.** Frappe resuelve los
   assets de una `Page` con `frappe.scrub(name)`, que convierte guiones en guiones
   bajos: `Page.load_assets()` busca `<módulo>/page/<scrub(name)>/<scrub(name)>.js`.
   Cuatro páginas vivían en carpetas con guion, así que el registro `Page` se creaba
   correctamente pero el script quedaba vacío y la pantalla se abría sin contenido,
   sin lanzar error. Afectaba a `nexora-dashboard` —ruta de `add_to_apps_screen`,
   `start_url` del PWA y primer acceso del workspace—, `nexora-reports`,
   `nexora-closing` y `nexora-search`. El directorio `page/nexora_dashboard/`
   existía con solo un `__init__.py`: evidencia de un renombrado dejado a medias.

3. **El núcleo de fondos estaba abierto a todo el sitio.**
   `nexora_finance.json` no declaraba `roles`. Con la tabla de roles vacía,
   `Page.has_permission()` de Frappe devuelve `True` para cualquier usuario
   autenticado, mientras las otras once páginas sí restringían a roles NEXORA.

4. **Un botón del dashboard no llevaba a ninguna parte.** «Avance de la obra →
   Detalle» enrutaba a `nexora-projects`, una página inexistente.

5. **El workspace ocultaba la mayor parte del producto.** Definía 21 accesos
   directos y solo renderizaba 6 en `content`; en Frappe v15 un acceso directo
   ausente de `content` es invisible. Quedaban inalcanzables desde el workspace el
   directorio de entidades, proveedores, solicitudes de compra, evidencias y los
   DocTypes del libro central. `nexora-operations` y `nexora-quotations` no tenían
   acceso directo alguno.

6. **Metadatos de página inconsistentes.** `nexora_quotations.json` usaba campos
   inexistentes en el DocType `Page` (`label`, `document_type`, `script`) y no
   declaraba `title` ni `standard`: se registraba sin título.

7. **18 de las 50 carpetas de DocType no tenían `__init__.py`**, frente a las otras
   32 que sí lo tenían.

### Ruido retirado del repositorio

| Elemento | Motivo |
|---|---|
| 8 workflows `nexora-*` de orquestación de agentes | Rechazados por el guard del repositorio; sin bloque `permissions:`; autoejecutaban `ops/agents/scripts` |
| `ops/agents/**` (77 archivos) | Andamiaje autorreferencial. `unified_gate.sh` y `validate.sh` invocaban `pytest` y `npm test`, que este repositorio no usa: no validaban el producto |
| `auto_merge_ready_prs.sh`, `nexora_mass_cleanup.sh` | Automatización no revisada que fusiona PRs y borra ramas en masa |
| `pr_audit_report.txt` | Instantánea de auditoría caducada |
| `docs/nexora-agent-architecture.md` | Quedaba huérfano al retirar `ops/agents` |

### Correcciones aplicadas

- Carpetas y archivos de página renombrados a la convención `frappe.scrub`:
  `nexora_dashboard`, `nexora_reports`, `nexora_closing`, `nexora_search`.
  Referencias actualizadas en scripts, workflows y pruebas.
- `__init__.py` añadido a los 6 paquetes de página y a los 18 de DocType que
  faltaban. Las 12 páginas y los 50 DocTypes quedan homogéneos.
- `nexora-finance` declara los cinco roles NEXORA. La escritura sigue validada en
  servidor por `require_action`; la lectura corresponde a `ACCESS_ROLES`, que ya
  incluye los cinco roles, de modo que no se bloquea ninguna operación legítima.
- `nexora-quotations` normalizado al esquema real del DocType `Page`.
- El botón «Detalle» abre el reporte `PR03`, que es exactamente el avance físico y
  financiero que la tarjeta resume.
- `content` del workspace reconstruido en seis secciones que exponen los 23 accesos
  directos; añadidos los de `nexora-operations` y `nexora-quotations`.
- `contract_query`, `expense_query`, `pending_query` y `snapshot_query` delegan sus
  helpers duplicados en `nexora.dashboard.query_utils`; `payload()` acepta un
  mensaje propio para conservar el error específico de cada módulo.

### Qué se validó

| Verificación | Resultado |
|---|---|
| `scripts/validate_nexora_app.py` | de `exit 1` a `exit 0` |
| `scripts/validate_nexora_financial_models.py` | 10 DocTypes canónicos |
| `scripts/validate_nexora_operational_acceptance.py` | 0 errores |
| `scripts/validate_nexora_completion.py` | 166 requisitos, 0 errores |
| `scripts/validate_nexora_governance.py` | línea base verificada |
| Suite de contrato (`test_*contract.py`) | 252 pruebas, OK |
| `test_financial_core`, `test_evidence_core`, `test_directory_core` | 34 pruebas, OK |
| `node --check` sobre las 12 páginas, los 6 bundles públicos, el service worker y el smoke | sin errores de sintaxis |
| `python -m compileall nexora_app/nexora scripts` | OK |

Prueba negativa y de persistencia sobre el defecto principal: se ejecutó una réplica
de `Page.load_assets()` contra los dos árboles. En `origin/main`, 8 páginas resolvían
script y **4 quedaban en blanco**, y `nexora-finance` figuraba como accesible para
todo usuario autenticado. En el árbol corregido, **12 páginas resuelven script, 0 en
blanco**, y las 12 declaran roles NEXORA.

Prueba de que la interfaz no promete más de lo que el backend soporta: las 75
referencias `nexora.*` que el JavaScript invoca por `frappe.call` se resolvieron
contra las 135 funciones `@frappe.whitelist()`, siguiendo las reexportaciones de las
fachadas `service.py`. **0 métodos inexistentes o no expuestos.**

### Pruebas de regresión añadidas

`nexora_app/nexora/tests/test_page_registry_contract.py` exige que la carpeta de cada
página sea `scrub(name)`, que el script exista y se registre bajo el nombre real del
`Page`, que no quede ningún asset con guion, que ninguna página tenga la tabla de
roles vacía y que sus roles pertenezcan a los cinco de NEXORA, que toda página sea
alcanzable desde el workspace, que todo acceso directo esté renderizado en `content` y
apunte a un destino existente, y que toda ruta de navegación del cliente
(`data-route`, `set_route`, `/app/…`) apunte a una página que existe.

`test_app_contract` exige además el marcador de paquete en cada carpeta de DocType.

### Limpieza de ramas y PRs

Los 10 PRs abiertos se cerraron con nota individual.

| PR | Rama | Clasificación | Acción |
|---|---|---|---|
| #49, #51, #53 | `nexora/bloque-2-auditoria`, `fix/remediation-96a0e1b5-471bf3`, `fix/remediation-a5eb7470-0fdc7f` | Duplicados anidados (#51 ⊂ #49 ⊂ #53), los tres en conflicto | Contenido útil absorbido en este bloque; cerrados sin pérdida |
| #54 | `Clopezgg-patch-2` | Instrucciones de agente, sin efecto en el producto; duplicado en 4 ramas | Cerrado |
| #39, #41, #42, #43 | `Clopezgg-patch-1`, `copilot/fix-predeploy-*`, `codex/confirmar-conexion-al-repositorio` | Carga no fusionable: ~12.900 inserciones con `archivos.txt` y `archives.txt` (5.404 líneas cada uno, duplicados), `SECURITY-FINDINGS.txt` (1,4 MB binario), 7 `Nexora-*.ps1` —3 vacíos— y un archivo cuyo nombre es un fragmento de shell | Cerrados; ramas conservadas por contener trabajo aprovechable (Sentry) |
| #37, #36 | `revert-35-chore/nexora-consolidacion-total`, `git-checkout--b-prueba-chatgpt-review` | Título ajeno al contenido (el diff real es un `cr.yml` de 61 líneas); #36 apuntaba a una rama de trabajo, no a `main` | Cerrados; ramas conservadas |

Ramas verificadas como retirables sin pérdida funcional (la eliminación remota quedó
bloqueada por el proxy git de este entorno, ver más abajo):

| Rama | Evidencia |
|---|---|
| `nexora-block1-identity` | Ancestro de `main`: 0 commits y 0 archivos propios |
| `fix/nexora-date-string-normalization` | Historia sin ancestro común; 0 archivos que no estén ya en `main`; `main` la supera en 5.361 líneas dentro de `nexora_app` |
| `fix/nexora-predeploy-block-1b` | Ídem; su único archivo propio, `nexora_guided_segregation.js`, no está registrado en `hooks.py` y duplica en cliente —de forma más débil— la segregación de funciones que `reference_rules.validate_segregation` ya impone en servidor exigiendo tres usuarios distintos |
| `fix/remediation-87b55af6-c00e30` | Árbol idéntico a `fix/remediation-87b55af6-17e808`, que se conserva |
| `coderabbitai/chat/629d637` | Árbol idéntico a `Clopezgg-patch-2`, que se conserva |

### Qué sigue pendiente

- **Ejecución en runtime real.** Este bloque se validó con las suites que no
  requieren Frappe, más una réplica de `Page.load_assets()`. La verificación con
  `bench --site … install-app` y con el recorrido de navegador
  (`scripts/nexora_browser_smoke.mjs`) corresponde a los jobs `install-rollback` y
  `browser` de `nexora-app.yml`, que necesitan MariaDB y Docker.
- **Sentry.** `nexora_app/nexora/sentry.py` y `public/js/nexora_sentry.js` existen en
  las ramas de los PRs cerrados y son trabajo aprovechable. Requieren un PR propio y
  pequeño, rebasado sobre `main` actual.
- **Reintegrar el ajuste de readiness** de `scripts/nexora_browser_smoke.mjs` que
  intentaban #41 y #42, también como cambio aislado.
- **`scripts/validate_construcontrol_architecture.py`** sigue fallando por contratos
  de coexistencia ausentes en la arquitectura heredada. Es un defecto previo a este
  bloque y ningún workflow lo ejecuta.

### Riesgos y decisiones requeridas

- **Eliminación de ramas bloqueada por el entorno.** El proxy git de esta sesión
  ignora los refspec de borrado (`git push origin --delete` responde «Everything
  up-to-date» tras desconectar el sideband) y el servidor MCP de GitHub no expone una
  herramienta de borrado de ramas. Las cinco ramas de la tabla anterior quedan
  verificadas y listas para que el propietario las elimine.
- **Revisión automática con ChatGPT.** El `cr.yml` de #36 y #37 engancha
  `anc95/ChatGPT-CodeReview@main` —referenciada por rama móvil, no por SHA— con
  `pull-requests: write` y `secrets.OPENAI_API_KEY`, y le entrega el diff de cada PR.
  Es una decisión de producto y seguridad del propietario.
- **`.mergify.yml` sigue activo** en el repositorio y puede fusionar PRs
  automáticamente. No se modificó: cambiar la política de fusión excede este bloque.

## Bloque 1.1 — cierre formal de fase 1

Este bloque cerró la fase documental e identidad sin tocar backend, frontend,
DocTypes, permisos, servicios ni lógica de negocio.

- Se alineó la superficie documental y operativa visible a **NEXORA**.
- Se conservó trazabilidad del legado donde sigue siendo útil o técnicamente necesario.
- Se evitó cualquier cambio en comportamiento funcional.

Commit del bloque 1 publicado en `main`: `18f7219a3ae4d566c502090b2543c84e11d89768`.

### Estado de NXR-CONS-001

- **Estado:** NO DEMOSTRADO como requisito trazable independiente en el árbol revisado.
- **Interpretación operativa:** el cierre de fase 1 dejó la identidad documental
  alineada, pero no aportó evidencia funcional nueva para elevarlo a validado.

## Base certificada anterior

- Fundación y consola: PR `#11` y `#26`; fusión `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.

## Veredicto

- **Bloque 1:** cerrado.
- **Bloque 1.1:** cerrado.
- **Bloque 2:** cerrado en árbol y validado con las suites que no requieren runtime
  Frappe. Pendiente la certificación en runtime real descrita arriba.
