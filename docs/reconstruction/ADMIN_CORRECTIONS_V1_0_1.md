# ConstruControl v1.0.1 — Correcciones administrativas críticas

## Propósito

Esta actualización añade un Centro de Correcciones Administrativas para resolver errores heredados de la migración sin borrar la fuente histórica, sin desactivar las validaciones normales y sin modificar directamente MariaDB mediante SQL manual.

La función está reservada exclusivamente para la cuenta `Administrator`.

## Principios obligatorios

- `ConstruControl Legacy Record` permanece intacto como evidencia del origen.
- `CC Audit Log` y `CC Immutable Audit Event` permanecen inmutables.
- Los gastos, fondos, contratos, cuentas por pagar y proveedores no se eliminan físicamente.
- Los usuarios con historia se archivan o consolidan; no se cambia `owner` ni `modified_by` de documentos anteriores.
- La edición ordinaria mantiene todas las restricciones existentes.
- Cada operación crítica exige vista previa y se ejecuta dentro de una transacción con rollback.
- Los estados derivados de gasto son de solo lectura en el formulario normal.

## Autorización reforzada

1. Iniciar sesión como `Administrator`.
2. Abrir **Mi perfil**.
3. Configurar una clave numérica de corrección de 6 a 12 dígitos.
4. Introducir la contraseña actual de `Administrator` para guardar o rotar la clave.
5. Abrir **Migración y correcciones administrativas**.
6. Autorizar una sesión temporal con la contraseña actual y la clave de corrección.

La clave:

- se guarda únicamente como hash;
- no aparece en el perfil, API, logs ni auditoría;
- no se almacena en `localStorage`, `sessionStorage` ni cookies;
- genera una autorización vinculada a la sesión actual durante diez minutos;
- se bloquea temporalmente después de cinco intentos fallidos;
- puede rotarse desde el perfil.

## Evidencia y motivo

Toda corrección exige un motivo de 12 a 1,000 caracteres.

Cuando existe impacto financiero, la operación exige un archivo privado como evidencia. El sistema rechaza archivos públicos o inexistentes.

Cada auditoría conserva:

- usuario ejecutor;
- fecha y hora;
- identificador de autorización;
- módulo afectado;
- documento afectado;
- estado anterior;
- estado posterior;
- impacto financiero o relacional;
- motivo;
- referencia de evidencia;
- correlación del lote cuando corresponda.

## Operaciones disponibles

### Gastos FI02

- corregir proveedor, proyecto, fase, fuente de fondos o contrato;
- corregir categoría, fecha, subtotal, monto pagado o estado de pago;
- anular un gasto migrado sin pago;
- revertir un pago importado incorrectamente;
- registrar un reembolso real;
- corregir hasta 50 gastos en una sola transacción.

El sistema recalcula la fuente de fondos, el contrato, el proyecto y la cuenta por pagar.

### Proveedores

- seleccionar un proveedor oficial;
- analizar referencias de los duplicados;
- bloquear la ejecución cuando existan enlaces no compatibles;
- reasignar gastos, cuentas por pagar, contratos y enlaces soportados;
- conservar nombres y RTN anteriores como alias;
- deshabilitar y marcar los duplicados como consolidados;
- mantener los registros Supplier existentes para trazabilidad.

### Fondos FI01

Permite corregir, mediante campos permitidos, proyecto, estado, conciliación, moneda, montos, comisión, tasa, institución y referencia. Las validaciones impiden que el fondo quede por debajo de gastos pagados o comprometidos.

### Fases PR01

Permite corregir proyecto, presupuesto, progreso, responsable, fechas y metadatos permitidos. Después recalcula el control del proyecto.

### Contratos CO01

Permite corregir proyecto, fase, proveedor, alcance, modalidad, fechas y valores. Las validaciones impiden que el valor quede por debajo de pagos o compromisos existentes.

### Cuentas por pagar

Reconstruye el registro operativo desde el gasto canónico. Las duplicadas se archivan y quedan sin impacto financiero; no se eliminan.

### Usuarios

- archivar y deshabilitar una cuenta;
- consolidar su acceso en otra cuenta activa;
- copiar permisos de proyecto;
- reasignar responsabilidades operativas soportadas;
- anonimizar únicamente datos de perfil cuando se solicite;
- conservar la cuenta y toda la autoría histórica.

Nunca se procesan `Administrator`, `Guest`, la sesión actual ni la última cuenta administrativa habilitada.

## Corrección masiva

El lote de gastos admite un máximo de 50 registros. Antes de ejecutar muestra:

- cantidad de gastos;
- variación total del gasto reconocido;
- variación del dinero pagado;
- variación del saldo pendiente.

Los bloqueos se adquieren en orden estable. Si una sola corrección falla, todas se revierten.

## Despliegue seguro

1. Crear un backup productivo verificable.
2. Restaurarlo en un entorno aislado.
3. Desplegar el SHA candidato en el entorno aislado.
4. Ejecutar `bench migrate` tres veces.
5. Comprobar que las tres ejecuciones sean idempotentes.
6. Ejecutar pruebas positivas, negativas, permisos y concurrencia.
7. Probar escritorio e iPhone.
8. Verificar que no se haya modificado ningún registro operativo solamente por instalar la actualización.
9. Fusionar el PR únicamente cuando todos los gates estén verdes sobre el mismo SHA.
10. Crear tag `construcontrol-v1.0.1`.
11. Crear un nuevo backup productivo.
12. Desplegar `main` desde Coolify.
13. Ejecutar smoke tests sin activar todavía la clave de corrección.
14. Configurar la clave desde `Administrator`.
15. Probar primero una sola corrección previamente identificada.

## Verificación posterior al despliegue

- login de `Administrator`;
- perfil sin revelar PIN o hash;
- centro visible únicamente para `Administrator`;
- usuario Manager u Operator sin acceso;
- estados derivados de gasto de solo lectura;
- vista previa sin escritura;
- evidencia pública rechazada;
- operación cancelada sin cambios;
- operación ejecutada con auditoría antes/después;
- FI01, FI02, CO01, proyecto y cuenta por pagar conciliados;
- escritorio e iPhone sin desbordamientos;
- logs sin errores 5xx;
- datos históricos intactos.

## Rollback

El rollback del software no debe borrar los campos añadidos ni los eventos de auditoría.

1. Desactivar `Acceso a correcciones críticas` antes del rollback cuando sea posible.
2. Detener nuevas sesiones de corrección.
3. Registrar el SHA y las operaciones ejecutadas.
4. Volver a la imagen anterior en Coolify.
5. Ejecutar `bench migrate` únicamente si la versión anterior lo requiere.
6. Verificar login, dashboard, fondos, gastos, contratos y reportes.
7. No restaurar la base automáticamente cuando las correcciones ya eran válidas.
8. Restaurar el backup previo únicamente ante corrupción comprobada y después de conservar una copia forense de la base actual.

Cada operación individual ya utiliza savepoint y rollback automático. El backup completo se reserva para fallos de despliegue o corrupción externa.

## Restricciones permanentes

- No usar SQL manual para corregir datos.
- No eliminar Legacy Records.
- No editar auditoría.
- No compartir la clave de corrección.
- No dejar una sesión Administrator abierta en un dispositivo ajeno.
- No ejecutar correcciones masivas sin revisar primero el impacto.
- No crear registros sustitutos mientras el registro incorrecto siga teniendo impacto.
