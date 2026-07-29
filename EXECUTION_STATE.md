# NEXORA — Estado de ejecución

- Fecha: 2026-07-29
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama vigente: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos productivos modificados: **NO**
- Migración de registros históricos: **NO**

## Historial certificado anterior

- Fundación y consola: PR `#11` y `#26`; fusión `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.
- Estos bloques permanecen **IMPLEMENTADOS Y VALIDADOS** según sus ejecuciones registradas.

## Rediseño UX-A…UX-H

### UX-A — Investigación y trazabilidad

Estado: **IMPLEMENTADO Y VALIDADO** únicamente para investigación y trazabilidad.

- Mapa inicial: `b3bdec5f93604a14556651ee75572160ea87674b`.
- Cierre: `7bc8dc459b8e396c3b7f169380d3aeb6cfb3f510`.
- Mapa integrado: `870797dd3a8b282fc81776e9d6394b307ebf674d`.

### UX-B — Vocabulario y sistema de diseño

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

- Vocabulario central: `79f5c8f49fbde501e56106c354badada471adb8a`.
- Buscador, proveedores y comprobantes: `21a565b06f291e17bac069589d5e39e02880ebbf`, `e7250398b5ee4d08a548ccd37fc96d3cc8dcc5cc`, `74434324ab37df911f60f7acb6b842cd09387ec1`.
- Errores y accesibilidad: `6d83c2efa0bb93408ee6ea7ed18ad7aafba150d9`, `b35c6054cb9ddef4184d83cf008e0f499ce3a108`, `faefa91a76af24f9ab539037546c4f1e38520713`.

### UX-C — Contexto global y dashboard

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- proyecto y período persistentes por usuario;
- acceso al proyecto validado en servidor;
- usuario y rol visibles;
- advertencia por datos sin guardar;
- dashboard conectado al snapshot canónico con disponible, comprometido, pendiente, alertas y actividad;
- responsive y ocultamiento por permisos.

Publicación: `272c4f7a473b65ef6f8e4a771835ef51fc539158`, `93524e35313f8070806e06a1849ab68131486de8`, `e658ab269e91afd41e9baaab90b6b8a2f6a1e3c4`, `6180e42d1ef5d90e9cd41007c317be345e1ea8f8`, `4a709624dfdcbbcbeed7d8cf81a8e6b9e1854b16`, cierre `58308bbf8fb76485df7145f1b370a97b24bf0811`.

### UX-D — Motor único de ingreso

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

- Todos los accesos convergen en `101`.
- Contexto y período propagados; fecha fuera de período bloqueada.
- Vista previa, `preview_hash`, idempotencia, cuenta, moneda y auditoría preservadas.
- Publicación: `1c130627e201981e0e3d0f0fd4182eed031b9c66`, `7fa76cfd5b320e15974124233efba2127d54e2a0`; cierre `f2901a8481afb1f246b5afb81de4bcc08f99d3c0`.

### UX-E — Motor único de gasto y pago

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- accesos globales, dashboard y Finanzas convergen en `102`;
- eliminado el diálogo rápido con ruta financiera diferente;
- proyecto, período, beneficiario, clasificación, centro de costo, medio, referencia y comprobante conectados al formulario canónico;
- distribución multifuente y saldos consultados en servidor;
- vista previa mediante `preview_operational_movement` y ejecución mediante `execute_operational_movement`;
- `preview_hash`, idempotencia, permisos, auditoría, rollback y prevención de doble envío preservados.

Pruebas: sintaxis JS, compilación del contrato, equivalencia de accesos, multifuente, período, doble envío, vista previa e idempotencia: **APROBADAS**.

Publicación: `a33bd1ef50db889f6620817200dbbbbf309ce9cc`, `eece644ce7afdf7bdf3b4f7855d265d72bd8f3d4`; cierre `5298ba1d4d5d13d0ad94893c06c132f91c13a37d`.

### UX-F — Correcciones desde el documento original

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- acciones contextuales: Corregir fecha o datos, Corregir importe, Sustituir documento, Anular, Revertir, Ver historial y Descargar;
- motivo mínimo de 10 caracteres y comprobante obligatorio para sustitución;
- original no se elimina ni sobrescribe;
- movimientos `303/304/501`, `reference_name`, vista previa, `preview_hash`, idempotencia, permisos, auditoría y rollback preservados.

Pruebas de acciones, motivo, comprobante, conservación del original y error transaccional: **APROBADAS**.

Publicación: `7c04d0eba563cde52f939411f33342100c12c4c7`, `67de852d460ecf8de26d4846183fb0928c4c7fff`; cierre `394f5ec562704f2763f47d7bc850e1eb50061bd1`.

### UX-G — Experiencia móvil

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- tablas de escritorio preservadas;
- tarjetas móviles para dashboard, Libro Central, línea operativa y buscador;
- contenido regenerado cuando cambian las filas, sin bucle del observador ni tarjetas obsoletas;
- enlaces y acciones originales preservados;
- 44 px, `safe-area-inset-*`, pie adhesivo, formularios a una columna, texto ampliado, `aria-busy` y movimiento reducido;
- PWA y service worker existentes preservados.

Pruebas responsive, accesibilidad, firma dinámica de filas y conservación de escritorio: **APROBADAS**.

Publicación: `5bc8697f6d8a5ee70a8483b3af2b247290ae7f33`, `1ac6dca6ddd722e55a989eeff15568fa6fa3b62b`, `97eed2a593aa97d43bd54ad53f9215166d7aa6c6`, corrección dinámica `0c4a0fc8412e69d46331c80fb824a4102f2e4157`, regresión `bc0e78c245301907ab4944b78a272096fcbdf6af`; cierre inicial `ffe2662a9a5ed6dd89304e6892970a97fb58d0ee`.

### UX-H — Búsqueda, coherencia y regresión

Estado: **IMPLEMENTADO, PUBLICADO Y VALIDADO TÉCNICAMENTE; VALIDACIÓN VISUAL MANUAL PENDIENTE**.

Capacidad:

- buscador canónico ampliado con proyectos, cuentas guardadas, movimientos y fondos;
- búsqueda por documentos, nombres, cuentas, referencias, remitentes, beneficiarios e instituciones;
- deduplicación, permiso de DocType y acceso al proyecto en servidor;
- cuentas enmascaradas antes de responder;
- vista consolidada con datos principales, comprobante, relaciones y efectos financieros;
- detalle con segunda validación de permiso y proyecto;
- equivalencia visible/canónica para Movimiento, Fondo y Comprobante;
- normalización visible de términos técnicos restantes en superficies NEXORA;
- regresión integrada de UX-D…UX-G.

Pruebas de sintaxis, compilación, permisos, proyecto, enmascaramiento, filtros, detalle, efectos, vocabulario y secretos: **APROBADAS**.

Publicación: `107ca54fa6cbe5ac7e11c74a0111c98bef4f3462`, `e213b4ba57604b44c0d73a5fdac730442298a7b8`, `b232ceb20eddfec00c92326e3706b067d0e20d71`, `f710a675fa0a8e3a086e988f35567a0b9cbf91d1`, `2ab6d88f5b9b8ee9635a63fa22dc2a3d68204ab4`, `60054721ae9b574c3fb17170b59847305032400f`, normalización final `0c4a0fc8412e69d46331c80fb824a4102f2e4157`, regresión final `bc0e78c245301907ab4944b78a272096fcbdf6af`.

## Certificación final disponible

Estado UX-A…UX-H: **IMPLEMENTADO Y PUBLICADO; VALIDADO TÉCNICAMENTE EN LAS COMPROBACIONES DISPONIBLES; VALIDACIÓN VISUAL MANUAL E INSTALACIÓN LIMPIA PENDIENTES**.

Aprobado:

- continuidad desde `f2901a8481afb1f246b5afb81de4bcc08f99d3c0`;
- compilación Python de archivos modificados;
- sintaxis JavaScript de buscador y coordinador;
- contratos de motores `101/102`, contexto, período, doble envío, correcciones, móvil, búsqueda y vocabulario;
- regresión estática de permisos, servicios canónicos, `preview_hash`, idempotencia, auditoría y rollback;
- escaneo de secretos: sin hallazgos;
- verificación de commits y blobs remotos.

No ejecutado y no declarado aprobado:

- pre-commit/ruff: herramientas no instaladas en el contenedor;
- Semgrep: herramienta no instalada;
- instalación/migración limpia Frappe/MariaDB;
- Playwright escritorio, iPhone WebKit y PWA;
- validación visual manual en staging;
- checks de GitHub Actions por `push`, no expuestos por el conector.

## Siguiente acción

Ejecutar la certificación dependiente de entorno sobre el HEAD final: instalación y migración limpia, pre-commit, Semgrep, navegador automatizado de escritorio/iPhone/PWA y validación visual manual. Corregir cualquier fallo real antes de autorizar despliegue productivo.
