# NEXORA — Catálogo de controles y pruebas comunes

- Controles: 32.
- Pruebas comunes: 9.
- Los permisos se aplican en servidor y la denegación es el valor predeterminado.

| ID | Objetivo | Condiciones / alcance | Evidencia o prueba |
|---|---|---|---|
| `CTL-PERM-001` | Autorizar en servidor por usuario, acción y proyecto; la interfaz nunca sustituye la decisión del servidor. | Usuario autenticado, rol vigente, proyecto permitido y acción explícita. | Respuesta del servidor, evento de auditoría y consulta posterior sin cambios. |
| `CTL-PERM-002` | Separar preparación, aprobación y ejecución en operaciones materiales. | Aplica cuando el umbral o tipo de operación exija maker-checker. | Identidades de preparador, aprobador y ejecutor en la línea de tiempo. |
| `CTL-PERM-003` | Restringir datos personales, cuentas, comprobantes y archivos privados. | Dato clasificado sensible o archivo privado. | Log de acceso sensible con actor, recurso y resultado. |
| `CTL-PERM-004` | Controlar poderes excepcionales de Administrator sin permitir edición silenciosa de historia. | Autorización superior, respaldo verificable, motivo, alcance y rollback documentados. | Expediente de intervención, respaldo, diff, validación y cierre. |
| `CTL-AUD-001` | Conservar un evento inmutable por cambio relevante. | Creación, transición, rechazo, fallo, sustitución o acceso sensible. | Evento consultable y reconciliado con el documento. |
| `CTL-AUD-002` | Registrar antes/después de todas las dimensiones financieras afectadas. | Operación o corrección con efecto financiero o dimensional. | Detalle de efectos y conciliación de sumas. |
| `CTL-AUD-003` | Mantener linaje entre NEXORA, ERPNext y evidencia. | Se crea o consume más de un documento técnico. | Grafo de referencias sin enlaces huérfanos. |
| `CTL-EVI-001` | Proteger evidencia privada con hash, versión y conservación del original. | Archivo cargado o generado. | Hashes, tamaños, autor y vínculo de sustitución. |
| `CTL-EVI-002` | Aplicar la política exacta por medio, monto y categoría. | Depósito y transferencia: obligatorio; efectivo ≤ L2,000 opcional salvo regla especial; efectivo ≥ L2,000.01 obligatorio. | Resultado de política y documento exigido u omisión permitida. |
| `CTL-EVI-003` | Validar una autorización externa, incluida WhatsApp, sin confundirla con el pago. | La categoría o excepción exige autorización externa. | Artefacto, metadatos y revisión humana. |
| `CTL-IDEMP-001` | Evitar duplicados por reintentos, doble toque móvil o respuestas tardías. | Solicitud con efecto persistente. | Clave, primera respuesta y reintentos asociados. |
| `CTL-CONC-001` | Impedir sobregiro y resultados parciales al asignar fondos. | Dos transacciones compiten por una o varias fuentes. | Orden de locks, resultado de ambas transacciones y saldo final. |
| `CTL-CONC-002` | Proteger límites contractuales, presupuestarios y existencias. | Operaciones concurrentes consumen el mismo límite o cantidad. | Valores leídos bajo lock y decisión de cada transacción. |
| `CTL-REV-001` | Aplicar la taxonomía A–L sin editar documentos ejecutados. | Se corrige una operación o evidencia. | Original, corrección, tipo, motivo, aprobación y efectos. |
| `CTL-REV-002` | Evitar restituciones ficticias de fondos. | La corrección pretende aumentar disponible. | Ingreso conciliado y vínculo a la operación original. |
| `CTL-FND-001` | Mantener saldo individual y no negativo por fuente. | Cualquier cálculo de disponible o reservado. | Saldos antes/después por fuente. |
| `CTL-FND-002` | Mostrar vista previa completa antes de ejecutar. | Antes de transición a APROBADA o EJECUTADA. | Snapshot de vista previa aprobado y fingerprint. |
| `CTL-FND-003` | Garantizar propiedad transaccional entre NEXORA y documentos nativos. | Una intención crea documentos en ambos modelos. | Log transaccional y ausencia de huérfanos. |
| `CTL-DOC-001` | Asignar un número único de 12 dígitos sin reutilización. | Emisión de documento sujeto a numeración. | Secuencia y documento asignado. |
| `CTL-DOC-002` | Conservar originales y versiones sustitutas. | Documento ya emitido o ejecutado. | Relación original–sustituto/compensatorio. |
| `CTL-DATA-001` | Evitar dos fuentes de verdad para el mismo saldo, costo o inventario. | Persistencia o consulta de una dimensión financiera. | Mapa de propiedad y conciliación. |
| `CTL-DATA-002` | Impedir migración de registros históricos al sitio NEXORA. | Preparación de sitio, migraciones y cutover. | Conteos cero y lista de migraciones ejecutadas. |
| `CTL-UX-001` | Captura progresiva desde iPhone con campos dinámicos pertinentes. | Viewport móvil y flujo de captura. | Prueba en iPhone/PWA y payload validado por servidor. |
| `CTL-SEC-001` | Proteger credenciales e integraciones. | Secreto o endpoint externo. | Configuración enmascarada y resultado real. |
| `CTL-SEC-002` | Evitar caché o exposición pública de datos privados en PWA. | Service worker o acceso offline. | Lista de caché y prueba de aislamiento. |
| `CTL-REP-001` | Conciliar reportes y estados de cuenta con fuentes canónicas. | Consulta o exportación. | Hash de parámetros, conteos y conciliación. |
| `CTL-CLOSE-001` | Mantener cierre mensual inmutable sin reapertura operativa. | Período en estado CERRADO. | Cierre, intento rechazado y documento posterior. |
| `CTL-COST-001` | Separar salida financiera de costo de construcción. | Operación con salida o consumo. | Efectos por dimensión y categoría. |
| `CTL-BUD-001` | Distinguir presupuesto, compromiso y ejecución. | Operación afecta partida. | Disponible, comprometido y ejecutado antes/después. |
| `CTL-CON-001` | Bloquear sobrepago y preservar valor vigente por adendas. | Cálculo de saldo contractual. | Cuenta contractual cronológica. |
| `CTL-INV-001` | Usar Stock Ledger Entry como inventario canónico y evitar doble escritura/valoración. | Movimiento físico o valoración. | Stock Ledger Entry y reporte de equivalencia. |
| `CTL-DEP-001` | Controlar sitio limpio, cutover y rollback. | Cambio de entorno o versión. | Runbook, manifests, logs y validación posterior. |
| `TST-STATE-001` | Rechazar toda transición cuyo origen o destino no pertenezca a la máquina referenciada. | Carga del catálogo y ejecución de prueba de transición. | Reporte de transición inválida con máquina y requisito. |
| `TST-PERM-001` | Comprobar denegación real de servidor. | Usuario sin acción o proyecto. | Código de respuesta y consulta posterior. |
| `TST-IDEMP-001` | Demostrar un solo efecto ante reintento. | Misma clave e igual payload. | IDs, clave y saldo. |
| `TST-CONC-001` | Demostrar serialización de límites. | Dos transacciones conflictivas. | Trazas y estado final. |
| `TST-ROLLBACK-001` | Demostrar rollback total ante fallo intermedio. | Fallo inyectado después de una escritura parcial. | Snapshot antes/después y error correlacionado. |
| `TST-RECON-001` | Verificar igualdad entre libro, subledger y reporte. | Dataset de prueba cerrado. | Tabla de conciliación. |
| `TST-MOBILE-001` | Verificar captura progresiva, accesibilidad y prevención de doble toque. | Viewport móvil y red lenta/intermitente. | Video/capturas, payload y documento resultante. |
| `TST-RESTORE-001` | Verificar restauración aislada y rollback. | Copia verificable disponible. | Manifiesto, logs y reporte. |
| `TST-SEM-001` | Detectar prosa particular duplicada o máquinas incompatibles. | Antes de empaquetar. | Grupos detectados y resultado final. |
