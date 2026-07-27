# NEXORA — Estado de ejecución

- Última actualización: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica certificada: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`
- HEAD de `main` previo a la fusión: `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- SHA funcional certificado: `94e6e8838727ce304500b1d0c4f9d92e6ade96b6`
- Producción modificada: **NO**
- AWS, Coolify, DNS, secretos, volúmenes o datos productivos modificados: **NO**
- Datos históricos migrados: **NO**
- Integración de Mail iniciada: **NO**

## Bloque — mejoras ejecutivas, reportes y cierre semanal

Estado: **IMPLEMENTADO Y VALIDADO**.

La ejecución completó y corrigió la implementación existente del dashboard ejecutivo, reportes y cierre semanal. No creó otro sistema, no sustituyó NEXORA, no introdujo un libro financiero paralelo y no eliminó documentos como mecanismo de corrección.

## Alcance terminado

- Dashboard, BI01, FI01, FI02, CO01 y cierre semanal consumen el motor financiero canónico basado en `NXR Operation Effect`.
- Saldos actuales e históricos, transferencias, reservas, liberaciones, devoluciones y reversos se calculan y presentan por separado.
- Consultas SQL variables están parametrizadas; filtros, agregados y paginación se ejecutan en servidor.
- PR02 utiliza la versión presupuestaria aplicable al corte histórico.
- Excel y PDF se generan en servidor con permiso, auditoría y rechazo sobre 5,000 filas.
- Conciliación, archivo de reportes y anulación compensatoria conservan trazabilidad e inmutabilidad.
- El cierre semanal `nexora-analytics-v3` conserva numeración de 12 dígitos, idempotencia, hash determinístico, auditoría, inmutabilidad y correcciones enlazadas.
- El navegador real valida escritorio Chromium, iPhone WebKit, PWA, rutas, autenticación, dashboard, reportes y cierre.
- La imagen de ejecución instala las páginas canónicas sin modificar el código fuente mediante parches temporales.
- El inventario canónico está sincronizado y verificado.

## Evidencia GitHub Actions del SHA funcional

| Validación | Run ID | Resultado |
|---|---:|---|
| NEXORA app — contratos, instalación/rollback y navegador/PWA | `30284969422` | APROBADO |
| NEXORA financial invariants — MariaDB e integraciones | `30284969713` | APROBADO |
| Linters — pre-commit y Semgrep | `30284969342` | APROBADO |
| NEXORA governance e inventario | `30284969347` | APROBADO |
| Patch | `30284969475` | APROBADO |
| Documentation Required | `30284969319` | APROBADO |
| Semantic Commits | `30284969324` | APROBADO |
| Read-only static server control | `30284969344` | APROBADO |
| Read-only non-Python patch control | `30284969317` | APROBADO |
| ConstruControl static verification evidence | `30284969329` | APROBADO |
| ConstruControl production validation | `30284969439` | APROBADO |
| Server (Postgres) | `30284969612` | OMITIDO POR CONDICIÓN DEL WORKFLOW; NO APLICABLE |

## Artefactos verificables

| Evidencia | Artefacto | Digest SHA-256 |
|---|---:|---|
| Aplicación, instalación y rollback | `8660533568` | `68d41afa95ac1d0768dadf29074eaf6f1ab2e571bddc3ff0e8cb5238e5ffdfa6` |
| Chromium, iPhone WebKit y PWA | `8660543711` | `935bb58cdc2ab095fe286e9b7107338294be7a1019cfb54723ea559df3cf60a3` |
| Invariantes e integraciones MariaDB | `8660589834` | `3e96a6f130c7e07b390f85b337bc1dabec212a5ce98f6e312d952331df7cdd15` |
| Pre-commit y linters | `8660425340` | `2e505a0ed2cbf1a1935b2355570392a256d6703eb3a089403e93d267ac8614b3` |
| Semgrep | `8660405729` | `0aba6b92ce2541f9ca6ab8fa31baa984b2039f2dbf95278291bf89f4bbf7a409` |

## Pruebas demostradas

- 201 pruebas contractuales aprobadas.
- 80 pruebas puras aprobadas.
- Instalación, migración, desinstalación, reinstalación, rollback y semillas idempotentes aprobados.
- Integraciones financieras, directorio, contratos, proveedores, solicitudes, reportes, presupuesto histórico y cierre v3 aprobadas en MariaDB.
- Concurrencia y bloqueos independientes aprobados.
- Ruff, Prettier, ESLint/pre-commit y Semgrep aprobados.
- Chromium, iPhone WebKit, manifiesto, service worker, caché pública y modo sin conexión aprobados.
- Pruebas negativas de permisos, límites, eliminación, períodos duplicados, conciliación y anulación no elegible aprobadas.

## Limitación funcional declarada

Fondos, reservas, presupuesto, obligaciones y avance físico se calculan al corte. El estado contractual y la conciliación documental reflejan el estado vigente al generar la fotografía porque todavía no existe un historial canónico completo de todas las transiciones contractuales, adendas y estados documentales. Esta limitación permanece explícita y no se presenta como resuelta.

## Siguiente acción autorizada

1. Publicar y validar este registro documental en el mismo PR.
2. Marcar el PR #19 listo para revisión.
3. Fusionar el PR #19 en `main`.
4. Verificar el nuevo HEAD y las validaciones posteriores de `main`.
5. Eliminar las ramas remotas distintas de `main` después de confirmar la fusión.
