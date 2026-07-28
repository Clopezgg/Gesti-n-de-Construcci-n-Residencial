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

### Arranque no bloqueante y fecha textual

- PR de despliegue: `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- PR de fecha textual: `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Runs finales del PR `#30`: NEXORA app `30396561503`, invariantes `30396561479`, linters `30396564004`, Patch `30396561828`, gobierno `30396561459`, documentación `30396561415`, validación segura `30396562192`.

## Rediseño integral de experiencia

Los requisitos funcionales vigentes son `NXR-UX-001…015`. La ejecución continúa directamente en `main`; no se creó otro repositorio, rama, Pull Request ni aplicación alternativa.

## UX-A — Verificación y mapa de impacto

Estado: **IMPLEMENTADO Y VALIDADO** únicamente para investigación y trazabilidad; no representa una funcionalidad de usuario terminada.

- HEAD base: `a43214659dcd9f8039d1d93c9a5f4f2d8717501a`.
- Mapa inicial: `b3bdec5f93604a14556651ee75572160ea87674b`.
- Cierre UX-A: `7bc8dc459b8e396c3b7f169380d3aeb6cfb3f510`.
- Mapa integrado en este archivo: `870797dd3a8b282fc81776e9d6394b307ebf674d`.
- Duplicaciones confirmadas: tres entradas visibles para ingreso, tres para gasto, proyecto/UUID/mensajes repetidos y vista previa inconsistente.

## UX-B — Vocabulario y sistema de diseño

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

### Implementación

- Diccionario visible y feedback compartido: `public/js/nexora_report_actions.js`.
- Buscador, proveedores y comprobantes con lenguaje humano en español.
- Foco visible, movimiento reducido, estado ocupado y objetivos táctiles de 44 px.
- Estados canónicos del servidor preservados; solo cambió su presentación.

### SHA principales

- `79f5c8f49fbde501e56106c354badada471adb8a` — vocabulario central.
- `21a565b06f291e17bac069589d5e39e02880ebbf` — buscador.
- `e7250398b5ee4d08a548ccd37fc96d3cc8dcc5cc` — proveedores.
- `74434324ab37df911f60f7acb6b842cd09387ec1` — comprobantes.
- `6d83c2efa0bb93408ee6ea7ed18ad7aafba150d9` — fallback de errores.
- `b35c6054cb9ddef4184d83cf008e0f499ce3a108` — accesibilidad.
- `faefa91a76af24f9ab539037546c4f1e38520713` — regresión de accesibilidad.
- `36647655c864e4e854e735044faaee11afabe018` — estado de reanudación verificado.

### Certificación técnica ejecutada

- Comandos oficiales identificados en `nexora-app.yml`, `linters.yml` y `.pre-commit-config.yaml`.
- `node --check`, compilación Python, pruebas contractuales, ejecución con Frappe simulado y contrato CSS: aprobados.
- La herramienta GitHub disponible no expone runs activados por `push`; el estado combinado no entregó checks.
- El contenedor no resolvió GitHub ni pudo descargar ERPNext, Playwright o reglas Semgrep. Instalación limpia, Semgrep y navegador real no se declaran ejecutados.

## UX-C — Contexto global persistente y dashboard orientado a decisiones

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

### Capacidad implementada

- proyecto activo persistente por usuario;
- período activo mensual persistente, validado como `AAAA-MM` y convertido en límites de mes en servidor;
- validación de acceso al proyecto mediante `require_project_access`;
- usuario y rol visibles en el shell y dashboard;
- advertencia antes de cambiar proyecto o período cuando existen datos sin guardar;
- contexto propagado a la navegación y al dashboard;
- dashboard conectado al snapshot ejecutivo canónico, sin cálculos financieros críticos paralelos;
- saldo disponible, comprometido, pendiente de pagar, alertas, actividad y tareas principales;
- ocultamiento de métricas cuando el perfil no puede ver detalle financiero;
- comportamiento responsive del contexto global.

### Publicación

- `272c4f7a473b65ef6f8e4a771835ef51fc539158` — persistencia y permisos del contexto en servidor.
- `93524e35313f8070806e06a1849ab68131486de8` — controlador global de proyecto, período y datos sin guardar.
- `e658ab269e91afd41e9baaab90b6b8a2f6a1e3c4` — dashboard conectado al contexto y snapshot.
- `6180e42d1ef5d90e9cd41007c317be345e1ea8f8` — contexto responsive y accesible.
- `4a709624dfdcbbcbeed7d8cf81a8e6b9e1854b16` — pruebas positivas y negativas.

### Pruebas aprobadas

- compilación de `boot.py` y prueba Python;
- sintaxis de los dos JavaScript modificados;
- 12 pruebas unitarias/contractuales;
- período válido y límites correctos para julio/agosto;
- formato de período inválido rechazado sin persistencia;
- proyecto persistido únicamente después de validar permiso;
- usuario restringido no puede limpiar el proyecto obligatorio;
- regresión del aviso de correo genérico preservada;
- contrato del dashboard para disponible, comprometido, pendiente y filtros de período;
- contrato responsive, foco, movimiento reducido, `aria-busy` y objetivo táctil;
- escaneo local de patrones de secretos: sin hallazgos.

### Seguridad y efectos

- no se modificaron modelos financieros, saldos, operaciones, permisos base ni datos reales;
- no se añadieron fuentes de datos paralelas;
- no se modificó infraestructura ni producción;
- no se ejecutaron migraciones destructivas.

## Pendiente de entorno

- instalación/migración limpia de este HEAD;
- pre-commit completo y Semgrep con dependencias descargadas;
- navegador real de escritorio, iPhone WebKit y PWA;
- checks de GitHub Actions activados por `push`, no visibles mediante la herramienta disponible.

## Siguiente acción

Ejecutar `UX-D — Motor único de ingreso`: hacer que todos los accesos de ingreso utilicen la operación `101` y el mismo formulario visible, reutilizar el backend canónico, aplicar proyecto/período activos, conservar vista previa, idempotencia, auditoría y permisos, retirar o redirigir las altas visibles duplicadas y publicar pruebas positivas, negativas y de regresión antes de iniciar UX-E.
