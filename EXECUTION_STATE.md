# NEXORA — Estado oficial de ejecución

- Última actualización: 2026-07-26
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama final y fuente de verdad: `main`
- HEAD inicial de `main`: `b65f7c119b5b15620ae312d11cb3eb3447b25b86`
- Árbol funcional final validado: `37d5d996b16871b30b498e19bd44cb08e791d0cc`
- Integración final inicial en `main`: `718633009014234fcb183d3c33695f238871e056`
- PR #11: fusionado en `main`
- PR #12: fusionado mediante PR #11
- PR #13: fusionado en `main`
- PR #14: fusionado en `main`
- PR #15: fusionado mediante squash en `main` después de aprobar el mismo SHA funcional
- Producción modificada durante la certificación: **NO**
- AWS, Coolify o DNS modificados durante la certificación: **NO**
- Credenciales externas utilizadas: **NO**
- Datos históricos migrados: **NO**

## Estado oficial por bloque

| Bloque | Estado | SHA funcional certificado | Pendientes |
| ---: | --- | --- | --- |
| 0–3 | **IMPLEMENTADO Y VALIDADO** | `83305b6e2bd897e4084d0ae694e94834e2622590` | — |
| 4 — Evidencia e inmutabilidad | **IMPLEMENTADO Y VALIDADO** | `96ff830ac174484959a5760a9a4d0284cb5bcdd6` | — |
| 5 — Directorio Universal de Entidades | **IMPLEMENTADO Y VALIDADO** | `e8c8278a88eadf177252631e032ac5009b1d5be0` | — |
| 6 — Contratistas y contratos | **IMPLEMENTADO Y VALIDADO** | `3d2b65792b149d5ad915e7b1aec64423b3b048f0` | — |
| 7 — Compras y proveedores | **IMPLEMENTADO Y VALIDADO** | `a60606151b8a6287d0a5d75d0b14851d6d4da674` | — |
| 8 — Órdenes, recepciones y vínculo financiero | **IMPLEMENTADO Y VALIDADO** | `dc638cdeb8f8de0b1da721a4f687f7f0a575f476` | — |
| 9 — Inventario y kardex | **IMPLEMENTADO Y VALIDADO** | `93feed5179b99f66b9173f31e8b5b2e4752c0b42` | — |
| 10 — Presupuestos y compromisos | **IMPLEMENTADO Y VALIDADO** | `43afd1c18dfd081da9d440dddd184e7d233ff4dc` | — |
| 11 — Buscador y dashboard | **IMPLEMENTADO Y VALIDADO** | `37d5d996b16871b30b498e19bd44cb08e791d0cc` | — |
| 12 — Reportes y estados de cuenta | **IMPLEMENTADO Y VALIDADO** | `ad309d079103b2a9ddd82aa578057c99eefa7e53` | — |
| 13 — Avance, calidad y evidencias | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 14 — Notificaciones | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 15 — Usuarios, roles y segregación | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 16 — Cierres, correcciones y reversión | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 17 — Integraciones | **IMPLEMENTADO Y VALIDADO** | `57a3438ddd931140f12fc417d5ba662dbbaaa315` | — |
| 18 — Identidad, UX, iPhone y PWA | **IMPLEMENTADO Y VALIDADO** | `37d5d996b16871b30b498e19bd44cb08e791d0cc` | — |
| 19 — Certificación integral | **IMPLEMENTADO Y VALIDADO** | `dc446ad4822b9753a42e17bc298cda80f0be48dc` | — |
| 20 — Infraestructura, backup y publicación | **IMPLEMENTADO Y VALIDADO** | `dc446ad4822b9753a42e17bc298cda80f0be48dc` | — |

## Certificación final de Fases 2 y 3

El SHA funcional `37d5d996b16871b30b498e19bd44cb08e791d0cc` aprobó en el mismo árbol:

- `NEXORA app`, incluidos contratos, instalación, desinstalación, reinstalación y rollback;
- navegador Frappe real en escritorio Chromium e iPhone WebKit;
- PWA, manifiesto, service worker, caché seguro y modo sin conexión;
- dashboard, rutas canónicas y acciones rápidas de ingreso y gasto;
- invariantes financieras MariaDB, concurrencia, idempotencia y rollback;
- gobierno del repositorio, inventario canónico, linters y Semantic Commits;
- validación de producción y suite Patch.

El PR #15 fue fusionado sin bypass mediante squash. La integración inicial resultante fue `718633009014234fcb183d3c33695f238871e056`.

## Criterios de integridad

- No se desactivaron workflows, pruebas, linters ni controles de seguridad.
- No se añadieron `continue-on-error` ni exclusiones artificiales para ocultar defectos.
- Los mensajes transitorios de Socket.IO solo se clasifican cuando la conexión final y la sesión continúan verificadas.
- Semgrep permanece obligatorio y usa comparación diferencial tanto en pull requests como en integraciones a `main`.
- La línea base documental debe ser ancestro de `main`; no se exige que un SHA histórico sea idéntico al commit nuevo.
- El inventario canónico se genera mediante `scripts/generate_file_inventory.py`.

## Evidencia detallada

La evidencia histórica y funcional permanece distribuida en:

- `docs/nexora/MATRIZ_REQUISITOS.md`;
- `docs/nexora/CATALOGO_MAQUINAS_ESTADO.md`;
- `docs/nexora/CATALOGO_CONTROLES.md`;
- `docs/nexora/DECISIONES.md`;
- `docs/nexora/BLOQUE_*.md`;
- `docs/final/NEXORA_MATRIZ_FINAL_CUMPLIMIENTO.md`;
- artefactos de GitHub Actions asociados a los SHA certificados.
