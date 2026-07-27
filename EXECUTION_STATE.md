# NEXORA — Estado de ejecución

- Última actualización: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica activa: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`, abierto, en borrador y no fusionado
- HEAD de `main` verificado: `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- Primer SHA publicado de reconstrucción ejecutiva: `78b9b73ed47d6fb593332f514c1777a0a206e1fd`
- SHA concurrente incorporado y revisado: `715dcb6fe5996ef7eb4fadad2690d57ee1694593`
- Producción modificada: **NO**
- AWS, Coolify o DNS modificados: **NO**
- Credenciales externas utilizadas: **NO**
- Datos históricos migrados: **NO**

## Bloque activo — reconstrucción ejecutiva y reportes

Estado: **NO DEMOSTRADO** hasta completar CI, instalación y migración limpia Frappe/MariaDB, pruebas de permisos, navegador de escritorio, iPhone WebKit y PWA sobre un único SHA publicado.

Alcance en ejecución:

- motor analítico único basado en `NXR Operation Effect`;
- saldos históricos `as-of`, saldo inicial, saldo al cierre y saldo actual separados;
- transferencias, reservas, liberaciones, devoluciones y reversos separados del gasto;
- dashboard premium conservando el contrato funcional certificado;
- FI01, FI02, FI03, CO01, PR02, PR03, MM03 y BI01;
- filtros y paginación server-side;
- Excel y PDF server-side con autorización y auditoría;
- conciliación explícita y anulación compensatoria de ingresos;
- reportes guardados;
- cierre semanal con número de 12 dígitos, idempotencia, hash, auditoría, inmutabilidad y corrección compensatoria;
- pruebas positivas, negativas, contractuales e integración.

## Registro compacto de certificaciones previas

Estas certificaciones pertenecen a lotes anteriores y se conservan como evidencia histórica. No certifican automáticamente la reconstrucción activa del PR #19.

## Bloque 0 — fundación certificada previamente

SHA `83305b6e2bd897e4084d0ae694e94834e2622590`

## Bloque 1 — fundación certificada previamente

SHA `83305b6e2bd897e4084d0ae694e94834e2622590`

## Bloque 2 — fundación certificada previamente

SHA `83305b6e2bd897e4084d0ae694e94834e2622590`

## Bloque 3 — fundación certificada previamente

SHA `83305b6e2bd897e4084d0ae694e94834e2622590`

## Bloque 4 — evidencia certificada previamente

SHA `96ff830ac174484959a5760a9a4d0284cb5bcdd6`

## Bloque 5 — directorio certificado previamente

SHA `e8c8278a88eadf177252631e032ac5009b1d5be0`

## Bloque 6 — contratos certificados previamente

SHA `3d2b65792b149d5ad915e7b1aec64423b3b048f0`

## Bloque 7 — compras certificadas previamente

SHA `a60606151b8a6287d0a5d75d0b14851d6d4da674`

## Bloque 8 — órdenes y recepciones certificadas previamente

SHA `dc638cdeb8f8de0b1da721a4f687f7f0a575f476`

## Bloque 9 — inventario certificado previamente

SHA `93feed5179b99f66b9173f31e8b5b2e4752c0b42`

## Bloque 10 — presupuestos certificados previamente

SHA `43afd1c18dfd081da9d440dddd184e7d233ff4dc`

## Bloque 11 — dashboard certificado previamente

SHA `3ebb2aab2d01d7289e2537d783099570d14b0a19`

## Bloque 12 — reportes certificados previamente

SHA `ad309d079103b2a9ddd82aa578057c99eefa7e53`

## Bloque 13 — avance certificado previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 14 — notificaciones certificadas previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 15 — segregación certificada previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 16 — cierres certificados previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 17 — integraciones certificadas previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 18 — identidad y PWA certificadas previamente

SHA `57a3438ddd931140f12fc417d5ba662dbbaaa315`

## Bloque 19 — certificación integral previa

SHA `dc446ad4822b9753a42e17bc298cda80f0be48dc`

## Bloque 20 — infraestructura previa

SHA `dc446ad4822b9753a42e17bc298cda80f0be48dc`

## Validación local demostrada antes del primer SHA

- compilación sintáctica Python de módulos nuevos y modificados;
- validación sintáctica Node de dashboard, reportes y cierre;
- cinco pruebas puras del motor analítico aprobadas.

Estas comprobaciones no sustituyen CI ni pruebas reales Frappe/MariaDB/navegador.

## Incidencia actual de CI

Los workflows del SHA `715dcb6fe5996ef7eb4fadad2690d57ee1694593` terminan en fallo antes de publicar pasos ejecutados, logs o artefactos. El código sigue bajo revisión estática y no se declara certificado mientras GitHub Actions no produzca evidencia ejecutable.

## Restricciones conservadas

- El PR #19 permanece en borrador y no se fusiona con checks fallidos o pendientes.
- No se crea segundo repositorio, aplicación sustituta ni ledger paralelo.
- Producción, AWS, Coolify, DNS, secretos, volúmenes y datos históricos permanecen sin cambios.

## Siguiente acción exacta

Incorporar las correcciones determinísticas detectadas sobre el HEAD remoto vigente, publicar un commit semántico, volver a ejecutar CI y revisar cada fallo que produzca pasos o logs accionables. Registrar el SHA certificado únicamente cuando todas las validaciones aplicables estén en verde.
