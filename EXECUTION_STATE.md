# NEXORA — Estado de ejecución

- Fecha: 2026-07-28
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama vigente: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Historial certificado

### Fundación, consola operativa y cuentas

- PR original de fundación: `#11`, cerrado y fusionado.
- PR de consola operativa: `#26`.
- SHA funcional: `b23d9b902191d5693e0841b39ba550ce7cb82d49`.
- HEAD certificado: `c0b9f9a06f8f9e3d4fc9e9b943abe5615b9c0755`.
- Fusión: `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- PR correctivo de cuentas e interfaz: `#27`.
- SHA funcional correctivo: `d4b95dd2b9d86c67215a196c8f791a02f5d202ef`.
- HEAD correctivo certificado: `862e676089e4efc67e6e97dbcef36545aee43fbb`.
- Fusión correctiva: `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Estado: **IMPLEMENTADO Y VALIDADO**.

### Corrección documental guiada

- Requisitos: `NXR-COR-20260728-01…06`, `NXR-UX-20260728-03`.
- PR: `#28`.
- SHA funcional: `9d5002d651a4b0d1afd4f80d7fbd550d812bacf0`.
- HEAD certificado: `6f42bc77f9e755ffdf18585c638f49642d378409`.
- Fusión: `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Conserva original, auditoría, idempotencia, permisos, períodos y bloqueo transaccional.

### Arranque no bloqueante en Coolify

- Requisitos: `NXR-DEP-20260728-01…04`.
- PR: `#29`.
- SHA funcional: `6237735c894dcf5ed4dc7449ab1c4e7192a56412`.
- HEAD certificado: `b611bc72ce59e070ba8c8c4ffaa7d7a5e807d037`.
- Fusión: `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Mantiene healthchecks, migración, respaldo y espera real de servicios.

### Normalización de fecha textual

- Requisitos: `NXR-DATE-20260728-01…03`.
- PR: `#30`.
- Base: `ee5282c75754032b18c721e4c0cfb1a60ecabb4c`.
- SHA funcional: `9ea31ef72c9d74c72820cac86143e3624a68e537`.
- HEAD certificado: `d0702d6402f56c91af73b4365d9788f6f4e90269`.
- Fusión: `0d8884c5419fca439e4808008fb1e59fbf92c647`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Runs finales aprobados: NEXORA app `30396561503`, invariantes `30396561479`, linters `30396564004`, Patch `30396561828`, gobierno `30396561459`, documentación `30396561415`, validación segura `30396562192`.

## Rediseño integral de experiencia

La orden maestra vigente define los requisitos `NXR-UX-001…015` y los bloques `UX-A…UX-H`. No se creó otro repositorio, rama ni Pull Request porque la rama histórica `nexora-reconstruccion` ya no estaba activa y el PR `#11` estaba cerrado y fusionado.

## UX-A — Verificación y mapa de impacto

Estado: **IMPLEMENTADO Y VALIDADO** para el alcance de verificación y trazabilidad. No clasifica como terminados los requisitos funcionales.

### Fuente remota

- HEAD base: `a43214659dcd9f8039d1d93c9a5f4f2d8717501a`.
- Rama: `main`.
- PR `#11`: cerrado y fusionado.
- Commit inicial del mapa: `b3bdec5f93604a14556651ee75572160ea87674b`.
- Cierre UX-A: `7bc8dc459b8e396c3b7f169380d3aeb6cfb3f510`.
- Retiro de ruta adicional para conservar inventario: `bb82ef7b38966a2c23eb25a422a22cf38838e45b`.
- Mapa definitivo integrado en `EXECUTION_STATE.md`: `870797dd3a8b282fc81776e9d6394b307ebf674d`.

### Duplicaciones confirmadas

1. Tres entradas visibles para ingreso: diálogo global, alta rápida en Finanzas e ingreso `101`.
2. Tres entradas visibles para gasto: diálogo rápido, Finanzas y gasto `102`.
3. Proyecto, UUID, mensajes, estados, vocabulario y tablas repetidos.
4. Vista previa visible en unos recorridos y oculta en otros.
5. Reglas bancarias y confirmaciones implementadas más de una vez.

### Clasificación inicial NXR-UX

- `NXR-UX-003`, `NXR-UX-007`, `NXR-UX-011`: **EXISTENTE Y REUTILIZABLE**, con alcance incompleto.
- `NXR-UX-004`, `NXR-UX-012`: **NO DEMOSTRADO**.
- Restantes requisitos: **EXISTENTE PERO DEFECTUOSO**.

### Archivos de impacto principales

- Shell y accesos: `public/js/nexora.js`, `nexora_quick_flows.js`, `nexora_operational_ui.js`.
- Dashboard: `page/nexora-dashboard/nexora-dashboard.js`, servicios ejecutivos.
- Motor operativo: `page/nexora-operations/nexora-operations.js`, `financial/operational_*.py`, `financial/service.py`.
- Finanzas: `page/nexora_finance/nexora_finance.js`.
- Correcciones: `public/js/nexora_operational_ui.js` y servicios `303/304/501`.
- Contratos, proveedores, comprobantes, reportes y buscador: páginas y servicios canónicos correspondientes.

## UX-B — Vocabulario y sistema de diseño

Estado actual: **EXISTENTE Y REUTILIZABLE**. Implementación publicada y pruebas locales aprobadas; pendiente de certificación integral en navegador/CI antes de usar **IMPLEMENTADO Y VALIDADO**.

### Implementación publicada

- Diccionario visible central y funciones compartidas: `nexora_app/nexora/public/js/nexora_report_actions.js`.
- Buscador con lenguaje de tareas, errores accionables y estados traducidos: `page/nexora-search/nexora-search.js`.
- Proveedores con clasificaciones, estados y acciones visibles en español: `page/nexora_suppliers/nexora_suppliers.js`.
- Comprobantes con tipos, canales, estados, revisión y mensajes en español: `page/nexora_evidence/nexora_evidence.js`.
- Accesibilidad base: foco visible, reducción de movimiento, estado ocupado y objetivos táctiles de 44 px en `public/css/nexora_dashboard_fixes.css`.
- Contrato de regresión: `nexora_app/nexora/tests/test_app_contract.py`.

### SHA publicados

- `79f5c8f49fbde501e56106c354badada471adb8a` — vocabulario central.
- `21a565b06f291e17bac069589d5e39e02880ebbf` — buscador.
- `e7250398b5ee4d08a548ccd37fc96d3cc8dcc5cc` — proveedores.
- `74434324ab37df911f60f7acb6b842cd09387ec1` — comprobantes.
- `2a157e10c3f1310ea3ee38b478614cf9a7effd78` — contrato de vocabulario.
- `6d83c2efa0bb93408ee6ea7ed18ad7aafba150d9` — fallback de errores.
- `b35c6054cb9ddef4184d83cf008e0f499ce3a108` — accesibilidad base.
- `faefa91a76af24f9ab539037546c4f1e38520713` — regresión de accesibilidad.

### Pruebas ejecutadas

- `node --check` para vocabulario central, buscador, proveedores y comprobantes: aprobado.
- `python -m py_compile` para el contrato actualizado: aprobado.
- Prueba de ejecución con entorno Frappe simulado: traducción de estado, término Fondo, opciones, confirmación con documento y fallback de error: aprobado.
- Aserciones contractuales de vocabulario compartido y adopción por tres páginas: aprobado.
- Contrato CSS: foco visible, movimiento reducido, `aria-busy` y objetivo táctil: aprobado.
- No se ejecutó una operación financiera ni se modificaron servicios, modelos, permisos, saldos o datos.

### Clasificación de requisitos después de UX-B

- `NXR-UX-005`: continúa **EXISTENTE PERO DEFECTUOSO** hasta normalizar contratos, reportes, consola, PDFs y demás superficies en UX-H.
- `NXR-UX-013`: base **EXISTENTE Y REUTILIZABLE**; la revelación progresiva de ingresos/gastos corresponde a UX-D/UX-E.
- `NXR-UX-014`: diccionario **EXISTENTE Y REUTILIZABLE**; las transiciones completas se cerrarán en UX-H.
- Accesibilidad fundamental: **EXISTENTE Y REUTILIZABLE**, pendiente de navegador real.

### Riesgos conservados

- no se renombraron estados canónicos del backend;
- no se alteraron permisos ni auditoría;
- no se añadieron rutas al inventario;
- no se cambió lógica financiera;
- no se modificó producción ni infraestructura.

## Bloqueo

La herramienta disponible no expone las ejecuciones `push` de GitHub Actions ni un navegador conectado al sitio desplegado. Por ello, UX-B no se declara completamente validado en escritorio, iPhone y PWA desde esta ejecución.

## Siguiente acción

Certificar el HEAD vigente de `main` con linters, contrato NEXORA, instalación/migración, navegador de escritorio, iPhone y PWA. Corregir cualquier fallo real. Solo después cerrar UX-B como **IMPLEMENTADO Y VALIDADO** y comenzar `UX-C — Contexto global y dashboard`.
