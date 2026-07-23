# NEXORA — Estado de ejecución

- Última actualización: 2026-07-23
- Repositorio: `Clopezgg/Gesti-n-de-Construcci-n-Residencial`
- Rama técnica única: `nexora-reconstruccion`
- HEAD inicial de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- HEAD actual de `main`: `73c9dadfb81f543e53f45887448fdecbee081850`
- SHA certificado de Bloques 1 y 2: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`
- SHA de código principal del Bloque 3: `ba94e2c39fc1222a5d127120629b0a628c583263`
- SHA de inventario limpio posterior: `c6858286e3aab0297a6bc8769428aab268b6dd56`
- Pull Request único: `#11` — abierto y sin fusionar
- Producción modificada: **NO**
- Migración histórica: **NO**

## Recuperación del Bloque 3

- HEAD remoto heredado: `5715160a425d3729c325f1c74dd8a9f65a34e993`.
- Paquete reconstruido desde `.nexora/block3-transport/part-*` en orden lexicográfico.
- SHA-256 verificado del paquete: `43c440fd174dab4c0f721d428e6aca36a326777a78d2623b5607f9632b321a41`.
- `SHA256SUMS` interno: **APROBADO**.
- Run original inspeccionado una vez: `29979475250`; job `89118121223`.
- Causa del rechazo original: el token del workflow no tenía permiso `workflows` para actualizar `.github/workflows/nexora-financial.yml`.
- Ruta alternativa aplicada sin `force push`, sin reset y sin alterar `main`.

### Commits de recuperación y limpieza

1. `2e843706af63aeefe8cd89cf67c51ac8c4034491` — `ci(nexora): stage block 3 publication without workflow mutation`.
2. `ba94e2c39fc1222a5d127120629b0a628c583263` — `test(nexora): prove central ledger reference invariants`.
3. `d00b991379f5e16628a454bfede57720403c8989` — `ci(nexora): certify central ledger runtime invariants`.
4. `29d4e4f2528d39d18c11c7c4fa6d377f66436bb5` — `chore(nexora): remove temporary block 3 publisher`.
5. `432aa9f7d4d07237b2bee9198a697da4a990a84c` — `chore(nexora): remove temporary block 3 staging`.
6. `6221726549e460ab041048674120055cccd455ac` — `ci(nexora): enforce canonical file inventory freshness`.
7. `aff3d87c24ee33d214f940d93d5dc307c91309d8` — `ci(nexora): publish canonical inventory on branch updates`.
8. `c6858286e3aab0297a6bc8769428aab268b6dd56` — `chore(nexora): refresh repository file inventory`.

### Evidencia de publicación

- Workflow de recuperación: `NEXORA Block 3 publisher`.
- Run ID: `29983835727`.
- Job: `89131265913` — **APROBADO**.
- Validaciones aprobadas antes del commit principal:
  - gobierno NEXORA;
  - contrato de aplicación;
  - validación de modelos financieros;
  - pruebas contractuales;
  - `test_financial_core`;
  - `test_ledger_core`;
  - `test_reference_rules`;
  - 36 pruebas puras dirigidas;
  - `node --check`;
  - `compileall`;
  - `validate_repository.py` con 0 errores sobre el árbol materializado.
- Inventario canónico posterior: 5,015 archivos rastreados.
- Transporte temporal eliminado: **SÍ**.
- Workflow publicador temporal eliminado: **SÍ**.
- Módulos `references.py` y `reference_rules.py` publicados: **SÍ**.
- Pruebas de ledger y referencias publicadas: **SÍ**.

## Certificación runtime de Bloques 1 y 2

### NEXORA app

- Workflow: `NEXORA app`.
- Run ID: `29973917049`.
- SHA: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`.
- Job contractual: `89101582734` — **APROBADO**.
- Job instalación/rollback: `89101582715` — **APROBADO**.
- Artefacto: `8550778391`.
- Digest: `sha256:65d9eec50f163c6c6866d633df5658fee263b3d8d74c99c98481140976cef4e1`.

### NEXORA financial invariants

- Workflow: `NEXORA financial invariants`.
- Run ID: `29973917014`.
- Job MariaDB: `89101582623` — **APROBADO**.
- SHA: `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`.
- Artefacto: `8550776607`.
- Digest: `sha256:6257913ef2480f1d863d8ec98328a58df2e5ae7bf25dda45de628c41705f6dfa`.

## Bloques

### Bloque 0 — TERMINADO Y PUBLICADO

Baseline, 166 requisitos, propietarios, máquinas, controles, decisiones y validador reproducible.

### Bloque 1 — TERMINADO Y VALIDADO

Certificado en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`, run `29973917049`.

### Bloque 2 — TERMINADO Y VALIDADO

Certificado en SHA `e0b8d1edccc13346c3429b8ef22d8bbf8173ce91`, run `29973917014`.

### Bloque 3 — PUBLICADO; CERTIFICACIÓN RUNTIME EN CURSO

- 10 DocTypes canónicos y catálogo oficial de operaciones.
- Efectos atómicos de fondos, reserva, costo, presupuesto, ahorro e inversión.
- Cuenta Máxima tratada como ahorro y no como proveedor.
- Transferencias internas neutrales.
- Anticipos con responsable, fechas, vencimiento y saldo liquidable.
- Devoluciones reales referenciadas, con evidencia y límite recuperable.
- Reclasificaciones sin efectivo, con efectos compensatorios derivados.
- Reversiones referenciadas sin restitución ficticia de fondos.
- Sustitución documental y segregación de funciones.
- Tipo técnico derivado del catálogo y de solo lectura en interfaz.
- Un solo `NXR Operation Effect`; cero escrituras nuevas a `CC Material Ledger`.
- Árbol final sin fragmentos, staging ni workflow publicador.

## Siguiente acción exacta

Ejecutar y revisar los workflows reales del PR #11 sobre el nuevo HEAD documental, registrar run IDs, jobs, artefactos y digests del Bloque 3; después iniciar el Bloque 4 con inmutabilidad de ejecutados y correcciones compensatorias sin modificar el documento original.
