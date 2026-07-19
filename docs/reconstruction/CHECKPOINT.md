# Checkpoint ConstruControl

- Fecha: 2026-07-19 14:12 America/Tegucigalpa
- Pull Request: #9 abierto y en borrador
- Rama: `reconstruccion-definitiva-construcontrol`
- Base de main: `56ad5d9186075b66a89c773bb9c5922329f5687e`
- Cierre del Bloque 4: `dd5067d0453f3104a4dd075754453fc5067ecf00`
- Bloques cerrados: 1, 2, 3 y 4
- Bloque actual: 5 — FI01 fondos, remesas, monedas, comisiones, conciliación y saldos
- Avance global real: 42%
- Implementación de este avance: cálculo canónico único de monto bruto, comisión, neto, moneda, tipo de cambio y neto HNL
- Corrección: los valores cero explícitos ya no se sustituyen accidentalmente por campos heredados y toda conversión usa la misma regla
- Pruebas agregadas: HNL, USD, comisión, monto negativo y tipo de cambio inválido
- Suite anterior aprobada: 119/119
- Suite nueva esperada: 123 pruebas; GitHub Actions pendiente del commit
- main no fue modificado
- PR permanece abierto, DRAFT y sin fusionar
- Siguiente acción: inspeccionar static, linters y runtime; luego consolidar estados y saldos FI01
