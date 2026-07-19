# ConstruControl — Despliegue y reversión segura

## Fuente única de verdad

La rama `main` de GitHub contiene el código, definiciones runtime, migraciones, activos PWA, validaciones y documentación. AWS y Coolify únicamente construyen y ejecutan esa versión.

## Antes de desplegar

1. Confirme que GitHub Actions finalizó correctamente:
   - Product, migration and security validation.
   - Build AWS EC2 x86_64 image.
   - Build verified source ZIP.
2. Registre el SHA exacto que se desplegará.
3. Confirme que los servicios actuales estén saludables.
4. No modifique ni elimine volúmenes persistentes.

## Despliegue en Coolify

1. Abra la aplicación ConstruControl.
2. Verifique repositorio, rama `main` y SHA esperado.
3. Ejecute un único despliegue.
4. Espere a que finalicen la construcción, migración y healthcheck.
5. No inicie un segundo despliegue mientras el primero esté ejecutándose.

Durante `after_migrate`, el sistema:

- valida el contrato runtime antes de modificar la base;
- crea o actualiza DocTypes y páginas de forma idempotente;
- instala campos profesionales;
- conserva los datos existentes;
- registra la versión y huella SHA-256 del contrato instalado;
- limpia caché después de completar la instalación.

## Validación posterior

Compruebe:

1. `/app/construcontrol-dashboard`
2. `/app/construcontrol-project-center`
3. `/app/construcontrol-profile`
4. `/app/construcontrol-integrations` con usuario administrador
5. `/app/construcontrol-reporting-center`
6. Ingresos, gastos, cuentas por pagar, contratos, fases, materiales y avances.
7. Navegación móvil y opción Agregar a pantalla de inicio.

No repita la migración histórica para validar una actualización de interfaz.

## Reversión de aplicación

Cuando una versión nueva no supera la validación posterior:

1. Identifique el último SHA productivo estable.
2. En Coolify seleccione ese commit o revierta el commit problemático en GitHub.
3. Despliegue una sola vez.
4. Mantenga los mismos volúmenes de MariaDB, Redis y archivos.
5. Verifique healthchecks y rutas ConstruControl.

## Reversión de datos

Una restauración de MariaDB se utiliza únicamente cuando existe evidencia de modificación de datos incompatible, no por fallas visuales.

1. Identifique el respaldo verificado creado antes de la operación.
2. Detenga escrituras de usuarios durante la restauración.
3. Utilice el procedimiento oficial de Bench/Coolify para restaurar el respaldo.
4. Conserve una copia del estado que se reemplazará.
5. Valide cantidades, totales y conciliación antes de reabrir el sistema.

## Acciones prohibidas

No ejecutar:

```text
docker system prune
docker volume prune
docker compose down -v
```

No eliminar manualmente volúmenes, tablas, archivos privados ni contenedores de datos. No editar archivos dentro del contenedor como solución permanente.

## Evidencia obligatoria de cierre

- SHA desplegado.
- Resultado de GitHub Actions.
- Estado saludable de servicios.
- Capturas o registro de rutas principales.
- Confirmación de totales financieros y cantidad de registros.
- Resultado de instalación PWA en móvil.
