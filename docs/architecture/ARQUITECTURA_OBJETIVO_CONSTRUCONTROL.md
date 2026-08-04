# Arquitectura objetivo NEXORA

## Principio rector

NEXORA es el producto visible. ERPNext/Frappe es el motor técnico interno.

El usuario debe reconocer una única plataforma en escritorio, móvil y PWA. Los servicios nativos de ERPNext/Frappe se reutilizan cuando aportan documentos, permisos, colas, impresión, archivos, auditoría o persistencia.

## Capas

### Presentación

- Shell único NEXORA.
- Navegación escritorio y móvil.
- PWA.
- Identidad y contexto de proyecto.

### Aplicación

- Fondos y operaciones.
- Tesorería.
- Gastos y pagos.
- Contratos.
- Planificación y avance.
- Materiales e inventario.
- Compras.
- Reportes.
- Usuarios y seguridad.
- Integraciones.

### Motor técnico

ERPNext/Frappe conserva:

- DocTypes.
- Roles y permisos.
- Archivos.
- Colas.
- Impresión.
- Persistencia.
- Auditoría técnica.

## Evolución

Los nombres técnicos heredados de ConstruControl pueden mantenerse temporalmente cuando sean dependencias internas. Su sustitución requiere validación de rutas, activos y compatibilidad.

## Contratos de coexistencia

NEXORA (`nexora_app/`) y ConstruControl (`erpnext/construcontrol/`, injertado como 22.º
módulo de ERPNext vía `erpnext/hooks.py`) se instalan en el mismo sitio Frappe durante
el período de convivencia. Estos cuatro contratos fijan los límites que impiden que esa
convivencia degrade al usuario o duplique una fuente de verdad, y son la base que
`scripts/validate_construcontrol_architecture.py` exige por escrito.

### Contrato de navegación

- El shell de navegación visible para el usuario ordinario es exclusivamente el de
  NEXORA: workspace `NEXORA`, páginas `nexora-*` y la barra `nxr-product-nav` de
  `nexora.js`. El workspace y las páginas de ConstruControl (`cc-*`, módulo
  `ConstruControl` dentro de `erpnext`) no se enlazan desde ahí ni se ofrecen como
  ruta de trabajo diaria.
- Ninguna ruta, `Page name` o `Workspace` de NEXORA colisiona con uno de
  ConstruControl: los espacios de nombres están separados por prefijo (`nexora-*`
  frente a `cc-*`/módulo `ConstruControl`) y `nexora_app` no registra ni modifica
  DocTypes `Page`/`Workspace` fuera de los suyos.
- El acceso a pantallas de ConstruControl, si todavía es necesario para consultar
  historial durante la transición, queda restringido a roles administrativos y no se
  promueve desde el flujo normal de NEXORA (dashboard, accesos directos, PWA).
- `nexora_app/nexora/tests/test_app_contract.py::test_new_app_has_no_legacy_import_or_visible_brand`
  hace cumplible la mitad técnica de este contrato: prohíbe que el código de NEXORA
  importe `erpnext.construcontrol` y prohíbe que el workspace de NEXORA mencione
  "ConstruControl" o "ERPNext".

### Contrato financiero

- Existe un único ledger canónico de fondos y operaciones: el que describe
  `docs/nexora/ARQUITECTURA.md` (`NXR Operation Effect` para saldos disponibles y
  reservados, `NXR Document Sequence` para numeración, `GL Entry`/`Stock Ledger Entry`
  nativos de ERPNext cuando corresponde). `NO_SEGUNDO_LEDGER_CANONICO: true` es
  vinculante: NEXORA no crea un segundo libro de fondos y no reconcilia saldos contra
  los DocTypes financieros heredados de ConstruControl (`ConstruControl Fund Entry`,
  `ConstruControl Expense Record`, etc.).
- Los documentos financieros heredados de ConstruControl que ya existan en el sitio se
  tratan como historial de solo lectura una vez NEXORA queda activo: no reciben nuevas
  escrituras operativas y no participan en el cálculo de `available`/`reserved`/`cost`
  de NEXORA.
- Si una operación necesita datos que solo existen en el histórico de ConstruControl,
  se migra explícitamente al modelo NEXORA (con el patrón `Legacy Record` descrito en
  `docs/migration/MAPA_CORRESPONDENCIA.md`, evidencia SHA-256 y clave de idempotencia
  propia) en lugar de leer o escribir directamente los DocTypes heredados desde el
  código de NEXORA.
- `NO_MIGRACION_HISTORICA: true` aplica también aquí: mientras ese contrato siga
  vigente, no se copian saldos ni movimientos históricos de ConstruControl al ledger
  de NEXORA de forma masiva; solo se referencian bajo demanda y de forma trazable.

### Contrato de PWA

- NEXORA es dueña de la identidad de instalación: `public/manifest.json` con
  `start_url: /app/nexora-dashboard`, `nexora-service-worker.js` como único
  service worker registrado por `nexora.js` en rutas `/app/nexora-*` y `/app/nxr-*`, e
  iconos propios (`nexora-192.png`, `nexora-512.png`).
- Los activos móviles heredados de ConstruControl que `erpnext/hooks.py` todavía
  registra (por ejemplo `construcontrol_mobile.js`, `construcontrol_canonical.css`) no
  declaran su propio `manifest.json` ni su propio `start_url`: no compiten por el
  mismo `beforeinstallprompt` ni ofrecen una segunda app instalable en el mismo
  dispositivo.
- El service worker de NEXORA solo cachea rutas bajo `/assets/nexora/` (ver
  `nexora-service-worker.js::isNexoraShell`) y excluye explícitamente `/api/`,
  `/private/`, `/files/` y `/app/`: no intercepta ni cachea tráfico de ConstruControl,
  de modo que retirar sus activos móviles más adelante no depende de invalidar la
  caché de NEXORA.
- Mientras ambos coexistan, ConstruControl no debe adquirir un `manifest.json` o
  `service worker` propios: eso crearía dos identidades de PWA instalables para el
  mismo usuario, exactamente lo que el principio rector de esta arquitectura prohíbe.

### Estrategia de evolución sin dañar producción

- La convivencia es temporal y unidireccional: NEXORA absorbe funcionalidad de
  ConstruControl pantalla por pantalla y ledger por ledger; ConstruControl no vuelve a
  ganar superficie una vez migrada.
- Cada absorción sigue el ciclo ya validado por el cutover de NEXORA
  (`docs/nexora/ARQUITECTURA.md::Cutover y rollback`): se prueba primero fuera de
  producción, sin copiar datos históricos, y el sistema anterior permanece intacto
  como camino de rollback hasta que la validación en el sitio real sea explícita.
- No se elimina un DocType, página o servicio de ConstruControl solo porque NEXORA ya
  ofrece un equivalente: se retira únicamente cuando existe evidencia de que ningún
  flujo de producción activo depende de él y de que su historial quedó preservado
  (migrado con `Legacy Record` o dejado como solo lectura, según el contrato
  financiero de esta sección).
- Toda migración de datos reales exige respaldo verificable y plan de reversión antes
  de ejecutarse, conforme a `README.md::Seguridad y operación` y a las reglas
  operativas de `AGENTS.md`; ninguna automatización de este repositorio puede saltarse
  ese requisito.
- El estado de la migración vive en `docs/migration/` (`MAPA_CORRESPONDENCIA.md`,
  `RIESGOS_Y_BLOQUEOS.md`, `VALIDACION_RESULTADOS.md`); una fase de evolución no se
  declara cerrada aquí si esos documentos todavía listan bloqueos activos para ella.

## Reglas

- No modificar producción sin autorización.
- No eliminar datos históricos.
- Validar permisos en backend.
- Mantener migraciones trazables.
