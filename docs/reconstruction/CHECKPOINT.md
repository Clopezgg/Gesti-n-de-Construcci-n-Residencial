# Checkpoint ConstruControl

- Fecha: 2026-07-19 America/Tegucigalpa
- Pull Request: #9 abierto y en borrador
- Rama única: `reconstruccion-definitiva-construcontrol`
- Rama protegida: `main`
- Base observada: `56ad5d9186075b66a89c773bb9c5922329f5687e`
- HEAD previo verificado: `43846b02b8b7d69f0e4c03e56780a4464a47405c`
- Implementación: **100% al publicar el commit que contiene este checkpoint**
- Certificación previa: **33% — Bloques 1–4**
- Estado: **SHA DE IMPLEMENTACIÓN CONGELADO POR EL WORKFLOW DE CERTIFICACIÓN**

## Bloques 1–11

- Bloques 1–4: implementación y certificación publicadas.
- Sprint A — FI01, FI02, PR01 y CO01: implementación completa; Puerta A requerida.
- Bloque 8 — MM01, MM02 y MIGO: implementación completa; Puerta B requerida.
- Bloque 9 — QC01 y CL01: implementación completa; Puerta B requerida.
- Bloque 10 — BI01 y AU01: commit `01ec1389282023b3a53d1cba7d452caeabbda678`; 12/12 pruebas dirigidas.
- Bloque 11 — escritorio, iPhone, móvil y PWA: commit `43846b02b8b7d69f0e4c03e56780a4464a47405c`; 9/9 pruebas dirigidas.

## Bloque 12 — infraestructura y cierre técnico

Estado: **IMPLEMENTACIÓN COMPLETA — PUERTA C PENDIENTE AL MOMENTO DE PUBLICACIÓN**.

Implementado:

- arquitectura productiva única AWS EC2 x86_64 + Coolify + Docker Compose;
- MariaDB 10.6 como base productiva;
- Supabase limitado a origen histórico de migración;
- diez servicios con health check;
- volúmenes persistentes;
- backup local completo con manifiesto, tamaños y SHA-256;
- restauración obligatoria en sitio aislado;
- tres migraciones después del restore;
- smoke test y conciliación de conteos;
- reinicio y redeploy con prueba de persistencia;
- inventario de datos demo sin borrado automático;
- manual oficial único;
- workflow secuencial A → B → C → FINAL → auditoría 1:1.

Pruebas rápidas incluidas:

- Python y compilación;
- Ruff/formato mediante carril rápido;
- Bash;
- YAML/Compose;
- pruebas funcionales del verificador de backup;
- pruebas del clasificador demo;
- contrato de arquitectura;
- contrato secuencial de certificación.

## Certificación agrupada

El archivo `docs/reconstruction/CERTIFICATION_REQUEST.yml` solicita:

1. Puerta A.
2. Puerta B.
3. Puerta C.
4. FINAL.
5. Auditoría independiente 1:1.

El workflow `.github/workflows/construcontrol-full-certification.yml`:

- congela `github.event.pull_request.head.sha`;
- ejecuta las puertas de forma secuencial;
- no cancela una puerta para ocultar fallos;
- no modifica `main`;
- no fusiona el PR;
- publica artifacts por puerta;
- bloquea FINAL hasta que A, B y C aprueben;
- bloquea auditoría hasta que FINAL apruebe.

## Gobierno

- `main` no se modifica.
- PR #9 permanece abierto y en borrador.
- No se crea otra rama ni otro PR.
- No se usa force push.
- No se eliminan respaldos, datos o volúmenes productivos.
- La fusión queda reservada al usuario.
