# NEXORA — Estado de ejecución

- Última actualización: 2026-07-27
- Repositorio único: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica activa: `feature/nexora-executive-dashboard-reporting-reconstruction`
- Pull Request oficial: `#19`, abierto, en borrador y no fusionado
- HEAD de `main` verificado: `1e6722f821ff3ae13a7e6f4a165dab9bd9e1525b`
- Último SHA funcional publicado antes de este registro: `c7926153dffebdb272204ccaeaab0e7a50d25518`
- Producción modificada: **NO**
- AWS, Coolify, DNS o secretos modificados: **NO**
- Datos históricos migrados: **NO**

## Bloque activo — mejoras ejecutivas, reportes y cierre

Estado: **NO DEMOSTRADO**.

La ejecución mejora los componentes acordados. No reconstruye NEXORA, no reemplaza el dashboard certificado, no crea otro sistema y no elimina registros financieros como método de corrección.

## Hecho y publicado

### Dashboard

- Conservación del contrato certificado: proyecto, identidad NEXORA, ingresos/gastos directos, alertas, fondos, presupuesto, evidencias, contratos, inventario y actividad.
- Refresco automático mediante `nexora:data-changed`.
- Visualización separada de ingresos, gastos, devoluciones y anulaciones/reversos.
- Estado `Compensated Total` traducido y alerta de movimientos compensados.

SHA principal del ajuste visual: `7314edc0b74c4a7ad66bff02e0654b0f6226b7f3`.

### Anulación y archivo sin borrado

- FI01 conecta la anulación de ingresos con `cancel_fund_source`.
- La anulación solo procede para una fuente sin gastos, reservas o ajustes relacionados.
- Se crea efecto inverso con referencia al efecto original, se conserva el documento y se registra auditoría.
- Reportes guardados pueden archivarse por su propietario; no se eliminan.
- Archivo y anulación son idempotentes, bloqueados y transaccionales.

SHAs principales: `715dcb6fe5996ef7eb4fadad2690d57ee1694593`, `02942cc`, `694d801` y `7a8f9bec`.

### Motor analítico y cortes históricos

- La fecha del ingreso coincide con la fecha de su operación en el Libro Central.
- Fuentes futuras quedan fuera de cortes anteriores.
- Reversos no se reclasifican como gasto ordinario.
- Disponible proyectado no resta dos veces obligaciones ya representadas por reservas.
- Cancelaciones no permanecen como alerta de conciliación pendiente.

SHAs principales: `3617f474`, `1689ca64`, `49820b73` y `337ed39f`.

### FI02

- Consulta detallada sobre `NXR Operation Effect`.
- Fuente, categoría económica y centro de costo se aplican antes de agregar importes.
- Una operación multifuente devuelve únicamente la porción asignada al filtro seleccionado.
- Pantalla y exportación usan la misma consulta.

SHAs principales: `6d776d05362299266d50aaa95ad868e37beb561d`, `2702cdbd2a48d7dcbc481bbc6a060f1420719a5e`, `19c8c138c13b1b3fa095bb7f3797f4a34115093a`, `99c20b2e94512956540ec7f4c9a1f2b290ad6d67` y `9ea1d020b09d6ad909581e1a2722d059b7b7d339`.

### Exportaciones

- Excel/PDF permanecen server-side.
- Se valida `export_reports` y acceso al proyecto.
- FI01, FI02 y CO01 superiores al límite se rechazan; no se truncan silenciosamente.

SHAs principales: `2598a66`, `bd67e8cb` y `0384aa6`.

### Cierre semanal

- Motor actualizado a `nexora-analytics-v2`.
- Reservas y obligaciones financieras se calculan al corte desde el Libro Central.
- Presupuesto aprobado usa la última versión vigente por fecha efectiva.
- Comprometido y ejecutado presupuestario se calculan con efectos hasta la fecha de cierre.
- La fotografía declara expresamente la base histórica y las limitaciones contractuales/documentales.
- Se conservan número de 12 dígitos, idempotencia, hash, auditoría, inmutabilidad, período único y corrección enlazada.

SHAs principales: `b2e0686b8819a79e2f2b8e071fef112cb154845b`, `724a3e915b323f21ad2aa7ebb3ff4df37e99e98f` y `efdfd6ab92d1053db304f74269276da82c786b43`.

### Documentación

- Especificación trazable actualizada sin lenguaje de reconstrucción funcional.
- Reglas, estados, efectos, permisos, pruebas positivas/negativas y limitaciones documentadas.

SHA: `c7926153dffebdb272204ccaeaab0e7a50d25518`.

## Evidencia disponible

- Código publicado en la rama oficial del PR #19.
- Commits semánticos publicados.
- Pruebas contractuales nuevas para dashboard, reversos, archivo, exportación, FI02 y cierre histórico.
- Prueba de integración MariaDB ampliada para permisos, conciliación, anulación, fecha canónica, asignaciones multifuente, cierre, archivo y exportación.
- Validaciones sintácticas locales puntuales de Python y JavaScript ejecutadas durante la edición.

Estas evidencias no sustituyen CI, instalación/migración limpia ni pruebas reales de navegador.

## Bloqueo de certificación

Los workflows consultados en varios SHA del PR terminan antes de publicar pasos, logs o artefactos. Los jobs regresan `steps=[]` y el endpoint de logs no entrega contenido accionable. Mientras GitHub Actions no ejecute y publique evidencia, el bloque permanece **NO DEMOSTRADO**.

No se declara que la incidencia sea causada por el código ni por la plataforma hasta obtener logs verificables.

## Pendiente

- verificar workflows sobre el HEAD vigente después de este registro;
- corregir cualquier fallo que produzca pasos o logs accionables;
- ejecutar instalación y migración Frappe/MariaDB sobre el mismo SHA;
- ejecutar pruebas contractuales e integración completas;
- validar escritorio Chromium, iPhone WebKit y PWA;
- consolidar el resumen ejecutivo para que todos los filtros detallados compartan el mismo adaptador analítico;
- revisar rendimiento con volúmenes cercanos a los límites;
- mantener el PR en borrador hasta obtener todas las validaciones aplicables en verde.

## Limitación conocida y declarada

El cierre v2 calcula fondos, reservas, presupuesto y avance físico al corte. El estado contractual y la conciliación documental reflejan el estado vigente al generar la fotografía porque todavía no existe un historial canónico completo de todas las transiciones y adendas. No se presenta esta limitación como resuelta.

## Siguiente acción exacta

1. Verificar el HEAD remoto y los workflows del nuevo SHA.
2. Revisar pasos, logs y artefactos disponibles.
3. Corregir únicamente fallos accionables sobre la misma rama y PR.
4. Ejecutar el bloque de consolidación de filtros del resumen ejecutivo.
5. Actualizar este registro con el primer SHA que complete todas las validaciones aplicables; solo entonces cambiar el estado a **IMPLEMENTADO Y VALIDADO**.
