# NEXORA — Estado de ejecución

- Fecha de cierre técnico: 2026-07-29
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**
- Migración histórica de registros: **NO**

## Base certificada anterior

- Fundación y consola: PR `#11` y `#26`; fusión `2e87a0b0ef967efccc3ee0969c095af873a32136`.
- Cuentas e interfaz: PR `#27`; fusión `6363ee429ffb9903e2430463e0652a62b82b374e`.
- Corrección documental guiada: PR `#28`; fusión `1697bf60b34b270568a674d6544137bf9fbc509b`.
- Arranque Coolify: PR `#29`; fusión `7e223e97f88512dab825d4c8c4e0021825c43544`.
- Fecha textual: PR `#30`; fusión `0d8884c5419fca439e4808008fb1e59fbf92c647`.

## Certificación independiente del rediseño UX-A…UX-H

El HEAD informado `c3377e95b03d50b5c11a1da6d2205c81407f80f0` fue verificado como punto de partida real. La revisión no aceptó como prueba suficiente las declaraciones documentales previas y contrastó código remoto, servicios, permisos, hooks, contratos y recorridos disponibles.

### Matriz NXR-UX

| Requisito | Estado final | Evidencia principal | Limitación |
|---|---|---|---|
| NXR-UX-001 — Motor único de captura | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Accesos de ingreso/gasto convergen en `nexora-operations`; servidor usa `preview_operational_movement` y `execute_operational_movement`. | Sin recorrido E2E en instalación limpia. |
| NXR-UX-002 — Modo guiado y opciones avanzadas | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | El modo guiado oculta el código y conserva acceso explícito a operaciones avanzadas. | Sin validación visual real. |
| NXR-UX-003 — Navegación basada en tareas | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Dashboard ofrece Registrar ingreso, Registrar gasto, compras, proveedores, búsqueda y cierre. | Sin prueba de navegación renderizada. |
| NXR-UX-004 — Contexto global persistente | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Proyecto/período persistidos por usuario y validados con `require_project_access`. | Sin migración/instalación limpia del HEAD final. |
| NXR-UX-005 — Vocabulario visible unificado | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Diccionario y normalización visible en shell, buscador, proveedores y comprobantes. | Sin inspección visual integral de todas las superficies. |
| NXR-UX-006 — Simplificación de cuentas bancarias | PARCIALMENTE IMPLEMENTADO | Cuenta guardada, cuenta nueva y uso único funcionan sobre el backend canónico. | El formulario avanzado aún expone tres modos técnicos y pestañas contables. |
| NXR-UX-007 — Dashboard orientado a decisiones | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Disponible, comprometido, pendiente, alertas, actividad y tareas usan snapshot servidor. | Sin navegador ni contraste visual final. |
| NXR-UX-008 — Flujo guiado de ingreso | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Movimiento `101`, proyecto/período, cuenta, moneda, vista previa e idempotencia. | Sin ingreso E2E sobre MariaDB limpio. |
| NXR-UX-009 — Flujo guiado de gasto y pago | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Movimiento `102`, beneficiario, clasificación, multifuente, saldo y vista previa servidor. | Sin gasto/pago E2E sobre MariaDB limpio. |
| NXR-UX-010 — Explicación del efecto financiero | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Vista previa muestra fondo, saldo anterior, importe afectado y saldo posterior. | Sin comparación E2E con saldos persistidos. |
| NXR-UX-011 — Correcciones desde el original | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Acciones contextuales, original inmutable, motivo, evidencia, referencia, auditoría y segregación. | Sin ejecución E2E de `303/304/501` en sitio limpio. |
| NXR-UX-012 — Experiencia móvil con tarjetas | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Tarjetas generadas desde tablas reales, 44 px y áreas seguras iPhone. | WebKit/iPhone/PWA no ejecutados. |
| NXR-UX-013 — Revelación progresiva | PARCIALMENTE IMPLEMENTADO | El modo guiado oculta códigos y selecciona la sección pertinente. | La consola sigue mostrando una arquitectura completa de cabecera, línea y pestañas; no se certificó un recorrido progresivo completo. |
| NXR-UX-014 — Estados comprensibles | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Estados canónicos se presentan en español sin cambiar valores servidor. | Sin revisión visual de cada transición. |
| NXR-UX-015 — Búsqueda y acceso directo | IMPLEMENTADO PERO NO VALIDADO INTEGRALMENTE | Búsqueda consolidada, detalle, efectos, relaciones, enmascaramiento y permisos por documento/proyecto. | Sin E2E de todas las entidades y perfiles. |

## Defectos reales encontrados y corregidos

### NXR-CERT-001 — Correcciones imposibles por segregación

- Defecto: las acciones `303/304/501` enviaban solicitante y aprobador iguales al ejecutor, mientras el servidor exige tres usuarios distintos.
- Riesgo: la vista previa de anulación, sustitución y reversión podía fallar siempre por segregación.
- Corrección: campos obligatorios de solicitante y aprobador, validación cliente, preservación de la validación servidor e invalidación de vista previa al cambiar datos.
- Publicación: `624f88da6289316c9e54e8e2f3c72740aba34010`.
- Regresión: `1043fdd9db71629a76f9dcf84a9d1b797e2dadf5`.

### NXR-CERT-002 — Ventana de doble envío e idempotencia inestable

- Defecto: el bloqueo cliente expiraba a los 30 segundos y cada reintento generaba otra clave de idempotencia.
- Riesgo: una operación lenta podía volver a enviarse con una clave distinta.
- Corrección: guardia ligada al ciclo real de la petición, bloqueo mientras exista ejecución activa y clave estable por `preview_hash` para reintentos después de error de red.
- Publicación: `624f88da6289316c9e54e8e2f3c72740aba34010`.
- Prueba de comportamiento aislada: primera petición pendiente, segundo envío rechazado y reintento conserva la clave; aprobada.

### NXR-CERT-003 — Búsqueda directa sin comprobación integral por fila

- Defecto: el endpoint canónico utilizaba una consulta no orientada a permisos y el consolidado no validaba de forma homogénea todos los resultados base.
- Riesgo: una llamada manipulada podía obtener títulos o números de documentos no autorizados.
- Corrección: overrides permanentes para ambos endpoints, `frappe.get_list`, permiso de DocType, permiso del documento, acceso al proyecto y enmascaramiento de cuentas.
- Publicación: `7a260c3c92a526cb25f1569576c1982b6453d7ea`, `3b0c7a95ed1ac76074f06f42d80e7e8401043192`.
- Regresión: `da4f8b4d3032140b151e41e4eeca455ac356412d`.
- Prueba negativa aislada: resultado de proyecto no autorizado y documento sin lectura excluidos; aprobada.

## Comprobaciones ejecutadas en esta certificación

- `node --check` sobre el coordinador UX corregido: **APROBADO**.
- Compilación Python de `permissions.py`, `hooks.py` y contrato modificado: **APROBADO**.
- Prueba aislada de ejecución concurrente e idempotencia estable: **APROBADO**.
- Prueba aislada de búsqueda con proyecto permitido, proyecto denegado y documento sin permiso: **APROBADO**.
- Aserciones contractuales de segregación, servicios canónicos, permisos y ausencia del temporizador de 30 segundos: **APROBADO**.
- Escaneo local de patrones de secretos en archivos modificados: **APROBADO, sin hallazgos**.
- Blobs remotos comparados con los archivos validados localmente: **APROBADO**.

## Certificaciones obligatorias no completadas

- Ruff: **NO EJECUTADO**; binario ausente e instalación aislada falló porque el índice disponible no contiene `ruff==0.16.0`.
- pre-commit completo: **NO EJECUTADO**; herramienta ausente y dependencias no descargables.
- Semgrep: **NO EJECUTADO**; herramienta ausente y dependencias no descargables.
- Instalación limpia Frappe/ERPNext/MariaDB: **NO EJECUTADO**; el entorno no dispone de Docker, Podman, Bench ni MariaDB y no resuelve GitHub para descargar dependencias.
- Migración limpia: **NO EJECUTADO** por la misma limitación.
- Suite NEXORA completa e integración MariaDB: **NO EJECUTADO** sobre el HEAD final.
- Chromium escritorio: **NO EJECUTADO**.
- WebKit/iPhone: **NO EJECUTADO**.
- PWA real: **NO EJECUTADO**.
- Validación visual manual en staging: **NO EJECUTADO** por falta de acceso autorizado al sitio.
- GitHub Actions por `push`: el conector disponible no expone esos runs y no se declaran aprobados.

## Veredicto oficial

**VEREDICTO FINAL: NO, EL OBJETIVO NO FUE CUMPLIDO COMPLETAMENTE.**

El código UX-A…UX-H existe y fue publicado, y los tres defectos detectados en esta revisión fueron corregidos. Sin embargo, NXR-UX-006 y NXR-UX-013 continúan parciales y faltan las certificaciones obligatorias de instalación, migración, Ruff, pre-commit, Semgrep, suite completa, escritorio, iPhone/WebKit y PWA.

## Siguiente acción exacta

Ejecutar sobre el HEAD remoto final una certificación aislada con las herramientas oficiales de `.github/workflows/nexora-app.yml` y `.github/workflows/linters.yml`: instalación y migración limpia, pre-commit dos veces con árbol limpio, Semgrep, suite NEXORA, integración MariaDB, Chromium, WebKit/iPhone y PWA. Corregir y publicar cualquier fallo antes de autorizar staging.
