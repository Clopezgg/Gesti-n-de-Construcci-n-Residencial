# Checkpoint canónico de ConstruControl

- Pull Request único: **#9**
- Rama de trabajo: `reconstruccion-definitiva-construcontrol`
- Rama protegida y destino final: `main`
- Último HEAD funcional previo a este checkpoint: `0d20b4b5167eb79d53f4de1f790655d066c3275f`
- Arquitectura vigente: AWS EC2 x86_64 + Coolify + Docker Compose + ERPNext/Frappe v15 + MariaDB 10.6 + Redis
- Supabase: únicamente origen histórico de migración
- Matriz: `docs/reconstruction/MATRIZ_ACEPTACION_1A1.md`
- Certificación: `.github/workflows/construcontrol-full-certification.yml`

## Regla de estado

Este archivo no autoriza porcentajes ni fusión. El único estado aprobatorio es una ejecución completa y exitosa de:

`A → B → C → FINAL → AUDIT_1_TO_1`

sobre el mismo SHA exacto del PR, seguida de verificación de que el HEAD no cambió.

## Correcciones publicadas en esta ejecución

- Linters: aplicado el formato exacto de Ruff 0.2.0 y corregido el import de `Iterable`.
- Gate C: reemplazados los health checks frágiles de workers y scheduler por verificación del proceso hijo supervisado por PID 1.
- Gate A financiero: el shard MariaDB ya ejecuta CRUD real de FI01/FI02, sincronización de CxP, conciliación y denegaciones de permisos.
- Auditor 1:1: ahora rechaza frases genéricas, evidencia sin identificador, ausencia de workflow/artifact y commits que no sean SHA exactos de 40 caracteres.
- PR #9: retirada la declaración prematura de “100 %”.

## Hallazgos adversariales abiertos

1. Las 224 filas existentes contienen evidencia repetitiva y no pueden considerarse certificadas.
2. Deben cambiarse a `NO DEMOSTRADO` hasta que cada una tenga evidencia específica ejecutada.
3. Gate B todavía necesita mayor cobertura runtime de contratos, inventario, calidad, BI y auditoría.
4. Escritorio, viewport iPhone y PWA todavía requieren una prueba real de navegador; las comprobaciones textuales no bastan.
5. Gate C, FINAL y AUDIT_1_TO_1 deben recertificarse sobre el HEAD definitivo.

## Gobierno

- PR abierto, en borrador y sin fusionar.
- Sin force push.
- Sin modificación directa de `main`.
- Sin omisión de validaciones.
- Sin eliminación de respaldos o volúmenes.
- Sin fusión, tag ni limpieza de ramas mientras exista un requisito rechazado o no demostrado.
