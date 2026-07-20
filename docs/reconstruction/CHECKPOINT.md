# Checkpoint canónico de ConstruControl

- Pull Request único: **#9**
- Rama de trabajo: `reconstruccion-definitiva-construcontrol`
- Rama protegida y destino final: `main`
- Arquitectura vigente: AWS EC2 x86_64 + Coolify + Docker Compose + ERPNext/Frappe v15 + MariaDB 10.6 + Redis
- Supabase: únicamente origen histórico de migración
- Matriz de aceptación: `docs/reconstruction/MATRIZ_ACEPTACION_1A1.md`
- Certificación: `.github/workflows/construcontrol-full-certification.yml`

## Regla de estado

Este archivo no autoriza por sí solo porcentajes ni fusión. El único estado aprobatorio es una ejecución
completa y exitosa de:

`A → B → C → FINAL → AUDIT_1_TO_1`

sobre el mismo SHA exacto del PR, seguida de verificación de que el HEAD no cambió.

## Alcance implementado

- US01: usuarios, roles, permisos backend y proyectos asignados.
- FI01: fondos, remesas, monedas, conciliación y saldos.
- FI02: gastos, facturas, CxP, aprobaciones, pagos, evidencia y reversión.
- PR01/CO01: proyectos, fases, presupuestos, contratos, anticipos, retenciones y pagos.
- MM01/MM02/MIGO: materiales, compras, recepciones, inventario y movimientos.
- QC01/CL01: avance, calidad, incidencias, evidencias y cierres idempotentes.
- BI01/AU01: indicadores reconciliados, exportaciones seguras y auditoría inmutable.
- Escritorio, iPhone, móvil y PWA versionada.
- Infraestructura, persistencia, backup verificable y restore aislado.
- Migración histórica idempotente y clasificación no destructiva de datos demo.
- Manual oficial único.

## Hallazgo adversarial previo al cierre

La ejecución exacta sobre `7921e74f654106e5cd5592a77b4a1b4a3ed61665` aprobó Puertas A y B,
pero Gate C detectó que los health checks de WebSocket, workers, scheduler y backup usaban `pgrep`
sin que la imagen productiva instalara `procps`. Los procesos estaban activos, pero Docker los marcaba
`unhealthy` y frontend quedaba bloqueado por dependencias.

La corrección mínima completa se publica junto con este checkpoint:

- instalación explícita de `procps` en la imagen;
- prueba negativa que rechaza una imagen sin la dependencia requerida;
- matriz viva de 224 requisitos;
- auditor independiente reforzado que exige matriz completa, paths reales y estados aprobados.

## Gobierno

- Sin force push.
- Sin modificación directa de `main`.
- Sin omisión de validaciones de CI.
- Sin eliminación de respaldos o volúmenes.
- Sin fusión hasta que todas las puertas y la auditoría 1:1 estén verdes.
