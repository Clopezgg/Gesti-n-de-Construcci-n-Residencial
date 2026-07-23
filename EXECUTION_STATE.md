# NEXORA — Estado de ejecución

- Última actualización: 2026-07-23
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama de base certificada: `nexora-reconstruccion`
- PR de base: `#11` — abierto y sin fusionar
- SHA certificado de Bloques 0–3: `83305b6e2bd897e4084d0ae694e94834e2622590`
- Rama de continuidad: `nexora-continuidad-total`
- PR apilado de continuidad: `#12` — abierto y sin fusionar
- Base exacta del PR #12: `83305b6e2bd897e4084d0ae694e94834e2622590`
- SHA funcional certificado del Bloque 4: `0005b44f19d1483e249e01928de7228b9270ac08`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- AWS, Coolify o DNS creados: **NO**
- Credenciales externas utilizadas: **NO**
- `main` modificado o fusionado: **NO**
- Datos históricos migrados: **NO**
- Bloque 5 iniciado: **NO**

## Base certificada conservada

Los Bloques 0–3 permanecen certificados en el SHA inmutable `83305b6e2bd897e4084d0ae694e94834e2622590`. El PR #11 no fue fusionado, cerrado, reescrito ni usado para agregar funciones nuevas.

El desarrollo posterior se ejecuta exclusivamente en la rama `nexora-continuidad-total` y en el PR apilado #12 contra `nexora-reconstruccion`.

## Estado oficial por bloque

- Bloque 0: **IMPLEMENTADO Y VALIDADO**.
- Bloque 1: **IMPLEMENTADO Y VALIDADO**.
- Bloque 2: **IMPLEMENTADO Y VALIDADO**.
- Bloque 3: **IMPLEMENTADO Y VALIDADO**.
- Bloque 4: **IMPLEMENTADO Y VALIDADO**.
- Bloques 5–20: **NO INICIADOS** en este checkpoint.

## Bloque 4 — requisitos cerrados

| Requisito | Estado | Evidencia funcional |
|---|---|---|
| `NXR-LCO-0007` — Inmutabilidad del ejecutado | **IMPLEMENTADO Y VALIDADO** | `NXR Operation` impide editar campos canónicos y eliminar documentos ejecutados; las correcciones avanzan mediante estados compensatorios y documentos nuevos. |
| `NXR-DOC-0004` — Artefacto verificable de evidencia WhatsApp | **IMPLEMENTADO Y VALIDADO** | `NXR Evidence` conserva archivo privado, SHA-256, versión, sustitución, revisión, idempotencia, auditoría y metadatos verificables del canal WhatsApp. |

La matriz oficial `docs/nexora/MATRIZ_REQUISITOS.md` conserva sus 166 requisitos y registra estas dos filas como **IMPLEMENTADO Y VALIDADO** con referencia al SHA funcional certificado.

## Implementación del Bloque 4

### Dominio y modelo de datos

- DocType canónico `NXR Evidence`.
- Numeración global de 12 dígitos.
- Máquina `Uploaded → Validated/Rejected → Superseded`.
- Contenido canónico inmutable.
- Sustitución no destructiva con incremento de versión.
- Hash SHA-256 calculado en servidor.
- Archivo privado obligatorio para expedientes canónicos.
- Idempotencia, huella de payload y correlación.

### Servicios

- `register_evidence`: carga, validación de archivo, numeración, hash, versión, auditoría y rollback.
- `review_evidence`: validación o rechazo con permiso gerencial, actor, fecha, notas, idempotencia y auditoría.
- `list_evidence`: consulta autorizada con filtro de proyecto y límite de resultados.
- Política integrada en `prepare_central_payload` antes de ejecutar operaciones.

### Política aplicada

- depósito y transferencia requieren evidencia;
- efectivo hasta L2,000.00 es opcional salvo regla especial;
- efectivo desde L2,000.01 requiere evidencia;
- regalos, donaciones, contribuciones y pagos especiales exigen autorización externa;
- autorización externa exige expediente validado con canal WhatsApp, autorizador, fecha y referencia;
- comprobantes privados ordinarios de Bloques 0–3 conservan compatibilidad;
- una ruta privada suelta no satisface una autorización especial.

### Permisos y auditoría

- operadores financieros pueden registrar evidencia;
- gerentes, administradores NEXORA y System Manager pueden revisar;
- usuarios limitados no pueden revisar;
- DocType sin creación, escritura o eliminación directa;
- carga y revisión generan `NXR Audit Event`;
- acciones desconocidas o roles insuficientes se rechazan en servidor.

### Interfaz

- página real `/app/nexora-evidence`;
- registro de archivo y metadatos;
- consulta de número, estado, versión y SHA-256;
- revisión gerencial;
- sustitución sin alterar el original;
- accesos desde el workspace NEXORA.

## Pruebas ejecutadas

### Estáticas, puras y contractuales

- validadores de gobierno, app y modelos: **APROBADOS**;
- 36 pruebas contractuales: **APROBADAS**;
- 43 pruebas puras: **APROBADAS**;
- política de evidencia y umbral exacto: **APROBADOS**;
- máquina de estados y SHA-256: **APROBADOS**;
- contratos de modelo, servicios, UI e inmutabilidad: **APROBADOS**;
- `node --check`: **APROBADO**;
- `python -m compileall`: **APROBADO**;
- pre-commit: **APROBADO**;
- Semgrep: **APROBADO**.

### Runtime Frappe v15 / MariaDB 10.6

- instalación y migración limpia: **APROBADAS**;
- fixtures, workspace, roles y DocTypes: **APROBADOS**;
- desinstalación, reinstalación y rollback: **APROBADOS**;
- archivo privado real y hash: **APROBADOS**;
- registro idempotente y auditoría: **APROBADOS**;
- permiso negativo de revisión: **APROBADO**;
- revisión gerencial: **APROBADA**;
- autorización especial no validada rechazada: **APROBADO**;
- autorización WhatsApp validada aceptada: **APROBADO**;
- ruta privada no registrada rechazada para regla especial: **APROBADO**;
- sustitución conserva original e incrementa versión: **APROBADO**;
- edición y eliminación del ejecutado rechazadas: **APROBADO**;
- invariantes financieras preexistentes: **APROBADAS**;
- concurrencia con conexiones independientes: **APROBADA**;
- seed demostrativo doble y salud: **APROBADOS**.

## Certificación del SHA funcional del Bloque 4

Los seis workflows obligatorios quedaron verdes sobre exactamente:

`0005b44f19d1483e249e01928de7228b9270ac08`

| Workflow | Run | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30048885103` | registro del workflow | APROBADO |
| NEXORA app | `30048884907` | `89346321570`, `89346321627` | APROBADO |
| NEXORA financial invariants | `30048884988` | `89346321685` | APROBADO |
| Linters | `30048885098` | `89346322109`, `89346322125` | APROBADO |
| Semantic Commits | `30048884906` | registro del workflow | APROBADO |
| Documentation Required | `30048884912` | registro del workflow | APROBADO |

## Artefactos del Bloque 4

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8580213584` | `sha256:0ad11dece7f4e4793800f822084291f379cb49c947c2ce1d59db3519a03e63d0` |
| Aplicación, instalación y rollback | `8580295286` | `sha256:91fa10ceb0de21455fc1137858bf7594e65ab3403008457ea413de530e54876e` |
| Invariantes financieras y evidencia | `8580329294` | `sha256:dbbd94a965851928b1a9a7df3d6908421abbba77b0f27f6d838ac01fefb2c90d` |
| Pre-commit / Linters | `8580231710` | `sha256:121b7359dd3064cd3355b20ae242f61d3b6bf172fe8aec0f9fb965d9013e0b51` |
| Semgrep | `8580218457` | `sha256:ff3f5444c2c23b580f8d70d6d651704b408d643e5c972aad2c238fa8f8925b46` |

## Inventario canónico

- Archivos rastreados: `5028`.
- Digest canónico: `sha256:0b81daf85908174d4aec869b7a95091d9aa29ea4ef80df025f6b3638dc8f3856`.
- El inventario es regenerado por el workflow permanente y debe producir diff vacío.

## Fallos corregidos durante el Bloque 4

1. El primer fixture runtime usaba un literal `bytes` con caracteres no ASCII y fallaba antes de ejecutar pruebas.
2. Un fixture fingía ser PDF sin contenido PDF válido; Frappe lo rechazó correctamente y la prueba pasó a utilizar texto permitido.
3. Pre-commit exigió formato en siete archivos y luego un ajuste final de una llamada; se aplicaron exactamente los parches del runner.
4. Documentation Required exigía una referencia oficial en el cuerpo del PR #12; se añadió documentación oficial de Frappe.
5. El inventario canónico cambió de 5016 a 5028 archivos por los componentes reales del Bloque 4 y fue regenerado por CI.

## Restricciones conservadas

- Sin despliegue externo intermedio.
- Sin AWS, Coolify, DNS o costos.
- Sin credenciales reales.
- Sin integraciones reales.
- Sin modificación de producción.
- Sin migración de registros históricos.
- Sin fusión o reescritura del PR #11.
- Sin modificación de `main`.

## Siguiente acción

Verificar los seis workflows obligatorios sobre el SHA del checkpoint documental que contiene este estado y la matriz actualizada. Solo después iniciar el Bloque 5 — Directorio Universal de Entidades — en el mismo PR apilado #12.
