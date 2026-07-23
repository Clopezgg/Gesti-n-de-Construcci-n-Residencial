# NEXORA — Estado de ejecución

- Última actualización: 2026-07-23
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- Pull Request único: `#11` — abierto y sin fusionar
- HEAD inicial de esta corrección: `6a7858d1fbcc0bfe0599c2a27d98ec5c80b9e6a2`
- SHA de código certificado de NEXORA 0.1: `46e0ea37988da1d2bd5d5942ccbd5780173f7de0`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- `main` modificado o fusionado: **NO**
- Datos históricos migrados: **NO**
- Bloques 4–20 iniciados: **NO**

## Alcance cerrado

Esta ejecución estabilizó y certificó exclusivamente los Bloques 0–3 como **NEXORA 0.1**. No se agregaron funciones de bloques futuros, no se crearon workflows temporales, no se publicaron paquetes de transporte y no se modificó producción.

## Fallos causales corregidos

1. El validador de gobierno no reconocía el nombre actualizado del campo documental del HEAD de `main`.
2. Faltaba el paquete Python `nexora.nexora.doctype`; Frappe resolvía controladores NEXORA mediante el módulo predeterminado `Core`.
3. El registro de `nexora` en `sites/apps.txt` no invalidaba la caché de módulos de Frappe.
4. Los catálogos NEXORA se sembraban antes de que Frappe sincronizara los DocTypes canónicos.
5. El seed demostrativo contenía tres patrones bloqueados por Semgrep: cambio global de usuario y control manual de commit/rollback.
6. La creación DDL del contador global se ejecutaba dentro de `after_migrate`, causando `ImplicitCommitError`.
7. Al retirar ese DDL de migración, el contador no existía después de una instalación/reinstalación limpia; quedó creado únicamente en el ciclo seguro `after_install` y prohibido en `after_migrate`.
8. Una integración heredada ejecutaba una reclasificación con importe cero; ahora demuestra que cero se rechaza y que un importe positivo no altera fondos.
9. Una prueba del Libro Central consultaba saldo cambiando al actor operador y no restauraba al gerente antes de una segunda devolución; el servidor rechazaba correctamente la operación. La prueba restaura explícitamente el actor autorizado.

## Regresiones incorporadas

- Los diez DocTypes NEXORA deben declarar `module: NEXORA` y disponer de controlador Python.
- El paquete `nexora.nexora.doctype` es obligatorio.
- Registrar una app nueva en `sites/apps.txt` invalida la caché de módulos del bench.
- `after_install` crea el contador global, pero no siembra catálogos.
- `after_migrate` siembra catálogos, pero no ejecuta DDL del contador.
- La carga demostrativa exige `nexora_staging=1`.
- Los servicios de corrección conservan sus permisos server-side durante todas las aserciones runtime.
- La reclasificación exige importe positivo y permanece neutral en fondos.

## Validaciones dirigidas previas a publicación

- `scripts/validate_nexora_governance.py`: **APROBADO**.
- `scripts/validate_nexora_app.py`: **APROBADO**.
- `scripts/validate_nexora_financial_models.py`: **APROBADO**.
- Pruebas contractuales dirigidas: **31 APROBADAS**.
- Pruebas puras financieras, Libro Central y referencias: **36 APROBADAS**.
- `node --check` de las dos superficies JavaScript: **APROBADO**.
- `python -m compileall`: **APROBADO**.
- Inventario canónico: **5,016 archivos verificados**.
- Digest canónico del inventario: `sha256:71d77c3a2acc59f6c6b10e96451f16a779834756b16aeef7f9bc3f566dc0385a`.
- Semgrep local no pudo instalarse por respuesta externa `503 Service Unavailable`; Semgrep oficial de GitHub quedó verde y es la evidencia autoritativa.

## Certificación del SHA de código

Los seis workflows obligatorios quedaron verdes sobre exactamente:

`46e0ea37988da1d2bd5d5942ccbd5780173f7de0`

| Workflow | Run | Job(s) | Resultado |
|---|---:|---:|---|
| NEXORA governance | `30017859436` | `89242500157` | APROBADO |
| NEXORA app | `30017859461` | `89242499956`, `89242499824` | APROBADO |
| NEXORA financial invariants | `30017862381` | `89242510392` | APROBADO |
| Linters | `30017862513` | `89242510424`, `89242510499` | APROBADO |
| Semantic Commits | `30017859295` | `89242499377` | APROBADO |
| Documentation Required | `30017859515` | `89242500309` | APROBADO |

### Artefactos y digests

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8567919807` | `sha256:839cb11a8c99a5a2fd56629a6ae55d4b25edc0985c236e28b202e6520079c05e` |
| Aplicación, instalación y rollback | `8568074421` | `sha256:1ad0ae1e16f2333548e17dfb87b52546a7f4438b7eeaab5bcbe8eadd9bdf18a8` |
| Invariantes financieras y Libro Central | `8568078004` | `sha256:95f0859b2c00112ceadc0c06601431b3b4e1605e54caafa6379e2010b19b89b3` |
| Pre-commit / Linters | `8567949625` | `sha256:1c470934a4427d8dd62eb62ba752696026ccc0ec44286823a988e48faf1be39c` |
| Semgrep | `8567936162` | `sha256:e97f2664849b4dd80c0630bfcb2aae922f6210103b60eb9d94fe5e41a882371a` |

## Evidencia runtime de NEXORA app

El job `89242499824` demostró sobre MariaDB/Frappe v15:

- instalación limpia;
- migración;
- fixtures y cinco roles NEXORA;
- workspace y página reales;
- convivencia con ERPNext;
- desinstalación limpia;
- reinstalación;
- rollback técnico;
- seed de staging ejecutado dos veces;
- verificación de salud final.

## Evidencia runtime de invariantes financieras

El job `89242510392` demostró:

- instalación limpia sobre MariaDB;
- catálogos, centros de costo y clasificación económica;
- fuentes HNL y moneda extranjera;
- Libro Central y numeración única de 12 dígitos;
- operaciones multifuente;
- compromisos, ejecución y liberación;
- ahorro e inversión;
- transferencias internas neutrales;
- anticipos y liquidaciones;
- devolución real referenciada;
- reclasificación sin movimiento de fondos;
- reversión sin restitución ficticia;
- permisos, segregación y auditoría;
- idempotencia;
- concurrencia con conexiones independientes;
- rollback tras fallo inyectado;
- staging idempotente y salud final.

Resultados runtime dirigidos dentro del workflow:

- integración financiera: **9 pruebas aprobadas**;
- integración del Libro Central: **8 pruebas aprobadas**;
- concurrencia: **APROBADA**;
- seed demostrativo doble: **APROBADO**.

## Entrega visible NEXORA 0.1

- Workspace `NEXORA 0.1`.
- Ruta principal: `/app/nexora-finance`.
- Núcleo de Fondos, alta de fuentes, ingresos y salidas.
- Selección multifuente y saldo independiente por fuente.
- Libro Central e historial cronológico.
- Tipos de operación y clasificación económica.
- Navegación responsiva para escritorio, iPhone y Desk/PWA.
- Datos demostrativos no históricos protegidos por `nexora_staging=1`.

## Estado definitivo de los Bloques 0–3

- Bloque 0: **IMPLEMENTADO Y VALIDADO**.
- Bloque 1: **IMPLEMENTADO Y VALIDADO**.
- Bloque 2: **IMPLEMENTADO Y VALIDADO**.
- Bloque 3: **IMPLEMENTADO Y VALIDADO**.

La evidencia de código corresponde al SHA `46e0ea37988da1d2bd5d5942ccbd5780173f7de0`. El commit que contiene este documento conserva el mismo árbol funcional y constituye el checkpoint documental final; debe mantener verdes los mismos seis workflows antes de cerrar la ejecución.

## Siguiente acción autorizada

Verificar los seis workflows sobre el SHA de este checkpoint documental, actualizar el cuerpo atrasado del PR #11 con ese SHA final y conservar el PR abierto y sin fusionar. **No iniciar Bloque 4.**
