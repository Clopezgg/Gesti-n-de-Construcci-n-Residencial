# Checkpoint ConstruControl

- Fecha: 2026-07-19 America/Tegucigalpa
- Pull Request: #9 abierto y en borrador
- Rama única: `reconstruccion-definitiva-construcontrol`
- Base protegida observada al inicio: `main` en `56ad5d9186075b66a89c773bb9c5922329f5687e`
- Bloques certificados: 1, 2, 3 y 4
- Sprint actual: C — interfaz e infraestructura
- Implementación global real: 92%
- Certificación global: 33% — Bloques 1–4
- HEAD funcional anterior: `01ec1389282023b3a53d1cba7d452caeabbda678`

## Sprint A — FI01, FI02, PR01 y CO01

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA A PENDIENTE**.
- No se reabrió porque no apareció un fallo bloqueante de saldo, permisos, doble contabilización o corrupción.

## Bloque 8 — MM01, MM02 y MIGO

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA B PENDIENTE**.
- Commits: `6f60d782683c28e5514f8dfbecd4b47c90e5db80`, `40409c46da58028c74abe92a47cdfe56373dfb77`.
- Evidencia dirigida publicada: 7/7 pruebas.

## Bloque 9 — QC01 y CL01

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA B PENDIENTE**.
- Commits: `5dd5379ea04578e4748dfe374562f688908f6ffc`, `4726ca09d869eb6b201c227478f9b6c0a459c361`.
- Evidencia dirigida publicada: 6/6 pruebas QC01/CL01 y 3/3 de migración histórica.

## Bloque 10 — BI01 y AU01

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA B PENDIENTE**.
- BI01 usa un único resumen canónico para dashboard, reportes, filtros, drill-down y exportación.
- Fondos, gastos, compromisos, contratos, inventario, avance, calidad y cierres provienen de registros vivos y reglas financieras compartidas.
- La exportación CSV exige rol autorizado y proyecto explícito, crea un archivo privado ligado al perfil del proyecto, neutraliza fórmulas y reutiliza la misma huella cuando el contenido no cambia.
- Los reportes guardados y las notificaciones son idempotentes.
- AU01 registra identidad, rol, acción, módulo, registro, fecha/hora, estados anterior y posterior, motivo, origen, correlación y huella SHA-256.
- Se distinguen creación, modificación, aprobación, rechazo, pago, anulación, reversión y eliminación.
- Los snapshots eliminan contraseñas, tokens, claves, secretos y payloads sensibles.
- Los registros de auditoría no pueden crearse, modificarse ni eliminarse manualmente.
- Evidencia dirigida: 12/12 pruebas BI01/AU01; compilación, Ruff, formato y sintaxis JavaScript aprobados.

## Bloque 11 — escritorio, iPhone, móvil y PWA

- Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA C PENDIENTE**.
- Se conserva el shell canónico con menú lateral, barra superior, navegación móvil, regreso, inicio, perfil, cerrar, cancelar, guardar y guardar/nuevo.
- La recuperación de rutas 404, modales, errores y cambios sin guardar permanece limitada a rutas ConstruControl.
- La PWA dispone de manifest instalable, iconos 192/512, `start_url`, service worker raíz, versión de despliegue y actualización controlada.
- La activación elimina cachés antiguas y recarga una sola vez al cambiar el controlador.
- API, páginas `/app/`, archivos públicos/privados y datos de negocio nunca se guardan en caché.
- Las acciones sensibles bloquean doble clic y los adjuntos permiten cámara, galería o PDF en móvil.
- El aviso sin conexión no simula guardado ni sustituye datos vivos por información obsoleta.
- Evidencia dirigida: 9/9 pruebas de contrato de interfaz/PWA; JSON, Python y sintaxis JavaScript aprobados.

## CI por carriles

- Carril rápido: sintaxis, Ruff, pre-commit, seguridad y pruebas dirigidas en Pull Requests.
- Carril pesado: MariaDB, runtime, contenedor y snapshot forense mediante Puerta A, B, C o FINAL.
- No se añadió `continue-on-error`, no se desactivaron controles y no se utilizó `skip-ci`.

## Puertas de certificación

- Puerta A: pendiente.
- Puerta B: pendiente; Bloques 8, 9 y 10 implementados.
- Puerta C y FINAL: pendientes; Bloque 11 implementado y Bloque 12 en ejecución.
- No se ejecutará ninguna puerta hasta publicar los Bloques 11 y 12.

## Gobierno preservado

- `main` no fue modificado.
- PR #9 permanece abierto, DRAFT y sin fusionar.
- No se creó otra rama ni otro Pull Request.
- No se usó force push ni se borraron datos, volúmenes, ramas o respaldos.

## Siguiente acción exacta

Continuar inmediatamente con el Bloque 12 — infraestructura, migración, persistencia, respaldo, restauración y documentación, sin ejecutar todavía las puertas A, B, C ni FINAL.
