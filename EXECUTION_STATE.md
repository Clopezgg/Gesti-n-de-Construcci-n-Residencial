# NEXORA — Estado de ejecución

- Última actualización: 2026-07-24
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama base certificada: `nexora-reconstruccion`
- PR base: `#11` — abierto y sin fusionar
- Rama de continuidad: `nexora-continuidad-total`
- PR de continuidad: `#12` — abierto y sin fusionar
- Base exacta del PR #12: `83305b6e2bd897e4084d0ae694e94834e2622590`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- AWS, Coolify o DNS creados: **NO**
- Credenciales externas utilizadas: **NO**
- Datos históricos migrados: **NO**

## Estado oficial por bloque

| Bloque | Estado | SHA funcional certificado |
|---:|---|---|
| 0–3 | **IMPLEMENTADO Y VALIDADO** | `83305b6e2bd897e4084d0ae694e94834e2622590` |
| 4 — Evidencia e inmutabilidad | **IMPLEMENTADO Y VALIDADO** | `96ff830ac174484959a5760a9a4d0284cb5bcdd6` |
| 5 — Directorio Universal de Entidades | **IMPLEMENTADO Y VALIDADO** | `e8c8278a88eadf177252631e032ac5009b1d5be0` |
| 6 — Contratistas y contratos | **IMPLEMENTADO Y VALIDADO** | `3d2b65792b149d5ad915e7b1aec64423b3b048f0` |
| 7 — Compras y proveedores | **NO INICIADO** | — |
| 8–20 | **NO INICIADOS** | — |

## Bloque 6 — certificación funcional

Los requisitos `NXR-CON-0001` a `NXR-CON-0012` están implementados y validados en el SHA `3d2b65792b149d5ad915e7b1aec64423b3b048f0`.

### Alcance demostrado

- contratista basado exclusivamente en `NXR Entity` y resolución canónica;
- múltiples contratos por entidad;
- modalidades y líneas separadas de mano de obra y materiales;
- adendas versionadas no destructivas;
- anticipos, amortizaciones, estimaciones, pagos, retenciones y devoluciones;
- liquidación contractual y estados terminales;
- expediente cronológico con `NXR Evidence`;
- motor financiero, fuentes y Libro Central reutilizados;
- numeración de 12 dígitos, idempotencia, auditoría, locks y rollback;
- permisos server-side e interfaz real `/app/nexora-contracts`;
- formato Jinja instalado `NEXORA Contract` y acción de impresión/PDF conectada.

### Pruebas aprobadas

- 49 pruebas contractuales estáticas;
- 60 pruebas puras;
- 4 pruebas de integración contractual Frappe/MariaDB;
- instalación, migración limpia, desinstalación, reinstalación y rollback;
- permisos negativos y rechazos de sobreestimación, superposición, adenda inválida y devolución excesiva;
- rollback de pago con fallo inyectado;
- liquidación terminal e inmutabilidad posterior;
- concurrencia con dos conexiones: un pago ejecutado y un sobrepago rechazado;
- pre-commit y Semgrep.

### Workflows del SHA funcional

| Workflow | Run ID | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30117634460` | `89562121818` | APROBADO |
| NEXORA app | `30117634489` | `89562121692`, `89562121707` | APROBADO |
| NEXORA financial invariants | `30117634438` | `89562121557` | APROBADO |
| Linters | `30117634559` | `89562121910`, `89562121930` | APROBADO |
| Semantic Commits | `30117634511` | `89562121923` | APROBADO |
| Documentation Required | `30117634482` | `89562121673` | APROBADO |

### Artefactos

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8606055472` | `sha256:a39ed33a0dfe6ed98417279ca3c79a051f2d3e92e0543a436c8282e1ad338a66` |
| Aplicación, instalación y rollback | `8606171543` | `sha256:7cf12d367d7c202f135676749cbfa3b2b5f522bd7004edd8508ba6ad285949c8` |
| Runtime financiero, contractual y concurrencia | `8606196349` | `sha256:2321f2c24a751a179b753a8b6e0195333f94ed75b7db350ea0866c12d769f612` |
| Pre-commit / Linters | `8606078373` | `sha256:6d46a2d70286abad49874fabd5ba6fbe65e9f417d2f1bc4b6c25b2a2bc44b8b0` |
| Semgrep | `8606068215` | `sha256:1b745063ae253b92ccd12138c6e42789a85051977969c1ffb9949f330e925c1c` |

## Restricciones conservadas

- `main` intacto.
- PR #11 y PR #12 abiertos y sin fusionar.
- Producción, AWS, Coolify, DNS, secretos y credenciales externas sin cambios.
- Cero migración de datos históricos.
- Cero despliegue externo.

## Siguiente acción exacta

Cerrar la matriz y el cuerpo del PR #12 con la evidencia del Bloque 6. Después iniciar el primer checkpoint del Bloque 7: proveedor basado exclusivamente en `NXR Entity`, clasificación, vigencia y cumplimiento, reutilizando evidencia, permisos, idempotencia, auditoría y locks.
