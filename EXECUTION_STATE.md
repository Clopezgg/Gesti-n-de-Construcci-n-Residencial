# NEXORA — Estado de ejecución

- Última actualización: 2026-07-24
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama de base certificada: `nexora-reconstruccion`
- PR de base: `#11` — abierto y sin fusionar
- SHA certificado de Bloques 0–3: `83305b6e2bd897e4084d0ae694e94834e2622590`
- Rama de continuidad: `nexora-continuidad-total`
- PR apilado de continuidad: `#12` — abierto y sin fusionar
- Base exacta del PR #12: `83305b6e2bd897e4084d0ae694e94834e2622590`
- SHA certificado del Bloque 4: `96ff830ac174484959a5760a9a4d0284cb5bcdd6`
- SHA funcional certificado del Bloque 5: `e8c8278a88eadf177252631e032ac5009b1d5be0`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- AWS, Coolify o DNS creados: **NO**
- Credenciales externas utilizadas: **NO**
- `main` modificado o fusionado: **NO**
- Datos históricos migrados: **NO**
- Bloque 5 certificado funcionalmente: **SÍ**
- Bloque 6 iniciado: **NO**

## Base certificada conservada

Los Bloques 0–3 permanecen certificados en el SHA inmutable `83305b6e2bd897e4084d0ae694e94834e2622590`. El PR #11 no fue fusionado, cerrado, reescrito ni usado para agregar funciones nuevas.

El desarrollo posterior se ejecuta exclusivamente en la rama `nexora-continuidad-total` y en el PR apilado #12 contra `nexora-reconstruccion`.

## Estado oficial por bloque

- Bloque 0: **IMPLEMENTADO Y VALIDADO**.
- Bloque 1: **IMPLEMENTADO Y VALIDADO**.
- Bloque 2: **IMPLEMENTADO Y VALIDADO**.
- Bloque 3: **IMPLEMENTADO Y VALIDADO**.
- Bloque 4: **IMPLEMENTADO Y VALIDADO**.
- Bloque 5: **IMPLEMENTADO Y VALIDADO**.
- Bloques 6–20: **NO INICIADOS** en este checkpoint.

## Bloque 4 — requisitos cerrados

| Requisito | Estado | Evidencia funcional |
|---|---|---|
| `NXR-LCO-0007` — Inmutabilidad del ejecutado | **IMPLEMENTADO Y VALIDADO** | `NXR Operation` impide editar campos canónicos y eliminar documentos ejecutados; las correcciones avanzan mediante estados compensatorios y documentos nuevos. |
| `NXR-DOC-0004` — Artefacto verificable de evidencia WhatsApp | **IMPLEMENTADO Y VALIDADO** | `NXR Evidence` conserva archivo privado, SHA-256, versión, sustitución, revisión, idempotencia, auditoría y metadatos verificables del canal WhatsApp. |

La matriz oficial `docs/nexora/MATRIZ_REQUISITOS.md` conserva sus 166 requisitos y registra estas dos filas como **IMPLEMENTADO Y VALIDADO** con SHA y evidencia explícitos en cada criterio verificable.

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
6. El validador de gobierno exigió la palabra explícita `evidencia` en cada requisito `IMPLEMENTADO Y VALIDADO`; el criterio de `NXR-LCO-0007` fue precisado sin modificar la regla ni la implementación.

## Restricciones conservadas

- Sin despliegue externo intermedio.
- Sin AWS, Coolify, DNS o costos.
- Sin credenciales reales.
- Sin integraciones reales.
- Sin modificación de producción.
- Sin migración de registros históricos.
- Sin fusión o reescritura del PR #11.
- Sin modificación de `main`.

## Bloque 5 — Directorio Universal de Entidades

### Requisitos cerrados

`NXR-ENT-0001` a `NXR-ENT-0008` quedan **IMPLEMENTADOS Y VALIDADOS** con evidencia de modelos, servicios, interfaz, permisos server-side, pruebas positivas y negativas, runtime MariaDB, auditoría, idempotencia, consolidación y concurrencia.

### SHA funcional certificado

`e8c8278a88eadf177252631e032ac5009b1d5be0`

| Workflow | Run ID | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30067357060` | `89400831695` | APROBADO |
| NEXORA app | `30067357041` | `89400831546`, `89400831600` | APROBADO |
| NEXORA financial invariants | `30067357258` | `89400832271` | APROBADO |
| Linters | `30067357076` | `89400831735`, `89400831705` | APROBADO |
| Semantic Commits | `30067357091` | `89400831750` | APROBADO |
| Documentation Required | `30067357068` | `89400831667` | APROBADO |

### Resultado runtime

- instalación, migración limpia, desinstalación, reinstalación y rollback: **APROBADOS**;
- permisos server-side y campos sensibles: **APROBADOS**;
- personas, organizaciones, identificadores, contactos, múltiples roles y vigencias: **APROBADOS**;
- prevención y detección de duplicados, búsqueda universal y cumplimiento con evidencia: **APROBADOS**;
- consolidación no destructiva, resolución canónica y preservación de referencias: **APROBADOS**;
- auditoría e idempotencia: **APROBADAS**;
- concurrencia financiera y del usuario vinculado con conexiones independientes: **APROBADA**;
- pre-commit y Semgrep: **APROBADOS**.

### Artefactos funcionales

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8586714930` | `sha256:74b34c1759f1365d4f0a4b1172bf567bd97e021abff217da47b53059fae1a09b` |
| Aplicación / instalación / rollback | `8586775690` | `sha256:365eea44c90e7d172ee274454045a56c96dfa7f5dbe37ce16b04f60365057081` |
| Runtime financiero y Directorio | `8586795376` | `sha256:8bedbaad792e12439c77f1c0af0441340b9eb62f915ec80c75a3b8e6a9d8801b` |
| Pre-commit | `8586728726` | `sha256:1a62257b244d1a3c9461b7db676508e9867bafb9a0d0b4f387eff76c407acab3` |
| Semgrep | `8586719885` | `sha256:a42726ac07709dc0d10be6ab1130a576f59e43267f6d8523390d651065bdfb52` |

Inventario canónico: `5069` archivos; digest `sha256:265654e417fc41db50ff8175cc591b3b2177a3fd880ad38c53db5ada2d44cda9`.

## Siguiente acción

Verificar los seis workflows obligatorios sobre el SHA del checkpoint documental final. Después registrar la certificación final en el cuerpo del PR #12. El siguiente bloque oficial es el **Bloque 6 — Contratistas, contratos, adendas, anticipos, pagos, retenciones y liquidación**, pero no debe iniciarse dentro de este cierre.

## Bloque 6 — checkpoint de implementación contractual

- Base certificada utilizada: `e04086e590641ac30ab6dad50b959a307a0393b8`.
- Estado: **EN EJECUCIÓN / NO DEMOSTRADO**.
- Bloque 7 iniciado: **NO**.
- Modelos añadidos: perfil de contratista, contrato, líneas, documentos, adendas, estimaciones y movimientos contractuales.
- Reutilización: `NXR Entity`, resolución canónica, roles, evidencias, fuentes, Libro Central, secuencias, idempotencia, auditoría, locks y permisos.
- Pruebas locales aprobadas antes del checkpoint: validadores de gobierno/app/modelos, 49 contratos, 59 pruebas puras, compilación Python y comprobación JavaScript.
- Evidencia todavía requerida: instalación/migración Frappe, rollback, runtime contractual, concurrencia y seis workflows verdes sobre un único SHA.
- Restricciones conservadas: `main` intacto; PR #11 y #12 abiertos; producción, AWS, Coolify, DNS, credenciales y datos históricos sin cambios.
