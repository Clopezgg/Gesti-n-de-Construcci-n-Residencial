# NEXORA — Estado de ejecución

- Fecha de cierre técnico: 2026-07-29
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama oficial: `main`
- HEAD inicial de `main` verificado: `6e0be61e34bac12e2a9cc01cb0420bd2e7c55958`
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

Ejecutar sobre el HEAD remoto final una certificación aislada con las herramientas oficiales de `.github/workflows/nexora-app.yml` y `.github/workflows/linters.yml`: instalación y migración limpia, pre-commit dos veces con árbol limpio, Semgrep, suite NEXORA, integración MariaDB, Chromium, WebKit/iPhone y PWA. Corregir cualquier fallo real antes de autorizar staging.

## Reanudación pre-deploy — Bloque de estabilización 1

- Base remota incorporada sin sobrescritura: `6e21f5a6c63c85a509ba1f45a57bdd052fa864c9`.
- Alcance consolidado: conservar el reformateo ya publicado, completar el contrato negativo de cuentas guardadas y estabilizar el arranque E2E del dashboard.
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados: **NO**.

### NXR-CERT-004 — Árbol modificado por pre-commit

- Evidencia recuperada: `pre-commit-first.patch`, `git-status-after-first.txt`, log completo y worktree formateado del run `30425992926`.
- Resultado: los cambios canónicos de Prettier/Ruff formatter fueron publicados previamente en `d940289a55166f7f5c49c5c229fc23bcb337e99d` y ajustados por Ruff en `6e21f5a6c63c85a509ba1f45a57bdd052fa864c9`.
- Integración: este bloque parte de ese HEAD y no revierte sus workflows ni sus correcciones.

### NXR-CERT-005 — Contrato negativo de cuentas guardadas

- Regla confirmada: ausencia de selección, cuenta inexistente, falta de permiso y cuenta incompatible son estados distintos y deben conservar mensajes distintos.
- Corrección: se añadieron pruebas negativas para selección vacía, cuenta inexistente, cuenta sin lectura, proyecto distinto y moneda incompatible.
- Backend: se conserva la diferenciación ya implementada en `_account_row` y `resolve_income`; no se degradaron permisos ni compatibilidad.

### NXR-CERT-006 — Arranque E2E del dashboard

- Causa real: el encadenamiento del thenable de Frappe detenía el montaje del contexto antes de renderizar el dashboard.
- Corrección publicada previamente: `loadContext` usa un contenedor `async` nativo con `try/catch/finally`, compatible con el retorno de `frappe.call`.
- Corrección de certificación: la espera de ruta usa estado renderizado estable, registra URL/ruta/visibilidad/texto al fallar y exige dashboard listo, proyecto, período, acciones Registrar ingreso/Registrar gasto y ausencia de errores críticos.

### Validaciones focales del bloque

- Sintaxis JavaScript/MJS y compilación Python de los archivos incorporados: **APROBADAS** en el worktree focal.
- 47 pruebas contractuales focales de navegador, dashboard, operaciones guiadas, certificación y flujos rápidos: **APROBADAS**.
- Escaneo de patrones de secretos en los archivos modificados: **APROBADO, sin hallazgos**.
- Certificación integral: queda delegada a los workflows permanentes del nuevo HEAD; no se declara aprobada antes de recibir sus resultados.

### Siguiente acción exacta

Verificar los workflows permanentes del commit publicado. Si linters, MariaDB o navegador/PWA fallan, descargar la evidencia exacta, corregir la causa real, publicar otro bloque coherente y repetir hasta que la certificación pre-deploy quede en verde.

## Auditoría interna 1:1 — estabilización del HEAD real

- Base remota verificada: `48aba08b565c7bf14fec13065cc42fef7e374936`.
- Ejecución fallida reproducida: `30453306410`; puertas rojas: `linters`, `contract`, `Frappe real · escritorio · iPhone · PWA` y `mariadb`.
- Producción, AWS, Coolify, DNS, secretos, bases y volúmenes reales modificados: **NO**.

### NXR-CERT-007 — workflows temporales inseguros

- Causa: cinco workflows de recuperación/finalización seguían versionados aunque el contrato permanente solo autoriza seis workflows NEXORA. Esos archivos solicitaban `contents: write`, ejecutaban `git commit`/`git push` y uno contenía `git reset --hard`.
- Efecto: `validate_nexora_app.py` detenía tanto el contrato como MariaDB antes de instalar o ejecutar pruebas.
- Corrección: retirada versionada y recuperable de los cinco workflows temporales; se conservan únicamente los workflows permanentes de aplicación, finanzas, gobierno, entrega, verificación y recibo pre-deploy.

### NXR-CERT-008 — árbol no canónico para pre-commit

- Causa: dos scripts de navegador y el modelo guiado no tenían el formato Prettier canónico; dos pruebas no tenían el formato Ruff canónico y una prueba MariaDB contenía contextos `with` anidados rechazados por Ruff `SIM117`.
- Corrección: formato canónico de scripts, modelo y pruebas, más un único `with` de múltiples contextos sin cambiar el caso negativo de permisos.

### NXR-CERT-009 — carrera en la espera de ruta del navegador

- Causa: la espera confirmaba el contenedor de Frappe dentro del navegador y luego volvía a localizarlo en una segunda operación. Durante el ciclo de montaje de la página, ese segundo acceso podía perder el contenedor ya validado y expirar, aunque el dashboard, su API, la sesión y todos los servicios estuvieran saludables.
- Corrección: la misma evaluación estable devuelve una instantánea de ruta y texto; la validación negativa de página no disponible se ejecuta sobre esa instantánea, sin una segunda localización susceptible a carrera.
- Regresión añadida: el contrato exige consumo de la instantánea y prohíbe reintroducir la segunda llamada a `locator.innerText()`.

### Validación local previa a publicación

- Inventario canónico regenerado desde el índice final: **5,401 archivos**, `sha256=f2d76a687bdba72ea299ac3648b61ca5230724b59bd58a701d11aac925e14679`.
- Validadores de repositorio, aplicación, modelos financieros, gobierno, workflows, aceptación operativa y completitud: **APROBADOS**.
- Pruebas contractuales: **238/238 APROBADAS**.
- Pruebas puras financieras, libro, referencias, evidencias, directorio, contratos, compras, solicitudes, cotizaciones y analítica: **80/80 APROBADAS**, incluidos fondos insuficientes, idempotencia conflictiva y rollback multifuente.
- Compilación Python y sintaxis JavaScript/MJS: **APROBADAS**.
- Ruff check y Ruff format check: **APROBADOS**.
- Prettier: **APROBADO**.
- Escaneo de secretos: **528 archivos, 0 hallazgos**.
- Pre-commit completo, primera y segunda ejecución consecutivas: **APROBADO; árbol sin modificaciones**.
- Certificación aislada Frappe/MariaDB/Chromium/WebKit/PWA: pendiente de repetición por los workflows permanentes del commit publicado.

### NXR-CERT-010 — contrato de checkout exacto desactualizado

- Fallo remoto reproducido: `Product, migration and security validation` del run `30455904410`; 238 pruebas pasaban y `test_linters_require_exact_head_and_two_clean_all_files_passes` fallaba con `3 != 2`.
- Causa: el contrato asumía dos checkouts exactos aunque el workflow permanente tiene tres puertas independientes (`linters`, `semgrep` y `secrets`), todas obligadas a certificar el SHA exacto.
- Corrección: el contrato deriva el número de checkouts reales y exige que cada uno fije el SHA del evento y lo compare contra `HEAD_SHA`; conserva la exigencia de dos pasadas completas y limpias de pre-commit.
- Validación local: prueba focal **3/3 APROBADA**, suite standalone completa **239/239 APROBADA** y seis validadores de producto/migración/seguridad **APROBADOS**.

### NXR-CERT-011 — certificación incompleta de algunos HEAD de main

- Defecto reproducido: el SHA `922b34fd4d402950225f47c74b3d9363d3eda56f` ejecutó aplicación, MariaDB, navegadores, entrega y validación de producto, pero no inició `linters` ni el recibo pre-deploy porque sus filtros de rutas no incluían el contrato compartido corregido.
- Riesgo: un HEAD distinto podía heredar resultados anteriores o quedar sin una comprobación obligatoria, por lo que no era certificable 1:1 aunque su árbol estuviera limpio.
- Corrección: `linters`, aplicación, finanzas, entrega y recibo pre-deploy se ejecutan para **cada push a main**. Los filtros de pull request focales se conservan donde ya existían.
- Regresión añadida: el contrato verifica las cinco puertas permanentes, la rama `main` y la ausencia de filtros de ruta en el evento `push`.
- Validación local: contrato pre-deploy **5/5 APROBADO**, YAML de workflows **APROBADO** y validadores de workflows, aplicación y gobierno **APROBADOS**.

### NXR-CERT-012 — búsqueda, corrección y doble envío en navegador real

- Defecto reproducido: la suite de navegador real visitaba las rutas de búsqueda y operaciones, pero no ejecutaba una búsqueda consolidada, una corrección controlada ni la repetición exacta de una solicitud definitiva contra la idempotencia del servidor.
- Corrección: Chromium y iPhone WebKit buscan un documento generado de 12 dígitos desde la interfaz, abren su efecto financiero consolidado, ejecutan una anulación auditada desde la operación original con tres usuarios segregados y repiten las solicitudes de ingreso y gasto.
- Evidencia positiva: cada perfil exige el número de la corrección, conserva número e importe del original, confirma el estado compensado y recibe el mismo número documental al repetir la solicitud exacta.
- Evidencia negativa relacionada: se conservan las pruebas de fondos insuficientes, corrección prohibida, permisos, segregación e inyección de fallo con rollback en las suites de integración; el contrato de navegador impide retirar búsqueda, consolidado, corrección o replay.
- Defecto de transición corregido: las compensaciones centrales ahora cambian únicamente el estado del original a `Compensated Partial` o `Compensated Total`, dentro del mismo savepoint; el fallo posterior inyectado revierte tanto el documento compensatorio como el estado original.

### NXR-CERT-013 — límite explícito de la certificación de navegador

- Bloqueo reproducido: dos ejecuciones independientes permanecieron más de 60 minutos en `Validate desktop, iPhone WebKit and PWA` sin avanzar a captura de evidencia ni limpieza. El conector autenticado confirmó el estado en curso; al no existir todavía un log final descargable, no se reintentó el ZIP completo.
- Causa corregible localizada: las llamadas `fetch` y `frappe.call` ejecutadas dentro de la página no tenían deadline ni cancelación, y el proceso Node heredaba únicamente el límite global de 180 minutos del job.
- Corrección: toda solicitud directa del navegador usa `AbortController` con 120 segundos configurables; las llamadas Frappe tienen el mismo deadline y error accionable; login, replay idempotente, lectura del libro operativo y manifest pasan por el transporte acotado.
- Resguardo de proceso: instalación npm, descarga de Chromium/WebKit y smoke completo tienen límites explícitos de 10, 20 y 50 minutos, cada uno con 30 segundos de gracia, conservando los pasos `if: always()` de evidencia, artefacto y limpieza.
- Regresión: el contrato exige deadline de red, cancelación, replay acotado y límite del proceso. Sintaxis MJS, 9 pruebas contractuales de navegador y validadores de aplicación/aceptación: **APROBADOS**.

### NXR-CERT-014 — respuesta del snapshot recibida sin transición del dashboard

- Evidencia exacta recuperada: el job de navegador `90611467636` del run `30462376918` recibió `200` para la página, activos, sesión, contexto y `nexora.dashboard.executive.get_executive_snapshot`; no registró errores de página, consola, servidor ni autenticación. La única falla fue la espera de 120 segundos por `.nxr-dashboard-shell[data-state="ready"]`.
- Causa reproducida: `load()` esperaba directamente el thenable devuelto por `frappe.call`. El callback HTTP terminaba con 2,984 bytes, pero esa espera no continuaba hasta `render()`, por lo que el shell permanecía en `loading`.
- Corrección: el snapshot ejecutivo usa una promesa nativa resuelta por los callbacks de Frappe, con deadline propio de 120 segundos, liberación del temporizador, rechazo explícito y mensaje accionable. El render consume directamente el snapshot resuelto y conserva la protección por número de serie contra respuestas obsoletas.
- Regresión positiva: el contrato exige callback exitoso, promesa nativa y render del snapshot. Regresión negativa: prohíbe `await frappe.call` dentro de `load()` y exige timeout y callback de error.

### NXR-CERT-015 — bucle de mutaciones y deadline dependiente de la página

- Fallo reproducido: el job `90618970748` del run `30464572739` recibió `200` para login, dashboard y snapshot, pero no alcanzó siquiera el probe autenticado. Terminó exactamente por el límite externo de 50 minutos con código `124`; el reporte ubicó la espera en `browserRequest()` dentro de `assertAuthenticated()`.
- Causa: el observador global de contexto reaccionaba a cada mutación del body y escribía incondicionalmente el mismo `textContent`, generando otra mutación y una cadena de microtareas que bloqueaba el hilo principal. Además, el deadline de `browserRequest()` vivía dentro de ese mismo hilo bloqueado, por lo que no podía cancelar la espera.
- Corrección de interfaz: las escrituras de texto del contexto son idempotentes y el observador se agrupa en un único `requestAnimationFrame`; una mutación provocada por el propio render ya no se realimenta.
- Corrección de certificación: el transporte HTTP usa `BrowserContext.request`, comparte las cookies de la sesión y aplica el timeout de Playwright fuera del hilo de la página. Las llamadas Frappe de fixtures usan el mismo transporte y serializan argumentos compuestos como JSON.
- Regresiones: el contrato exige transporte fuera de `page.evaluate`, timeout nativo, observador agrupado e igualdad previa antes de cambiar texto; prohíbe reintroducir `AbortController` dependiente de la página o escrituras directas repetitivas del contexto.

### NXR-CERT-016 — revisión guiada invalidada entre validación y clic

- Fallo exacto reproducido: el job `90636325012` del run `30469667935` completó login, dashboard y vista previa de ingreso con HTTP `200`, pero el botón `data-guided-next="4"` pasó de habilitado a oculto antes del clic. Playwright agotó 30 segundos y la captura mostró el flujo de vuelta en la etapa 2, sin errores de página, consola, servidor o autenticación.
- Evidencia acotada: logs directos del job y únicamente los archivos `browser/nexora-browser-report.json`, `browser.log`, `compose.log` y `browser/desktop-chromium-failure.png` del artifact `8731220823`; ZIP de 758,523 bytes verificado con `sha256=003e96587a3b9a22f9d4dd592a8d5b6e00c0e13afacec08e2d651c9cb882f108`.
- Causa: el observador del flujo guiado volvía a sustituir en cada frame el selector de cuentas y el HTML de revisión aunque nada hubiera cambiado. En paralelo, la prueba podía iniciar la vista previa antes de que terminaran validaciones Link y consultas de la etapa, dejando una ventana entre la primera detección de etapa 3 y el clic definitivo.
- Corrección de interfaz: visibilidad, solo lectura, etapa activa, selector de cuentas, revisión, botones, estado y `aria-busy` se actualizan únicamente cuando cambia su valor; la firma del selector evita reconstruir sus controles en cada ciclo del observador.
- Corrección de navegador: la vista previa espera inactividad de red y ausencia del overlay Frappe; la etapa 3 debe conservar durante 750 ms la vista previa, el botón canónico y el ejecutor original habilitados antes de efectuar el clic real.
- Regresiones positiva y negativa: el contrato exige quietud de red, estabilidad temporal e idempotencia de render, y rechaza la escritura incondicional anterior. Sintaxis JavaScript/MJS y 18 pruebas focales de navegador/cuenta progresiva: **APROBADAS**.
- Producción, AWS, Coolify, DNS, secretos, bases y volúmenes reales modificados: **NO**.
