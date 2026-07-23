# NEXORA 0.1

Aplicación Frappe separada, alojada en el repositorio oficial de NEXORA e instalada junto con ERPNext.

Esta app no importa módulos ConstruControl, no migra registros históricos y no modifica producción durante sus pruebas.

## Alcance visible de los Bloques 0–3

- identidad NEXORA y login estándar de Frappe;
- workspace y navegación móvil;
- Núcleo de Fondos;
- registro de ingresos mediante fuentes independientes;
- registro de salidas con vista previa del servidor;
- selección multifuente y saldo por fuente;
- Libro Central e historial cronológico;
- catálogos de tipos de operación y clasificación económica;
- ahorro, inversión, transferencias internas, anticipos, liquidaciones, devoluciones, reclasificaciones y reversiones;
- permisos, auditoría, idempotencia, concurrencia y rollback.

## Staging reproducible

El comando rechaza nombres de sitio que no contengan `staging`, `test`, `.localhost` o sean `localhost`. No debe utilizarse contra producción.

Desde la raíz del checkout exacto de `nexora-reconstruccion`:

```bash
python scripts/register_nexora_app.py bootstrap \
  --bench "$HOME/frappe-bench" \
  --site test_site \
  --admin-password "CAMBIAR-EN-STAGING"
```

El comando crea o reutiliza el bench, enlaza el paquete local, instala y migra NEXORA, construye assets, activa `nexora_staging=1`, carga dos veces el mismo conjunto demostrativo para probar idempotencia y ejecuta la verificación de salud.

Los datos son explícitamente demostrativos y no históricos:

- dos proyectos NEXORA 0.1;
- tres fuentes de fondos;
- una salida a Cuenta Máxima distribuida entre dos fuentes;
- un anticipo con responsable y vencimiento determinístico;
- una transferencia interna entre proyectos;
- usuarios de prueba con roles NEXORA.

## Certificación completa

```bash
python scripts/register_nexora_app.py verify \
  --bench "$HOME/frappe-bench" \
  --site test_site
```

La verificación ejecuta gobierno, imports y contratos, modelos, pruebas puras, sintaxis JavaScript, compilación Python, migración, instalación, invariantes financieras MariaDB, Libro Central, concurrencia y salud de staging.

El Bloque 3 solo está certificado cuando **NEXORA app** y **NEXORA financial invariants** están verdes sobre el mismo SHA.

## Servidor local de staging

```bash
python scripts/register_nexora_app.py serve \
  --bench "$HOME/frappe-bench" \
  --site test_site
```

Acceso habitual del bench de desarrollo:

```text
http://127.0.0.1:8000
```

Después del login, abra el workspace **NEXORA** o:

```text
/app/nexora-finance
```

## Evidencia y rollback

Conserve la salida completa de `bootstrap` y `verify`, la lista de aplicaciones instaladas, el JSON de `nexora.financial.seeds.assert_staging_health` y los artefactos de los workflows permanentes.

Antes de eliminar un staging:

```bash
cd "$HOME/frappe-bench"
bench --site test_site backup --with-files
```

NEXORA bloquea la desinstalación destructiva cuando existen operaciones. Para un sitio demostrativo, conserve el backup y elimine el sitio completo mediante el procedimiento administrativo del bench. No aplique este rollback a producción ni a registros reales.
