# NEXORA — Estado de ejecución

- Última actualización: 2026-07-22
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD de código runtime previo a esta actualización: `5270fac05a648c9bf648a5457a383052e2a38f30`
- Pull Request único: `#11` — abierto y sin fusionar
- Producción modificada: **NO**
- Migración histórica: **NO**

## Recuperación

- La clonación HTTPS local continúa bloqueada por DNS: `Could not resolve host: github.com`.
- GitHub Actions recupera la rama y ejecuta Frappe/ERPNext/MariaDB 10.6 en runners aislados.
- No se usó `main` como árbol de trabajo, no se reescribió historia y no se realizó `force push`.
- `/mnt/data/nexora-block3` es una reconstrucción local no canónica usada únicamente para validar el siguiente bloque; GitHub es la fuente vigente.

## Evidencia runtime acumulada

- Bloque 1 aprobado en run `29972703634`, jobs `89097929904` y `89097929946`:
  - contrato;
  - instalación y migración;
  - fixtures, workspace, roles y permisos;
  - convivencia con ConstruControl;
  - desinstalación, reinstalación y rollback.
- Bloque 2, run `29973490385`, job `89100294549`:
  - gates estáticos — aprobados;
  - instalación limpia — aprobada;
  - convivencia y rollback — aprobados;
  - nueve pruebas financieras Frappe/MariaDB — aprobadas;
  - concurrencia — falló porque el saldo se recalculaba con una lectura consistente anterior a la liberación del lock.
- Artefacto del fallo de concurrencia: `8550632495`, digest `sha256:c441d4a256dc7e9e995627943233bd7edfe2c4d8a37018f26c9bc69555719a65`.
- Commit `5270fac05a648c9bf648a5457a383052e2a38f30` cambia el recálculo ejecutable a una lectura actual `FOR UPDATE` de los efectos canónicos después de bloquear las fuentes y añade una prueba contractual de regresión.
- Este commit humano activa la certificación del árbol corregido.

## Bloques

### Bloque 0 — TERMINADO Y PUBLICADO

Baseline, 166 requisitos, propietarios, máquinas, controles, decisiones y validador reproducible.

### Bloque 1 — TERMINADO Y VALIDADO

Certificación runtime: run `29972703634`; job `89097929946`; SHA `666dbb8b8ad9543235b3e423e72a245e8b9f911f`.
La misma app continúa sin cambios funcionales en el candidato actual y será reconfirmada por el nuevo run.

### Bloque 2 — PARCIAL; CERTIFICACIÓN FINAL EN CURSO

Código terminado:

- DocTypes canónicos y numeración de 12 dígitos;
- fuentes HNL/FX, efectivo y transferencias validadas;
- vista previa y ejecución multifuente;
- sobregiro bloqueado;
- idempotencia, compromisos, devolución y reclasificación;
- permisos server-side y escritura mediante orquestador;
- rollback real de segunda asignación aprobado;
- nueve pruebas MariaDB aprobadas.

Pendiente único:

- aprobar el probe de dos conexiones con el recálculo de saldo bajo lectura actual bloqueada.

## Bloque 3 preparado localmente

- 10 DocTypes canónicos validados;
- 23 tipos oficiales de operación;
- 21 categorías económicas;
- Cuenta Máxima, ahorro, transferencias, otros proyectos, terrenos, propietaria, regalos, donaciones, contribuciones, impuestos, pagos legales, viajes, especiales, anticipos, liquidaciones, reclasificaciones, devoluciones, reversiones y sustituciones;
- 22 pruebas contractuales y 26 pruebas puras aprobadas;
- interfaz mínima conectada al mismo kernel del Bloque 2;
- sin segundo ledger ni escrituras a `CC Material Ledger`.

## Siguiente acción exacta

1. Ejecutar una vez los nuevos runs de aplicación y finanzas sobre este commit humano.
2. Certificar Bloques 1 y 2 si suite y concurrencia aprueban sobre el mismo SHA.
3. Publicar inmediatamente el Bloque 3 en tres commits coherentes y validar su CI en el mismo PR.
