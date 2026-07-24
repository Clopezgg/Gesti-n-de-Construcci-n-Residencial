# NEXORA — Orden maestra de finalización total

## Mandato

Esta sesión debe continuar directamente el desarrollo de **NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones** hasta completar y certificar el sistema integralmente.

Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`  
Rama base certificada: `nexora-reconstruccion`  
PR base: `#11`  
Rama única de continuidad: `nexora-continuidad-total`  
PR único de continuidad: `#12`  
Rama protegida: `main`

El SHA mencionado en documentos previos es solo referencia. Antes de actuar, obtener el HEAD real local y remoto y continuar desde el más reciente de la misma rama.

## Objetivo final

Completar NEXORA como producto real, conectado, coherente, instalable, mantenible, seguro, usable, móvil, auditable y certificable. No basta analizar, recomendar, crear maquetas, páginas vacías, botones muertos, documentación sin código o pruebas autorreferenciales.

Cada módulo debe tener backend, persistencia, permisos server-side, interfaz real, validaciones, auditoría, idempotencia, manejo de errores, evidencia, integración con módulos anteriores y pruebas positivas y negativas.

El sistema solo puede declararse terminado cuando los 166 requisitos de `docs/nexora/MATRIZ_REQUISITOS.md` estén resueltos como `IMPLEMENTADO Y VALIDADO`, `OBSOLETO JUSTIFICADO` o `NO APLICA JUSTIFICADO`, con evidencia verificable y SHA exacto.

## Fuente única de verdad

Usar este orden:

1. HEAD real de `nexora-continuidad-total`.
2. Código, migraciones y pruebas reales.
3. PR #12.
4. `EXECUTION_STATE.md`.
5. `docs/nexora/MATRIZ_REQUISITOS.md`.
6. `docs/nexora/BLOQUE_*.md`.
7. GitHub Actions, jobs, artifacts y digests.
8. PR #11 y su base certificada.
9. ConstruControl solo como historial y fuente de funciones reutilizables.

`docs/reconstruction/CHECKPOINT.md` es histórico de ConstruControl/PR #9. No usarlo como checkpoint vigente. Crear o mantener `docs/nexora/CHECKPOINT.md` como checkpoint canónico de NEXORA.

## Estado adoptado

Bloques 0–3: implementados y validados.  
Bloque 4: evidencia e inmutabilidad, validado.  
Bloque 5: Directorio Universal de Entidades, validado.  
Bloque 6: contratistas y contratos, validado.

No reconstruirlos ni sustituirlos. Solo modificarlos ante regresión comprobada que impida el bloque activo, duplique datos, corrompa saldos, debilite permisos o rompa integración.

Bloque activo: **Bloque 7 — compras y proveedores**.

Ya existen `NXR Supplier Profile`, `NXR Purchase Request`, `NXR Purchase Request Line`, servicios, páginas y pruebas. Continuar desde ese código, sin arquitectura paralela.

Existe un fallo conocido de `Linters → Run pre-commit twice over the complete tree`. Resolverlo primero sobre el HEAD actual.

## Prohibiciones

No modificar `main`. No crear otra rama ni otro PR. No fusionar ni cerrar PR #11/#12. No force push, rebase destructivo, `reset --hard`, `clean -fd`, borrado de datos, respaldos o volúmenes, ni `docker compose down -v`.

No modificar producción, AWS, Coolify, DNS, bases productivas o credenciales. No publicar secretos ni pedir claves privadas. No migrar datos históricos. No desactivar pruebas, Semgrep, pre-commit o workflows; no agregar `continue-on-error`; no simular resultados; no marcar manualmente `passed`; no duplicar DocTypes o arquitecturas existentes.

Un solo escritor debe trabajar sobre `nexora-continuidad-total`.

## Política para computadora limitada

Usar localmente solo inspección, edición, pruebas unitarias/contractuales específicas, validación liviana, Ruff, pre-commit, JS, Semgrep razonable, Git, commit y push.

Usar GitHub Actions para Frappe, MariaDB, instalación, migraciones, integración, concurrencia, Docker, persistencia, backup, restore, navegador y PWA. No instalar infraestructura pesada local solo para demostrar pruebas.

## Ciclo obligatorio por requisito

1. Obtener estado Git y HEAD real.
2. Identificar requisito exacto de la matriz.
3. Localizar implementación existente.
4. Detectar causa raíz.
5. Implementar corrección mínima completa.
6. Revisar diff.
7. Prueba positiva.
8. Prueba negativa.
9. Permiso server-side.
10. Idempotencia cuando corresponda.
11. Rollback cuando corresponda.
12. Concurrencia cuando corresponda.
13. Regresiones relacionadas.
14. Pre-commit.
15. Corregir fallos.
16. Commit semántico.
17. Push a `origin/nexora-continuidad-total`.
18. Confirmar commit en PR #12.
19. Actualizar matriz, checkpoint, estado y documento de bloque.
20. Continuar con el siguiente requisito del mismo bloque.

No abandonar un bloque a medias salvo bloqueo externo real y trabajo independiente seguro.

# Fase 0 — recuperación y estabilización

Ejecutar primero:

- `git status`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git log --oneline -15`
- `git diff`
- leer `EXECUTION_STATE.md`
- leer `docs/nexora/MATRIZ_REQUISITOS.md`
- revisar `nexora_app/nexora/purchases`
- revisar pruebas de purchases
- revisar `.pre-commit-config.yaml`

Ejecutar `pre-commit run --all-files`, identificar hook, archivo, línea, mensaje y causa raíz. Corregir sin ocultar el fallo. Ejecutar dos veces consecutivas `pre-commit run --all-files`; ambas deben terminar limpias y sin modificar archivos.

Ejecutar las pruebas reales disponibles de compras y solicitudes, especialmente:

- `test_purchase_contract.py`
- `test_purchase_core.py`
- `test_purchase_integration.py`
- `test_purchase_request_core.py`
- `test_purchase_request_integration.py`

Usar los comandos definidos por el repositorio. Validar sintaxis, Ruff y Semgrep aplicables. Revisar `git diff` y `git status`. Publicar una corrección semántica real y continuar inmediatamente con el Bloque 7.

# Bloque 7 — proveedores, solicitudes, cotizaciones y catálogo

Resolver y certificar `NXR-COM-0001`, `NXR-COM-0002`, `NXR-COM-0003` y `NXR-COM-0007`.

## Proveedores

Proveedor basado exclusivamente en `NXR Entity`, con perfil, tipo persona/organización, clasificación, categorías, productos/servicios, vigencia, estado, cumplimiento, documentos, evidencias, contactos, información de pago protegida, múltiples roles, resolución canónica, consolidación no destructiva, bloqueo de vencidos/no habilitados, permisos, auditoría e historial cronológico.

No crear directorio paralelo al Directorio Universal de Entidades.

## Solicitudes de compra

Soportar múltiples líneas, producto/servicio, descripción controlada, cantidad, unidad, fecha requerida, proyecto, fase, centro de costo, clasificación económica, presupuesto, fuente prevista, responsable, prioridad, justificación, evidencia, moneda, estimado, impuestos previstos, estado y observaciones.

Estados mínimos: Borrador, Enviada, En revisión, Aprobada, Rechazada, Cancelada y Convertida.

Impedir líneas vacías, cantidades no positivas, duplicación por idempotencia, edición no autorizada, autoaprobación incompatible con segregación, modificación terminal, conversión duplicada y aprobación sin relaciones obligatorias.

## Aprobación

Aprobador, fecha, comentario, monto, líneas aprobadas/rechazadas, trazabilidad, segregación, permisos server-side, rechazo motivado, devolución controlada, cancelación y auditoría antes/después.

## Cotizaciones

Varios proveedores y cotizaciones por solicitud; precios por línea, impuestos, descuentos, entrega, vigencia, condiciones de pago, moneda, garantía, evidencia, comparación homogénea, selección justificada, rechazo de cotización vencida y prevención de selección duplicada.

## Catálogo

Reutilizar `Item`, `UOM` y estructuras ERPNext cuando cubran el requisito. Integrar materiales, productos, servicios, unidades, categorías, activo/inactivo, proveedor habitual, descripción, especificaciones, equivalencias, impuestos y costos de referencia. No duplicar modelos estándar innecesariamente.

## Interfaz

Completar `/app/nexora-suppliers`, `/app/nexora-purchase-requests`, cotizaciones, comparación, aprobación, expediente, búsqueda, filtros, estados y acciones. Cada botón debe llamar backend real.

## Cierre del Bloque 7

Demostrar creación, modificación, aprobación, rechazo, cancelación, idempotencia, permisos negativos, proveedor inválido y duplicado rechazados, vigencia, cumplimiento, solicitud multítem, cotizaciones múltiples, selección, rollback, concurrencia aplicable, instalación, migración repetida, interfaz conectada, Frappe/MariaDB, pre-commit y Semgrep.

Crear/actualizar:

- `docs/nexora/BLOQUE_7_COMPRAS_PROVEEDORES.md`
- `docs/nexora/MATRIZ_REQUISITOS.md`
- `docs/nexora/CHECKPOINT.md`
- `EXECUTION_STATE.md`
- cuerpo del PR #12

No cerrar el bloque hasta que los workflows obligatorios aprueben el mismo SHA funcional.

# Bloque 8 — órdenes, recepciones y vínculo financiero

Resolver `NXR-COM-0004`, `NXR-COM-0005`, `NXR-COM-0006`, `NXR-COM-0008`.

Implementar conversión idempotente desde solicitud aprobada, orden multítem, proveedor canónico, proyecto, fase, centro de costo, presupuesto, compromiso, fuente, moneda, impuestos, descuentos, condiciones, aprobación, envío, recepción parcial/completa, cancelación, devolución, factura, CxP, pago, expediente, evidencia, auditoría, saldos por línea, tolerancias, pendientes, sobreentrega controlada, sobrepago rechazado, liberación de compromiso y rollback financiero.

Reutilizar motor financiero, Libro Central, `NXR Operation`, `NXR Commitment`, `NXR Fund Source`, `NXR Evidence`, secuencia de 12 dígitos, idempotencia y locks.

# Bloque 9 — inventario y kardex

Resolver `NXR-INV-0001` a `NXR-INV-0008`.

Implementar producto, bodega, proyecto, ubicación, entrada, recepción, traslado, entrega a contratista, consumo, devolución, daño, pérdida, ajuste, conteo físico, conciliación, valoración, lote/referencia aplicable, kardex cronológico, saldo físico y valorizado, evidencia, permisos, auditoría, trazabilidad a compra/contrato/fase, bloqueo de inventario negativo, concurrencia de salida y rollback.

Reutilizar ERPNext Stock Ledger si cumple, sin segundo ledger paralelo.

# Bloque 10 — presupuestos y compromisos

Resolver `NXR-PRE-0001` a `NXR-PRE-0006`.

Presupuesto versionado por proyecto/fase/centro/clasificación, líneas, aprobado, comprometido, ejecutado, disponible, proyectado, reservas, liberaciones, reclasificaciones, adendas, sobregiro, pronóstico, desviación, historial, evidencia, permisos y auditoría.

Conectar contratos, compras, inventario, pagos, Libro Central, fuentes y centros de costo. Ninguna operación excede presupuesto sin excepción formal auditada.

# Bloque 11 — buscador y dashboard

Implementar buscador universal, dashboard NEXORA, indicadores operativos/financieros, filtros, drill-down, permisos, tarjetas, alertas, acciones rápidas, rendimiento, sin consultas duplicadas, recargas infinitas ni congelamiento. Solo datos reales desde servicios canónicos; no recalcular saldos en el navegador.

# Bloque 12 — estados de cuenta, reportes y documentos

Resolver `NXR-REP-0001` a `NXR-REP-0007`, `NXR-DOC-0002`, `NXR-DOC-0003`.

Estados de cuenta por fuente, entidad y contrato; reportes financieros/costos; conciliación, filtros, permisos, PDF real, Excel real, plantillas, versión, hash, documentos verificables y totales conciliados con Libro Central.

# Bloque 13 — avance, calidad y evidencias

Resolver `NXR-AVA-0001` a `NXR-AVA-0005`.

Avance cronológico por proyecto/fase, porcentaje, cantidad, fotos, videos/documentos permitidos, cámara/galería, descripción, fecha, ubicación autorizada, responsable, revisión, aprobación/rechazo/corrección, evidencia privada, vínculo contractual/estimación/hito, calidad, observaciones, no conformidad, acción correctiva y cierre. No eliminar originales destructivamente.

# Bloque 14 — notificaciones

Resolver `NXR-NOT-0001` a `NXR-NOT-0004`.

Eventos, destinatarios, canales configurables, bandeja interna, correo configurado, PWA cuando sea viable, reintentos, idempotencia, estados reales, no simular éxito, auditoría, preferencias, plantillas y permisos. El sistema sigue funcionando sin canal externo.

# Bloque 15 — usuarios, roles y segregación

Resolver `NXR-USR-0001` a `NXR-USR-0006`.

Roles granulares, permisos por proyecto/acción, segregación, aprobaciones separadas, auditoría de acceso sensible, corrección administrativa reforzada, acceso a evidencias, finanzas, contratos, proveedores y reportes, denegaciones reales, sesiones, usuario deshabilitado y revocación. No confiar solo en ocultar botones.

# Bloque 16 — cierres, correcciones y reversión

Resolver `NXR-CIE-0001` a `NXR-CIE-0007` y `NXR-DOC-0005`.

Cierre mensual, prevalidaciones, conciliación, saldos, pendientes, inmutabilidad posterior, anulación, reversión, sustitución, corrección compensatoria, intervención excepcional, evidencia, motivo, autorización, auditoría, rollback y conservación de originales. No cerrar con inconsistencias.

# Bloque 17 — integraciones

Resolver `NXR-INT-0001` en adelante.

Registro, credenciales protegidas, adaptadores reales, prueba de conexión, logs, estados, modo manual sin credenciales, webhooks firmados, reintentos, idempotencia, límites, errores comprensibles y auditoría. Nunca guardar claves en repositorio.

# Bloque 18 — identidad NEXORA, español, iPhone y PWA

Resolver `NXR-UX-0001` a `NXR-UX-0006` y `NXR-DOC-0006`.

Identidad NEXORA, español, navegación, menú, escritorio, iPhone, móvil, tablet, formularios, tablas responsivas, listas, tarjetas, botones, modales, búsqueda, accesibilidad, estados vacíos, errores claros, cámara, galería, manifest, service worker, caché, actualización, PWA, offline limitado seguro, sin scroll horizontal, botones muertos, páginas duplicadas, refrescos infinitos o congelamientos. Certificar con navegador real.

# Bloque 19 — certificación integral

Resolver `NXR-QA-0001` a `NXR-QA-0008`.

Cada bloque debe tener prueba positiva/negativa, permiso server-side, idempotencia, concurrencia y rollback aplicables, instalación, migración, reinstalación, persistencia, evidencia y SHA exacto.

Crear auditoría automática de 166 requisitos que rechace filas sin prueba, evidencia específica, SHA completo, workflow, artifact, digest, código real o validación real. No permitir 100 % si falta una fila.

# Bloque 20 — infraestructura, backup y publicación

Resolver `NXR-INF-0002` a `NXR-INF-0009`.

Validar remotamente Docker Compose, Frappe, ERPNext, NEXORA, MariaDB, Redis, workers, scheduler, WebSocket, health checks, volúmenes, persistencia, reinicio, redeploy, migraciones repetidas, backup verificable, restore aislado, rollback, HTTPS, cutover preparado, sitio/base limpia, datos iniciales y no migración histórica. No desplegar producción sin autorización expresa.

# Certificación por bloque

1. Congelar SHA funcional.
2. Pruebas específicas y regresiones.
3. Pre-commit dos veces.
4. Semgrep.
5. Publicar SHA.
6. Dejar ejecutar Actions.
7. Registrar workflow, run ID, job ID, resultado, artifact ID y digest SHA-256.
8. Actualizar matriz, checkpoint, estado, documento y PR.
9. Solo entonces marcar `IMPLEMENTADO Y VALIDADO`.

Si existe un commit posterior, repetir cualquier certificación global dependiente del SHA anterior.

# Commits

No crear commit por archivo ni commits vacíos. Preferir uno o dos commits funcionales por bloque y uno de estabilización si existe fallo real. Usar Conventional Commits (`feat(purchases)`, `fix(purchases)`, `feat(inventory)`, `feat(budgets)`, `feat(reports)`, `feat(progress)`, `feat(notifications)`, `feat(security)`, `feat(integrations)`, `feat(ux)`, `test(nexora)`, `docs(nexora)`).

# Fallos de workflows

No reiniciar todo ciegamente. Localizar workflow, job, step, error, archivo y línea; reproducir cuando sea posible; corregir causa raíz; probar; publicar; dejar correr Actions. No hacer polling. Si hay trabajo independiente del mismo bloque, continuar; de lo contrario, publicar checkpoint exacto.

# Fin de sesión

Antes de cerrar: revisar cambios, no dejar trabajo importante sin commit, hacer push, actualizar `docs/nexora/CHECKPOINT.md` con SHA, bloque, requisito, pruebas, workflows y siguiente acción exacta.

# Validación final única

Cuando todos los bloques estén implementados:

- confirmar 166/166;
- congelar candidato final;
- todos los workflows sobre el mismo SHA;
- instalación limpia;
- actualización existente;
- tres migraciones consecutivas;
- desinstalación/reinstalación;
- permisos;
- finanzas;
- entidades;
- contratos;
- proveedores;
- compras;
- inventario;
- presupuestos;
- reportes;
- avance;
- notificaciones;
- cierres;
- integraciones;
- escritorio;
- iPhone;
- PWA;
- concurrencia;
- rollback;
- persistencia;
- reinicio;
- redeploy aislado;
- backup;
- verificación;
- restore aislado;
- auditoría independiente 166/166;
- artifact final;
- digest SHA-256;
- documentación final;
- estado `READY FOR USER AUTHORIZATION`.

No fusionar ni desplegar automáticamente.

# Publicación final preparada, no automática

Solo con autorización expresa:

1. Fusionar PR #12 hacia `nexora-reconstruccion`.
2. Confirmar contenido completo en PR #11.
3. Revalidar SHA resultante.
4. Fusionar PR #11 hacia `main`.
5. Crear tag NEXORA y release.
6. Crear y validar staging aislado.
7. Preparar producción.
8. Cutover autorizado con rollback verificable.

# Primera acción inmediata

No responder solo con plan. Empezar ahora verificando HEAD y estado Git, reproduciendo y corrigiendo pre-commit, ejecutando pruebas específicas, publicando la corrección en la misma rama y continuando con el primer requisito incompleto del Bloque 7.
