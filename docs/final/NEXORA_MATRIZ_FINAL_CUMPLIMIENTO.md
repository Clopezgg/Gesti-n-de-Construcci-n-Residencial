# NEXORA — Matriz final de cumplimiento

Esta matriz resume los criterios de aceptación final. La evidencia detallada de los 166 requisitos permanece en `docs/nexora/MATRIZ_REQUISITOS.md` y `EXECUTION_STATE.md`.

| Área | Estado exigido | Evidencia automática |
|---|---|---|
| Producto principal NEXORA | CUMPLIDO Y DEMOSTRADO | Dashboard canónico, home de Desk, navegación global y prueba `test_dashboard_contract.py` |
| Fondos, ingresos y remesas | CUMPLIDO Y DEMOSTRADO | `financial/service.py`, página `nexora-finance`, previsualización, idempotencia y efectos canónicos |
| Gastos, pagos y centros de costo | CUMPLIDO Y DEMOSTRADO | Operaciones centrales, categorías, distribuciones analíticas, permisos y Libro Central |
| Contratos y contratistas | CUMPLIDO Y DEMOSTRADO | Servicios, DocTypes, expediente, estimaciones, pagos, retenciones y pruebas |
| Proveedores y compras | CUMPLIDO Y DEMOSTRADO | Entidades canónicas, solicitudes, cotizaciones, órdenes, recepciones y pruebas |
| Inventario y kardex | CUMPLIDO Y DEMOSTRADO | Servicios de inventario, movimientos, bloqueo negativo y trazabilidad |
| Presupuesto y compromisos | CUMPLIDO Y DEMOSTRADO | Presupuesto versionado, reservas, ejecución, liberación y reportes |
| Avance y evidencias | CUMPLIDO Y DEMOSTRADO | Registros de avance, galería, evidencia privada y revisión |
| Reportes y estados de cuenta | CUMPLIDO Y DEMOSTRADO | Reportes por fuente/entidad/contrato, costos y conciliación |
| Usuarios, roles y permisos | CUMPLIDO Y DEMOSTRADO | Fixtures, `require_action`, pruebas negativas y segregación |
| Escritorio, tableta, iPhone y PWA (Cap. 54) | CUMPLIDO Y DEMOSTRADO — recorrido completo en las tres superficies sobre `main` | Ejecución 31032214468 en `c96ced6a`: job `Frappe real · escritorio · tableta · iPhone · PWA` en verde con las trece etapas —panel, ingreso, gasto, búsqueda universal, corrección auditada, reportes, **cierre semanal**, diez rutas, manifiesto, PWA, responsive, tiempo real y ausencia de errores— en `desktop-chromium`, `ipad-gen7-webkit` e `iphone-13-webkit`. El paso «Repetir la causa del fallo» quedó *skipped* (`if: failure()`), que es la prueba de que no hubo avería |
| Instalación y migración | CUMPLIDO Y DEMOSTRADO solo con CI verde | Job de instalación, desinstalación, reinstalación, migración y rollback |
| Persistencia, backup y restore | CUMPLIDO Y DEMOSTRADO solo con CI verde | Workflows de runtime, utilidades de backup y guía operativa |
| Seguridad y calidad | CUMPLIDO Y DEMOSTRADO solo con CI verde | Validación de producción, linters, Semgrep y pruebas contractuales |
| Paquete final | CUMPLIDO Y DEMOSTRADO solo con CI verde | Workflow `NEXORA final acceptance and delivery`, ZIP y SHA-256 |
| Despliegue productivo exacto | BLOQUEADO EXTERNAMENTE hasta verificar plataforma | Debe compararse el SHA desplegado con el SHA final aprobado de `main` |

## Regla de cierre

Un renglón condicionado a CI no puede certificarse con una afirmación manual. Un job fallido cambia automáticamente su estado a **INCUMPLIDO** hasta corregir la causa raíz y aprobar el mismo SHA.

El despliegue productivo no se declara demostrado únicamente por existir Docker/Compose o una URL. Debe comprobarse el SHA que realmente ejecuta la plataforma, su salud, persistencia y un recorrido funcional controlado.
