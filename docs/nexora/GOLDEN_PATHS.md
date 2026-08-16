# NEXORA — Golden Paths

Este documento convierte RG-007 en una lista verificable de recorridos críticos. Un
recorrido no se considera certificado solo por existir su UI o sus funciones: debe
atravesar API/servicio, persistencia, permisos, auditoría, idempotencia cuando aplique
y efecto financiero/físico esperado.

## Estado

- Diseñados: 12
- Certificados en runtime real en este entorno: **0**
- Estado global RG-007: **PENDIENTE DE EJECUCIÓN**

## Recorridos

1. **Ingreso de fondos** — registrar remesa/fondo → fuente independiente → saldo → número documental → auditoría.
2. **Gasto financiado** — preview → validación de fuente → Libro Central → efecto financiero → saldo.
3. **Compromiso** — solicitud aprobada → compromiso → reserva → consulta de comprometido/disponible → liberación o ejecución.
4. **Compra completa** — solicitud → cotización → orden → compromiso → recepción → obligación/pago → Libro Central.
5. **Recepción de inventario** — recepción aprobada → bodega obligatoria → movimiento de stock → saldo físico.
6. **Salida de inventario** — solicitud/salida → validación de saldo → movimiento de stock → prohibición de negativo.
7. **Contrato** — contratista → contrato → adenda → estimación → anticipo/pago → retención → auditoría.
8. **Cierre mensual** — período → snapshot → presupuesto/reservas/obligaciones/avance → hash → cierre inmutable → corrección enlazada.
9. **Corrección financiera** — documento original → corrección autorizada → efecto compensatorio → trazabilidad al original.
10. **Evidencia y avance** — operación/avance → evidencia → revisión → vínculo documental → consulta histórica.
11. **Directorio y permisos** — entidad → roles/contactos/compliance → acceso según rol → auditoría de cambios.
12. **Notificación e integración** — evento interno → registro de notificación → entrega/reintento/idempotencia; integraciones externas permanecen NO DEMOSTRADAS hasta prueba real.

## Pruebas negativas obligatorias

- saldo insuficiente;
- compromiso duplicado/idempotencia;
- recepción sin bodega;
- salida que genera saldo negativo;
- operación sin segregación válida;
- evidencia obligatoria ausente;
- corrección sin documento origen;
- cierre mensual duplicado o modificación directa;
- eliminación de operación ejecutada;
- acceso con rol no autorizado;
- integración externa sin credenciales/autorización;
- repetición del mismo request con la misma idempotency key.

## Regla de certificación

Cada recorrido necesita evidencia de código, test positivo, test negativo y, cuando
la dependencia sea Frappe/MariaDB/servicio externo, ejecución de integración/runtime.
Un test contractual no sustituye una prueba de runtime. WhatsApp, SAP, AWS/Coolify,
DNS, secretos y producción siguen siendo dependencias externas y no se elevan a
IMPLEMENTADO Y VALIDADO sin evidencia operacional real.
