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
| 1 · Experiencia | Recorrer las ocho operaciones del Capítulo 53 | El recorrido cubre crear, anular y corregir; editar, consultar, aprobar, rechazar y exportar no se recorren todavía |
| 2 · Integridad financiera | Huella canónica versionada en la reserva de la clave de idempotencia | Hoy el replay compara campos persistidos; la forma correcta es guardar la huella completa al reservar y compararla antes de devolver la respuesta |
| 3 · Confiabilidad | `Patch Test` en rojo sin causa nombrada | El registro solo devuelve la cola, ocupada por el volcado del contenedor de MariaDB. Sin causa identificable no se corrige a ciegas (Capítulo 51) |

## Cerrado con evidencia

- **Recorrido completo en escritorio, tableta, iPhone y PWA** (Capítulo 54): ejecución
  `31032214468` sobre `c96ced6a`, trece etapas en verde en los tres perfiles. El recibo de
  certificación previa al despliegue —que espera a los nueve controles obligatorios—
  también cerró en verde sobre ese mismo commit.

## Esperando una decisión del responsable

Ninguno de estos puntos se toca sin autorización explícita (Capítulos 5 y 55).

- **27 ramas remotas abandonadas** (`copilot/*`, `fix/remediation-*`, `codex/*`,
  `jules-*`, `Clopezgg-patch-*`, `revert-35-*`). Hay que revisar el contenido de cada una
  antes de borrar nada: una rama con trabajo útil no se borra por impulso.
- **`OPENAI_API_KEY` de `cr-gpt[bot]`**: o se configura en el repositorio o se desinstala
  la aplicación. Comenta en cada PR pidiendo una clave que nadie le ha dado.

## Cómo se actualiza

Al cerrar un bloque se retira su fila; al descubrir un defecto que no se corrige en el
momento, se añade con su prioridad del Capítulo 64 y el motivo real de no corregirlo
ahora. Una hoja de ruta que no cambia cuando cambia el producto es decoración.
