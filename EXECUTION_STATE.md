# NEXORA — Estado de ejecución

- Última actualización: 2026-07-23
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- Pull Request único: `#11` — abierto y sin fusionar
- HEAD inicial obligatorio de esta ejecución: `7f4ed47789df6b6f62401d048435947f020adb7e`
- HEAD de código previo al checkpoint final: `620bd0d1f4aaf73bdaa5cc02ace4eb8cd0aa4d8b`
- HEAD de `main` verificado: `73c9dadfb81f543e53f45887448fdecbee081850`
- Producción modificada: **NO**
- `main` modificado o fusionado: **NO**
- Datos históricos migrados: **NO**
- Bloques 4–20 iniciados: **NO**

## Objetivo de esta ejecución

Estabilizar y entregar únicamente los Bloques 0–3 como NEXORA 0.1 instalable, certificable y visible en un sitio limpio de staging.

## Hecho

### Árbol y workflows

- `NEXORA governance` quedó estrictamente de solo lectura: `contents: read`, sin `git add`, `git commit`, `git push`, publicadores ni transporte temporal.
- Permanecen únicamente tres workflows NEXORA: `NEXORA governance`, `NEXORA app` y `NEXORA financial invariants`.
- `validate_nexora_app.py` resuelve imports locales, hooks, endpoints reexportados, servicios de interfaz y rechaza workflows temporales o con escritura.
- El diff neto contra el HEAD inicial modifica 11 rutas existentes y no agrega ni elimina archivos; el universo del inventario canónico permanece en 5,015 rutas.
- El checkpoint de este documento activa los tres workflows sobre el mismo SHA.

### Aplicación e instalación

- Instalador reproducible consolidado en `scripts/register_nexora_app.py` con comandos `bootstrap`, `verify` y `serve`.
- Compatibilidad conservada con el registro histórico `register_nexora_app.py sites/apps.txt` usado por CI.
- El comando rechaza sitios con tokens `prod`, `production` o `live` y exige `test`, `staging` o localhost.
- El flujo instala el paquete local, migra, construye assets, carga dos veces datos demostrativos y verifica salud.
- La guía completa quedó consolidada en `nexora_app/README.md`.

### Staging NEXORA 0.1

- Datos demostrativos protegidos por `nexora_staging=1` y consolidados en `nexora.financial.seeds`.
- Dos proyectos, tres fuentes, una salida multifuente a Cuenta Máxima, un anticipo y una transferencia interna.
- Claves y fechas determinísticas para demostrar idempotencia entre ejecuciones.
- Salud previa al commit; cualquier fallo ejecuta rollback de la transacción demostrativa.
- Verificación de app, ERPNext, DocTypes, roles, workspace, página, catálogos, fuentes, operaciones y auditoría.

### Entrega visible

- Workspace `NEXORA 0.1` con accesos a Núcleo de Fondos, Fuentes de fondos, Libro Central, Tipos de operación y Clasificación económica.
- Navegación persistente para Resumen, Fondos, Fuentes y Libro Central.
- Indicadores visibles de ingresos, salidas, multifuente y auditoría.
- CSS responsivo para escritorio, iPhone y PWA/Desk móvil.
- Ruta principal: `/app/nexora-finance`.

### Pruebas incorporadas

- Contrato de imports, hooks, servicios de interfaz y workflows permanentes.
- Prueba negativa: la carga demostrativa falla sin `nexora_staging=1`.
- Prueba del workspace y sus superficies exclusivas de Bloques 0–3.
- `NEXORA app`: instalación, migración, fixtures, coexistencia, desinstalación limpia, reinstalación, carga doble idempotente y salud.
- `NEXORA financial invariants`: catálogos, centros de costo, clasificación económica, Libro Central, fondos, ahorro, inversión, transferencias, anticipos, liquidaciones, devoluciones, reclasificaciones, reversiones, permisos, auditoría, rollback, idempotencia y concurrencia.

## Evidencia publicada en esta ejecución

1. `fececa74380f37a696f2522c8b7686aac0ead94c` — gobierno de solo lectura.
2. `ee57a7c1a68fd787475fe537651e385b14217a67` — puerta de imports y workflows permanentes.
3. `014c15e5f058492e3721e64eb3bc3aff4f3e3063` — resolución de endpoints reexportados.
4. `2481ca2cb91f729e1658959f724ae719ba79a567` — instalación/reinstalación con staging.
5. `26b27dc7a069337d8553aa748a729502ec870a33` — staging después de invariantes financieras.
6. `b79133833fef4609bcbd59bab03b001e14fd1100` y `c6cfb18557d5f08430c5714967d5a2ebc0e6c1d8` — workspace visible y contrato canónico.
7. `1e67e8233958f9bbbc10f9aa69572e356569b74e`, `204e68e32294e1908500c60770baa0b7e45ad63c` y `c845505256831c9437eb74184087c65de8a96abb` — navegación y experiencia móvil.
8. `2766c6af06d0df306c48f07e5cae8ca5724e323d`, `ebe80b02489a603f56044300c468347fd2084286` y `620bd0d1f4aaf73bdaa5cc02ace4eb8cd0aa4d8b` — datos idempotentes y rollback de staging.
9. `a00ffee205513ae1f51622ef603288d5fb64183e`, `b932d346bba8455292289fc3eaffce6550b738e8` y `7b746d9b886e31ab6fe10ef32e7a0ee602a4497e` — comandos reproducibles y bloqueo de producción.
10. `fd6938618f999c5f8fec23c197542193a7295a52` — guía consolidada de NEXORA 0.1.
11. `2e9c96f622fa1faf49321e981852e69d125747bb`, `473510c0272ae0ef21a2890a1a861461ab9abe64`, `fc5c57fdd7cfb94a52eb736adf8273bb2b211f2e` y `151d8400fa455ffdaf57b883d89506521b913036` — certificación coordinada de aplicación e invariantes.
12. `0592e1668ffef97795634b58a1f1372f74ac9244` — pruebas negativas y superficies visibles.

Los archivos intermedios `nexora_app/nexora/staging.py`, `scripts/nexora_staging_01.sh` y `docs/nexora/STAGING_0_1.md` fueron consolidados en rutas permanentes y eliminados mediante `7143cafb496188610187c6be88e2337f7a918765`, `2e439d1408150b32b75b28e284de36ce01d67bc1` y `3e01b46e539e01d932f25a96ed9b41cf3f971e23`.

## Estado definitivo de los Bloques 0–3

- Bloque 0: **IMPLEMENTADO Y VALIDADO** en la cadena previa certificada y conservado sin regresiones demostradas.
- Bloque 1: **IMPLEMENTADO Y VALIDADO** en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`.
- Bloque 2: **IMPLEMENTADO Y VALIDADO** en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`.
- Bloque 3: **EXISTENTE Y REUTILIZABLE**; código, interfaz y certificación reproducible publicados. No cambiar a `IMPLEMENTADO Y VALIDADO` hasta que `NEXORA app` y `NEXORA financial invariants` estén verdes sobre el SHA de este checkpoint.

## Bloqueo externo y siguiente acción exacta

El entorno de ejecución actual no dispone de DNS, bench Frappe ni MariaDB, por lo que no puede materializar el runtime local. Los runs de PR observados previamente quedaron en `action_required` sin jobs, condición que exige una acción externa de GitHub.

Siguiente acción única: aprobar/permitir los tres workflows del PR #11 para el SHA de este checkpoint, verificar que `NEXORA app` y `NEXORA financial invariants` estén verdes sobre ese mismo SHA, descargar sus artefactos y registrar run IDs, jobs y digests. No iniciar Bloques 4–20.
