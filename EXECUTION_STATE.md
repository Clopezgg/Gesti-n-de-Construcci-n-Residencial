# NEXORA — Estado de ejecución

- Última actualización: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica activa: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`, abierto, en borrador y no fusionado
- HEAD remoto verificado al iniciar esta corrección: `0e2a23a672466190f33c7b07fbacde319eacfb36`
- HEAD de `main` verificado: `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- Producción modificada: **NO**
- AWS, Coolify, DNS, secretos, volúmenes o datos productivos modificados: **NO**
- Integración de Mail iniciada: **NO**

## Bloque activo — mejoras ejecutivas, reportes y cierre

Estado: **NO DEMOSTRADO** hasta que el SHA publicado por esta corrección complete en verde todas las validaciones aplicables.

La ejecución corrige y completa la implementación existente del dashboard ejecutivo, reportes y cierre semanal. No crea otro sistema, no sustituye NEXORA, no introduce un libro financiero paralelo y no elimina documentos como mecanismo de corrección.

## Evidencia real recuperada de GitHub Actions

La limitación que impedía iniciar los runners quedó resuelta. En el SHA `0e2a23a672466190f33c7b07fbacde319eacfb36` GitHub Actions publicó pasos, logs y artefactos verificables.

Resultados relevantes del SHA anterior:

- instalación, migración, desinstalación, reinstalación y datos de staging de NEXORA: **APROBADO**;
- documentación: **APROBADO**;
- commits semánticos: **APROBADO**;
- control de parche no Python: **APROBADO**;
- contratos estáticos: **FALLÓ** por tres expectativas desactualizadas;
- invariantes financieras: **FALLÓ** en la compuerta estática antes de MariaDB;
- Ruff/Prettier: **FALLÓ** por formato y reglas concretas;
- Semgrep: **FALLÓ** por consultas SQL construidas con interpolación textual;
- gobierno: **FALLÓ** por inventario canónico desactualizado;
- navegador real: **FALLÓ** porque la navegación global reutilizaba y reemplazaba el contenedor del dashboard.

## Correcciones materializadas para el siguiente SHA

### SQL, seguridad y rendimiento

- Las consultas de cortes históricos, contratos, pendientes y gastos usan SQL estático con valores variables parametrizados.
- Se eliminaron las consultas construidas mediante f-strings señaladas por Semgrep sin desactivar reglas ni ocultar hallazgos.
- Se conservaron filtros de proyecto, fechas, fuente, categoría económica, centro de costo, entidad, método de pago, contratista y estado contractual.
- El antiguo módulo analítico monolítico se dividió en consultas enfocadas y limitadas para fuentes, contratos, inventario y utilidades de paginación; `executive.py` conserva únicamente la fachada pública compatible.
- Dashboard, reportes y cierre siguen leyendo `NXR Operation Effect` y los modelos canónicos existentes; no se creó un segundo libro financiero.

### Contratos y cierre semanal

- El contrato de instalación reconoce los 48 DocTypes canónicos existentes.
- Los contratos del snapshot filtrado se alinearon con las consultas parametrizadas y los módulos enfocados actuales.
- El contrato del cierre semanal v3 dejó de depender de coincidencias textuales frágiles.
- Se conservaron el motor `nexora-analytics-v3`, número único de 12 dígitos, idempotencia, hash determinístico, auditoría, inmutabilidad y correcciones enlazadas.

### Navegador, iPhone y PWA

- La navegación global usa el contenedor dedicado `.nxr-product-navigation` y ya no reemplaza el `.nxr-product-shell` interno del dashboard.
- Se añadió una prueba negativa que impide reintroducir la colisión de selectores.
- El smoke de navegador fue dividido en soporte, validadores y ejecutor para mantener responsabilidades acotadas sin cambiar la cobertura: Chromium, iPhone WebKit, reportes, cierre v3, PWA, autenticación y rutas directas.

### Formato, validadores e inventario

- Se aplicaron las correcciones concretas recuperadas del artefacto de pre-commit del SHA anterior sobre los archivos ya señalados.
- Los archivos nuevos se ajustaron al formato y convenciones declaradas; Ruff, Prettier, ESLint y Semgrep reales quedan pendientes de confirmación por CI.
- El validador de marcadores pendientes distingue comentarios Python reales de identificadores válidos como `ToDo`, evitando el falso positivo del control de parche.
- El inventario canónico fue regenerado al final del conjunto local de correcciones.
- Inventario: **5,354 archivos**; huella canónica `10f57c7abfb54e7c8e1fbcf9bd9bc94507aa9862ae13cd9e1dee8d2bbc461a37`.

## Validación local ejecutada antes de publicar

- `scripts/validate_nexora_governance.py`: aprobado — 166 requisitos, 37 máquinas, 32 controles, 9 pruebas compartidas y 19 decisiones.
- `scripts/validate_nexora_app.py`: aprobado.
- `scripts/validate_nexora_financial_models.py`: aprobado.
- contratos estáticos: **201 pruebas aprobadas**.
- pruebas puras financieras, de libro, evidencia, directorio, contratos, compras, solicitudes, cotizaciones y analítica: **80 pruebas aprobadas**.
- compilación Python completa de `nexora_app/nexora` y `scripts`: aprobada.
- comprobación de sintaxis de las superficies JavaScript principales y de los tres módulos del smoke de navegador: aprobada.
- inventario canónico `--check`: aprobado.

Estas comprobaciones locales no sustituyen MariaDB/Frappe, Semgrep, pre-commit, Chromium, WebKit ni PWA reales. La certificación depende de GitHub Actions sobre el nuevo SHA publicado.

## Limitación funcional declarada

Fondos, reservas, presupuesto, obligaciones y avance físico se calculan al corte. El estado contractual y la conciliación documental reflejan el estado vigente al generar la fotografía porque todavía no existe un historial canónico completo de todas las transiciones contractuales, adendas y estados documentales. Esta limitación no se presenta como resuelta.

## Criterio pendiente de terminado

El bloque solo podrá cambiar a **IMPLEMENTADO Y VALIDADO** cuando un único SHA publicado apruebe:

- contratos y pruebas puras;
- Ruff, Prettier, ESLint, pre-commit y Semgrep;
- gobierno e inventario;
- instalación, migración, desinstalación, reinstalación y rollback Frappe/MariaDB;
- integraciones financieras, ejecutivas y de cierre;
- Chromium de escritorio, iPhone WebKit y PWA;
- documentación, commits semánticos y controles de parche aplicables;
- logs y artefactos verificables.

El PR debe permanecer en borrador y sin fusionar mientras esta evidencia no exista.

## Siguiente acción exacta

1. Publicar este conjunto coherente de correcciones en la misma rama y PR.
2. Verificar el nuevo SHA remoto.
3. Ejecutar todas las validaciones aplicables sobre ese único SHA.
4. Corregir cualquier fallo real adicional sin desactivar controles.
5. Marcar el PR listo para revisión únicamente cuando todos los controles aplicables estén en verde.
