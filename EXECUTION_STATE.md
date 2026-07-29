# NEXORA — Estado de ejecución

- Fecha: 2026-07-29
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama vigente: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Historial certificado anterior

- Fundación y consola: PR `#11`, PR `#26`; fusión funcional `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Corrección de cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Normalización de fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.
- Esos bloques permanecen **IMPLEMENTADOS Y VALIDADOS** según sus ejecuciones registradas.

## Rediseño integral de experiencia

### UX-A — Investigación y trazabilidad

Estado: **IMPLEMENTADO Y VALIDADO** únicamente para investigación y trazabilidad.

- Mapa inicial: `b3bdec5f93604a14556651ee75572160ea87674b`.
- Cierre: `7bc8dc459b8e396c3b7f169380d3aeb6cfb3f510`.
- Mapa integrado: `870797dd3a8b282fc81776e9d6394b307ebf674d`.

### UX-B — Vocabulario y sistema de diseño

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

- Vocabulario central: `79f5c8f49fbde501e56106c354badada471adb8a`.
- Buscador: `21a565b06f291e17bac069589d5e39e02880ebbf`.
- Proveedores: `e7250398b5ee4d08a548ccd37fc96d3cc8dcc5cc`.
- Comprobantes: `74434324ab37df911f60f7acb6b842cd09387ec1`.
- Errores accionables: `6d83c2efa0bb93408ee6ea7ed18ad7aafba150d9`.
- Accesibilidad: `b35c6054cb9ddef4184d83cf008e0f499ce3a108` y `faefa91a76af24f9ab539037546c4f1e38520713`.

### UX-C — Contexto global y dashboard

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- proyecto y período activos persistentes por usuario;
- acceso al proyecto validado en servidor;
- usuario y rol visibles;
- advertencia ante datos sin guardar;
- dashboard conectado al snapshot financiero canónico;
- saldo disponible, comprometido, pendiente de pagar, alertas y actividad;
- comportamiento responsive y ocultamiento por permisos.

Publicación:

- servidor: `272c4f7a473b65ef6f8e4a771835ef51fc539158`;
- contexto global: `93524e35313f8070806e06a1849ab68131486de8`;
- dashboard: `e658ab269e91afd41e9baaab90b6b8a2f6a1e3c4`;
- responsive: `6180e42d1ef5d90e9cd41007c317be345e1ea8f8`;
- pruebas: `4a709624dfdcbbcbeed7d8cf81a8e6b9e1854b16`;
- cierre: `58308bbf8fb76485df7145f1b370a97b24bf0811`.

### UX-D — Motor único de ingreso

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- todos los accesos de ingreso convergen en el movimiento `101`;
- proyecto y período activos propagados;
- alta rápida heredada sustituida;
- modo guiado con acceso consciente a operaciones avanzadas;
- fecha fuera del período bloqueada;
- vista previa, `preview_hash`, idempotencia, cuenta, moneda y auditoría preservadas.

Publicación:

- motor visible: `1c130627e201981e0e3d0f0fd4182eed031b9c66`;
- regresión: `7fa76cfd5b320e15974124233efba2127d54e2a0`;
- cierre: `f2901a8481afb1f246b5afb81de4bcc08f99d3c0`.

### UX-E — Motor único de gasto y pago

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- accesos globales, dashboard y Finanzas convergen en el movimiento `102` de `nexora-operations`;
- se retiró el diálogo rápido que ejecutaba una ruta financiera diferente;
- proyecto, período y límites de fecha activos se propagan al motor;
- beneficiario, clasificación económica, centro de costo, medio de pago, referencia y comprobante permanecen en el formulario canónico;
- la distribución multifuente permanece conectada a `list_source_balances` y al backend central;
- la vista previa se calcula mediante `preview_operational_movement` y muestra saldos antes/después por fondo;
- la ejecución usa `execute_operational_movement`, `preview_hash`, clave de idempotencia, permisos y rollback transaccional del servidor;
- doble envío bloqueado en la interfaz sin sustituir la idempotencia del servidor;
- mensajes de período y de resultado expresados en lenguaje de tarea.

Pruebas ejecutadas:

- `node --check` del coordinador compartido: aprobado;
- compilación del contrato Python: aprobada;
- contrato de equivalencia entre accesos rápidos y motor `102`: aprobado;
- contrato de distribución multifuente y vista previa servidor: aprobado;
- contrato de `preview_hash` e idempotencia: aprobado;
- prueba negativa de fecha fuera del período: aprobada;
- prueba negativa de doble envío: aprobada;
- ausencia de llamadas directas a `preview_central_operation` y `execute_central_operation` desde el acceso rápido: aprobada.

Publicación:

- `a33bd1ef50db889f6620817200dbbbbf309ce9cc` — coordinador único de ingreso/gasto;
- `eece644ce7afdf7bdf3b4f7855d265d72bd8f3d4` — regresión del motor único de gasto.

Seguridad y efectos:

- no se modificaron modelos, saldos, permisos, numeración ni datos reales;
- el servidor conserva validaciones de proyecto, beneficiario, categoría, fondos, saldo, distribución, evidencia, permisos, auditoría y rollback;
- no se modificó producción ni infraestructura.

### UX-F — Correcciones desde el documento original

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- la vista de `NXR Operation` muestra acciones contextuales según estado y rol;
- **Corregir fecha o datos** y **Corregir importe** reutilizan la corrección guiada existente cuando el ingreso lo permite;
- **Sustituir documento**, **Anular operación** y **Revertir operación** reutilizan los movimientos `304`, `303` y `501`;
- **Ver historial** abre el Libro Central filtrado por proyecto;
- **Descargar** usa la vista de impresión del documento real;
- cada acción exige motivo de al menos 10 caracteres;
- la sustitución exige comprobante;
- la interfaz explica que el original no se elimina ni sobrescribe;
- vista previa y ejecución pasan por `preview_operational_movement` y `execute_operational_movement`;
- `reference_name`, `preview_hash`, idempotencia, permisos, auditoría y rollback permanecen en servidor;
- doble envío bloqueado durante la ejecución del diálogo.

Pruebas ejecutadas:

- `node --check` del coordinador ampliado: aprobado;
- compilación del contrato Python: aprobada;
- contrato de siete acciones documentales: aprobado;
- motivo obligatorio y comprobante de sustitución: aprobados;
- contrato de conservación del original: aprobado;
- contrato de referencia al documento, vista previa, ejecución, `preview_hash` e idempotencia: aprobado;
- contrato de error transaccional sin alteración del original: aprobado.

Publicación:

- `7c04d0eba563cde52f939411f33342100c12c4c7` — acciones auditadas desde la operación original;
- `67de852d460ecf8de26d4846183fb0928c4c7fff` — regresión de correcciones contextuales.

Seguridad y efectos:

- no se habilitó edición directa de documentos contabilizados;
- los botones visibles no sustituyen permisos de servidor;
- no se modificaron datos reales, infraestructura ni producción.

### UX-G — Experiencia móvil

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- las tablas de escritorio se conservan;
- dashboard, Libro Central, línea operativa y buscador generan tarjetas móviles a partir de sus encabezados reales;
- las tarjetas muestran documento, fecha, tipo, contraparte, importe, moneda, estado y demás columnas disponibles;
- enlaces y acciones del contenido original se conservan dentro de las tarjetas;
- controles y enlaces táctiles usan mínimo 44 px;
- se aplican `safe-area-inset-*` para iPhone;
- acciones operativas permanecen visibles mediante pie adhesivo en móvil;
- formularios operativos pasan a una columna;
- importes y textos largos usan ajuste seguro;
- `aria-busy`, foco visible, movimiento reducido y bloqueo de doble envío se preservan;
- PWA y service worker existentes no fueron sustituidos.

Pruebas ejecutadas:

- `node --check` del generador de tarjetas: aprobado;
- compilación del contrato Python: aprobada;
- contrato de tarjetas para dashboard, operaciones y buscador: aprobado;
- contrato de preservación de tablas en escritorio: aprobado;
- contrato de 44 px, áreas seguras, `touch-action`, foco, movimiento reducido y `aria-busy`: aprobado;
- contrato de formularios a una columna y acción principal adhesiva: aprobado.

Publicación:

- `5bc8697f6d8a5ee70a8483b3af2b247290ae7f33` — tarjetas móviles generadas desde tablas reales;
- `1ac6dca6ddd722e55a989eeff15568fa6fa3b62b` — estilos iPhone/PWA y formularios responsive;
- `97eed2a593aa97d43bd54ad53f9215166d7aa6c6` — regresión móvil y accesibilidad.

Seguridad y efectos:

- no se ocultaron ni eliminaron tablas de escritorio;
- no se duplicaron datos financieros ni cálculos;
- no se modificaron datos reales, infraestructura ni producción.

## Pendiente de entorno común

- instalación y migración limpia del HEAD final;
- pre-commit completo y Semgrep con dependencias descargadas;
- navegador real de escritorio, iPhone WebKit y PWA;
- checks de GitHub Actions por `push`, no expuestos por la herramienta disponible.

## Siguiente acción

Ejecutar `UX-H — Búsqueda, coherencia integral y regresión`: ampliar la búsqueda única con permisos y vista consolidada, normalizar estados, moneda, fechas, acciones y mensajes en superficies restantes, conectar acceso al documento y ejecutar regresión UX-A…UX-G antes de la certificación final.
