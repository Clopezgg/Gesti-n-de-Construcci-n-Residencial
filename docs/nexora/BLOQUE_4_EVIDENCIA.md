# NEXORA — Bloque 4: inmutabilidad y evidencia verificable

## Estado

- Rama: `nexora-continuidad-total`
- PR apilado: `#12`
- Base certificada de Bloques 0–3: `83305b6e2bd897e4084d0ae694e94834e2622590`
- SHA funcional certificado del Bloque 4: `0005b44f19d1483e249e01928de7228b9270ac08`
- Estado: **IMPLEMENTADO Y VALIDADO**.
- Infraestructura externa utilizada: **NO**.
- Datos históricos migrados: **NO**.

## Requisitos propietarios

| Requisito | Estado | Implementación y evidencia |
|---|---|---|
| `NXR-LCO-0007` — Inmutabilidad del ejecutado | **IMPLEMENTADO Y VALIDADO** | Máquina de estados de `NXR Operation`, protección de campos de negocio, eliminación rechazada y corrección exclusivamente mediante documentos compensatorios; prueba contractual y runtime MariaDB de edición y eliminación rechazadas. |
| `NXR-DOC-0004` — Artefacto verificable de evidencia WhatsApp | **IMPLEMENTADO Y VALIDADO** | DocType `NXR Evidence`, archivo privado, SHA-256, versión, sustitución, revisión humana, permisos, auditoría e idempotencia; pruebas puras, contractuales y runtime Frappe/MariaDB. |

## Modelo canónico

`NXR Evidence` conserva:

- número global de 12 dígitos;
- proyecto, tipo y canal;
- archivo privado, nombre, MIME, tamaño y SHA-256;
- fecha del mensaje o comprobante;
- emisor o autorizador y referencia externa;
- versión y evidencia sustituida;
- actor y fecha de carga;
- actor, fecha y notas de revisión;
- idempotencia, huella del payload y correlación.

El documento no admite creación directa por permisos DocType, edición de su contenido canónico ni eliminación. Toda escritura pasa por servicios NEXORA transaccionales y auditados.

## Máquina de estados

```text
Uploaded -> Validated
Uploaded -> Rejected
Validated -> Superseded
Rejected -> Superseded
```

No se permite regresar una evidencia revisada a `Uploaded`. La sustitución crea un documento nuevo, incrementa la versión y conserva el original.

## Política aplicada

Conforme a `DEC-017`:

- depósito y transferencia: evidencia obligatoria;
- efectivo hasta L2,000.00: opcional salvo regla especial;
- efectivo desde L2,000.01: evidencia obligatoria;
- regalos, donaciones, contribuciones y pagos especiales: autorización externa obligatoria;
- devolución real y sustitución documental: evidencia obligatoria por perfil.

Una autorización especial exige un expediente `NXR Evidence` validado con canal `WhatsApp`, autorizador, fecha, referencia externa y archivo privado íntegro. Una ruta privada heredada sigue siendo compatible para comprobantes ordinarios, pero no sustituye el expediente canónico cuando se exige autorización externa.

## Servicios y permisos

### `register_evidence`

- operador financiero o superior;
- valida proyecto, tipo, canal y archivo privado;
- límite de 15 MB;
- admite JPEG, PNG, WebP, PDF y texto;
- calcula SHA-256 en servidor;
- asigna número de 12 dígitos;
- registra idempotencia y auditoría;
- crea versión inicial o sustituta;
- rollback total ante error.

### `review_evidence`

- gerente financiero, administrador NEXORA o System Manager;
- decisiones `Validated` o `Rejected`;
- solo procesa evidencias `Uploaded`;
- conserva revisor, fecha y notas;
- idempotencia, auditoría y rollback.

### `list_evidence`

- consulta autorizada por servidor;
- filtro opcional por proyecto;
- máximo de 200 registros;
- no expone contenido binario ni secretos.

## Interfaz real

La página `/app/nexora-evidence` permite registrar, consultar, revisar y sustituir expedientes. Muestra número, estado, versión y SHA-256. El workspace NEXORA enlaza la página y la lista canónica `NXR Evidence`.

## Seguridad

- archivos canónicos privados;
- permisos server-side;
- MariaDB transaccional;
- idempotencia y auditoría;
- sin correo real, tokens, credenciales o integraciones externas;
- sin llamadas a WhatsApp: WhatsApp se registra únicamente como origen verificable de un artefacto aportado por el usuario;
- denegación predeterminada para acciones desconocidas o roles insuficientes.

## Pruebas aprobadas

### Puras y contractuales

- política de depósito, transferencia y umbral exacto de efectivo;
- categoría especial y autorización externa;
- transiciones válidas e inválidas;
- SHA-256 determinístico;
- importe negativo rechazado;
- modelo canónico y permisos sin escritura directa;
- operación ejecutada inmutable;
- servicios exportados y UI conectada;
- workflows permanentes para el PR apilado.

### Runtime Frappe/MariaDB

- archivo privado real;
- registro idempotente y auditoría;
- usuario limitado no revisa;
- gerente valida;
- operación especial rechaza evidencia no validada;
- operación especial acepta autorización WhatsApp validada;
- ruta privada no registrada se rechaza para autorización especial;
- sustitución conserva original e incrementa versión;
- edición y eliminación de operación ejecutada rechazadas;
- instalación, migración, desinstalación, reinstalación y rollback;
- concurrencia e idempotencia de datos demostrativos.

## Workflows verdes del SHA funcional

| Workflow | Run ID | Resultado |
|---|---:|---|
| NEXORA governance | `30048885103` | SUCCESS |
| NEXORA app | `30048884907` | SUCCESS |
| NEXORA financial invariants | `30048884988` | SUCCESS |
| Linters | `30048885098` | SUCCESS |
| Semantic Commits | `30048884906` | SUCCESS |
| Documentation Required | `30048884912` | SUCCESS |

Jobs principales:

- App contract: `89346321570`;
- App install/rollback: `89346321627`;
- MariaDB: `89346321685`;
- Semgrep: `89346322109`;
- pre-commit: `89346322125`.

## Artefactos

| Evidencia | Artefacto | Digest |
|---|---:|---|
| Inventario de gobierno | `8580213584` | `sha256:0ad11dece7f4e4793800f822084291f379cb49c947c2ce1d59db3519a03e63d0` |
| Aplicación, instalación y rollback | `8580295286` | `sha256:91fa10ceb0de21455fc1137858bf7594e65ab3403008457ea413de530e54876e` |
| Invariantes financieras y evidencia | `8580329294` | `sha256:dbbd94a965851928b1a9a7df3d6908421abbba77b0f27f6d838ac01fefb2c90d` |
| Pre-commit / Linters | `8580231710` | `sha256:121b7359dd3064cd3355b20ae242f61d3b6bf172fe8aec0f9fb965d9013e0b51` |
| Semgrep | `8580218457` | `sha256:ff3f5444c2c23b580f8d70d6d651704b408d643e5c972aad2c238fa8f8925b46` |

Inventario canónico: `5028` archivos; digest `sha256:0b81daf85908174d4aec869b7a95091d9aa29ea4ef80df025f6b3638dc8f3856`.

## Cierre

El SHA funcional `0005b44f19d1483e249e01928de7228b9270ac08` cumple los criterios de terminado del Bloque 4. El checkpoint documental que contiene este registro debe conservar verdes los mismos seis workflows antes de iniciar el Bloque 5.
