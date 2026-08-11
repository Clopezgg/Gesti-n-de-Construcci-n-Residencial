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
| Escritorio, tableta, iPhone y PWA (Cap. 54) | INCUMPLIDO — `panel` corregido y confirmado en verde en los tres perfiles; dos defectos distintos, ya conocidos, siguen bloqueando el recorrido completo | La ejecución 31032214468 en `c96ced6a` (Bloque 18) fue real y verde en su momento, pero el PR #93 (`c513789d`, posterior) rompió la etapa `panel` (`.nxr-dashboard-period` perdió los dos puntos que el recorrido exige) sin que nadie corrigiera esta fila: desde entonces, toda ejecución real conocida de este job (Bloques 24-29, PRs #114/#115/#116/#118×2/#119/#120) falló en `panel` con el mismo mensaje. Corregido en el Bloque 30 (`27b168d0`→`77cfcd84`) restaurando el texto. **Resultado real confirmado (PR #121, run `31526163976`):** `panel` pasó sin fallo en `desktop-chromium`, `ipad-gen7-webkit` e `iphone-13-webkit` — primera vez desde el PR #93. Al dejar de detenerse ahí, el recorrido expuso dos defectos **ya catalogados, no nuevos**, que `panel` venía enmascarando: `operaciones: Guided stage 4 never opened` en `ipad-gen7-webkit` (mismo patrón intermitente del Bloque 26, visto antes en `desktop-chromium`) y el defecto de `NXR-UX-0010` (Bloque 17, PR #102) del campo `project` en `comprobantes`, ahora visible en `iphone-13-webkit`. **Segundo run real sobre el mismo código (run `31527274646`, commit `097025f1` — solo documentación sobre `77cfcd84`, cero cambios de app):** terminó completamente verde en los tres perfiles, sin ninguna etapa fallida — primera vez en toda la misión. Como el código de la aplicación es idéntico entre ambos runs y el resultado cambió, `operaciones`/`comprobantes` quedan confirmados como intermitentes, no deterministas. La fila permanece `INCUMPLIDO` a propósito: no se sube a `CUMPLIDO Y DEMOSTRADO` por un solo run verde cuando el mismo commit ya mostró lo contrario — por la regla de cierre de este documento, solo se certifica con una serie de runs reales consistentemente verdes, no con el más favorable de dos |
| Instalación y migración | CUMPLIDO Y DEMOSTRADO solo con CI verde | Job de instalación, desinstalación, reinstalación, migración y rollback |
| Persistencia, backup y restore | CUMPLIDO Y DEMOSTRADO solo con CI verde | Workflows de runtime, utilidades de backup y guía operativa |
| Seguridad y calidad | CUMPLIDO Y DEMOSTRADO solo con CI verde | Validación de producción, linters, Semgrep y pruebas contractuales |
| Paquete final | CUMPLIDO Y DEMOSTRADO solo con CI verde | Workflow `NEXORA final acceptance and delivery`, ZIP y SHA-256 |
| Despliegue productivo exacto | BLOQUEADO EXTERNAMENTE hasta verificar plataforma | Debe compararse el SHA desplegado con el SHA final aprobado de `main` |

## Regla de cierre

Un renglón condicionado a CI no puede certificarse con una afirmación manual. Un job fallido cambia automáticamente su estado a **INCUMPLIDO** hasta corregir la causa raíz y aprobar el mismo SHA.

El despliegue productivo no se declara demostrado únicamente por existir Docker/Compose o una URL. Debe comprobarse el SHA que realmente ejecuta la plataforma, su salud, persistencia y un recorrido funcional controlado.
