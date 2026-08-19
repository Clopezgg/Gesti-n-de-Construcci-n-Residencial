# NEXORA — Plan Maestro canónico

## Propósito

Conducir NEXORA como producto único para gestión integral de fondos, proyectos y operaciones, en español claro, con Frappe/ERPNext como motor interno y sin identidades, ledgers, dashboards o fuentes de saldo paralelas.

## Fuente de verdad

1. `NEXORA_CONSTITUTION.md` manda sobre cualquier otro documento.
2. `AGENTS.md` define la operación del agente en este repositorio.
3. `EXECUTION_STATE.md` registra la evidencia histórica por bloque y sus límites.
4. `docs/nexora/` contiene antecedentes operativos, auditorías, matrices ampliadas y decisiones.
5. Los tests bajo `nexora_app/nexora/tests/` son evidencia ejecutable, pero no sustituyen pruebas de runtime real cuando el requisito depende de Frappe/MariaDB/navegador/servicio externo.

## Estados permitidos

Toda planificación y todo requisito deben usar solo: `CONFIRMADO`, `PROPUESTO`, `REQUIERE DECISIÓN`, `EXISTENTE Y REUTILIZABLE`, `EXISTENTE PERO DEFECTUOSO`, `OBSOLETO`, `OBSOLETO JUSTIFICADO`, `NO DEMOSTRADO`, `IMPLEMENTADO Y VALIDADO` o `IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE`.

## Fases únicas

| Fase | Objetivo | Estado | Entregables |
|---|---|---|---|
| Fase 1 | Recuperación del producto principal: NEXORA como inicio, navegación y experiencia principal. | EXISTENTE Y REUTILIZABLE | Dashboard, navegación, páginas, PWA, proyectos, fondos, operaciones, contratos, proveedores, evidencias, cuentas y reportes. |
| Fase 2 | Simplificación operativa: ingresos, remesas, depósitos, gastos, pagos y correcciones con datos conocidos por el usuario. | EXISTENTE Y REUTILIZABLE | Wizards, preview, validaciones, locks, secuencias, permisos, integridad, conciliación y rollback en backend. |
| Fase 3 | Integración y publicación definitiva: recorridos reales, permisos, saldos, errores, persistencia, escritorio, iPhone, PWA, migraciones, seguridad y CI. Alcance ampliado por la enmienda del propietario de 2026-08-16 (ver `AGENTS.md`): identidad NEXORA única de extremo a extremo (un solo login, shell, navegación y dashboard — sin ConstruControl/Frappe/ERPNext visible al usuario ordinario), administración funcional propia de NEXORA separada de la cuenta técnica `Administrator`, instalación limpia sin datos empresariales/demo/staging, y experiencia operativa con densidad y navegación fuertemente familiares a un ERP empresarial (referencia de experiencia, no de activos ni marca). *Actualización (Bloques 47/48/92/93/94):* los cuatro entregables ampliados ya tienen investigación real, cada uno con su propio límite de evidencia — identidad única e instalación limpia auditadas sin hallazgos (Bloque 47/48, sin acceso a sitio real, solo código/fixtures versionados); administración funcional propia (`NXR-ADM-001`) con CI/navegador/permisos/auditoría confirmados (Bloques 92/93); densidad y navegación tipo ERP confirmadas con evidencia de código real — token de tipografía explícito "13px · interfaz densa" (`nexora_design_system.css`), tablas con `padding` 0.42-0.5rem y `font-size` 0.72-0.8rem (por debajo del rango típico de ERP compacto), paleta de comandos Ctrl+K/Cmd+K (`nexora_shell.js`, NXR-UX-0008) y navegación agrupada por 6 secciones/24 páginas al estilo de menú modular de ERP (Bloque 94) — sin acceso a navegador real en este entorno, así que sigue siendo evidencia de código, no de renderizado visual. | NO DEMOSTRADO | Requiere CI completo del SHA publicado, smoke de navegador, instalación/migración/rollback y confirmación de `main`, más evidencia por bloque de cada entregable ampliado listado arriba. Con los cuatro entregables ampliados ya investigados a nivel de código, lo que falta para todo el conjunto de Fase 3 (no solo la enmienda) es el smoke de navegador real, instalación/migración/rollback real y CI completo del SHA publicado — bloqueado en este entorno por falta de `docker`/`bench`/credenciales de despliegue (confirmado desde el Bloque 46). |

## Reglas de avance

- No iniciar auditorías generales completas como sustituto de trabajo real. Reconstruir, eliminar o consolidar componentes concretos que no cumplan el objetivo del propietario está autorizado por bloque, con evidencia (ver `AGENTS.md`, "Enmienda del propietario — 2026-08-16").
- Conservar o integrar lo existente cuando sea funcional y coherente.
- Corregir causa raíz cuando algo sea defectuoso.
- Retirar solo lo obsoleto con justificación y sin pérdida de datos, permisos o relaciones.
- No crear aplicaciones, dashboards, ledgers, saldos o modelos financieros paralelos.
- No exponer campos técnicos al usuario ordinario si el sistema puede derivarlos.

## Criterio de terminado

Un requisito solo puede marcarse `IMPLEMENTADO Y VALIDADO` si existe evidencia acumulada de código real, integración, pruebas positivas y negativas, permisos server-side, auditoría, manejo de errores, documentación, commit, SHA verificable en `main` y CI verde para ese mismo SHA. Las integraciones con credenciales o servicios externos se clasifican como `IMPLEMENTADO — ACTIVACIÓN EXTERNA PENDIENTE` hasta ejecutar una prueba real autorizada.

## Próxima prioridad operativa

1. ~~Confirmar remoto oficial y publicar el lote documental sin sobrescribir cambios ajenos.~~ Confirmado en Bloque 46 (`NXR-GOV-002` → `CONFIRMADO`; SHA `2b238f0` verificado contra `origin/main`).
2. Ejecutar validadores y pruebas dirigidas de documentación/gobierno disponibles en el entorno. Bloque 46: `validate_repository.py`, `validate_nexora_constitution.py`, `validate_nexora_financial_models.py` y `validate_nexora_operational_acceptance.py` en verde localmente. `validate_nexora_governance.py`, `validate_nexora_completion.py` y `validate_nexora_app.py` no pudieron ejecutarse en este entorno local (Python del sistema es 3.9.6; requieren ≥3.10/3.11 — sin `pyenv`/Homebrew/`bench` disponibles para instalar una versión compatible) y quedan pendientes de confirmación en CI del SHA de este lote.
3. Cerrar `NXR-PWA-001`/`GP-12` (navegador real, PWA, escritorio/iPhone) mediante el job de CI existente (`Frappe real · escritorio · tableta · iPhone · PWA`); este entorno local no tiene `docker`/`bench`, por lo que la validación real solo puede confirmarse en el PR/CI del SHA publicado, no localmente.
4. Corregir cualquier estado documental fuera del catálogo permitido que afecte documentos canónicos raíz.
5. Mantener la matriz raíz como resumen canónico y la matriz amplia de `docs/nexora/` como antecedente trazable hasta que un validador unifique ambas.
