# NEXORA — Auditoría por capas y corrección secuencial

## Activación

Este protocolo fue autorizado expresamente mediante la palabra **SIRILAN**. Desde esta autorización, los estados finales escritos en `MATRIZ_REQUISITOS.md` se consideran **afirmaciones documentales**, no certificaciones suficientes.

La certificación real se calcula desde:

1. objetivo original verificable;
2. requisito individual;
3. implementación y componentes relacionados;
4. validaciones obligatorias;
5. evidencia reproducible del mismo SHA completo;
6. defectos abiertos;
7. GitHub Actions del mismo SHA;
8. regresiones de bloques anteriores.

## Fuente original de verdad

Aplicar este orden:

1. objetivo institucional y operativo original de NEXORA;
2. órdenes maestras y decisiones aprobadas;
3. código, migraciones, persistencia, permisos e interfaces reales;
4. pruebas positivas y negativas;
5. `docs/nexora/AUDIT_RESULTS.json`;
6. `docs/nexora/DEFECTS.json`;
7. GitHub Actions, jobs, logs, artifacts y digests del SHA exacto;
8. matriz, checkpoint, estado de ejecución y documentos de bloque.

Cuando un documento contradiga el código o CI, prevalecen el comportamiento reproducible y la evidencia técnica.

## Jerarquía obligatoria

```text
NEXORA
└── Bloques 0–20
    └── Requisitos
        └── Componentes y archivos relacionados
            └── Validaciones
                ├── coincidencia con objetivo original
                ├── implementación real
                ├── prueba positiva
                ├── prueba negativa
                ├── permiso server-side
                ├── seguridad
                ├── integridad financiera
                ├── idempotencia
                ├── concurrencia
                ├── rollback
                ├── instalación/migración
                ├── regresión
                └── evidencia del mismo SHA
```

El progreso nunca se calcula por número de archivos ni por número de commits.

## Estados de auditoría

- `certified`: cumple exactamente y tiene evidencia reproducible.
- `technical_error`: una prueba, migración, workflow, dependencia o ejecución falla.
- `objective_mismatch`: ejecuta, pero no resuelve exactamente el objetivo original.
- `running`: auditoría, corrección o prueba en ejecución.
- `pending`: todavía no auditado o sin evidencia suficiente.
- `blocked`: no puede avanzar por dependencia o bloqueo externo real.
- `decision_required`: requiere una decisión humana funcional auténtica.
- `not_applicable`: no aplica con justificación y evidencia.

Está prohibido convertir automáticamente un estado de matriz en `certified`.

## Ciclo por requisito

```text
DETECTADO
↓
DIAGNOSTICADO
↓
ASIGNADO A OPENCODE
↓
CORRIGIENDO
↓
PRUEBA ESPECÍFICA
↓
PRUEBA NEGATIVA
↓
REGRESIÓN
↓
COMMIT SEMÁNTICO
↓
PUSH PR #12
↓
GITHUB ACTIONS DEL MISMO SHA
↓
CERTIFICADO
```

Todo fallo regresa a diagnóstico. No se permite corregir repetidamente sin registrar causa raíz, evidencia, intento y resultado.

## Defectos estructurados

Cada defecto usa un identificador estable:

```text
NXR-DEF-B00-0001
```

Campos mínimos:

- bloque;
- requisito;
- categoría;
- severidad;
- estado;
- comportamiento esperado;
- comportamiento encontrado;
- causa raíz;
- archivos afectados;
- evidencia;
- intentos;
- último resultado;
- responsable;
- fecha de actualización.

OpenCode recibe defectos concretos. No recibe órdenes vagas como “corrige todo”.

## Linters

Los fallos de linters se agrupan por causa raíz:

1. formato automático seguro;
2. errores con riesgo funcional;
3. configuración o parser defectuoso;
4. falso positivo justificable.

No se permite silenciar masivamente reglas, usar `continue-on-error`, reducir alcance, insertar excepciones globales ni aprobar mediante `noqa`, `eslint-disable` o equivalentes sin justificación mínima y comprobable.

Después de cada paquete de corrección:

1. linter sobre archivos afectados;
2. pruebas relacionadas;
3. linter completo;
4. regresión;
5. pre-commit dos veces sin modificar el árbol;
6. Semgrep;
7. commit y push;
8. CI del mismo SHA.

## Secuencia de bloques

La auditoría comienza en el Bloque 0 y avanza hasta el Bloque 20. Un bloque no se certifica hasta que:

- todos sus requisitos estén auditados;
- no existan errores técnicos;
- no existan incumplimientos funcionales;
- no existan pendientes o bloqueos;
- cada validación tenga evidencia;
- CI del mismo SHA esté verde;
- las regresiones anteriores pasen;
- código y documentos coincidan;
- el árbol esté limpio.

Al cerrar un bloque se ejecuta una regresión representativa de todos los bloques anteriores. Después del Bloque 20 se ejecuta regresión global.

## Porcentajes

### Avance de auditoría

```text
validaciones ejecutadas / validaciones totales
```

### Certificación real

```text
validaciones certificadas o no aplicables / validaciones totales
```

Los dos porcentajes deben mostrarse por separado.

## Archivos canónicos

- `docs/nexora/AUDIT_RESULTS.json`: resultados por requisito y validación.
- `docs/nexora/DEFECTS.json`: defectos y ciclos de corrección.
- `tools/nexora_monitor/audit_model.js`: modelo y agregación determinista.
- `tools/nexora_monitor/audit_cli.js`: resumen, validación y puerta de auditoría.
- `tools/nexora_monitor/dashboard_server_v3.js`: servidor del monitor por capas.
- `tools/nexora_monitor/dashboard.html`: interfaz en tiempo real.

## Puerta final

Solo puede alcanzarse cuando simultáneamente:

- auditoría 100%;
- certificación 100%;
- 166/166 requisitos certificados;
- 21/21 bloques certificados;
- cero errores técnicos;
- cero incumplimientos funcionales;
- cero bloqueos;
- cero decisiones pendientes;
- cero validaciones pendientes;
- todos los workflows obligatorios verdes sobre el mismo SHA;
- instalación, migración, uninstall, reinstall y seed doble aprobados;
- permisos, finanzas, concurrencia, rollback, backup/restore, móvil y PWA demostrados;
- árbol Git limpio;
- paquete final coherente.

La puerta final abre una ventana de autorización. No fusiona por sí sola.

La autorización de PR #12, la autorización de PR #11 hacia `main`, la eliminación de ramas antiguas y el despliegue son decisiones separadas. Ninguna rama con commits exclusivos puede eliminarse.
