# NEXORA — Hoja de ruta permanente

> Documento vivo exigido por el **Capítulo 63** de [`NEXORA_CONSTITUTION.md`](NEXORA_CONSTITUTION.md).
> No es una lista de módulos por completar: es lo que hoy le falta al producto para que
> una persona pueda trabajar una jornada entera sin fricción (Capítulos 61 y 65).
>
> El orden lo fija el **Capítulo 64** —experiencia, integridad financiera, confiabilidad,
> seguridad, velocidad, coherencia, escalabilidad, rendimiento, arquitectura,
> optimización—, no la comodidad de quien implementa.
>
> Aquí no se copia nada. La deuda registrada vive en
> [`PROJECT_RECONSTRUCTION.md`](PROJECT_RECONSTRUCTION.md) y el histórico de ejecución en
> [`EXECUTION_STATE.md`](EXECUTION_STATE.md); duplicarlos los haría divergir
> (Capítulos 44 y 67).

## Abierto ahora

| Prioridad (Cap. 64) | Bloque | Por qué sigue abierto |
|---|---|---|
| 1 · Experiencia | **Bloque B — carcasa propia** | Código y contratos en verde (344). La carcasa ya no mueve el DOM del marco: la segunda vuelta del recorrido confirmó que ese defecto quedó resuelto, y encontró y corrigió otros dos —vista previa anulada por un blur sin línea base en `correccion` (iPhone) y el manejador de «Continuar» leyendo un estado más estricto que el que pinta el botón en `operaciones` (escritorio)—, documentados en `PROJECT_RECONSTRUCTION.md` (Bloque 33). **El responsable autorizó explícitamente aplazar el cierre en verde del recorrido real (escritorio, iPhone WebKit, PWA) para el final**, y avanzar el resto de la reconstrucción visual (Bloques C y D) sin esperarlo; queda abierto hasta esa certificación pendiente, no como bloqueo del resto del trabajo |
| 1 · Experiencia | **Bloque C — centro de mando** | Cerrado por código: banda de agenda, tarjetas en `nxr-ds-card`, y las tres zonas que el responsable pidió (actividad del equipo, cumplimiento y vencimientos, accesos recientes). 353 contratos en verde. Las dos zonas nuevas con backend (`activity_query.py`, `compliance_query.py`) no se han ejecutado contra un sitio Frappe real —este entorno no tiene uno—; esa certificación queda para el recorrido real, aplazado a propósito hasta el final por decisión del responsable |
| 1 · Experiencia | **Bloque D — sistema de diseño completo** | Las doce pantallas del inventario original usan `nxr-ds-btn` en cada botón (variantes `--sm`, `--danger`, `--success`, `--warning` añadidas según hacía falta). Queda un componente `nxr-ds-table` que no existe todavía: las tablas del marco (`table`, `table-bordered`, `table-sm`) siguen en las doce pantallas, sin diseñar a ciegas sin la validación visual del recorrido real |
| 1 · Experiencia | Recorrer las ocho operaciones del Capítulo 53 | El recorrido ya ejerce las ocho —crear, editar, consultar, aprobar, rechazar, anular, corregir y exportar— sobre las pantallas reales; falta la ejecución en verde que lo demuestre. Escrito no es lo mismo que comprobado (Capítulo 53) |
| 2 · Integridad financiera | Huella canónica versionada en la reserva de la clave de idempotencia | Hoy el replay compara campos persistidos; la forma correcta es guardar la huella completa al reservar y compararla antes de devolver la respuesta |
| 3 · Confiabilidad | `Patch Test` en rojo sin causa nombrada | El registro solo devuelve la cola, ocupada por el volcado del contenedor de MariaDB. Sin causa identificable no se corrige a ciegas (Capítulo 51) |

## Cerrado con evidencia

- **Recorrido completo en escritorio, tableta, iPhone y PWA** (Capítulo 54): ejecución
  `31032214468` sobre `c96ced6a`, trece etapas en verde en los tres perfiles. El recibo de
  certificación previa al despliegue —que espera a los nueve controles obligatorios—
  también cerró en verde sobre ese mismo commit.

## Esperando una decisión del responsable

Ninguno de estos puntos se toca sin autorización explícita (Capítulos 5 y 55).

- **Ramas remotas por borrar**. El responsable ya decidió que solo quede `main`, y su
  contenido está inventariado antes de tocar nada en
  [`docs/architecture/BRANCH_ARCHIVE.md`](docs/architecture/BRANCH_ARCHIVE.md) —nombre,
  SHA completo, commits por delante y orden de restauración—, así que ninguna se pierde.
  **El recuento vive en ese inventario y solo ahí** (hoy, veintinueve): repetir la cifra
  en cada documento vivo garantiza que acaben discrepando, y el borrado depende de ella.
  El borrado no puede ejecutarse desde esta sesión: tanto `git push origin --delete` como
  `DELETE /git/refs/heads/…` devuelven **HTTP 403**, y el cuerpo de la respuesta lo dice
  literalmente: «Write access to this GitHub API path is not permitted through this
  proxy». Es un límite del entorno de ejecución, no del permiso sobre el repositorio: lo
  ejecuta el responsable desde un equipo con acceso directo.
- **`OPENAI_API_KEY` de `cr-gpt[bot]`**: o se configura en el repositorio o se desinstala
  la aplicación. Comenta en cada PR pidiendo una clave que nadie le ha dado.

## Cómo se actualiza

Al cerrar un bloque se retira su fila; al descubrir un defecto que no se corrige en el
momento, se añade con su prioridad del Capítulo 64 y el motivo real de no corregirlo
ahora. Una hoja de ruta que no cambia cuando cambia el producto es decoración.
