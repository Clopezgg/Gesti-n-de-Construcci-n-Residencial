# NEXORA — Bloque 5: Directorio Universal de Entidades

## Estado

- Rama: `nexora-continuidad-total`.
- PR apilado: `#12`.
- Base certificada del Bloque 4: `96ff830ac174484959a5760a9a4d0284cb5bcdd6`.
- Estado funcional: **IMPLEMENTADO Y VALIDADO** en `e8c8278a88eadf177252631e032ac5009b1d5be0`.
- Certificación funcional: seis workflows obligatorios verdes sobre ese mismo SHA.
- Infraestructura externa utilizada: **NO**.
- Datos históricos migrados: **NO**.

## Requisitos propietarios

| Requisito | Estado | Implementación trazable | Evidencia requerida |
|---|---|---|---|
| `NXR-ENT-0001` — Directorio Universal de Entidades | IMPLEMENTADO Y VALIDADO | `NXR Entity`, servicios y página `/app/nexora-entities` | instalación, UI, permisos, pruebas runtime y SHA |
| `NXR-ENT-0002` — Identificadores y contactos | IMPLEMENTADO Y VALIDADO | tablas protegidas, cifrado Password, máscara y huella normalizada | persona, empresa, identificadores y contactos en MariaDB |
| `NXR-ENT-0003` — Roles múltiples y vigentes | IMPLEMENTADO Y VALIDADO | `NXR Entity Role`, vigencias, estados y rechazo de superposición | pruebas positivas, negativas y permisos |
| `NXR-ENT-0004` — Detección de duplicados | IMPLEMENTADO Y VALIDADO | coincidencia por identificador, usuario, contacto y nombre normalizado | prevención exacta, candidatos y concurrencia |
| `NXR-ENT-0005` — Consolidación no destructiva | IMPLEMENTADO Y VALIDADO | expediente de consolidación, huella, destino canónico y conservación del origen | referencias preservadas, redirección y auditoría |
| `NXR-ENT-0006` — Estado de cumplimiento | IMPLEMENTADO Y VALIDADO | `NXR Entity Compliance` y evidencia validada | transiciones, evidencia, permisos y auditoría |
| `NXR-ENT-0007` — Acceso restringido a datos sensibles | IMPLEMENTADO Y VALIDADO | permisos server-side, máscaras y lectura sensible separada | prueba de visor denegado y auditor autorizado |
| `NXR-ENT-0008` — Administradores como entidades y usuarios separados | IMPLEMENTADO Y VALIDADO | entidad, usuario vinculado y rol de directorio independientes | contrato de modelo, roles múltiples y vínculo único |

## Modelo de datos

- `NXR Entity`: persona u organización, número global, estado, nombre, país, usuario vinculado y destino canónico.
- `NXR Entity Identifier`: tipo, valor protegido, máscara, huella global, principal y vigencia.
- `NXR Entity Contact`: tipo, valor protegido, máscara, huella, verificación y vigencia.
- `NXR Entity Role`: rol, proyecto opcional, período, estado, asignador y revisor.
- `NXR Entity Compliance`: tipo de cumplimiento, período, evidencia, estado y revisión.
- `NXR Entity Consolidation`: origen, destino, motivo, huella del expediente y actor.

## Reglas operativas

1. Toda alta inicia en `Draft` y se activa mediante servicio autorizado.
2. Una persona o empresa activa requiere identificador, contacto o usuario vinculado.
3. Los identificadores exactos son únicos globalmente por huella normalizada.
4. Un usuario no puede vincularse simultáneamente a dos entidades no consolidadas.
5. Los contactos se comparan por huella y solo se exponen enmascarados a lectores ordinarios.
6. Una entidad admite múltiples roles, pero no períodos superpuestos para el mismo rol, proyecto y entidad.
7. El cumplimiento vigente o exceptuado requiere evidencia `NXR Evidence` validada.
8. Consolidar no mueve ni elimina identificadores, contactos, roles, cumplimiento u otras referencias del origen.
9. Toda consulta puede resolver una entidad consolidada hacia su destino canónico y conserva la cadena.
10. Las entidades inactivas o consolidadas son terminales e inmutables.

## Permisos

- lectura enmascarada: roles con acceso NEXORA;
- lectura sensible: System Manager, NEXORA Administrator, Finance Manager y Auditor;
- alta y actualización: operadores o superior;
- estados, roles, cumplimiento y consolidación: gerente o administrador;
- toda validación se repite en servidor; la UI no concede permisos.

## Interfaz

La página `/app/nexora-entities` ofrece:

- alta de personas y empresas;
- identificador, contacto, país y usuario vinculado;
- búsqueda por número, nombre, identificador, contacto y rol;
- detección de candidatos duplicados;
- expediente enmascarado;
- estados, roles y vigencias;
- cumplimiento y evidencia;
- consolidación hacia la entidad canónica;
- redirección visible sin alterar el original.

## Pruebas previstas

### Puras

- normalización de nombres, RTN, pasaporte, correo, teléfono y WhatsApp;
- máscaras y huellas;
- estados y transiciones;
- períodos y superposición;
- puntuación de duplicados;
- ciclos de consolidación.

### Contractuales

- seis DocTypes y controladores;
- Password y permlevel para campos sensibles;
- servicios, permisos y API pública;
- página y workspace;
- workflows permanentes con pruebas del Directorio.

### Runtime Frappe/MariaDB

- personas y empresas;
- identificadores, contactos y búsqueda universal;
- idempotencia;
- roles múltiples, vigencia y superposición negativa;
- duplicados exactos y candidatos;
- usuario vinculado único bajo concurrencia;
- lectura sensible positiva y negativa;
- cumplimiento con evidencia validada;
- consolidación, redirección y preservación de referencias;
- auditoría;
- instalación, migración, desinstalación, reinstalación y rollback.

## Criterio de terminado

El Bloque 5 solo podrá marcarse **IMPLEMENTADO Y VALIDADO** cuando:

1. toda la implementación esté publicada;
2. el checkout remoto corresponda al SHA informado;
3. pruebas puras, contractuales y runtime aprueben;
4. instalación, migración, desinstalación, reinstalación y rollback aprueben;
5. permisos y campos sensibles estén probados en servidor;
6. consolidación y referencias estén demostradas;
7. concurrencia e idempotencia aprueben;
8. pre-commit y Semgrep aprueben;
9. los seis workflows obligatorios estén verdes sobre un único SHA;
10. matriz, `EXECUTION_STATE.md` y PR #12 registren runs, jobs, artefactos y SHA.


## Certificación funcional del Bloque 5

SHA funcional certificado:

`e8c8278a88eadf177252631e032ac5009b1d5be0`

| Workflow | Run ID | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30067357060` | `89400831695` | APROBADO |
| NEXORA app | `30067357041` | `89400831546`, `89400831600` | APROBADO |
| NEXORA financial invariants | `30067357258` | `89400832271` | APROBADO |
| Linters | `30067357076` | `89400831735`, `89400831705` | APROBADO |
| Semantic Commits | `30067357091` | `89400831750` | APROBADO |
| Documentation Required | `30067357068` | `89400831667` | APROBADO |

### Evidencia runtime Frappe v15 / MariaDB 10.6

- instalación y migración limpia: **APROBADAS**;
- desinstalación, reinstalación y rollback: **APROBADOS**;
- 44 pruebas contractuales y 53 pruebas puras: **APROBADAS**;
- integración financiera: 9 pruebas **APROBADAS**;
- integración de Libro Central: 8 pruebas **APROBADAS**;
- integración de evidencia: 4 pruebas **APROBADAS**;
- integración del Directorio: 5 pruebas **APROBADAS**;
- concurrencia financiera: exactamente una operación ejecutada y una denegada: **APROBADA**;
- concurrencia del usuario vinculado: `created` + `denied_duplicate_user`, conteo final 1: **APROBADA**;
- seed doble y salud del staging efímero: **APROBADOS**.

### Artefactos

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8586714930` | `sha256:74b34c1759f1365d4f0a4b1172bf567bd97e021abff217da47b53059fae1a09b` |
| Aplicación, instalación y rollback | `8586775690` | `sha256:365eea44c90e7d172ee274454045a56c96dfa7f5dbe37ce16b04f60365057081` |
| Runtime financiero y Directorio | `8586795376` | `sha256:8bedbaad792e12439c77f1c0af0441340b9eb62f915ec80c75a3b8e6a9d8801b` |
| Pre-commit / Linters | `8586728726` | `sha256:1a62257b244d1a3c9461b7db676508e9867bafb9a0d0b4f387eff76c407acab3` |
| Semgrep | `8586719885` | `sha256:a42726ac07709dc0d10be6ab1130a576f59e43267f6d8523390d651065bdfb52` |

Inventario canónico: `5069` archivos; digest `sha256:265654e417fc41db50ff8175cc591b3b2177a3fd880ad38c53db5ada2d44cda9`.
