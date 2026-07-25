# NEXORA — Decisiones ejecutables

- Las decisiones provisionales siguientes están autorizadas para los Bloques 0–2.
- Solo se reabren por instrucción expresa o incompatibilidad técnica demostrada.

| ID | Título | Estado | Regla vigente | Requisitos | Bloques |
|---|---|---|---|---|---|
| `DEC-001` | Alcance de la numeración de 12 dígitos | PROVISIONAL EJECUTABLE | Secuencia global, perpetua, numérica, única, no reutilizable y de 12 dígitos. | `NXR-LCO-0002`, `NXR-DOC-0001` | BLOQUE 1 |
| `DEC-002` | Política de sobregiro presupuestario | PROVISIONAL EJECUTABLE | Sobregiro presupuestario bloqueado; sin excepciones en esta etapa. | `NXR-PRE-0004`, `NXR-COM-0008`, `NXR-USR-0004` | BLOQUE 10, BLOQUE 15 |
| `DEC-003` | Momento del costo de materiales | PROVISIONAL EJECUTABLE | Recepción aumenta inventario; consumo reconoce costo mediante Stock Ledger canónico. | `NXR-COM-0006`, `NXR-INV-0004`, `NXR-INV-0007` | BLOQUE 8, BLOQUE 9, BLOQUE 10, BLOQUE 12 |
| `DEC-004` | Clasificación de transferencias y destinos | RESUELTA | B; decisión vigente y no reabrible sin incompatibilidad demostrada. | `NXR-FND-0008`, `NXR-FND-0013`, `NXR-FND-0014`, `NXR-FND-0015` | BLOQUE 2, BLOQUE 3, BLOQUE 12 |
| `DEC-005` | Modelo de anticipos y liquidaciones | PROVISIONAL EJECUTABLE | Anticipo con titular, fecha, responsable, saldo, vencimiento y liquidación; titular vencido requiere autorización reforzada. | `NXR-FND-0009`, `NXR-CON-0005`, `NXR-CIE-0002` | BLOQUE 2, BLOQUE 4, BLOQUE 6, BLOQUE 16 |
| `DEC-006` | Catálogo de retenciones e impuestos | PROVISIONAL EJECUTABLE | Sin cálculo automático de impuestos/retenciones no confirmados; líneas manuales autorizadas y auditadas. | `NXR-CON-0007`, `NXR-CON-0008` | BLOQUE 6, BLOQUE 12, BLOQUE 16 |
| `DEC-007` | Inventario canónico final | RESUELTA | A; DEC-016 define transición, no reabre la fuente canónica final. | `NXR-INV-0001`, `NXR-INV-0007` | BLOQUE 8, BLOQUE 9, BLOQUE 19 |
| `DEC-008` | Segregación de funciones y doble aprobación | PROVISIONAL EJECUTABLE | Solicitante, aprobador y ejecutor separados; autoaprobación prohibida. | `NXR-USR-0004`, `NXR-USR-0007` | BLOQUE 15, BLOQUE 19 |
| `DEC-009` | Inmutabilidad del cierre mensual | RESUELTA | Sin reapertura operativa; NXR-CIE-0004 queda OBSOLETO para uso normal. | `NXR-CIE-0003`, `NXR-CIE-0004`, `NXR-CIE-0008` | BLOQUE 16, BLOQUE 19 |
| `DEC-010` | Contenido del sitio limpio | PROVISIONAL EJECUTABLE | Sitio limpio solo con configuración técnica, HNL, país, roles, administradores y catálogos indispensables. | `NXR-INF-0006`, `NXR-INF-0007` | BLOQUE 0, BLOQUE 20 |
| `DEC-011` | Tratamiento de Cuenta Máxima | RESUELTA | Administrada solo con conciliación; de lo contrario salida externa. Nunca proveedor ni costo. | `NXR-FND-0013`, `NXR-FND-0020` | BLOQUE 2, BLOQUE 12 |
| `DEC-012` | Materiales en contratos de mano de obra | RESUELTA | B; decisión vigente. | `NXR-CON-0011`, `NXR-INV-0003`, `NXR-INV-0009` | BLOQUE 6, BLOQUE 9, BLOQUE 12 |
| `DEC-013` | Estructura técnica de NEXORA | PROVISIONAL EJECUTABLE | Aplicación Frappe NEXORA separada dentro del mismo repositorio, instalada junto con ERPNext. | `NXR-INF-0001`, `NXR-UX-0001`, `NXR-GOV-0001` | BLOQUE 0, BLOQUE 1, BLOQUE 18, BLOQUE 20 |
| `DEC-014` | Sitio limpio, datos iniciales, cutover y producción | PROVISIONAL EJECUTABLE | Sitio/base nuevos; sistema anterior intacto para respaldo y rollback. | `NXR-INF-0006`, `NXR-INF-0007`, `NXR-INF-0008`, `NXR-INF-0009` | BLOQUE 0, BLOQUE 20 |
| `DEC-015` | Taxonomía oficial de correcciones, devoluciones y reversiones | RESUELTA | Aplicar la matriz A–L de PMI-0.3; solo devolución real/restitución comprobada aumenta disponible. | `NXR-CIE-0005`, `NXR-CIE-0006`, `NXR-CIE-0007`, `NXR-CIE-0008`, `NXR-FND-0010` | BLOQUE 3, BLOQUE 4, BLOQUE 16, BLOQUE 19 |
| `DEC-016` | Retirada o adaptación del ledger de inventario ConstruControl | PROVISIONAL EJECUTABLE | Stock Ledger ERPNext canónico; cero nuevas escrituras en CC Material Ledger. | `NXR-INV-0001`, `NXR-INV-0007`, `NXR-INF-0007` | BLOQUE 8, BLOQUE 9, BLOQUE 19, BLOQUE 20 |
| `DEC-017` | Política de evidencia por medio, monto y categoría | RESUELTA | Depósito/transferencia obligatorio; efectivo ≤L2,000 opcional salvo regla especial; ≥L2,000.01 obligatorio; especiales con autorizador, medio, fecha y referencia. | `NXR-LCO-0012`, `NXR-DOC-0004`, `NXR-DOC-0008` | BLOQUE 2, BLOQUE 4, BLOQUE 18, BLOQUE 19 |
| `DEC-018` | Experiencia de alta rápida desde iPhone | RESUELTA | B; operaciones financieras no se ejecutan offline y el servidor recalcula la vista previa. | `NXR-FND-0001`, `NXR-LCO-0001`, `NXR-UX-0003`, `NXR-UX-0007` | BLOQUE 2, BLOQUE 3, BLOQUE 18, BLOQUE 19 |
| `DEC-019` | Propiedad transaccional entre NEXORA y documentos nativos ERPNext | PROVISIONAL EJECUTABLE | NEXORA orquesta Operation, Effects, Allocations y documentos nativos en una sola transacción MariaDB. | `NXR-LCO-0004`, `NXR-LCO-0005`, `NXR-INV-0007`, `NXR-INF-0001` | BLOQUE 1, BLOQUE 3, BLOQUE 8, BLOQUE 9, BLOQUE 19 |
