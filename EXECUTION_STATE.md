# NEXORA — Estado de ejecución

- **Última actualización:** 2026-08-22
- **Repositorio único:** `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- **Rama oficial:** `main`
- **HEAD verificado:** `b29152f6b88d26ee713b4753b51f9d7f5de1ecfc`
- **Certificación CI actualmente reportada:** `NEXORA Predeploy Certification` = **SUCCESS** sobre `main`.
- **Producción, AWS, Coolify, DNS, secretos, volúmenes y datos reales modificados por esta actualización:** **NO**
- **Migración histórica de registros:** **NO**

## Regla de verdad del estado

Este archivo describe el estado real conocido del repositorio y **no sustituye la evidencia de CI/runtime**. Un requisito solo puede clasificarse como `IMPLEMENTADO Y VALIDADO` cuando existe código verificable, pruebas ejecutadas, commit publicado y SHA verificable; una rama, PR, captura o descripción de otro agente no constituye por sí sola prueba de implementación.

## Estado actual de `main`

### Confirmado

- `main` apunta a `b29152f6b88d26ee713b4753b51f9d7f5de1ecfc`.
- PR #342 está **fusionado** y contiene únicamente el formateo Ruff del adaptador SAP que había provocado el rojo de linters; el PR documenta `ruff format --check` y `ruff check` limpios. 
- El estado combinado de CI de `main` consultado el 2026-08-22 reporta `NEXORA Predeploy Certification` en **success**.
- El historial reciente muestra correcciones reales y sucesivas en SAP, dashboard, identidad visual, integración y controles de aceptación. No se debe interpretar este estado verde como prueba de cierre de todas las capacidades de producto.

### No demostrado todavía como cierre global

- `EXECUTION_STATE.md` contenía hasta hoy referencias históricas de cierre del 2026-08-04 y SHA antiguos; esas referencias no describían correctamente el `main` actual y por eso se corrigen aquí.
- PR #343 (`feat/nexora-login-opcion3`) sigue **abierto y sin fusionar**; su diseño no forma parte de `main`.
- La certificación de producto completo requiere mantener separados los resultados de contrato estático, instalación/migración, navegador real, seguridad, integración externa y runtime productivo. Un `success` agregado no autoriza a inferir que cada superficie esté individualmente cerrada.
- La validación de producción/Coolify sigue fuera del alcance de esta actualización porque no se hizo ningún cambio de infraestructura ni existe evidencia aquí de un redeploy posterior al `HEAD` actual.

## Correcciones históricas que permanecen en `main`

Entre las correcciones verificables del historial reciente se encuentran:

1. Corrección de errores HTTP del adaptador SAP y posterior formateo Ruff en PR #342.
2. Integración SAP Sandbox real de lectura, con autenticación, CSRF, pruebas vivas y correcciones para respuestas gzip y HTTP sin cabeceras.
3. Reemplazo del dashboard ejecutivo duplicado y corrección de sus contratos.
4. Corrección de marcadores de aceptación operativa tras el cambio del dashboard.
5. Corrección de fugas visuales de ERPNext en favicon/footer y rutas administrativas.
6. Correcciones de shell, navegación, contexto activo, formularios nativos, diálogos, toasts, breadcrumbs y sidebar.
7. Integración SAP → NEXORA mediante staging de entrada con idempotencia y trazabilidad.
8. Catálogo real de mapeos SAP, auditoría y correlación de eventos.

Estas entradas son **historial de cambios publicados**, no una afirmación de que todas las capacidades de negocio finales de NEXORA estén terminadas.

## Reglas para la continuación

1. Trabajar únicamente sobre el repositorio oficial `Clopezgg/Gesti-n-de-Construcci-n-Residencial`.
2. No crear producto paralelo ni repositorio alternativo.
3. No modificar producción, AWS, Coolify, DNS, secretos, volúmenes o datos reales sin autorización expresa, respaldo verificable, rollback y validación posterior.
4. Corregir causa raíz, no síntomas.
5. Implementar backend + interfaz + permisos servidor + auditoría + manejo de errores + pruebas positivas y negativas + documentación.
6. Publicar cada bloque coherente con commit semántico y SHA verificable antes de continuar.
7. No clasificar como `IMPLEMENTADO Y VALIDADO` aquello que solo tenga pruebas estáticas, mocks, capturas o una PR sin merge.
8. Mantener el producto completamente en español y con identidad propia NEXORA; ERPNext/Frappe es únicamente motor técnico interno.

## Próximo bloque de trabajo

**Estado:** `REQUIERE EJECUCIÓN`

Hacer una auditoría de cierre contra `main` actual que cubra, como mínimo:

- todos los jobs de GitHub Actions y sus dependencias;
- pruebas de linters, contrato, seguridad, secretos y validación del repositorio;
- instalación/migración/reinstalación y coexistencia con ERPNext/Frappe;
- recorrido navegador real en escritorio, tableta, iPhone y PWA;
- permisos negativos en servidor;
- endpoints financieros y mutaciones con auditoría;
- navegación y rutas reales;
- SAP Sandbox frente a SAP Productivo, manteniendo la separación entre lo demostrado y lo externo/bloqueado;
- deuda técnica, ramas/PRs abiertos y documentación desactualizada;
- búsqueda de rutas falsas, botones sin backend, simulaciones de éxito y marcadores de implementación incompleta;
- consistencia de los modelos de Proyecto/Fase/Centro de Costo/Fondo/Operación con la estructura económica de la obra.

### Criterio de cierre

El siguiente bloque **no se declara cerrado** hasta que cada hallazgo tenga una de estas categorías permanentes:

`CONFIRMADO` · `PROPUESTO` · `REQUIERE DECISIÓN` · `EXISTENTE Y REUTILIZABLE` · `EXISTENTE PERO DEFECTUOSO` · `OBSOLETO` · `NO DEMOSTRADO` · `IMPLEMENTADO Y VALIDADO`.

La clasificación `IMPLEMENTADO Y VALIDADO` exige código + pruebas positivas/negativas + commit publicado + SHA verificable.
