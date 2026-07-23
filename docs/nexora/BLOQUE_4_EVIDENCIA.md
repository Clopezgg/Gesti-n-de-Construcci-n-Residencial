# NEXORA — Bloque 4: inmutabilidad y evidencia verificable

## Estado

- Rama: `nexora-continuidad-total`
- PR apilado: `#12`
- Base certificada: `83305b6e2bd897e4084d0ae694e94834e2622590`
- Estado del bloque durante esta revisión: **NO DEMOSTRADO** hasta completar CI Frappe/MariaDB sobre un único SHA.
- Infraestructura externa utilizada: **NO**.
- Datos históricos migrados: **NO**.

## Requisitos propietarios

| Requisito | Estado previo | Implementación trazable | Evidencia exigida para cierre |
|---|---|---|---|
| `NXR-LCO-0007` — las operaciones ejecutadas no se editan ni eliminan | CONFIRMADO | máquina de estados y protección de campos de negocio en `NXR Operation`; eliminación rechazada; corrección solo mediante documentos compensatorios | prueba contractual, prueba runtime de edición y eliminación rechazadas, migración limpia y CI verde |
| `NXR-DOC-0004` — autorización WhatsApp como artefacto verificable | CONFIRMADO | DocType `NXR Evidence`, servicio de carga, SHA-256, archivo privado, versión, sustitución, revisión humana, permisos y auditoría | pruebas puras de política, permisos negativos, idempotencia, revisión, sustitución, operación especial y CI verde |

## Modelo de datos

### NXR Evidence

Documento canónico separado de la operación financiera. Conserva:

- número global de 12 dígitos;
- proyecto;
- tipo de evidencia;
- canal de origen;
- archivo privado;
- nombre, MIME, tamaño y SHA-256 del contenido;
- fecha del mensaje o comprobante;
- emisor o autorizador;
- referencia externa;
- notas;
- versión y evidencia sustituida;
- actor y fecha de carga;
- actor, fecha y notas de revisión;
- idempotencia, huella del payload y correlación.

El documento no admite creación directa por permisos DocType, edición de contenido ni eliminación. Toda escritura pasa por servicios transaccionales NEXORA.

## Máquina de estados

```text
Uploaded -> Validated
Uploaded -> Rejected
Validated -> Superseded
Rejected -> Superseded
```

No se permite regresar una evidencia validada o rechazada a `Uploaded`. Una sustitución crea un documento nuevo, incrementa la versión y conserva el original en estado `Superseded`.

## Política de evidencia

Conforme a `DEC-017`:

- depósito: obligatoria;
- transferencia: obligatoria;
- efectivo hasta L2,000.00: opcional, salvo regla especial;
- efectivo desde L2,000.01: obligatoria;
- regalos, donaciones, contribuciones y pagos especiales: autorización externa obligatoria;
- devolución real y sustitución documental: evidencia obligatoria por perfil.

La autorización externa del Bloque 4 requiere un expediente `NXR Evidence` validado con:

- canal `WhatsApp`;
- autorizador o emisor;
- fecha del mensaje;
- referencia externa;
- archivo privado íntegro y hash SHA-256.

La ruta privada heredada sigue aceptándose para comprobantes ordinarios y correcciones no especiales, preservando la compatibilidad certificada de los Bloques 0–3. No sustituye el expediente canónico cuando la categoría exige autorización externa.

## Servicios

### register_evidence

- permiso: operador financiero o superior;
- valida proyecto, tipo, canal y archivo privado;
- limita tamaño a 15 MB;
- admite JPEG, PNG, WebP, PDF y texto;
- calcula SHA-256 en servidor;
- asigna número de 12 dígitos;
- registra idempotencia y auditoría;
- crea una versión nueva o sustituta;
- revierte toda la transacción ante error.

### review_evidence

- permiso: gerente financiero, administrador NEXORA o System Manager;
- decisiones permitidas: `Validated` o `Rejected`;
- exige que la evidencia esté `Uploaded`;
- conserva revisor, fecha y notas;
- registra idempotencia y auditoría;
- revierte toda la transacción ante error.

### list_evidence

- consulta autorizada por servidor;
- filtro opcional por proyecto;
- máximo de 200 registros por solicitud;
- no expone contenido binario ni secretos.

## Interfaz

La página `/app/nexora-evidence` permite:

- registrar archivo y metadatos;
- visualizar número, estado, versión y SHA-256;
- seleccionar evidencia reciente;
- validar o rechazar según permisos server-side;
- registrar una sustitución sin alterar el original.

El workspace NEXORA contiene accesos a la página de operación y a la lista canónica de expedientes.

## Seguridad

- archivo privado obligatorio para expedientes canónicos;
- MariaDB transaccional e idempotencia;
- sin correo real ni integraciones externas;
- sin tokens o credenciales;
- sin llamadas a WhatsApp;
- WhatsApp se modela únicamente como origen verificable de un artefacto aportado por un usuario;
- auditoría por carga y revisión;
- denegación predeterminada para acciones desconocidas o roles insuficientes.

## Pruebas positivas y negativas

### Puras

- depósito y transferencia obligan evidencia;
- umbral de efectivo exacto;
- categoría especial exige autorización externa;
- transición válida e inválida;
- SHA-256 determinístico;
- importe negativo rechazado.

### Contractuales

- modelo y campos canónicos presentes;
- permisos DocType sin creación, escritura o eliminación directa;
- controlador exige contexto de servicio;
- operación ejecutada contiene máquina e inmutabilidad;
- servicios exportados y UI conectada;
- workflows permanentes reconocen el PR apilado.

### Runtime Frappe/MariaDB

- archivo privado real;
- registro idempotente;
- auditoría creada;
- usuario limitado no revisa;
- gerente valida;
- operación especial rechaza evidencia no validada;
- operación especial acepta autorización WhatsApp validada;
- ruta privada no registrada es rechazada para autorización especial;
- sustitución conserva original e incrementa versión;
- edición de operación ejecutada rechazada;
- eliminación de operación ejecutada rechazada.

## Criterio de terminado

El Bloque 4 solo cambiará a **IMPLEMENTADO Y VALIDADO** cuando:

1. instalación y migración limpia aprueben;
2. pruebas contractuales y puras aprueben;
3. pruebas runtime Frappe/MariaDB aprueben;
4. linters y Semgrep aprueben;
5. los seis workflows obligatorios estén verdes sobre el mismo SHA;
6. el inventario canónico esté actualizado;
7. `EXECUTION_STATE.md` y el PR #12 registren runs, jobs, artefactos y SHA remoto.
