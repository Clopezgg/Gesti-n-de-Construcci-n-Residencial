# NEXORA — Estado de ejecución

Última actualización: 2026-07-27

## Fuente única de verdad

- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`
- Base verificada antes de reconstruir: `main` en `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- PR duplicado `#20`: cerrado, no fusionado y no autorizado como línea de trabajo.

## Bloque activo

**Dashboard ejecutivo, motor analítico, FI01, FI02, CO01, BI01, conciliación, exportaciones y cierre semanal.**

Estado: **NO DEMOSTRADO** hasta que el SHA publicado complete todas las validaciones aplicables en verde.

## Cambios incluidos en el bloque

- motor analítico canónico basado en `NXR Operation Effect`;
- saldos históricos `as-of`, saldo inicial, saldo al cierre y saldo actual separados;
- transferencias internas, reservas, liberaciones, devoluciones y reversos separados del gasto;
- dashboard premium conservando el contrato funcional certificado;
- FI01, FI02 y CO01 paginados;
- BI01 con reportes ejecutivos, proveedores, inventario, fases y control operativo;
- Excel y PDF generados en servidor con permiso y auditoría;
- conciliación explícita de ingresos;
- reportes guardados;
- cierre semanal con número numérico de 12 dígitos, idempotencia, hash, auditoría, inmutabilidad y corrección compensatoria;
- navegación, documentación y pruebas de aceptación.

## Validación ejecutada antes de publicar

- compilación sintáctica Python de los módulos nuevos y modificados;
- validación sintáctica Node de las tres páginas JavaScript;
- cinco pruebas puras del motor analítico: aprobadas.

Estas comprobaciones locales no sustituyen CI, instalación Frappe/MariaDB ni pruebas de navegador.

## Validaciones pendientes del SHA publicado

1. Semantic Commits.
2. Documentation Required.
3. Linters y formato.
4. Patch y controles de solo lectura.
5. NEXORA financial invariants.
6. NEXORA app: contratos, pruebas puras, instalación, migración, desinstalación y reinstalación.
7. Chromium escritorio, iPhone WebKit y PWA.
8. Validación final del PR sobre un único SHA.

## Restricciones

- PR #19 permanece en borrador.
- No fusionar mientras exista un check aplicable fallido o pendiente.
- No tocar producción, AWS, Coolify, DNS, secretos ni datos históricos.

## Siguiente acción

Publicar el commit semántico del bloque en la rama oficial, ejecutar CI, investigar cada fallo real, corregirlo y repetir hasta dejar todos los checks aplicables en verde. Después registrar el SHA certificado en este archivo.
