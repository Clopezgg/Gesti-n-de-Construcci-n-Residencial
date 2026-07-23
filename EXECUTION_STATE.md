# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial y actual de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD remoto verificado antes de este cierre: `d8f6ba1dbc2afbb425c26917f07f7dc499ab6cfe`
- Rama respecto de `main`: 12 commits adelante, 0 atrás antes del commit de cierre
- Producción modificada: **NO**
- Rama `main` modificada: **NO**
- Migración histórica: **NO**
- Pull Request abierto: **NO**

## Estado del entorno de ejecución

El entorno temporal ya no conserva un checkout Git ni archivos locales de la ejecución técnica. Por tanto:

- `git status` local no es ejecutable porque no existe un directorio `.git` persistente;
- no existen cambios locales recuperables o pendientes de publicación;
- el estado remoto es la única fuente vigente;
- no se clonó nuevamente, no se ejecutó reset, clean ni checkout destructivo.

## Estado de CI

- No existe Pull Request para `nexora-reconstruccion`.
- No existen comprobaciones de CI asociadas visibles para el HEAD remoto.
- El archivo marcador `docs/nexora/CI_FINANCIAL_LATEST.md` no existe.
- En consecuencia, las pruebas Frappe/MariaDB, instalación, desinstalación, concurrencia y rollback definidas en los workflows se clasifican como **NO DEMOSTRADAS / NO EJECUTABLES DESDE EL ENTORNO ACTUAL**.
- No se realizará más polling de CI durante esta ejecución.

## Bloques

### Bloque 0 — Gobierno técnico ejecutable

**TERMINADO Y PUBLICADO**

- Baseline concisa en repositorio.
- 166 identificadores conservados con propietario primario.
- Catálogos de máquinas, controles y decisiones.
- Validador reproducible y workflow de gobierno.
- Commit principal: `2814acfc655cfbb470e96614cbbc06651023649a`.

### Bloque 1 — Aplicación Frappe NEXORA

**PARCIAL Y PUBLICADO**

Terminado:

- aplicación Frappe separada dentro del mismo repositorio;
- hooks, fixtures, roles, workspace, identidad y assets;
- instalación y rollback codificados;
- convivencia sin eliminar ConstruControl;
- pruebas contractuales y compilación local registradas como aprobadas.

Pendiente para terminado:

- instalación, migración, desinstalación y reinstalación ejecutadas sobre sitio Frappe/MariaDB real con evidencia verificable.

Commit principal: `4335c3aaa9bb3f629d2d3198e3309b5d95b86c56`.

### Bloque 2 — Núcleo financiero base

**PARCIAL Y PUBLICADO**

Terminado:

- DocTypes canónicos de secuencia, fuente, operación, efecto, asignación, compromiso, idempotencia y auditoría;
- numeración global de 12 dígitos;
- motor financiero determinístico;
- vista previa y ejecución con reglas compartidas;
- asignación multifuente, compromisos, devolución real y reclasificación;
- locks estables, savepoint, rollback e idempotencia implementados;
- permisos server-side y escritura obligatoria mediante orquestador NEXORA;
- interfaz mínima conectada a servicios reales;
- 33 pruebas locales puras/contractuales registradas como aprobadas;
- validadores, `node --check` y `compileall` registrados como aprobados.

Pendiente para terminado:

- suite Frappe/MariaDB real;
- dos conexiones concurrentes reales;
- rollback real después de la segunda asignación;
- instalación y convivencia verificadas en sitio;
- artefactos o logs CI asociados al SHA probado.

Commits principales: `fc60faf678a01c6aac0e5224e45f552352b0b1e6`, `64c3467d173983d4ed77fef39fcbb0d2f6f3eb16` y `87b3e877b6209dce96524c39b66243478cbe42c8`.

## Commits publicados en la ejecución

1. `2814acfc655cfbb470e96614cbbc06651023649a` — `docs(nexora): establish executable governance baseline`
2. `4335c3aaa9bb3f629d2d3198e3309b5d95b86c56` — `feat(nexora): create installable frappe application`
3. `fc60faf678a01c6aac0e5224e45f552352b0b1e6` — `feat(nexora): add canonical financial document models`
4. `64c3467d173983d4ed77fef39fcbb0d2f6f3eb16` — `feat(nexora): implement atomic multi-source fund allocation`
5. `87b3e877b6209dce96524c39b66243478cbe42c8` — `test(nexora): prove financial invariants and rollback`
6. `c4c219ae9c16726a18658e9de43c2c94edcbac12` — `ci(nexora): publish financial certification evidence`
7. `20820e22cf748a0c57b57b2c0a9fa1a82981390c` — `fix(ci): test clean rollback before financial operations`
8. `3c9dc749308dfefeead925b0ff637d635a9bbf6c` — `fix(nexora): normalize financial validation errors`
9. `cb9cda8b67729e2df2e0e7d8b00248725f917116` — `fix(nexora): make concurrency probe self-contained`
10. `fd84a209bb4665f9b194c9a49adf452014ae0bdc` — `fix(nexora): enforce orchestrated operation writes`
11. `381d997d3da2868a9ef75b38f9b7ea22e5854906` — `fix(nexora): require orchestrator for canonical writes`
12. `d8f6ba1dbc2afbb425c26917f07f7dc499ab6cfe` — `test(nexora): reject direct canonical writes`

## Errores y bloqueos reales

- Error operativo: la ejecución quedó esperando un marcador CI que nunca apareció.
- Causa comprobada: no existe Pull Request y el conector no expone una ejecución asociada al HEAD; el marcador de certificación tampoco existe.
- Bloqueo actual: no hay checkout ni sitio Frappe/MariaDB persistente para ejecutar las pruebas runtime pendientes desde este entorno.
- Este bloqueo no afecta el código publicado, pero impide clasificar Bloques 1 y 2 como terminados y validados.

## Siguiente acción exacta

1. Crear el único Pull Request de `nexora-reconstruccion` hacia `main`, sin fusionarlo.
2. Ejecutar y revisar los workflows Frappe/MariaDB de instalación, rollback, concurrencia e invariantes financieras.
3. Corregir cualquier fallo en la misma rama y registrar los SHA y artefactos.
4. Cuando Bloques 1 y 2 tengan evidencia runtime aprobada, iniciar el **Bloque 3: Libro Central completo, clasificación económica, centros de costo, tipos operativos y efectos analíticos**.
